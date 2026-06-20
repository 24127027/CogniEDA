# Raw Data

Place immutable source snapshots here.

Expected workflow:

1. Copy or export the source file into `data/raw/`.
2. Run `dvc add data/raw/<dataset-file>`.
3. Commit the generated `.dvc` metafile and the related `DatasetAsset` metadata artifact.

Do not overwrite raw files in place. A new source snapshot should create a new dataset version.
