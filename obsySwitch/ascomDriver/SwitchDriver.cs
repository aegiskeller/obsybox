using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using ASCOM;
using ASCOM.Utilities;
using ASCOM.DeviceInterface;
using System.IO.Ports;
using Newtonsoft.Json;

namespace ASCOM.ObsyBox.RelaySwitch
{
    /// <summary>
    /// ASCOM Switch Driver for ObsyBox Relay Controller
    /// Controls Arduino-based relay switches for observatory equipment
    /// </summary>
    [Guid("F9E8D7C6-B5A4-3E2F-C8D9-6F5A4B3C2D1E")]
    [ProgId("ASCOM.ObsyBox.RelaySwitch")]
    [ServedClassName("ObsyBox Relay Switch")]
    [ClassInterface(ClassInterfaceType.None)]
    [ComVisible(true)]
    public class Switch : ISwitchV2, IDisposable
    {
        internal static string driverID = "ASCOM.ObsyBox.RelaySwitch";
        private static string driverDescription = "ObsyBox Arduino Relay Switch Controller";

        private bool connectedState = false;
        private TraceLogger tl;
        private Util utilities;
        private SerialPort serialPort;
        
        // Configuration
        private string serialPortName = "COM3";  // Default port
        private int baudRate = 9600;
        private int timeoutMs = 5000;
        
        // Switch configuration
        private const int maxSwitches = 4;
        private bool[] switchStates = new bool[maxSwitches];
        private string[] switchNames = { "Mount", "Camera", "Focuser", "Aux" };
        private bool[] switchCanWrite = { true, true, true, true };

