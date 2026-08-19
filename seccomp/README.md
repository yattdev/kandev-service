# Kandev Codex seccomp profile

`kandev-bwrap.json` is based on Moby's official `seccomp/v0.2.1`
deny-by-default profile:

https://raw.githubusercontent.com/moby/profiles/seccomp/v0.2.1/seccomp/default.json

Upstream SHA-256 before local changes:

`536529b665dd0972c37bfb569f5d4ac8a53592e7b00752bc39ff063ca9864c74`

The local additions are labeled with `Bubblewrap` comments. They permit:

- `clone` only when `CLONE_NEWUSER` is present;
- `unshare` only when `CLONE_NEWUSER` is present;
- `mount`, `umount2`, and `pivot_root`, which remain denied by the kernel until
  the unprivileged process is inside its own user/mount namespace.

Do not replace this with `seccomp=unconfined` or add `CAP_SYS_ADMIN`.
