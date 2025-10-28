using System;
using System.Collections;
using System.Runtime.InteropServices;
using ASCOM.Utilities;
using ASCOM.DeviceInterface;

namespace ASCOM.ArduSafeMon.SafetyMonitor
{
    /// <summary>
    /// ASCOM Switch Driver for ArduSafeMon - exposes sensor values as readable gauges
    /// </summary>
    [Guid("B2C3D4E5-F6A7-5B6C-8D9E-6F5A4B3C2D1E")]
    [ProgId("ASCOM.ArduSafeMon.Switch")]
    [ServedClassName("ArduSafeMon Switch")]
    [ClassInterface(ClassInterfaceType.None)]
    [ComVisible(true)]
    public class Switch : ISwitchV2, IDisposable
    {
        internal static string driverID = "ASCOM.ArduSafeMon.Switch";
        private static string driverDescription = "ArduSafeMon Switch (Sensor Values)";

        private bool connectedState = false;
        internal TraceLogger tl;

        public Switch()
        {
            try
            {
                tl = new TraceLogger("", "ArduSafeMon.Switch");
                tl.Enabled = true;  // Force enable immediately
                tl.LogMessage("Switch Constructor", "=== STARTING SWITCH DRIVER ===");
                tl.LogMessage("Switch Constructor", $"Process ID: {System.Diagnostics.Process.GetCurrentProcess().Id}");
                
                ReadProfile();
                tl.LogMessage("Switch Constructor", "Profile read successfully");
                
                // Register as a Switch device in ASCOM Profile
                using (var p = new Profile())
                {
                    p.DeviceType = "Switch";
                    p.Register(driverID, driverDescription);
                }
                
                tl.LogMessage("Switch Constructor", "Completed initialization successfully");
            }
            catch (Exception ex)
            {
                if (tl != null)
                {
                    tl.LogMessage("Switch Constructor", $"ERROR: {ex.Message}");
                    tl.LogMessage("Switch Constructor", $"Stack trace: {ex.StackTrace}");
                }
                throw;
            }
        }

        public void Dispose()
        {
            tl.LogMessage("Dispose", "Disposing driver");
            tl.Enabled = false;
            tl.Dispose();
            tl = null;
        }

        #region Common Properties and Methods

        public void SetupDialog()
        {
            System.Windows.Forms.MessageBox.Show(
                "ArduSafeMon Switch shares the same COM port as the ArduSafeMon Safety Monitor.\n\n" +
                "Please configure the COM port in the Safety Monitor setup dialog.",
                "ArduSafeMon Switch Setup",
                System.Windows.Forms.MessageBoxButtons.OK,
                System.Windows.Forms.MessageBoxIcon.Information);
        }

        public ArrayList SupportedActions
        {
            get
            {
                tl.LogMessage("SupportedActions Get", "Returning empty arraylist");
                return new ArrayList();
            }
        }

        public string Action(string actionName, string actionParameters)
        {
            LogMessage("Action", "Not implemented");
            throw new ASCOM.MethodNotImplementedException("Action");
        }

        public void CommandBlind(string command, bool raw)
        {
            CheckConnected("CommandBlind");
            throw new ASCOM.MethodNotImplementedException("CommandBlind");
        }

        public bool CommandBool(string command, bool raw)
        {
            CheckConnected("CommandBool");
            throw new ASCOM.MethodNotImplementedException("CommandBool");
        }

        public string CommandString(string command, bool raw)
        {
            CheckConnected("CommandString");
            throw new ASCOM.MethodNotImplementedException("CommandString");
        }

        public bool Connected
        {
            get
            {
                LogMessage("Connected", "Get {0}", connectedState);
                return connectedState;
            }
            set
            {
                tl.LogMessage("Connected", "Set {0}", value);
                if (value == connectedState)
                    return;

                if (value)
                {
                    connectedState = true;
                    LogMessage("Connected Set", "Connecting via SharedHardware");
                    
                    try
                    {
                        // Get COM port from profile (same as SafetyMonitor)
                        using (Profile driverProfile = new Profile())
                        {
                            driverProfile.DeviceType = "SafetyMonitor";
                            string comPort = driverProfile.GetValue("ASCOM.ArduSafeMon.SafetyMonitor", "COM Port");
                            SharedHardware.ComPort = comPort;
                        }
                        SharedHardware.Connect();
                    }
                    catch (Exception ex)
                    {
                        connectedState = false;
                        LogMessage("Connected Set", "Error: " + ex.Message);
                        throw;
                    }
                }
                else
                {
                    connectedState = false;
                    LogMessage("Connected Set", "Disconnecting via SharedHardware");
                    SharedHardware.Disconnect();
                }
            }
        }

        public string Description
        {
            get
            {
                tl.LogMessage("Description Get", $"Returning: {driverDescription}");
                return driverDescription;
            }
        }

