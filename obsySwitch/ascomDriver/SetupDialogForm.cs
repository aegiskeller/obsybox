using System;
using System.Drawing;
using System.IO.Ports;
using System.Linq;
using System.Windows.Forms;
using ASCOM.Utilities;

namespace ASCOM.ObsyBox.RelaySwitch
{
    public partial class SetupDialogForm : Form
    {
        private TraceLogger tl;

        public SetupDialogForm(Switch driver)
        {
            InitializeComponent();

            // Initialize trace logger
            tl = new TraceLogger("", "ObsyBoxRelaySwitch.Setup");
            tl.Enabled = true;
            tl.LogMessage("SetupDialogForm", "Setup dialog created");

            // Set up the list of COM ports
            comboBoxComPort.Items.Clear();
            comboBoxComPort.Items.AddRange(SerialPort.GetPortNames());
            comboBoxComPort.Text = driver.SerialPort;

            // Initialize other controls
            textBoxBaudRate.Text = driver.BaudRate.ToString();
            textBoxTimeout.Text = driver.TimeoutMs.ToString();

            // Initialize switch names
            string[] switchNames = driver.SwitchNames;
            textBoxSwitch0.Text = switchNames[0];
            textBoxSwitch1.Text = switchNames[1];
            textBoxSwitch2.Text = switchNames[2];
            textBoxSwitch3.Text = switchNames[3];

            // Set the trace checkbox
            chkTrace.Checked = tl.Enabled;

            // Set up the ASCOM logo
            try
            {
                // Try to load ASCOM logo from resources
                picASCOM.Image = Properties.Resources.ASCOM;
            }
            catch
            {
                // If logo not available, just leave it blank
                picASCOM.Visible = false;
            }

            tl.LogMessage("SetupDialogForm", "Setup dialog initialized");
        }

        private void cmdOK_Click(object sender, EventArgs e)
        {
            tl.LogMessage("cmdOK_Click", "OK button clicked");

            // Validate settings
            if (!ValidateSettings())
            {
                return;
            }

            // Update the driver with the new settings
            Switch driver = (Switch)((Form)this).Tag;
            if (driver != null)
            {
                driver.SerialPort = comboBoxComPort.Text;
                
                if (int.TryParse(textBoxBaudRate.Text, out int baudRate))
                {
                    driver.BaudRate = baudRate;
                }
                
                if (int.TryParse(textBoxTimeout.Text, out int timeout))
                {
                    driver.TimeoutMs = timeout;
                }

                // Update switch names
                string[] switchNames = new string[4];
                switchNames[0] = textBoxSwitch0.Text.Trim();
                switchNames[1] = textBoxSwitch1.Text.Trim();
                switchNames[2] = textBoxSwitch2.Text.Trim();
                switchNames[3] = textBoxSwitch3.Text.Trim();
                driver.SwitchNames = switchNames;
            }

            tl.LogMessage("cmdOK_Click", "Settings updated successfully");
        }

        private void cmdCancel_Click(object sender, EventArgs e)
        {
            tl.LogMessage("cmdCancel_Click", "Cancel button clicked");
        }

        private void picASCOM_Click(object sender, EventArgs e)
        {
            try
            {
                System.Diagnostics.Process.Start("https://ascom-standards.org/");
            }
            catch (System.ComponentModel.Win32Exception noBrowser)
            {
                if (noBrowser.ErrorCode == -2147467259)
                    MessageBox.Show("No web browser is available to open the ASCOM website.");
            }
            catch (System.Exception other)
            {
                MessageBox.Show($"Error opening ASCOM website: {other.Message}");
            }
        }

