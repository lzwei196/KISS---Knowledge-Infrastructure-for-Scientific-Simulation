# flow/data — the planner's data, shipped with the desktop

This directory contains the snapshot bundled for desktop planning. On the server,
`DataRoots.server()` can instead read the live
`/mnt/disk1/Hydrocraft_server/ata-kdt/{cards,couplings,forcing_providers}` and
`artifacts/coupling_matrix_v2.yaml`. Refresh this directory explicitly with
`python -m ki_tools_common.flow.build_data --dest <here>` (copies cards/*_ata_card.yaml,
couplings/coupling_config_*.yaml + couple_*.py, forcing_providers/*.yaml,
obtain_maps/_schema.md, coupling_matrix_v2.yaml — ≈3.6 MB) and then `DataRoots.bundled()`
points here (plan v3 map A8). `MANIFEST.json` records the source and per-file hashes.

These are catalogue metadata and coupling definitions, not downloaded scientific input
data or proof that a dataset exists on this machine. Server paths in a card are provenance
or lookup hints; the desktop must inventory its actual local paths before marking data ready.
The planner does not execute bundled coupling scripts during planning.
