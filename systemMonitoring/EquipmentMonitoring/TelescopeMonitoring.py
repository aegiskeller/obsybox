import sys

# Add the path to the ASCOM Platform's DLLs (adjust as needed)
sys.path.append(r"C:\Program Files (x86)\Common Files\ASCOM\Platform")

# Import pythonnet and load ASCOM driver access
import pythoncom
import win32com.client

def get_mount_ra_dec():
    # Initialize COM
    pythoncom.CoInitialize()
    # Connect to the telescope (this will prompt for driver selection if not set)
    telescope = win32com.client.Dispatch("ASCOM.Utilities.Chooser").Choose("Telescope")
    if not telescope:
        print("No telescope selected.")
        return

    scope = win32com.client.Dispatch(telescope)
    if not scope.Connected:
        scope.Connected = True

    ra = scope.RightAscension  # In hours
    dec = scope.Declination    # In degrees

    print(f"Current RA: {ra} hours")
    print(f"Current Dec: {dec} degrees")

    scope.Connected = False

if __name__ == "__main__":
    get_mount_ra_dec()