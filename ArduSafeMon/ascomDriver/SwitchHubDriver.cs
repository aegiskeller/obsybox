using System;
using System.Collections;
using System.Net.Http;
using System.Runtime.InteropServices;
using ASCOM.Utilities;
using ASCOM.DeviceInterface;

namespace ASCOM.ArduSafeMon.SafetyMonitor
{
    /// <summary>
    /// ASCOM Switch Hub Driver - Combines ArduSafeMon rain sensor and OPIR sensors
    /// </summary>
    [Guid("C3D4E5F6-A7B8-6C7D-9E0F-8A9B0C1D2E3F")]
    [ProgId("ASCOM.ArduSafeMon.SwitchHub")]
    [ServedClassName("Wombat Switch Hub")]
    [ClassInterface(ClassInterfaceType.None)]
    [ComVisible(true)]
    public class SwitchHub : ISwitchV2, IDisposable
    {
        internal static string driverID = "ASCOM.ArduSafeMon.SwitchHub";
        private static string driverDescription = "Wombat Switch Hub (All Sensors)";

        private bool connectedState = false;
        internal TraceLogger tl;
        
        private static HttpClient httpClient = new HttpClient() { Timeout = TimeSpan.FromSeconds(5) };
        private const string OPIR_SENSOR_URL = "http://192.168.1.101";
        
        // Cached sensor values
        private double rainSensorValue = 0;
        private double luxValue = 0;
        private double skyTempValue = 0;
        private double ambientTempValue = 0;
        private double ahtTempValue = 0;
        private double ahtHumidityValue = 0;
        private DateTime lastUpdateTime = DateTime.MinValue;
        
        // Switch definitions
        private const int SWITCH_RAIN_SENSOR = 0;
        private const int SWITCH_LUX = 1;
        private const int SWITCH_SKY_TEMP = 2;
        private const int SWITCH_AMBIENT_TEMP = 3;
        private const int SWITCH_AHT_TEMP = 4;
        private const int SWITCH_AHT_HUMIDITY = 5;

        public SwitchHub()
        {
            try
            {
                tl = new TraceLogger("", "Wombat.SwitchHub");
                tl.Enabled = true;
                tl.LogMessage("SwitchHub Constructor", "=== STARTING SWITCH HUB DRIVER ===");
                tl.LogMessage("SwitchHub Constructor", $"Process ID: {System.Diagnostics.Process.GetCurrentProcess().Id}");
                
                ReadProfile();
                tl.LogMessage("SwitchHub Constructor", "Profile read successfully");
                
                // Register as a Switch device in ASCOM Profile
                using (var p = new Profile())
                {
                    p.DeviceType = "Switch";
                    p.Register(driverID, driverDescription);
                }
                
                tl.LogMessage("SwitchHub Constructor", "Completed initialization successfully");
            }
            catch (Exception ex)
            {
                if (tl != null)
                {
                    tl.LogMessage("SwitchHub Constructor", $"ERROR: {ex.Message}");
                    tl.LogMessage("SwitchHub Constructor", $"Stack trace: {ex.StackTrace}");
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
                "ArduSafeMon Switch Hub combines:\n\n" +
                "• Rain sensor data from ArduSafeMon (COM port)\n" +
                "• OPIR sensor data from HTTP (192.168.1.101)\n\n" +
                "Configure the COM port in the SafetyMonitor setup dialog.",
                "ArduSafeMon Switch Hub Setup",
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
                    LogMessage("Connected Set", "Connecting to sensors");
                    
                    try
                    {
                        // Get COM port from SafetyMonitor profile
                        using (Profile driverProfile = new Profile())
                        {
                            driverProfile.DeviceType = "SafetyMonitor";
                            string comPort = driverProfile.GetValue("ASCOM.ArduSafeMon.SafetyMonitor", "COM Port");
                            SharedHardware.ComPort = comPort;
                        }
                        
                        SharedHardware.Connect();
                        LogMessage("Connected Set", "Connected successfully");
                    }
                    catch (Exception ex)
                    {
                        LogMessage("Connected Set", $"ERROR: {ex.Message}");
                        throw;
                    }
                }
                else
                {
                    connectedState = false;
                    LogMessage("Connected Set", "Disconnecting from sensors");
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
                string name = "ArduSafeMon Switch Hub";
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
                // Return 6 (0-5 = 6 switches) to work around clients that need MaxSwitch > 0
                tl.LogMessage("MaxSwitch Get", "Returning 6 (0-5: rain, lux, sky, ambient, aht_temp, aht_hum)");
                return 6;
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
            
            UpdateSensorData();
            
            // Return true if sensor value is within "good" range (simplified)
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    return rainSensorValue < 999; // Safe when < threshold
                case SWITCH_LUX:
                    return luxValue > 0; // Has light
                case SWITCH_SKY_TEMP:
                case SWITCH_AMBIENT_TEMP:
                case SWITCH_AHT_TEMP:
                    return true; // Temperature always "on"
                case SWITCH_AHT_HUMIDITY:
                    return ahtHumidityValue < 90; // Safe when humidity < 90%
                default:
                    throw new ASCOM.InvalidValueException("GetSwitch", id.ToString(), "0-5");
            }
        }

        public string GetSwitchDescription(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    return "Rain sensor analog value (0-1023). Higher = damper.";
                case SWITCH_LUX:
                    return "Light intensity in lux. Higher = brighter.";
                case SWITCH_SKY_TEMP:
                    return "Sky temperature from MLX90614 (°C). Lower = clearer sky.";
                case SWITCH_AMBIENT_TEMP:
                    return "Ambient temperature from MLX90614 (°C).";
                case SWITCH_AHT_TEMP:
                    return "Temperature from AHT10 sensor (°C).";
                case SWITCH_AHT_HUMIDITY:
                    return "Relative humidity from AHT10 (%). Lower = drier.";
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchDescription", id.ToString(), "0-5");
            }
        }

