# DatasetAsset Records

Store one Git-tracked JSON mirror per dataset version.

Recommended naming:

- `<dataset-name>_<version>.json`

Each record should align with `schemas.artifacts.DatasetAsset` and should point to a specific file path or external source location.

These files are reviewable metadata mirrors. The runtime repository layer can also persist the same artifact contract in the local operational store.
