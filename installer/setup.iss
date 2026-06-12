; ============================================================
; Odoo Inmobiliaria - Instalador Windows (Inno Setup)
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
OutputDir=..
OutputBaseFilename=OdooInmobiliaria_Setup_{#AppVersion}
SetupIconFile=..\launcher\icon.ico
Compression=lzma/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstall=64
ArchitecturesAllowed=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1
Name: "autostart"; Description: "Iniciar automáticamente con Windows"; GroupDescription: "Opciones adicionales"; Flags: unchecked

[Files]
; Launcher principal
Source: "..\launcher\odoo_launcher.py"; DestDir: "{app}"; Flags: ignoreversion

; Icono
Source: "..\launcher\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; Script de inicio optimizado
Source: "..\launcher\start_odoo.bat"; DestDir: "{app}"; Flags: ignoreversion

; PostgreSQL Portable (se descarga durante instalación)
; Source: "postgresql\*"; DestDir: "{app}\postgresql"; Flags: ignoreversion recursesubdirs createallsubdirs

; Odoo Source (copia local del código)
Source: "..\odoo\*"; DestDir: "{app}\odoo"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.pyc;__pycache__;*.git*"

; Módulos personalizados
Source: "..\addons\*"; DestDir: "{app}\addons"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.pyc;__pycache__;*.git*"

; Configuración
Source: "..\config\odoo.conf"; DestDir: "{app}\config"; Flags: ignoreversion

; Documentación
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion islicense

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#AppName}"

[Registry]
; Autostart opcional
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

[Code]
var
  PostgreSQLDownloadURL: String;
  PostgreSQLExtractPath: String;

function InitializeSetup(): Boolean;
begin
  PostgreSQLDownloadURL := 'https://get.enterprisedb.com/postgresql/postgresql-16.2-1-windows-x64-binaries.zip';
  PostgreSQLExtractPath := ExpandConstant('{app}\postgresql');
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ZipPath: String;
begin
  if CurStep = ssPostInstall then begin
    // Descargar y extraer PostgreSQL portable
    ZipPath := ExpandConstant('{tmp}\postgresql.zip');
    
    // Descargar
    if not DownloadFile(PostgreSQLDownloadURL, ZipPath, '', True, False) then begin
      MsgBox('Error descargando PostgreSQL. Se intentará usar el del sistema.', mbError, MB_OK);
    end else begin
      // Extraer usando PowerShell
      Exec('powershell.exe', 
        '-Command "Expand-Archive -Path ''' + ZipPath + ''' -DestinationPath ''' + PostgreSQLExtractPath + ''' -Force"',
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
      // Renombrar carpeta extraída (viene como pgsql)
      if DirExists(PostgreSQLExtractPath + '\pgsql') then begin
        RenameFile(PostgreSQLExtractPath + '\pgsql', PostgreSQLExtractPath + '\bin');
      end;
    end;
    
    // Crear script de inicio rápido
    CreateStartScript();
    
    // Instalar dependencias Python
    InstallPythonDependencies();
  end;
end;

procedure CreateStartScript();
var
  ScriptPath: String;
  ScriptContent: String;
begin
  ScriptPath := ExpandConstant('{app}\start_odoo.bat');
  ScriptContent := 
    '@echo off' + #13#10 +
    'title Odoo Inmobiliaria - Iniciando...' + #13#10 +
    'cd /d "%~dp0"' + #13#10 +
    'set APPDATA_DIR=%APPDATA%\OdooInmobiliaria' + #13#10 +
    'mkdir "%APPDATA_DIR%\data\postgresql" 2>nul' + #13#10 +
    'mkdir "%APPDATA_DIR%\logs" 2>nul' + #13#10 +
    'echo Iniciando PostgreSQL...' + #13#10 +
    'start /b "" "%~dp0postgresql\bin\postgres.exe" -D "%APPDATA_DIR%\data\postgresql"' + #13#10 +
    'timeout /t 3 >nul' + #13#10 +
    'echo Iniciando Odoo...' + #13#10 +
    'python "%~dp0odoo\odoo-bin" -c "%~dp0config\odoo.conf"' + #13#10;
  
  SaveStringToFile(ScriptPath, ScriptContent, False);
end;

procedure InstallPythonDependencies();
var
  ResultCode: Integer;
  RequirementsPath: String;
begin
  RequirementsPath := ExpandConstant('{app}\odoo\requirements.txt');
  if FileExists(RequirementsPath) then begin
    Exec('cmd.exe', '/c pip install -r "' + RequirementsPath + '" --quiet', 
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;