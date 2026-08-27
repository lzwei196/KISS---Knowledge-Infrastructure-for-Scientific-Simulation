# Windows installer

Build the Python 3.11 one-folder application first, then compile the installer:

```powershell
ISCC.exe /DAppVersion=0.6.46 `
  "/DSourceDir=D:\path\to\GeoForge Desktop 0.6.46 Windows" `
  "/DOutputDir=D:\path\to\installer-output" `
  installer\GeoForgeDesktopWindows.iss
```

The installer is per-user (`%LOCALAPPDATA%\Programs\GeoForge Desktop`), so the
end user does not need administrator rights. It installs the complete PyInstaller
runtime directory; the executable must never be separated from `_internal`.
