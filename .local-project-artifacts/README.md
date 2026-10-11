This build input contains only optional operator-reviewed `registry.json`.
The private registry is ignored by Git and installed root-owned and read-only
in the image. An absent registry builds an empty registration set.
See [the broker contract](../PROJECT-ARTIFACTS.md) for ownership, schema,
registration review, synthetic acceptance, and the Coordinator/task commands.
Never put artifact bytes, credentials, or source backups in this directory.
