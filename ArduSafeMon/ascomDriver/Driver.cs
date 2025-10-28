using System;
using System.Collections;
using System.IO.Ports;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using ASCOM.Utilities;
using ASCOM.DeviceInterface;

namespace ASCOM.ArduSafeMon.SafetyMonitor
{
    /// <summary>
    /// ASCOM SafetyMonitor Driver for ArduSafeMon.
    /// </summary>
    [Guid("A1B2C3D4-E5F6-4A5B-9C8D-7E6F5A4B3C2D")]
    [ProgId("ASCOM.ArduSafeMon.SafetyMonitor")]
    [ServedClassName("ArduSafeMon Safety Monitor")]
    [ClassInterface(ClassInterfaceType.None)]
    [ComVisible(true)]
    public class SafetyMonitor : ISafetyMonitor, IDisposable
    {
        // ASCOM DeviceID (COM ProgID) for this driver
        internal static string driverID = "ASCOM.ArduSafeMon.SafetyMonitor";
        private static string driverDescription = "Wombat Enclosure Safety Monitor";

        // Serial port communication
        private SerialPort serialPort;
        private string comPort = "";
        private const int baudRate = 9600;
        private const int readTimeout = 2000; // 2 seconds
        private bool connectedState = false;

        // Safety monitoring
        private bool isSafe = false;
        private string unsafeReason = "";
        private double rainSensorValue = 0;
        private DateTime lastUpdateTime = DateTime.MinValue;
        private readonly object safeLock = new object();

        // ASCOM Profile for settings persistence
        //private Profile profile;  // Removed - not needed, Profile is used directly in methods
        private const string comPortProfileName = "COM Port";
        private const string traceStateProfileName = "Trace Level";

        // Logging
        internal TraceLogger tl;  // Made internal so SetupDialogForm can access it

        /// <summary>
        /// Initializes a new instance of the driver.
        /// </summary>
        public SafetyMonitor()
        {
            tl = new TraceLogger("", "ArduSafeMon");
            ReadProfile();
            tl.LogMessage("SafetyMonitor", "Starting initialization");
            
            serialPort = new SerialPort();
            serialPort.BaudRate = baudRate;
            serialPort.DataBits = 8;
            serialPort.Parity = Parity.None;
            serialPort.StopBits = StopBits.One;
            serialPort.Handshake = Handshake.None;
            serialPort.ReadTimeout = 10000;  // Increased to 10 seconds to handle slow Arduino loop
            serialPort.WriteTimeout = 1000;
            serialPort.NewLine = "#";
            serialPort.DtrEnable = true;  // Enable DTR to reset Arduino on connection
            serialPort.RtsEnable = false;
            
            tl.LogMessage("SafetyMonitor", "Completed initialization");
        }

        #region Common properties and methods

        /// <summary>
        /// Displays the Setup Dialog form.
        /// </summary>
        public void SetupDialog()
        {
            if (connectedState)
            {
                System.Windows.Forms.MessageBox.Show("Already connected, just press OK");
            }

            using (SetupDialogForm F = new SetupDialogForm(this))
            {
                var result = F.ShowDialog();
                if (result == System.Windows.Forms.DialogResult.OK)
                {
                    WriteProfile();
                }
            }
        }

        public ArrayList SupportedActions
        {
            get
            {
                ArrayList actions = new ArrayList();
                actions.Add("RainSensorValue");
                actions.Add("UnsafeReason");
                tl.LogMessage("SupportedActions Get", "Returning 2 custom actions");
                return actions;
            }
        }

        public string Action(string actionName, string actionParameters)
        {
            LogMessage("Action", "Action: " + actionName);
            
            switch (actionName.ToLower())
            {
                case "rainsensorvalue":
                    return RainSensorValue.ToString();
                    
                case "unsafereason":
                    return UnsafeReason;
                    
                default:
                    LogMessage("Action", "Unknown action: " + actionName);
                    throw new ASCOM.ActionNotImplementedException("Action " + actionName + " is not implemented by this driver");
            }
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

        public void Dispose()
        {
            tl.LogMessage("Dispose", "Disposing driver");
            Connected = false;
            tl.Enabled = false;
            tl.Dispose();
            tl = null;
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
                        SharedHardware.ComPort = comPort;
                        SharedHardware.Connect();
                        LogMessage("Connected Set", "Connected successfully");
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
                tl.LogMessage("Description Get", driverDescription);
                return driverDescription;
            }
        }

