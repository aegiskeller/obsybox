@echo off
REM Build script for ArduSafeMon ASCOM Driver
REM Run this from Visual Studio Developer Command Prompt or install .NET Framework SDK

echo Building ArduSafeMon ASCOM SafetyMonitor Driver...
echo.

REM Check if MSBuild is available
where msbuild >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: MSBuild not found!
    echo Please run this from Visual Studio Developer Command Prompt
    echo Or install .NET Framework 4.8 Developer Pack
    pause
    exit /b 1
)

REM Restore NuGet packages
echo Restoring NuGet packages...
nuget restore ArduSafeMon.csproj
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to restore NuGet packages
    echo Install NuGet CLI from https://www.nuget.org/downloads
    pause
    exit /b 1
)

REM Build Release configuration
echo.
echo Building Release configuration...
msbuild ArduSafeMon.csproj /p:Configuration=Release /p:Platform=x86 /t:Rebuild
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output location: bin\Release\
echo.
echo To install the driver:
echo 1. Open PowerShell as Administrator
echo 2. Navigate to bin\Release\
echo 3. Run: regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
echo.
pause
