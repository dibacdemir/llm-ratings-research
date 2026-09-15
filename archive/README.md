# archive/

Kept for provenance; nothing here is read by the pipeline.

| folder | what it is |
|---|---|
| `norm_datasets/`, `instructions/` | the published norms as Andrea and Diba prepared them (`<study>_data/<task>.csv`, `<study>_instructions/<task>_i.txt`) |
| `surveyor_norms/`, `mturk_norms/` | the TedLab surveyor and MTurk collections, with their `a_index.csv` provenance and `a_manifest.csv` |
| `pipeline_original/` | the first scoring pipeline (Andrea/Diba); superseded by `pipeline/` |
| `presentation_2026_summer/` | Diba's data-descriptives figures and catalog for the summer presentation, on the earlier 335-task / 6-level organisation; superseded by `metadata/` |
| `scripts_legacy/` | retired scripts, including `build_data_tree.py`, the one-off migration that created `data/` from the three trees on 2026-09-03 |
| `docs_github_pages_attempt/` | an abandoned attempt to publish the pages through GitHub Pages |

`data/<level>/<task>/` was copied from the three trees; each `metadata.json`
records the original path under `original`. `audit/dataset_levels.csv` still
names the original paths in `csv_path` and `instruction_path` (prefix them with
`archive/`).
