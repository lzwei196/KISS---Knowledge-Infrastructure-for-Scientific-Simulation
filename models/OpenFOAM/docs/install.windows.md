# OpenFOAM: Windows installation experience

This record is specific to Windows. Use the recipe for the current operating system; preserve macOS and Linux experience separately.

Latest recorded attempt: **needs-user** (2026-09-05T01:34:35+08:00; 100.3 seconds).
Provider: DeepSeek through GeoForge's installation-only HTTP/agent workflow; this was not a manual GUI click-through.

Independent installation check:  of the attempt. I'll leave a note but not fight for deletion since no deletion tool exists. Let me verify the tree integrity and record the definitive environment blockers.

Let me now produce the structured setup request — this is the mandated action when a missing shared/system toolchain + protected environment requires a person. This is precisely option severity for an installation-only test where native Windows cannot host OpenFOAM-dev at all.

Let me create the structured setup request with clear, actionable options for the human.

First, let me update the project progress.
`> report_project_progress(stage='software', status='failed', summary='OpenFOAM-dev (9,257 C++ files, POSIX)`
Now let me create the structured setup request. This is the sanctioned path: the missing/runtime toolchain (a POSIX Linux environment capable of running the official OpenFOAM binaries) is a system-level resource that only a human can provide by either (a) installing WSL with Ubuntu plus OpenFOAM, or (b) making a prebuilt Linux OpenFOAM container/files available, or (c) pointing at a Linux host. Each requires system privilege/protected resource access outside the sandbox.

Let me build the most actionable request.
`> request_user_action(kind='choice', title='OpenFOAM needs a POSIX/Linux runtime that this Windows san)`
I have escalated via a structured setup request, which is the correct and mandated disposition for this test. Let me verify the workspace is left in a clean, honest state and summarize.

Let me confirm what remains in the workspace root (the throwaway scratch files and the genuine source tree).
`> list_work_files(subdir='OpenFOAM-dev')`

setup agent failed: FileNotFoundError: [WinError 3] 系统找不到指定的路径。: 'D:\\BaiduNetdiskDownload\\kiss-source-v0.6.9-windows\\kiss\\_stress_deepseek_windows_0652_install_only\\installs\\OpenFOAM\\OpenFOAM-dev\\applications\\modules\\multiphaseEuler\\momentumTransportModels\\kineticTheoryModels\\frictionalStressModel\\JohnsonJacksonSchaeffer'


This is an unresolved attempt, not proof that Windows cannot support the model. A missing dependency or executable path still needs diagnosis before assigning a user action.

Last agent request category: `choice`.



## Next installation

Read this KI's SKILL.md, diagnostics and upstream installation documentation. No reviewed Windows-specific recipe has been embedded yet. Reproduce the real software and record its source revision, local dependencies, executable path and independent check before promoting a new recipe to observed.

## Verification scope

The recorded classification covers software installation and its startup/import probe. It does not establish successful basin/site simulation, scientific validity, available forcing/observations, or calibration readiness. Installation files can be cleaned after testing; retain this record and the test logs.
