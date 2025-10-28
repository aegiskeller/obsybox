using System;
using System.IO.Ports;
using System.Text;
using System.Threading;
using ASCOM.Utilities;

namespace ASCOM.ArduSafeMon.SafetyMonitor
{
    /// <summary>
    /// Shared hardware access for ArduSafeMon devices.
    /// Ensures only one COM port connection is used by all driver instances.
    /// </summary>
    internal static class SharedHardware
    {
        private static SerialPort serialPort;
        private static string comPort = "";
        private static int connectionCount = 0;
        private static readonly object hardwareLock = new object();
        
        // Cached sensor data
        private static bool isSafe = false;
        private static string unsafeReason = "";
        private static double rainSensorValue = 0;
        private static DateTime lastUpdateTime = DateTime.MinValue;
        
        private static TraceLogger tl;
        
        // Static constructor to initialize and enable the logger
        static SharedHardware()
        {
            tl = new TraceLogger("", "ArduSafeMon.SharedHardware");
            tl.Enabled = true;  // Always enable logging for SharedHardware
        }

        public static string ComPort
        {
            get { lock (hardwareLock) { return comPort; } }
            set { lock (hardwareLock) { comPort = value; } }
        }

        public static bool IsSafe
        {
            get { lock (hardwareLock) { return isSafe; } }
        }

        public static double RainSensorValue
        {
            get { lock (hardwareLock) { return rainSensorValue; } }
        }

        public static string UnsafeReason
        {
            get { lock (hardwareLock) { return unsafeReason; } }
        }

        /// <summary>
        /// Connect to the hardware. Increments connection count.
        /// </summary>
        public static void Connect()
        {
            lock (hardwareLock)
            {
                connectionCount++;
                tl.LogMessage("Connect", $"Connection count: {connectionCount}");

                if (serialPort != null && serialPort.IsOpen)
                {
                    tl.LogMessage("Connect", "Already connected, reusing connection");
                    return;
                }

                if (string.IsNullOrEmpty(comPort))
                {
                    throw new ASCOM.NotConnectedException("COM Port not configured. Please run Setup.");
                }

                try
                {
                    serialPort = new SerialPort();
                    serialPort.PortName = comPort;
                    serialPort.BaudRate = 9600;
                    serialPort.DataBits = 8;
                    serialPort.Parity = Parity.None;
                    serialPort.StopBits = StopBits.One;
                    serialPort.Handshake = Handshake.None;
                    serialPort.ReadTimeout = 10000;
                    serialPort.WriteTimeout = 1000;
                    serialPort.NewLine = "#";
                    serialPort.DtrEnable = true;  // Reset Arduino on connection
                    serialPort.RtsEnable = false;

                    serialPort.Open();
                    tl.LogMessage("Connect", "Port opened, waiting for Arduino...");

                    // Wait for Arduino to complete its loop cycle
                    Thread.Sleep(5000);

                    // Flush any initial data
                    if (serialPort.BytesToRead > 0)
                    {
                        string initial = serialPort.ReadExisting();
                        tl.LogMessage("Connect", "Initial data: " + initial);
                    }

                    // Test communication with retries
                    bool success = false;
                    for (int attempt = 1; attempt <= 3; attempt++)
                    {
                        tl.LogMessage("Connect", "Communication test attempt " + attempt);
                        try
                        {
                            UpdateSafetyState();
                            success = true;
                            break;
                        }
                        catch (TimeoutException)
                        {
                            tl.LogMessage("Connect", "Attempt " + attempt + " timed out");
                            if (attempt < 3)
                            {
                                Thread.Sleep(1000);
                            }
                        }
                    }

                    if (!success)
                    {
                        throw new TimeoutException("Arduino did not respond after 3 attempts");
                    }

                    tl.LogMessage("Connect", "Connected successfully");
                }
                catch (Exception ex)
                {
                    connectionCount--;
                    tl.LogMessage("Connect", "Error: " + ex.Message);
                    if (serialPort != null && serialPort.IsOpen)
                    {
                        serialPort.Close();
                    }
                    throw new ASCOM.NotConnectedException("Cannot connect to " + comPort + ": " + ex.Message);
                }
            }
        }

