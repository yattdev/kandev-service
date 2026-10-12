#!/usr/bin/env python3
"""Offline preservation evidence analysis; never changes or accepts a candidate.

Complete reconstructed maps must reproduce the externally pinned transfer
hashes before any delta is attributed. Partial history remains explicitly
unproven. No filesystem traversal, database, provider or correction operation
is exposed by this command.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


COLLECTIONS = ('git_metadata_sha256', 'shared_inventory_sha256')
IDENTITY = ('task', 'workspace', 'repo', 'original', 'original_head', 'head',
            'base', 'branch', 'slot', 'successor', 'successor_execution')
HEX = re.compile(r'[0-9a-f]{64}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def hash_value(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def absolute(path):
    require(isinstance(path, str) and path.startswith('/'), 'absolute entry path required')
    require(str(PurePosixPath(path)) == path and '..' not in PurePosixPath(path).parts,
            'noncanonical entry path')
    return path


def entry_valid(collection, value):
    if collection == 'git_metadata_sha256':
        require(value is None or hash_value(value), 'metadata entry must be a digest or null')
    else:
        require(isinstance(value, list) and len(value) == 4
                and all(type(item) is int and item >= 0 for item in value),
                'inventory entry must contain exact size, mtime_ns, mode and inode')


def prospective_manifest(identity, entries):
    """Package maps retained by a future reviewed snapshot, without reading paths.

    Retain these exact maps *before* hashing them in original_snapshot. A new
    manifest cannot fill an old receipt's missing baseline retroactively.
    """
    require(set(identity) == set(IDENTITY), 'manifest identity fields differ')
    require(set(entries) == set(COLLECTIONS), 'complete collection maps required')
    for collection, mapping in entries.items():
        require(isinstance(mapping, dict), 'collection map required')
        for path, value in mapping.items():
            absolute(path)
            entry_valid(collection, value)
    return dict(schema=1, identity=identity, entries=entries,
                aggregates={name: sha(entries[name]) for name in COLLECTIONS})


def checked_manifest(manifest, identity, expected):
    require(isinstance(manifest, dict) and manifest.get('schema') == 1,
            'versioned per-entry manifest required')
    rebuilt = prospective_manifest(manifest['identity'], manifest['entries'])
    require(rebuilt['identity'] == identity, 'manifest ownership/incarnation differs')
    require(rebuilt == manifest, 'manifest aggregate or schema differs')
    for name in COLLECTIONS:
        require(hash_value(expected.get(name)), 'pinned aggregate required')
        require(manifest['aggregates'][name] == expected[name],
                name + ': reconstructed entries do not reproduce pinned aggregate')
    return manifest['entries']


def scoped(path, collection, transfer, admin):
    common = absolute(transfer['binding']['source']) + '/.git'
    original = absolute(transfer['original'])
    absolute(path)
    if collection == 'shared_inventory_sha256':
        require(path.startswith(common + '/') and not path.startswith(common + '/worktrees/'),
                'inventory entry outside original aggregate scope')
    else:
        require(path == original + '/.git' or path in (common + '/config', common + '/HEAD', common + '/packed-refs')
                or path.startswith(common + '/refs/') or path.startswith(admin + '/'),
                'metadata entry outside exact original administration/shared refs')


def analyze(transfer, pinned_digest, evidence):
    require(hash_value(pinned_digest) and sha(transfer) == pinned_digest,
            'externally pinned transfer digest differs')
    require(transfer['operation'] == 'transfer', 'transfer receipt required')
    identity = {key: transfer[key] for key in IDENTITY}
    require(evidence.get('schema') == 1 and evidence['identity'] == identity,
            'evidence ownership/incarnation differs')
    observed = evidence['recorded_observed']
    require(set(observed) == set(COLLECTIONS) and all(hash_value(v) for v in observed.values()),
            'recorded diagnostic aggregates required')
    require(isinstance(evidence.get('unknowns', []), list), 'explicit unknown predicates must be a list')
    report = dict(schema=1, status='blocked', transfer=transfer['receipt'],
                  transfer_sha256=pinned_digest, evidence_sha256=sha(evidence),
                  identity=identity, source_access_granted=False, correction_issued=False,
                  aggregates={name: dict(pinned=transfer['preservation'][name], observed=observed[name])
                              for name in COLLECTIONS},
                  historical_entries=[], blockers=list(evidence.get('unknowns', [])), deltas=[])
    for row in evidence.get('historical_entries', []):
        require(row['collection'] in COLLECTIONS, 'unknown historical collection')
        absolute(row['path'])
        require(hash_value(row['evidence_sha256']), 'historical evidence digest required')
        for side in ('before', 'after'):
            require(isinstance(row[side], dict) and type(row[side]['present']) is bool,
                    'explicit historical presence required')
            if row[side]['present']:
                entry_valid(row['collection'], row[side]['value'])
        # A partial entry is informational; never describe it as aggregate-proven.
        report['historical_entries'].append(dict(**row, aggregate_proven=False))
    incomplete = False
    for side in ('before', 'after'):
        if evidence.get(side) is None:
            incomplete = True
            report['blockers'].append(dict(predicate='complete_' + side + '_manifest',
                                           reason='missing per-entry evidence; history cannot substitute aggregate proof'))
    if incomplete:
        return report
    before = checked_manifest(evidence['before'], identity, transfer['preservation'])
    after = checked_manifest(evidence['after'], identity, observed)
    admin = absolute(evidence['original_admin'])
    common = absolute(transfer['binding']['source']) + '/.git'
    require(admin.startswith(common + '/worktrees/') and '/' not in admin[len(common + '/worktrees/'):],
            'one exact original administration directory required')
    marker = ('gitdir: ' + admin + '\n').encode()
    require(hashlib.sha256(marker).hexdigest() == transfer['preservation']['marker_sha256'],
            'original administration not bound by pinned marker')
    authorizations = evidence.get('authorizations', [])
    for name in COLLECTIONS:
        old, new = before[name], after[name]
        for path in sorted(set(old) | set(new)):
            scoped(path, name, transfer, admin)
            left = dict(present=path in old, value=old.get(path))
            right = dict(present=path in new, value=new.get(path))
            if left == right:
                continue
            delta = dict(collection=name, path=path, before=left, after=right)
            matches = [row for row in authorizations if all(row.get(k) == v for k, v in delta.items())]
            require(len(matches) <= 1, 'ambiguous exact-entry authorization')
            if matches:
                authorization = matches[0]
                require(all(isinstance(authorization.get(k), str) and authorization[k]
                            for k in ('actor', 'operation', 'review_receipt'))
                        and hash_value(authorization.get('evidence_sha256')), 'bounded provenance required')
                delta['authorization'] = {k: authorization[k] for k in
                                          ('actor', 'operation', 'review_receipt', 'evidence_sha256')}
            else:
                delta['authorization'] = None
                report['blockers'].append(dict(predicate='exact_entry_authorization', collection=name, path=path))
            report['deltas'].append(delta)
    if not report['blockers']:
        report['status'] = 'offline_delta_proven'
    return report


def read_json(path):
    require(path.is_file() and not path.is_symlink(), 'regular inert JSON artifact required')
    require(path.stat().st_size <= 32 * 1024 * 1024, 'evidence artifact exceeds bounded size')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transfer', type=Path, required=True)
    parser.add_argument('--transfer-sha256', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(read_json(args.transfer), args.transfer_sha256, read_json(args.evidence))
        print(json.dumps(dict(report_sha256=sha(result), **result), sort_keys=True))
        return 0 if result['status'] == 'offline_delta_proven' else 78
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('preservation evidence blocked: ' + str(error), file=sys.stderr)
        return 78


if __name__ == '__main__':
    sys.exit(main())
