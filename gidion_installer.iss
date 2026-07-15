; Gidion installer script (SDLC Phase 5.1/5.3).
; Requires Inno Setup (free): https://jrsoftware.org/isinfo.php
; Build dist\gidion\ with build.bat FIRST, then compile this with Inno
; Setup's ISCC.exe or the Inno Setup Compiler GUI.

#define MyAppName "Gidion"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Cosvexa"
#define MyAppExeName "gidion.exe"

[Setup]
AppId={{B8E1F2A0-4C3D-4E5F-9A1B-2C3D4E5F6A7B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Given the bundle size (5-10GB with models), don't compress twice --
; the model files (gguf/onnx/bin) are already compressed formats, so
; re-compressing them in the installer wastes a lot of build time for
; almost no size reduction.
Compression=lzma2/fast
SolidCompression=no
OutputDir=installer_output
OutputBaseFilename=GidionSetup-{#MyAppVersion}
; Not code-signed -- Windows SmartScreen WILL warn users on first run
; until this is signed with a real certificate. See notes in README.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64

[Files]
; Pulls in everything PyInstaller produced -- app code, Python runtime,
; every collected package, AND the bundled models -- recursively.
Source: "dist\gidion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent

; Deliberately NOT deleting %LOCALAPPDATA%\Gidion (override logs) on
; uninstall -- that's the user's own data (SDLC's opt-in logging), not
; part of the application. Uninstalling the app shouldn't silently
; delete a clinician's review history.