        private void buttonTestConnection_Click(object sender, EventArgs e)
        {
            tl.LogMessage("buttonTestConnection_Click", "Testing connection");
            
            if (!ValidateSettings())
            {
                labelConnectionStatus.Text = "Please fix validation errors first";
                labelConnectionStatus.ForeColor = Color.Red;
                return;
            }

            try
            {
                labelConnectionStatus.Text = "Testing connection...";
                labelConnectionStatus.ForeColor = Color.Blue;
                Application.DoEvents();

                // Test serial port connection
                using (SerialPort testPort = new SerialPort(comboBoxComPort.Text, 
                    int.Parse(textBoxBaudRate.Text), Parity.None, 8, StopBits.One))
                {
                    testPort.Timeout = int.Parse(textBoxTimeout.Text);
                    testPort.WriteTimeout = testPort.Timeout;
                    testPort.ReadTimeout = testPort.Timeout;

                    tl.LogMessage("buttonTestConnection_Click", $"Opening port {comboBoxComPort.Text}");
                    testPort.Open();

                    // Wait for Arduino to initialize
                    System.Threading.Thread.Sleep(2000);

                    // Send ping command
                    testPort.WriteLine("PING");
                    tl.LogMessage("buttonTestConnection_Click", "Sent PING command");

                    // Read response
                    DateTime startTime = DateTime.Now;
                    string response = "";
                    
                    while ((DateTime.Now - startTime).TotalMilliseconds < testPort.Timeout)
                    {
                        try
                        {
                            string line = testPort.ReadLine().Trim();
                            
                            if (line.StartsWith("#"))
                            {
                                // Debug message, continue
                                continue;
                            }
                            
                            if (line.Contains("PONG"))
                            {
                                response = line;
                                break;
                            }
                        }
                        catch (TimeoutException)
                        {
                            continue;
                        }
                    }

                    testPort.Close();

                    if (response.Contains("PONG"))
                    {
                        labelConnectionStatus.Text = "✅ Connection successful! Arduino responding.";
                        labelConnectionStatus.ForeColor = Color.Green;
                        tl.LogMessage("buttonTestConnection_Click", "Connection test successful");
                    }
                    else
                    {
                        labelConnectionStatus.Text = "❌ Arduino not responding. Check sketch and wiring.";
                        labelConnectionStatus.ForeColor = Color.Red;
                        tl.LogMessage("buttonTestConnection_Click", "Arduino not responding");
                    }
                }
            }
            catch (UnauthorizedAccessException)
            {
                labelConnectionStatus.Text = "❌ Port in use by another application.";
                labelConnectionStatus.ForeColor = Color.Red;
                tl.LogMessage("buttonTestConnection_Click", "Port access denied");
            }
            catch (Exception ex)
            {
                labelConnectionStatus.Text = $"❌ Connection failed: {ex.Message}";
                labelConnectionStatus.ForeColor = Color.Red;
                tl.LogMessage("buttonTestConnection_Click", $"Connection test failed: {ex.Message}");
            }
        }

        private bool ValidateSettings()
        {
            // Validate COM port
            if (string.IsNullOrEmpty(comboBoxComPort.Text))
            {
                MessageBox.Show("Please select a COM port.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                comboBoxComPort.Focus();
                return false;
            }

            // Validate baud rate
            if (!int.TryParse(textBoxBaudRate.Text, out int baudRate) || baudRate <= 0)
            {
                MessageBox.Show("Please enter a valid baud rate.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                textBoxBaudRate.Focus();
                return false;
            }

            // Validate timeout
            if (!int.TryParse(textBoxTimeout.Text, out int timeout) || timeout <= 0)
            {
                MessageBox.Show("Please enter a valid timeout value.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                textBoxTimeout.Focus();
                return false;
            }

            // Validate switch names are not empty
            if (string.IsNullOrWhiteSpace(textBoxSwitch0.Text) ||
                string.IsNullOrWhiteSpace(textBoxSwitch1.Text) ||
                string.IsNullOrWhiteSpace(textBoxSwitch2.Text) ||
                string.IsNullOrWhiteSpace(textBoxSwitch3.Text))
            {
                MessageBox.Show("All switch names must be specified.", "Validation Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return false;
            }

            tl.LogMessage("ValidateSettings", "All settings validated successfully");
            return true;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                tl?.LogMessage("Dispose", "Disposing setup dialog");
                components?.Dispose();
                tl?.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}