        public string DriverInfo
        {
            get
            {
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
                LogMessage("InterfaceVersion Get", "2");
                return 2;
            }
        }

        public string Name
        {
            get
            {
                string name = "ArduSafeMon Safety Monitor";
                tl.LogMessage("Name Get", name);
                return name;
            }
        }

        #endregion

        #region ISafetyMonitor Implementation

        public bool IsSafe
        {
            get
            {
                CheckConnected("IsSafe");
                SharedHardware.UpdateSafetyState();
                bool result = SharedHardware.IsSafe;
                LogMessage("IsSafe Get", result.ToString());
                return result;
            }
        }

        /// <summary>
        /// Rain sensor analog value (0-1023)
        /// Exposed via SupportedActions mechanism
        /// </summary>
        public double RainSensorValue
        {
            get
            {
                CheckConnected("RainSensorValue");
                return SharedHardware.RainSensorValue;
            }
        }

        /// <summary>
        /// Reason for unsafe conditions
        /// Exposed via SupportedActions mechanism
        /// </summary>
        public string UnsafeReason
        {
            get
            {
                CheckConnected("UnsafeReason");
                return SharedHardware.UnsafeReason;
            }
        }

        #endregion

        #region Private methods

        /// <summary>
        /// Query the Arduino for current safety state
        /// </summary>
        private void UpdateSafetyState()
        {
            if (!serialPort.IsOpen)
            {
                throw new ASCOM.NotConnectedException("Serial port is not open");
            }

            try
            {
                // Aggressively clear buffer - Arduino may be flooding with debug output
                serialPort.DiscardInBuffer();
                Thread.Sleep(100); // Let any in-flight data arrive
                serialPort.DiscardInBuffer();

                // Send command multiple times to increase chance Arduino sees it
                serialPort.Write("S#S#S#");
                LogMessage("UpdateSafetyState", "Sent S# command (x3)");

                // Read all available data until we find a response
                StringBuilder allData = new StringBuilder();
                DateTime startTime = DateTime.Now;
                bool foundResponse = false;
                
                while ((DateTime.Now - startTime).TotalMilliseconds < serialPort.ReadTimeout)
                {
                    if (serialPort.BytesToRead > 0)
                    {
                        string chunk = serialPort.ReadExisting();
                        allData.Append(chunk);
                        
                        // Check if we have a complete response
                        string data = allData.ToString();
                        if (data.Contains("safe#") || data.Contains("notsafe#"))
                        {
                            foundResponse = true;
                            break;
                        }
                    }
                    Thread.Sleep(50);
                }
                
                if (!foundResponse)
                {
                    LogMessage("UpdateSafetyState", "Received no valid response: " + allData.ToString());
                    throw new TimeoutException("Timeout reading from Arduino");
                }
                
                string fullResponse = allData.ToString();
                LogMessage("UpdateSafetyState", "Received raw: " + fullResponse);

                // Parse the response - look for "safe#" or "notsafe#" in the output
                string response = "";
                if (fullResponse.Contains("notsafe#"))
                {
                    response = "notsafe";
                }
                else if (fullResponse.Contains("safe#"))
                {
                    response = "safe";
                }

                lock (safeLock)
                {
                    if (response.Equals("safe", StringComparison.OrdinalIgnoreCase))
                    {
                        isSafe = true;
                        unsafeReason = "All conditions normal";
                        LogMessage("UpdateSafetyState", "Status: SAFE");
                    }
                    else if (response.Equals("notsafe", StringComparison.OrdinalIgnoreCase))
                    {
                        isSafe = false;
                        LogMessage("UpdateSafetyState", "Status: NOT SAFE");
                        
                        // Parse the reason from the response
                        unsafeReason = ParseUnsafeReason(fullResponse);
                    }
                    else
                    {
                        LogMessage("UpdateSafetyState", "Could not parse status from: " + fullResponse);
                    }
                    
                    // Parse rain sensor value
                    rainSensorValue = ParseRainSensorValue(fullResponse);
                    
                    lastUpdateTime = DateTime.Now;
                }

                // Discard any remaining debug output
                Thread.Sleep(100);
                serialPort.DiscardInBuffer();
            }
            catch (TimeoutException)
            {
                LogMessage("UpdateSafetyState", "Timeout reading from Arduino");
                throw new ASCOM.DriverException("Timeout reading from ArduSafeMon");
            }
            catch (Exception ex)
            {
                LogMessage("UpdateSafetyState", "Error: " + ex.Message);
                throw new ASCOM.DriverException("Error communicating with ArduSafeMon: " + ex.Message);
            }
        }

