GeoForge Desktop — 127 Earth-system models with their KISS Knowledge
Infrastructures, driven by the GeoForge agent.

## What is new in v0.6.50

- The KI harness now has a real plan → user approval → execute → verify gate.
  Downloads and model tools remain unavailable until the recorded data inventory
  and plan are approved; approved runs produce validation receipts.
- Harness and Flow are frozen as importable code. Startup and CI verify all nine
  Flow modules, including the modules that decide tool trust and build data.
- The internal `GEOFORGE_INTAKE` control record is consumed but no longer appears
  in chat.
- Localhost write endpoints require a random SameSite token and matching local
  origin. API keys and proxy settings are saved atomically with user-only access.
- Shared NetCDF helpers correctly handle descending axes, 0–360 longitude and
  antimeridian windows, reproject basin vectors, and reject empty or all-missing
  selections instead of returning plausible bad data.
- KI Observatory, evidence-graded Agent activity, provider-specific proxy routes,
  selectable existing installations and portable CRHM/Alpine3D/WRF-Hydro setup
  are included in the same release.
- macOS, Windows, Linux and CLI packages use one version source. See
  `release-manifest.json` for the machine-readable update contract and
  `DESKTOP_CHANGELOG.md` for bilingual details.

Local validation: 311 Desktop/Flow tests, 98 KI-tool tests, 83 climate/unit tests
and 46 diagnostic checks passed. The frozen application and each platform build
are additionally smoke-tested by the release workflow.

## Install

**macOS** (Apple Silicon — M1 through M4)

    unzip GeoForge-Desktop-macos-arm64.app.zip
    xattr -dr com.apple.quarantine "GeoForge Desktop.app"
    open "GeoForge Desktop.app"

The `xattr` line is required: the build is not signed by Apple, and without it
macOS refuses to open the app.

**Windows** (Intel or AMD, 64-bit)

Unzip `GeoForge-Desktop-windows-x86_64.zip` and double-click
`GeoForge Desktop.exe`. SmartScreen will warn that the publisher is unknown —
**More info** then **Run anyway**. Same cause as the macOS step above.

**Linux** (Intel or AMD, 64-bit, glibc 2.35+)

    tar xzf GeoForge-Desktop-linux-x86_64.tar.gz
    ./GeoForge-Desktop

The UI opens in your default browser rather than its own window: pywebview's
Linux backend needs WebKit2GTK from the system and cannot be frozen into a
portable binary. Same engine, same interface.

Everything is inside the download — all 127 KI packages, the engine, the UI.
No Python installation and no first-run network access.

## Talking to models

Uses an agent CLI you already have (claude / codex / gemini / kimi / qwen) or
an API key via ⚙ Settings (Anthropic / DeepSeek / OpenAI / OpenRouter). Switch
between the two with the CLI / API button in the menu bar; provider and model
are per session.

## Also here

`kiss-<platform>` — the engine as a terminal command (`list`, `info`, `init`,
`verify`, `papers`, `doctor`). `kiss-ki-packages.tar.gz` is the KI content on
its own, for running from source; the desktop downloads already contain it.

## Not in this release

Intel Macs (x86_64) — GitHub's Intel runners have been unavailable for hours
at a time, so that build is best-effort and the release ships without it
rather than waiting. Linux and Windows on ARM are not built. Build from source
for either: `pip install -e kiss/`.
