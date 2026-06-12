; ============================================================
; Odoo Inmobiliaria - Instalador Nativo Windows (Inno Setup)
; Genera .exe instalable que incluye TODO: Python, WebView2, Odoo, PostgreSQL
; ============================================================

#define AppName "OdooInmobiliaria"
#define AppVersion "19.0.1.0"
#define AppPublisher "Tu Inmobiliaria"
#define AppURL "https://tu-inmobiliaria.com"
#define AppExeName "OdooInmobiliaria.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=..\dist_native
OutputBaseFilename=OdooInmobiliaria_Setup_{#AppVersion}
SetupIconFile=..\native_app\icon.ico
Compression=lzma/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstall=64
ArchitecturesAllowed=x64
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousLanguage=no
UsePreviousTasks=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "autostart"; Description: "Iniciar automáticamente con Windows (minimizado)"; GroupDescription: "Opciones adicionales"; Flags: unchecked

[Files]
; EJECUTABLE PRINCIPAL (compilado con PyInstaller - incluye Python + WebView2 + Odoo + psycopg2)
Source: "..\dist_native\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Icono
Source: "..\native_app\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; Documentación
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion islicense

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "Sistema Inmobiliario 100% Local"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Sistema Inmobiliario 100% Local"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpia datos de usuario al desinstalar (opcional - comentar para preservar datos)
; Type: filesandordirs; Name: "{localappdata}\{#AppName}"
Type: filesandordirs; Name: "{userappdata}\{#AppName}\webview2_data"

[Registry]
; Autostart opcional
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

; Asociación de protocolo personalizado (opcional: odooinmobiliaria://)
Root: HKCR; Subkey: "odooinmobiliaria"; ValueType: string; ValueData: "URL:Odoo Inmobiliaria Protocol"; Flags: uninsdeletekey
Root: HKCR; Subkey: "odooinmobiliaria\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey

[Code]
var
  Page: TWizardPage;
  StatusLabel: TLabel;

procedure InitializeWizard();
begin
  // Página personalizada de progreso de primera ejecución
  Page := CreateCustomPage(wpReady, 
    'Preparando primera ejecución...', 
    'La primera vez se descargará PostgreSQL portable y configurará la base de datos.');
  StatusLabel := TLabel.Create(Page);
  StatusLabel.Parent := Page.Surface;
  StatusLabel.AutoSize := False;
  StatusLabel.WordWrap := True;
  StatusLabel.Left := 0;
  StatusLabel.Top := 0;
  StatusLabel.Width := Page.Surface.Width;
  StatusLabel.Height := Page.Surface.Height;
  StatusLabel.Caption := 'Esto solo ocurre la primera vez. Puede tardar 1-2 minutos.';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    // La primera ejecución del .exe descargará PostgreSQL y configurará todo
    // No hacemos nada aquí, el .exe se encarga solo
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  // Saltar página de directorio y grupo
  Result := (PageID = wpSelectDir) or (PageID = wpSelectProgramGroup);
end;

function InitializeSetup(): Boolean;
begin
  // Verificar Windows 10+ (necesario para WebView2)
  if not (GetWindowsVersion >= $0A000000) then begin // Windows 10 = 10.0
    MsgBox('Esta aplicación requiere Windows 10 o superior (para WebView2).', mbError, MB_OK);
    Result := False;
  end else begin
    Result := True;
  end;
end;