# Install Notes
1. make sure ASCOM is present
2. get .dll from https://github.com/jlecomte/ascom-telescope-cover/releases
3. C:\Users\Stefan\Documents\obsybox\dustCover\lecomte_dustCover>C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /tlb /codebase ASCOM.DarkSkyGeek.TelescopeCover.dll
Microsoft .NET Framework Assembly Registration Utility version 4.8.9037.0
for Microsoft .NET Framework version 4.8.9037.0
Copyright (C) Microsoft Corporation.  All rights reserved.

RegAsm : warning RA0000 : Registering an unsigned assembly with /codebase can cause your assembly to interfere with other applications that may be installed on the same computer. The /codebase switch is intended to be used only with signed assemblies. Please give your assembly a strong name and re-register it.
Types registered successfully
Assembly exported to 'C:\Users\Stefan\Documents\obsybox\dustCover\lecomte_dustCover\ASCOM.DarkSkyGeek.TelescopeCover.tlb', and the type library was registered successfully


# How to use the device

NINA external script examples:

venv? python -m venv .venv
. .\.venv\Scripts\Activate.ps1

Python executable:

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/.venv/Scripts/python.exe`

Arguments:

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/lecomte_dustCover/openClose.py open`

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/lecomte_dustCover/openClose.py close`

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/lecomte_dustCover/openClose.py ping`

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/lecomte_dustCover/openClose.py info`

`c:/Users/Admin/Documents/Arduino/obsybox/dustCover/lecomte_dustCover/openClose.py getstate`

If the NINA window closes quickly, that is usually normal for a short-running script. Check `openClose.log` next to the script for the real output and any traceback.

# use in NINA

External Script element

C:\Users\Stefan\Documents\obsybox\dustCover\lecomte_dustCover\.venv\Scripts\python.exe C:\Users\Stefan\Documents\obsybox\dustCover\lecomte_dustCover\openClose.py open