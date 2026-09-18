Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
Name "Shellground"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\Shellground"
RequestExecutionLevel user
SetCompressor /SOLID zlib
BrandingText "Shellground · Linux · Docker · ROS 2 · Python"
VIProductVersion "4.7.4.3"
VIAddVersionKey "ProductName" "Shellground Setup"
VIAddVersionKey "FileDescription" "Shellground 설치 프로그램"
VIAddVersionKey "FileVersion" "4.7.4.3"
VIAddVersionKey "LegalCopyright" "Shellground contributors"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Shellground 설치"
!define MUI_WELCOMEPAGE_TEXT "실습 자료는 설치 중 자동으로 내려받습니다.$\r$\n$\r$\n인터넷 연결과 약 9GB의 여유 공간이 필요합니다.$\r$\n파일을 따로 받거나 합칠 필요가 없습니다.$\r$\n$\r$\n개인 Docker·WSL·Python 환경과 학습 진도는 변경하지 않습니다."
!define APPDIR "app-4.7.4-windows.2"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPDIR}\Shellground.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Shellground 실행"
!define MUI_FINISHPAGE_TEXT "설치가 완료됐습니다. 시작 메뉴 또는 바탕화면의 Shellground로 실행하세요."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"
Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Windows 10/11 64비트가 필요합니다."
    Abort
  ${EndIf}
FunctionEnd
Section "Shellground" Main
  AddSize 8800000
  SetShellVarContext current
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "windows_setup.ps1"
  File "windows_download.cs"
  File "manifest.json"
  DetailPrint "설치 자료를 준비합니다. 별도 설치창에서 진행률을 확인하세요."
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$PLUGINSDIR\windows_setup.ps1" -InstallDir "$INSTDIR" -ManifestPath "$PLUGINSDIR\manifest.json"' $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "설치가 완료되지 않았습니다. 설치파일을 다시 실행하면 이어 받을 수 있습니다."
    Abort
  ${EndIf}
  SetOutPath "$INSTDIR\${APPDIR}"
  CreateShortCut "$SMPROGRAMS\Shellground.lnk" "$INSTDIR\${APPDIR}\Shellground.exe"
  CreateShortCut "$DESKTOP\Shellground.lnk" "$INSTDIR\${APPDIR}\Shellground.exe"
  WriteUninstaller "$INSTDIR\Shellground-Uninstall.exe"
  SetOutPath "$INSTDIR"
  File "Installer-Licenses.txt"
  SetOutPath "$INSTDIR\${APPDIR}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Shellground" "DisplayName" "Shellground"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Shellground" "DisplayVersion" "4.7.4-windows.2"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Shellground" "UninstallString" '"$INSTDIR\Shellground-Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Shellground" "InstallLocation" "$INSTDIR"
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  IfFileExists "$INSTDIR\.shellground-installer" 0 unsafe
  IfFileExists "$INSTDIR\${APPDIR}\installed.sha256" 0 unsafe
  RMDir /r "$INSTDIR\${APPDIR}"
  IfFileExists "$INSTDIR\${APPDIR}\Shellground.exe" busy 0
  Delete "$SMPROGRAMS\Shellground.lnk"
  Delete "$DESKTOP\Shellground.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Shellground"
  Delete "$INSTDIR\.shellground-installer"
  Delete "$INSTDIR\.setup.lock"
  Delete "$INSTDIR\Installer-Licenses.txt"
  Delete "$INSTDIR\Shellground-Uninstall.exe"
  RMDir "$INSTDIR"
  Goto done
  unsafe:
  MessageBox MB_ICONSTOP "설치 소유 정보를 확인하지 못해 파일을 삭제하지 않았습니다."
  Abort
  busy:
  MessageBox MB_ICONEXCLAMATION "Shellground를 종료한 뒤 다시 제거하세요. 학습 진도는 유지됩니다."
  Abort
  done:
SectionEnd