        public string GetSwitchName(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    return "Rain Sensor";
                case SWITCH_LUX:
                    return "Light (Lux)";
                case SWITCH_SKY_TEMP:
                    return "Sky Temperature";
                case SWITCH_AMBIENT_TEMP:
                    return "Ambient Temperature";
                case SWITCH_AHT_TEMP:
                    return "AHT10 Temperature";
                case SWITCH_AHT_HUMIDITY:
                    return "AHT10 Humidity";
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchName", id.ToString(), "0-5");
            }
        }

        public double GetSwitchValue(short id)
        {
            tl.LogMessage("GetSwitchValue", $"Called for switch {id}");
            CheckConnected("GetSwitchValue");
            ValidateSwitchId(id);
            
            tl.LogMessage("GetSwitchValue", "Updating sensor data");
            UpdateSensorData();
            
            double value;
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    value = rainSensorValue;
                    break;
                case SWITCH_LUX:
                    value = luxValue;
                    break;
                case SWITCH_SKY_TEMP:
                    value = skyTempValue;
                    break;
                case SWITCH_AMBIENT_TEMP:
                    value = ambientTempValue;
                    break;
                case SWITCH_AHT_TEMP:
                    value = ahtTempValue;
                    break;
                case SWITCH_AHT_HUMIDITY:
                    value = ahtHumidityValue;
                    break;
                default:
                    throw new ASCOM.InvalidValueException("GetSwitchValue", id.ToString(), "0-5");
            }
            
