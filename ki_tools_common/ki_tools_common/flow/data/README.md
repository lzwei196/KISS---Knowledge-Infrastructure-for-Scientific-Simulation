# flow/data — the planner's data, shipped with the desktop

Empty in the server checkout on purpose: on the server `DataRoots.server()` reads the real
`/mnt/disk1/Hydrocraft_server/ata-kdt/{cards,couplings,forcing_providers}` and
`artifacts/coupling_matrix_v2.yaml`. The desktop build fills this directory with
`python -m ki_tools_common.flow.build_data --dest <here>` (copies cards/*_ata_card.yaml,
couplings/coupling_config_*.yaml + couple_*.py, forcing_providers/*.yaml,
obtain_maps/_schema.md, coupling_matrix_v2.yaml — ≈3.6 MB) and then `DataRoots.bundled()`
points here (plan v3 map A8).