        public Switch()
        {
            try
            {
                tl = new TraceLogger("", "ObsyBoxRelaySwitch");
                tl.Enabled = true;
                tl.LogMessage("Switch Constructor", "=== STARTING OBSYBOX RELAY SWITCH DRIVER ===");
                tl.LogMessage("Switch Constructor", $"Driver ID: {driverID}");
                
                utilities = new Util();
                ReadProfile();
                
                // Register the driver
                using (var p = new Profile())
                {
                    p.DeviceType = "Switch";
                    p.Register(driverID, driverDescription);
                }
                
                tl.LogMessage("Switch Constructor", "Driver initialization completed");
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
            try
            {
                tl?.LogMessage("Dispose", "Disposing driver");
                Connected = false;
                tl?.Dispose();
                utilities?.Dispose();
            }
            catch (Exception ex)
            {
                tl?.LogMessage("Dispose", $"Error during dispose: {ex.Message}");
            }
        }

        #region ASCOM Registration
        [ComRegisterFunction]
        public static void RegisterASCOM(Type t)
        {
            RegUnregASCOM(true);
        }

        [ComUnregisterFunction]
        public static void UnregisterASCOM(Type t)
        {
            RegUnregASCOM(false);
        }

        static void RegUnregASCOM(bool bRegister)
        {
            using (var P = new Profile())
            {
                P.DeviceType = "Switch";
                if (bRegister)
                {
                    P.Register(driverID, driverDescription);
                }
                else
                {
                    P.Unregister(driverID);
                }
            }
        }
        #endregion

        #region ASCOM Common Properties and Methods

        public string Action(string actionName, string actionParameters)
        {
            tl.LogMessage("Action", $"Action {actionName}, parameters {actionParameters}");
            
            switch (actionName.ToUpperInvariant())
            {
                case "EMERGENCY_STOP":
                    EmergencyStop();
                    return "All switches turned OFF";
                    
                case "GET_DEVICE_INFO":
                    return GetDeviceInfo();
                    
                case "TEST_CONNECTION":
                    return TestConnection() ? "Connection OK" : "Connection Failed";
                    
                default:
                    tl.LogMessage("Action", $"Action {actionName} not implemented");
                    throw new ASCOM.ActionNotImplementedException("Action " + actionName + " is not implemented by this driver");
            }
        }

        public void CommandBlind(string command, bool raw = false)
        {
            CheckConnected("CommandBlind");
            tl.LogMessage("CommandBlind", $"Command: {command}");
            
            if (!raw)
                command += "\n";
                
            SendCommand(command);
        }

        public bool CommandBool(string command, bool raw = false)
        {
            CheckConnected("CommandBool");
            tl.LogMessage("CommandBool", $"Command: {command}");
            
            string response = CommandString(command, raw);
            return response.StartsWith("OK");
        }

        public string CommandString(string command, bool raw = false)
        {
            CheckConnected("CommandString");
            tl.LogMessage("CommandString", $"Command: {command}");
            
            if (!raw)
                command += "\n";
                
            return SendCommand(command);
        }

        public bool Connected
        {
            get
            {
                tl.LogMessage("Connected Get", $"Connected state: {connectedState}");
                return connectedState;
            }
            set
            {
                tl.LogMessage("Connected Set", $"Setting connected to {value}");
                
                if (value == connectedState)
                    return;

                if (value)
                {
                    ConnectToDevice();
                    connectedState = value;
                }
                else
                {
                    DisconnectFromDevice();
                    connectedState = false;
                }
            }
        }

        public string Description
        {
            get
            {
                tl.LogMessage("Description Get", driverDescription);
                return driverDescription;
            }
        }

        public string DriverInfo
        {
            get
            {
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                string driverInfo = $"ObsyBox Relay Switch Driver v{version} - Arduino-based relay controller for observatory equipment";
                tl.LogMessage("DriverInfo Get", driverInfo);
                return driverInfo;
            }
        }

        public string DriverVersion
        {
            get
            {
                Version version = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version;
                string driverVersion = String.Format(CultureInfo.InvariantCulture, "{0}.{1}", version.Major, version.Minor);
                tl.LogMessage("DriverVersion Get", driverVersion);
                return driverVersion;
            }
        }

        public short InterfaceVersion
        {
            get
            {
                tl.LogMessage("InterfaceVersion Get", "2");
                return 2;
            }
        }

        public string Name
        {
            get
            {
                string name = "ObsyBox Relay Switch";
                tl.LogMessage("Name Get", name);
                return name;
            }
        }

        public ArrayList SupportedActions
        {
            get
            {
                tl.LogMessage("SupportedActions Get", "Returning supported actions");
                ArrayList supportedActions = new ArrayList
                {
                    "EMERGENCY_STOP",
                    "GET_DEVICE_INFO", 
                    "TEST_CONNECTION"
                };
                return supportedActions;
            }
        }

        #endregion

        #region ISwitchV2 Implementation

        public short MaxSwitch
        {
            get
            {
                tl.LogMessage("MaxSwitch Get", $"Max switch: {maxSwitches - 1}");
                return (short)(maxSwitches - 1);  // 0-based indexing
            }
        }

        public bool CanWrite(short id)
        {
            tl.LogMessage("CanWrite", $"Switch {id}: {ValidateSwitchId(id) && switchCanWrite[id]}");
            return ValidateSwitchId(id) && switchCanWrite[id];
        }

        public bool GetSwitch(short id)
        {
            CheckConnected("GetSwitch");
            
            if (!ValidateSwitchId(id))
                throw new InvalidValueException($"GetSwitch: Invalid switch ID {id}");

            try
            {
                // Get switch state from Arduino
                string command = $"GET_RELAY,{id + 1}";  // Convert to 1-based
                string response = SendCommand(command);
                
                if (response.StartsWith("STATUS,"))
                {
                    string jsonStr = response.Substring(7);  // Remove "STATUS," prefix
                    var switchData = JsonConvert.DeserializeObject<dynamic>(jsonStr);
                    bool state = switchData.state;
                    
                    switchStates[id] = state;
                    tl.LogMessage("GetSwitch", $"Switch {id} ({switchNames[id]}): {state}");
                    return state;
                }
                else
                {
                    tl.LogMessage("GetSwitch", $"Unexpected response for switch {id}: {response}");
                    return switchStates[id];  // Return cached state
                }
            }
            catch (Exception ex)
            {
                tl.LogMessage("GetSwitch", $"Error getting switch {id}: {ex.Message}");
                throw new DriverException($"Error getting switch {id}: {ex.Message}");
            }
        }

        public string GetSwitchName(short id)
        {
            tl.LogMessage("GetSwitchName", $"Switch {id}");
            
            if (!ValidateSwitchId(id))
                return string.Empty;
                
            string name = switchNames[id];
            tl.LogMessage("GetSwitchName", $"Switch {id} name: {name}");
            return name;
        }

        public string GetSwitchDescription(short id)
        {
            tl.LogMessage("GetSwitchDescription", $"Switch {id}");
            
            if (!ValidateSwitchId(id))
                return string.Empty;
                
            string description = $"{switchNames[id]} - Observatory equipment relay control";
            tl.LogMessage("GetSwitchDescription", $"Switch {id} description: {description}");
            return description;
        }

        public double GetSwitchValue(short id)
        {
            // For boolean switches, return 0.0 or 1.0
            bool state = GetSwitch(id);
            double value = state ? 1.0 : 0.0;
            tl.LogMessage("GetSwitchValue", $"Switch {id} value: {value}");
            return value;
        }

        public double MaxSwitchValue(short id)
        {
            tl.LogMessage("MaxSwitchValue", $"Switch {id}: 1.0");
            return ValidateSwitchId(id) ? 1.0 : 0.0;
        }

        public double MinSwitchValue(short id)
        {
            tl.LogMessage("MinSwitchValue", $"Switch {id}: 0.0");
            return ValidateSwitchId(id) ? 0.0 : 0.0;
        }

        public void SetSwitch(short id, bool state)
        {
            CheckConnected("SetSwitch");
            tl.LogMessage("SetSwitch", $"Setting switch {id} ({switchNames[id]}) to {state}");
            
            if (!ValidateSwitchId(id))
                throw new InvalidValueException($"SetSwitch: Invalid switch ID {id}");

            if (!CanWrite(id))
                throw new MethodNotImplementedException($"SetSwitch: Switch {id} is read-only");

            try
            {
                // Send command to Arduino
                string command = $"SET_RELAY,{id + 1},{(state ? "ON" : "OFF")}";  // Convert to 1-based
                string response = SendCommand(command);
                
                if (response.StartsWith("OK,"))
                {
                    switchStates[id] = state;
                    tl.LogMessage("SetSwitch", $"Successfully set switch {id} to {state}");
                }
                else
                {
                    tl.LogMessage("SetSwitch", $"Failed to set switch {id}: {response}");
                    throw new DriverException($"Failed to set switch {id}: {response}");
                }
            }
            catch (Exception ex)
            {
                tl.LogMessage("SetSwitch", $"Error setting switch {id}: {ex.Message}");
                throw new DriverException($"Error setting switch {id}: {ex.Message}");
            }
        }

        public string SetSwitchName(short id, string name)
        {
            tl.LogMessage("SetSwitchName", $"Setting switch {id} name to {name}");
            
            if (!ValidateSwitchId(id))
                throw new InvalidValueException($"SetSwitchName: Invalid switch ID {id}");

            // Store the name
            switchNames[id] = name;
            WriteProfile();  // Save to profile
            
            tl.LogMessage("SetSwitchName", $"Switch {id} name set to: {name}");
            return switchNames[id];
        }

        public void SetSwitchValue(short id, double value)
        {
            tl.LogMessage("SetSwitchValue", $"Setting switch {id} value to {value}");
            
            // Convert value to boolean (0.0 = false, anything else = true)
            bool state = Math.Abs(value) > 0.5;
            SetSwitch(id, state);
        }

        public double SwitchStep(short id)
        {
            tl.LogMessage("SwitchStep", $"Switch {id}: 1.0");
            return ValidateSwitchId(id) ? 1.0 : 0.0;
        }

        #endregion

        #region Private Methods

        private bool ValidateSwitchId(short id)
        {
            return id >= 0 && id < maxSwitches;
        }

        private void CheckConnected(string operation)
        {
            if (!connectedState)
            {
                tl.LogMessage(operation, "Device not connected");
                throw new NotConnectedException($"{operation}: Device not connected");
            }
        }

        private void ConnectToDevice()
        {
            try
            {
                tl.LogMessage("ConnectToDevice", $"Connecting to {serialPortName} at {baudRate} baud");
                
                serialPort = new SerialPort(serialPortName, baudRate, Parity.None, 8, StopBits.One)
                {
                    Timeout = timeoutMs,
                    WriteTimeout = timeoutMs,
                    ReadTimeout = timeoutMs
                };
                
                serialPort.Open();
                
                // Wait for Arduino to initialize
                System.Threading.Thread.Sleep(2000);
                
                // Test connection with ping
                string response = SendCommand("PING");
                if (!response.Contains("PONG"))
                {
                    throw new DriverException($"Arduino not responding properly: {response}");
                }
                
                // Get initial switch states
                UpdateAllSwitchStates();
                
                tl.LogMessage("ConnectToDevice", "Successfully connected to Arduino");
            }
            catch (Exception ex)
            {
                tl.LogMessage("ConnectToDevice", $"Connection failed: {ex.Message}");
                
                if (serialPort?.IsOpen == true)
                {
                    serialPort.Close();
                    serialPort = null;
                }
                
                throw new DriverException($"Failed to connect to Arduino: {ex.Message}");
            }
        }

        private void DisconnectFromDevice()
        {
            try
            {
                tl.LogMessage("DisconnectFromDevice", "Disconnecting from Arduino");
                
                if (serialPort?.IsOpen == true)
                {
                    serialPort.Close();
                }
                
                serialPort = null;
                tl.LogMessage("DisconnectFromDevice", "Disconnected successfully");
            }
            catch (Exception ex)
            {
                tl.LogMessage("DisconnectFromDevice", $"Error during disconnect: {ex.Message}");
            }
        }

        private string SendCommand(string command)
        {
            if (serialPort == null || !serialPort.IsOpen)
                throw new NotConnectedException("Serial port not open");

            try
            {
                // Clear input buffer
                serialPort.DiscardInBuffer();
                
                // Send command
                if (!command.EndsWith("\n"))
                    command += "\n";
                    
                serialPort.Write(command);
                
                // Read response
                DateTime startTime = DateTime.Now;
                StringBuilder responseBuilder = new StringBuilder();
                
                while ((DateTime.Now - startTime).TotalMilliseconds < timeoutMs)
                {
                    try
                    {
                        string line = serialPort.ReadLine().Trim();
                        
                        if (line.StartsWith("#"))
                        {
                            // Debug message, ignore
                            tl.LogMessage("SendCommand", $"Arduino debug: {line}");
                            continue;
                        }
                        
                        if (line.StartsWith("OK,") || line.StartsWith("ERROR,") || line.StartsWith("STATUS,"))
                        {
                            tl.LogMessage("SendCommand", $"Command: {command.Trim()} -> Response: {line}");
                            return line;
                        }
                    }
                    catch (TimeoutException)
                    {
                        // Continue reading
                        continue;
                    }
                }
                
                throw new DriverException($"Timeout waiting for response to command: {command.Trim()}");
            }
            catch (Exception ex)
            {
                tl.LogMessage("SendCommand", $"Communication error: {ex.Message}");
                throw new DriverException($"Communication error: {ex.Message}");
            }
        }

        private void UpdateAllSwitchStates()
        {
            try
            {
                string response = SendCommand("GET_STATUS");
                
                if (response.StartsWith("STATUS,"))
                {
                    string jsonStr = response.Substring(7);
                    var statusData = JsonConvert.DeserializeObject<dynamic>(jsonStr);
                    
                    for (int i = 0; i < maxSwitches && i < statusData.relays.Count; i++)
                    {
                        var relay = statusData.relays[i];
                        int relayId = (int)relay.id - 1;  // Convert to 0-based
                        
                        if (relayId >= 0 && relayId < maxSwitches)
                        {
                            switchStates[relayId] = relay.state;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                tl.LogMessage("UpdateAllSwitchStates", $"Error updating states: {ex.Message}");
            }
        }

        private void EmergencyStop()
        {
            try
            {
                tl.LogMessage("EmergencyStop", "Executing emergency stop");
                string response = SendCommand("EMERGENCY_STOP");
                
                // Update cached states
                for (int i = 0; i < maxSwitches; i++)
                {
                    switchStates[i] = false;
                }
                
                tl.LogMessage("EmergencyStop", $"Emergency stop completed: {response}");
            }
            catch (Exception ex)
            {
                tl.LogMessage("EmergencyStop", $"Error during emergency stop: {ex.Message}");
                throw new DriverException($"Emergency stop failed: {ex.Message}");
            }
        }

        private string GetDeviceInfo()
        {
            try
            {
                string response = SendCommand("GET_STATUS");
                tl.LogMessage("GetDeviceInfo", $"Device info: {response}");
                return response;
            }
            catch (Exception ex)
            {
                tl.LogMessage("GetDeviceInfo", $"Error getting device info: {ex.Message}");
                return $"Error: {ex.Message}";
            }
        }

        private bool TestConnection()
        {
            try
            {
                string response = SendCommand("PING");
                bool success = response.Contains("PONG");
                tl.LogMessage("TestConnection", $"Connection test: {(success ? "PASS" : "FAIL")}");
                return success;
            }
            catch (Exception ex)
            {
                tl.LogMessage("TestConnection", $"Connection test failed: {ex.Message}");
                return false;
            }
        }

        #endregion

        #region Profile Management

        private void ReadProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "Switch";
                
                serialPortName = driverProfile.GetValue(driverID, "Serial Port", string.Empty, "COM3");
                baudRate = Convert.ToInt32(driverProfile.GetValue(driverID, "Baud Rate", string.Empty, "9600"));
                timeoutMs = Convert.ToInt32(driverProfile.GetValue(driverID, "Timeout", string.Empty, "5000"));
                
                // Read switch names
                for (int i = 0; i < maxSwitches; i++)
                {
                    string defaultName = new string[] { "Mount", "Camera", "Focuser", "Aux" }[i];
                    switchNames[i] = driverProfile.GetValue(driverID, $"Switch{i}Name", string.Empty, defaultName);
                }
                
                tl?.LogMessage("ReadProfile", $"Port: {serialPortName}, Baud: {baudRate}, Timeout: {timeoutMs}ms");
            }
        }

        private void WriteProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "Switch";
                
                driverProfile.WriteValue(driverID, "Serial Port", serialPortName);
                driverProfile.WriteValue(driverID, "Baud Rate", baudRate.ToString());
                driverProfile.WriteValue(driverID, "Timeout", timeoutMs.ToString());
                
                // Write switch names
                for (int i = 0; i < maxSwitches; i++)
                {
                    driverProfile.WriteValue(driverID, $"Switch{i}Name", switchNames[i]);
                }
                
                tl?.LogMessage("WriteProfile", "Profile saved");
            }
        }

        public void SetupDialog()
        {
            if (connectedState)
            {
                System.Windows.Forms.MessageBox.Show("Already connected, just press OK");
                return;
            }

            using (SetupDialogForm F = new SetupDialogForm(this))
            {
                var result = F.ShowDialog();
                if (result == System.Windows.Forms.DialogResult.OK)
                {
                    WriteProfile();
                    tl?.LogMessage("SetupDialog", "Setup dialog completed successfully");
                }
            }
        }

        #endregion

        #region Public Properties for Setup Dialog

        public string SerialPort
        {
            get { return serialPortName; }
            set { serialPortName = value; }
        }

        public int BaudRate
        {
            get { return baudRate; }
            set { baudRate = value; }
        }

        public int TimeoutMs
        {
            get { return timeoutMs; }
            set { timeoutMs = value; }
        }

        public string[] SwitchNames
        {
            get { return (string[])switchNames.Clone(); }
            set
            {
                if (value != null && value.Length == maxSwitches)
                {
                    switchNames = (string[])value.Clone();
                }
            }
        }

        #endregion
    }
}