# APEX: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **needs-user** (2026-09-06T13:04:50+08:00; 144.6 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check: APEX runtime/py stack is installed and probe-verified, but the core model is a licence-gated proprietary Windows binary (APEX0806) absent from this workspace. GeoForge/manifest forbids substituting freely-downloadable APEX1501. Please obtain the exact v0806 asset from the Texas A&M AgriLife BREC distribution page and place: APEX0806.exe at <workspace>\ki\reference\APEX0806.exe, and the ex1_RiselTX reference template at <workspace>\ki\examples\ex1_RiselTX\.
After files arrive, re-check ki\reference\APEX0806.exe and ki\examples\ex1_RiselTX\ presence and re-run the venv import probe.

Reported executable: `<workspace>\binaries\APEX\source\repo\Apex.exe`.

This is an unresolved attempt, not proof that Windows cannot support the model. A missing dependency or executable path still needs diagnosis before assigning a user action.

Last agent request category: `download`.
Provide the protected APEX v0806 executable + reference template
APEX runtime/py stack is installed and probe-verified, but the core model is a licence-gated proprietary Windows binary (APEX0806) absent from this workspace. GeoForge/manifest forbids substituting freely-downloadable APEX1501. Please obtain the exact v0806 asset from the Texas A&M AgriLife BREC distribution page and place: APEX0806.exe at <workspace>\ki\reference\APEX0806.exe, and the ex1_RiselTX reference template at <workspace>\ki\examples\ex1_RiselTX\.
After files arrive, re-check ki\reference\APEX0806.exe and ki\examples\ex1_RiselTX\ presence and re-run the venv import probe.

## Recipe and fixes

Read [`../kiss.windows.yaml`](../kiss.windows.yaml) for the executable contract, pinned sources and dependencies. The same recipe is retained in the legacy shared manifest for older GeoForge versions.

Deliberately manual. APEX0806.exe is present on the authoring machine but is
not shipped in the public repository, so no automated path can exist without
redistributing a binary we do not have the right to redistribute.

Obtain APEX0806.exe from the Texas A&M AgriLife BREC APEX distribution page,
and obtain the ex1_RiselTX reference template. GeoForge keeps these protected
assets in the shared APEX KI and automatically reuses them in each session;
do not ask the user to download or copy them again when they are already
present there. If this is a first install, place them at
ki/reference/APEX0806.exe and ki/examples/ex1_RiselTX/. Run the executable
directly on Windows; install Wine only on macOS/Linux hosts.
Do not substitute the freely downloadable APEX1501 executable: this KI's
v0806 input formats, operation codes and documented crop-yield behavior are
not interchangeable with v1501. If the exact v0806 protected asset is not
already present, create a structured licence/download request instead of
installing another APEX version or claiming installation success. If an
official v0806 Windows installer is publicly downloadable without accepting
a new licence, first stage portable 7zr/innoextract inside the workspace and
try a headless extraction of the exact APEX0806.exe payload; a GUI wrapper
alone is not proof that human interaction is required.
APEX writes output next to the exe, so the whole project directory must be
writable. Check diagnostics/ for the fixed-width column traps before parsing
any output — they are the most common source of silently wrong results.

## Additional evidence or limitation

APEX0806 and its required example/template files are protected downloads. A different APEX release must not be substituted merely to pass verification.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
