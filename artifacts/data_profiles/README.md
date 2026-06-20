# DataProfile Records

Store append-only profiling snapshots as Git-tracked JSON mirrors.

Recommended naming:

- `<dataset-name>_<method>_<version>.json`

Each record should align with `schemas.artifacts.DataProfile` and should reference exactly one `dataset_id`.

These files are reviewable metadata mirrors. The runtime repository layer can also persist the same artifact contract in the local operational store.