        /// <summary>
        /// Disconnect from the hardware. Decrements connection count.
        /// Only closes port when count reaches zero.
        /// </summary>
        public static void Disconnect()
        {
            lock (hardwareLock)
            {
                connectionCount--;
                tl.LogMessage("Disconnect", $"Connection count: {connectionCount}");

                if (connectionCount <= 0)
                {
                    connectionCount = 0;
                    if (serialPort != null && serialPort.IsOpen)
                    {
                        try
                        {
                            serialPort.Close();
                            tl.LogMessage("Disconnect", "Port closed");
                        }
                        catch (Exception ex)
                        {
                            tl.LogMessage("Disconnect", "Error closing port: " + ex.Message);
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Query the Arduino for current safety state.
        /// Updates cached values.
        /// </summary>
        public static void UpdateSafetyState()
        {
            lock (hardwareLock)
            {
                // Check if update is needed (5 second cache)
                if ((DateTime.Now - lastUpdateTime).TotalSeconds < 5)
                {
                    return;
                }

                if (serialPort == null || !serialPort.IsOpen)
                {
                    throw new ASCOM.NotConnectedException("Serial port is not open");
                }

                try
                {
                    // Aggressively clear buffer
                    serialPort.DiscardInBuffer();
                    Thread.Sleep(100);
                    serialPort.DiscardInBuffer();

                    // Send command multiple times
                    serialPort.Write("S#S#S#");
                    tl.LogMessage("UpdateSafetyState", "Sent S# command (x3)");

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
                        tl.LogMessage("UpdateSafetyState", "Received no valid response: " + allData.ToString());
                        throw new TimeoutException("Timeout reading from Arduino");
                    }

                    string fullResponse = allData.ToString();
                    tl.LogMessage("UpdateSafetyState", "Received raw: " + fullResponse);

                    // Parse the response
                    string response = "";
                    if (fullResponse.Contains("notsafe#"))
                    {
                        response = "notsafe";
                    }
                    else if (fullResponse.Contains("safe#"))
                    {
                        response = "safe";
                    }

                    if (response.Equals("safe", StringComparison.OrdinalIgnoreCase))
                    {
                        isSafe = true;
                        unsafeReason = "All conditions normal";
                        tl.LogMessage("UpdateSafetyState", "Status: SAFE");
                    }
                    else if (response.Equals("notsafe", StringComparison.OrdinalIgnoreCase))
                    {
                        isSafe = false;
                        tl.LogMessage("UpdateSafetyState", "Status: NOT SAFE");
                        unsafeReason = ParseUnsafeReason(fullResponse);
                    }
                    else
                    {
                        tl.LogMessage("UpdateSafetyState", "Could not parse status from: " + fullResponse);
                    }

                    // Parse rain sensor value
                    rainSensorValue = ParseRainSensorValue(fullResponse);

                    lastUpdateTime = DateTime.Now;

                    // Discard any remaining debug output
                    Thread.Sleep(100);
                    serialPort.DiscardInBuffer();
                }
                catch (TimeoutException)
                {
                    tl.LogMessage("UpdateSafetyState", "Timeout reading from Arduino");
                    throw new ASCOM.DriverException("Timeout reading from ArduSafeMon");
                }
                catch (Exception ex)
                {
                    tl.LogMessage("UpdateSafetyState", "Error: " + ex.Message);
                    throw new ASCOM.DriverException("Error communicating with ArduSafeMon: " + ex.Message);
                }
            }
        }

        private static double ParseRainSensorValue(string response)
        {
            try
            {
                tl.LogMessage("ParseRainSensorValue", "Parsing response for rain sensor value");
                int idx = response.IndexOf("Rain sensor value:");
                tl.LogMessage("ParseRainSensorValue", $"IndexOf result: {idx}");
                
                if (idx >= 0)  // Changed from > 0 to >= 0 to catch index 0
                {
                    int start = idx + 18;
                    int end = response.IndexOf("(", start);
                    if (end > start)
                    {
                        string valueStr = response.Substring(start, end - start).Trim();
                        tl.LogMessage("ParseRainSensorValue", $"Extracted string: '{valueStr}'");
                        if (double.TryParse(valueStr, out double value))
                        {
                            tl.LogMessage("ParseRainSensorValue", $"Parsed value: {value}");
                            return value;
                        }
                    }
                }
                tl.LogMessage("ParseRainSensorValue", "Failed to find or parse rain sensor value");
            }
            catch (Exception ex)
            {
                tl.LogMessage("ParseRainSensorValue", "Error parsing: " + ex.Message);
            }
            return 0;
        }

        private static string ParseUnsafeReason(string response)
        {
            StringBuilder reasons = new StringBuilder();

            if (response.Contains("Clouds:"))
            {
                int idx = response.IndexOf("Clouds:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        reasons.Append(response.Substring(idx, endIdx - idx).Trim());
                    }
                }
            }

            if (response.Contains("Wind:"))
            {
                int idx = response.IndexOf("Wind:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        if (reasons.Length > 0) reasons.Append("; ");
                        reasons.Append(response.Substring(idx, endIdx - idx).Trim());
                    }
                }
            }

            if (response.Contains("Humidity:"))
            {
                int idx = response.IndexOf("Humidity:");
                if (idx > 0)
                {
                    int endIdx = response.IndexOf("\r", idx);
                    if (endIdx < 0) endIdx = response.IndexOf("\n", idx);
                    if (endIdx > idx)
                    {
                        if (reasons.Length > 0) reasons.Append("; ");
                        reasons.Append(response.Substring(idx, endIdx - idx).Trim());
                    }
                }
            }

            if (response.Contains("Rain detected"))
            {
                if (reasons.Length > 0) reasons.Append("; ");
                reasons.Append("Rain detected");
            }

            return reasons.Length > 0 ? reasons.ToString() : "Unsafe conditions detected";
        }
    }
}