        public string DriverInfo
        {
            get
            {
                tl.LogMessage("DriverInfo Get", "Called");
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                string driverInfo = driverDescription + " Version: " + version.ToString();
                tl.LogMessage("DriverInfo Get", driverInfo);
                return driverInfo;
            }
        }

        public string DriverVersion
        {
            get
            {
                tl.LogMessage("DriverVersion Get", "Called");
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                string driverVersion = String.Format("{0}.{1}", version.Major, version.Minor);
                tl.LogMessage("DriverVersion Get", driverVersion);
                return driverVersion;
            }
        }

        public short InterfaceVersion
        {
            get
            {
                tl.LogMessage("InterfaceVersion Get", "Returning 2");
                LogMessage("InterfaceVersion Get", "2");
                return Convert.ToInt16("2");
            }
        }

        public string Name
        {
            get
            {
                string name = "ArduSafeMon Switch";
                tl.LogMessage("Name Get", $"Returning: {name}");
                return name;
            }
        }

        #endregion

        #region ISwitchV2 Implementation

        public short MaxSwitch
        {
            get
            {
                // NOTE: Returning 1 instead of 0 because some ASCOM clients
                // incorrectly interpret MaxSwitch=0 as "no switches"
                // We only implement switch ID 0; switch ID 1 will throw InvalidValueException
                tl.LogMessage("MaxSwitch Get", "Returning 1 (workaround for clients that need MaxSwitch > 0)");
                return 1;
            }
        }

        public bool CanWrite(short id)
        {
            CheckConnected("CanWrite");
            ValidateSwitchId(id);
            return false; // All switches are read-only sensors
        }

        public bool GetSwitch(short id)
        {
            CheckConnected("GetSwitch");
            ValidateSwitchId(id);
            // Return the safety status as a boolean
            SharedHardware.UpdateSafetyState();
            return SharedHardware.IsSafe;
        }

        public string GetSwitchDescription(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case 0:
                    return "Rain sensor analog value (0-1023). Higher values indicate drier conditions.";
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchDescription", id.ToString(), "0");
            }
        }

        public string GetSwitchName(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case 0:
                    return "Rain Sensor";
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchName", id.ToString(), "0");
            }
        }

        public double GetSwitchValue(short id)
        {
            tl.LogMessage("GetSwitchValue", $"Called for switch {id}");
            CheckConnected("GetSwitchValue");
            ValidateSwitchId(id);
            
            tl.LogMessage("GetSwitchValue", "Calling SharedHardware.UpdateSafetyState()");
            SharedHardware.UpdateSafetyState();
            
            switch (id)
            {
                case 0:
                    double value = SharedHardware.RainSensorValue;
                    tl.LogMessage("GetSwitchValue", $"Rain Sensor value from SharedHardware: {value}");
                    return value;
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchValue", id.ToString(), "0");
            }
        }

        public double MaxSwitchValue(short id)
        {
            ValidateSwitchId(id);
            return 1023.0; // Rain sensor is 10-bit ADC
        }

        public double MinSwitchValue(short id)
        {
            ValidateSwitchId(id);
            return 0.0;
        }

        public void SetSwitch(short id, bool state)
        {
            CheckConnected("SetSwitch");
            throw new ASCOM.MethodNotImplementedException("SetSwitch - all switches are read-only");
        }

        public void SetSwitchName(short id, string name)
        {
            throw new ASCOM.MethodNotImplementedException("SetSwitchName - switch names are fixed");
        }

        public void SetSwitchValue(short id, double value)
        {
            CheckConnected("SetSwitchValue");
            throw new ASCOM.MethodNotImplementedException("SetSwitchValue - all switches are read-only");
        }

        public double SwitchStep(short id)
        {
            ValidateSwitchId(id);
            return 1.0; // ADC step size
        }

        #endregion

        #region Private methods

        private void ValidateSwitchId(short id)
        {
            if (id < 0 || id > MaxSwitch)
            {
                throw new ASCOM.InvalidValueException("Switch ID", id.ToString(), $"0 to {MaxSwitch}");
            }
        }

        private void CheckConnected(string message)
        {
            if (!connectedState)
            {
                throw new ASCOM.NotConnectedException(message);
            }
        }

        private void ReadProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "Switch";
                tl.Enabled = Convert.ToBoolean(driverProfile.GetValue(driverID, "Trace Level", string.Empty, "true"));
            }
        }

        internal void WriteProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "Switch";
                driverProfile.WriteValue(driverID, "Trace Level", tl.Enabled.ToString());
            }
        }

        private void LogMessage(string identifier, string message, params object[] args)
        {
            var msg = string.Format(message, args);
            tl.LogMessage(identifier, msg);
        }

        #endregion
    }
}