            tl.LogMessage("GetSwitchValue", $"{GetSwitchName(id)} value: {value}");
            return value;
        }

        public double MaxSwitchValue(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    return 1023.0; // 10-bit ADC
                case SWITCH_LUX:
                    return 100000.0; // Max lux
                case SWITCH_SKY_TEMP:
                case SWITCH_AMBIENT_TEMP:
                case SWITCH_AHT_TEMP:
                    return 50.0; // Max temp °C
                case SWITCH_AHT_HUMIDITY:
                    return 100.0; // Max humidity %
                default:
                    return 100.0;
            }
        }

        public double MinSwitchValue(short id)
        {
            ValidateSwitchId(id);
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                case SWITCH_LUX:
                case SWITCH_AHT_HUMIDITY:
                    return 0.0;
                case SWITCH_SKY_TEMP:
                case SWITCH_AMBIENT_TEMP:
                case SWITCH_AHT_TEMP:
                    return -40.0; // Min temp °C
                default:
                    return 0.0;
            }
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
            switch (id)
            {
                case SWITCH_RAIN_SENSOR:
                    return 1.0; // ADC step
                case SWITCH_LUX:
                    return 0.1;
                case SWITCH_SKY_TEMP:
                case SWITCH_AMBIENT_TEMP:
                case SWITCH_AHT_TEMP:
                    return 0.1; // 0.1°C
                case SWITCH_AHT_HUMIDITY:
                    return 0.1; // 0.1%
                default:
                    return 1.0;
            }
        }

        #endregion

        #region Private methods

        private void UpdateSensorData()
        {
            // Cache for 5 seconds
            if ((DateTime.Now - lastUpdateTime).TotalSeconds < 5)
            {
                return;
            }
            
            try
            {
                // Update rain sensor from SharedHardware
                SharedHardware.UpdateSafetyState();
                rainSensorValue = SharedHardware.RainSensorValue;
                tl.LogMessage("UpdateSensorData", $"Rain sensor: {rainSensorValue}");
                
                // Update OPIR sensors via HTTP
                UpdateOpirSensors();
                
                lastUpdateTime = DateTime.Now;
            }
            catch (Exception ex)
            {
                tl.LogMessage("UpdateSensorData", $"ERROR: {ex.Message}");
            }
        }
        
        private void UpdateOpirSensors()
        {
            try
            {
                tl.LogMessage("UpdateOpirSensors", "Fetching data from OPIR sensor");
                var response = httpClient.GetStringAsync($"{OPIR_SENSOR_URL}/lux").Result;
                
                // Parse simple response format like "123.45"
                if (double.TryParse(response.Trim(), out double lux))
                {
                    luxValue = lux;
                    tl.LogMessage("UpdateOpirSensors", $"Lux: {luxValue}");
                }
                
                response = httpClient.GetStringAsync($"{OPIR_SENSOR_URL}/sky").Result;
                if (double.TryParse(response.Trim(), out double sky))
                {
                    skyTempValue = sky;
                    tl.LogMessage("UpdateOpirSensors", $"Sky temp: {skyTempValue}");
                }
                
                response = httpClient.GetStringAsync($"{OPIR_SENSOR_URL}/ambient").Result;
                if (double.TryParse(response.Trim(), out double ambient))
                {
                    ambientTempValue = ambient;
                    tl.LogMessage("UpdateOpirSensors", $"Ambient temp: {ambientTempValue}");
                }
                
                // Try to get AHT10 values if available
                try
                {
                    response = httpClient.GetStringAsync($"{OPIR_SENSOR_URL}/aht_temp").Result;
                    if (double.TryParse(response.Trim(), out double ahtTemp))
                    {
                        ahtTempValue = ahtTemp;
                    }
                    
                    response = httpClient.GetStringAsync($"{OPIR_SENSOR_URL}/aht_humidity").Result;
                    if (double.TryParse(response.Trim(), out double ahtHum))
                    {
                        ahtHumidityValue = ahtHum;
                    }
                }
                catch
                {
                    // AHT10 endpoints might not exist on older firmware
                    tl.LogMessage("UpdateOpirSensors", "AHT10 values not available");
                }
            }
            catch (Exception ex)
            {
                tl.LogMessage("UpdateOpirSensors", $"ERROR fetching OPIR data: {ex.Message}");
            }
        }

        private void ValidateSwitchId(short id)
        {
            if (id < 0 || id > MaxSwitch - 1)
            {
                throw new ASCOM.InvalidValueException("Switch ID", id.ToString(), $"0 to {MaxSwitch - 1}");
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

        private void WriteProfile()
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
