; Per-user English installer: no administrator access, services, or startup tasks.
Unicode True
!include "MUI2.nsh"
!include "x64.nsh"
!ifndef BUNDLE
  !error "Pass /DBUNDLE=path/to/VideoToMP4"
!endif
!ifndef OUTPUT
  !define OUTPUT "../artifacts/VideoToMP4-v1.0-windows-setup.exe"
!endif
Name "Video to MP4 v1.0"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\VideoToMP4"
RequestExecutionLevel user
SetCompressor /SOLID lzma
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductName" "Video to MP4"
VIAddVersionKey /LANG=1033 "ProductVersion" "1.0"
VIAddVersionKey /LANG=1033 "FileVersion" "1.0"
VIAddVersionKey /LANG=1033 "FileDescription" "Video to MP4 Setup"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright (c) 2026 jotadev27"
!define MUI_ICON "../../assets/logo.ico"
!define MUI_UNICON "../../assets/logo.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Welcome to Video to MP4 v1.0"
!define MUI_WELCOMEPAGE_TEXT "Convert your videos locally. Your originals stay safe.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\VideoToMP4.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Open Video to MP4"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "../../LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK "Video to MP4 requires a 64-bit Windows system."
    Abort
  ${EndIf}
FunctionEnd

Section "Video to MP4" MainSection
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "${BUNDLE}/*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Video to MP4"
  CreateShortcut "$SMPROGRAMS\Video to MP4\Video to MP4.lnk" "$INSTDIR\VideoToMP4.exe"
  CreateShortcut "$SMPROGRAMS\Video to MP4\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "DisplayName" "Video to MP4"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "DisplayVersion" "1.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "Publisher" "jotadev27"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "DisplayIcon" "$INSTDIR\VideoToMP4.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Video to MP4\Video to MP4.lnk"
  Delete "$SMPROGRAMS\Video to MP4\Uninstall.lnk"
  RMDir "$SMPROGRAMS\Video to MP4"
  ; Remove application-owned files only. Never delete source or converted videos.
  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\licenses"
  Delete "$INSTDIR\VideoToMP4.exe"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\THIRD_PARTY_NOTICES.md"
  Delete "$INSTDIR\VERSION.txt"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VideoToMP4"
SectionEnd