        /// <summary>
        /// Parse rain sensor value from Arduino response
        /// </summary>
        private double ParseRainSensorValue(string response)
        {
            try
            {
                // Look for "Rain sensor value: 217.90"
                int idx = response.IndexOf("Rain sensor value:");
                if (idx > 0)
                {
                    int start = idx + 18; // Length of "Rain sensor value:"
                    int end = response.IndexOf("(", start);
                    if (end > start)
                    {
                        string valueStr = response.Substring(start, end - start).Trim();
                        if (double.TryParse(valueStr, out double value))
                        {
                            return value;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                LogMessage("ParseRainSensorValue", "Error parsing: " + ex.Message);
            }
            return 0;
        }

        /// <summary>
        /// Parse unsafe reason from Arduino response
        /// </summary>
        private string ParseUnsafeReason(string response)
        {
            StringBuilder reasons = new StringBuilder();
            
            // Check for clouds
            if (response.Contains("Clouds too high") || response.Contains("Clouds:"))
            {
                int idx = response.IndexOf("Clouds:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        string cloudInfo = response.Substring(idx, endIdx - idx).Trim();
                        reasons.Append(cloudInfo);
                    }
                }
            }
            
            // Check for wind
            if (response.Contains("Wind too high") || response.Contains("Wind:"))
            {
                int idx = response.IndexOf("Wind:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        if (reasons.Length > 0) reasons.Append("; ");
                        string windInfo = response.Substring(idx, endIdx - idx).Trim();
                        reasons.Append(windInfo);
                    }
                }
            }
            
            // Check for humidity
            if (response.Contains("Humidity too high") || response.Contains("Humidity:"))
            {
                int idx = response.IndexOf("Humidity:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        if (reasons.Length > 0) reasons.Append("; ");
                        string humidityInfo = response.Substring(idx, endIdx - idx).Trim();
                        reasons.Append(humidityInfo);
                    }
                }
            }
            
            // Check for rain (though usually handled by sensor value)
            if (response.Contains("Rain detected"))
            {
                if (reasons.Length > 0) reasons.Append("; ");
                reasons.Append("Rain detected");
            }
            
            return reasons.Length > 0 ? reasons.ToString() : "Unsafe conditions detected";
        }

        /// <summary>
        /// Read the device configuration from the ASCOM Profile store
        /// </summary>
        internal void ReadProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "SafetyMonitor";
                tl.Enabled = Convert.ToBoolean(driverProfile.GetValue(driverID, traceStateProfileName, string.Empty, "true"));
                comPort = driverProfile.GetValue(driverID, comPortProfileName, string.Empty, "COM1");
            }
        }

        /// <summary>
        /// Write the device configuration to the ASCOM Profile store
        /// </summary>
        internal void WriteProfile()
        {
            using (Profile driverProfile = new Profile())
            {
                driverProfile.DeviceType = "SafetyMonitor";
                driverProfile.WriteValue(driverID, traceStateProfileName, tl.Enabled.ToString());
                driverProfile.WriteValue(driverID, comPortProfileName, comPort);
            }
        }

        /// <summary>
        /// Log helper function
        /// </summary>
        private void LogMessage(string identifier, string message, params object[] args)
        {
            var msg = string.Format(message, args);
            tl.LogMessage(identifier, msg);
        }

        private void CheckConnected(string message)
        {
            if (!connectedState)
            {
                throw new ASCOM.NotConnectedException(message);
            }
        }

        internal string ComPort
        {
            get { return comPort; }
            set { comPort = value; }
        }

        #endregion
    }
}
