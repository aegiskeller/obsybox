using System;
using System.IO.Ports;
using System.Windows.Forms;

namespace ASCOM.ArduSafeMon.SafetyMonitor
{
    public partial class SetupDialogForm : Form
    {
        SafetyMonitor driver;

        public SetupDialogForm(SafetyMonitor driver)
        {
            InitializeComponent();
            this.driver = driver;
            InitUI();
        }

        private void InitUI()
        {
            chkTrace.Checked = driver.tl.Enabled;
            
            // Populate COM ports
            comboBoxComPort.Items.Clear();
            comboBoxComPort.Items.AddRange(SerialPort.GetPortNames());
            
            // Set current port
            if (!string.IsNullOrEmpty(driver.ComPort))
            {
                comboBoxComPort.Text = driver.ComPort;
            }
            else if (comboBoxComPort.Items.Count > 0)
            {
                comboBoxComPort.SelectedIndex = 0;
            }
        }

        private void cmdOK_Click(object sender, EventArgs e)
        {
            driver.tl.Enabled = chkTrace.Checked;
            
            if (comboBoxComPort.SelectedItem != null || !string.IsNullOrEmpty(comboBoxComPort.Text))
            {
                driver.ComPort = comboBoxComPort.Text;
            }
            else
            {
                MessageBox.Show("Please select a COM port", "Configuration Error", 
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                DialogResult = DialogResult.None;
                return;
            }
        }

        private void cmdCancel_Click(object sender, EventArgs e)
        {
            Close();
        }

        private void BrowseToAscom(object sender, EventArgs e)
        {
            try
            {
                System.Diagnostics.Process.Start("https://ascom-standards.org/");
            }
            catch (System.ComponentModel.Win32Exception noBrowser)
            {
                if (noBrowser.ErrorCode == -2147467259)
                    MessageBox.Show(noBrowser.Message);
            }
            catch (System.Exception other)
            {
                MessageBox.Show(other.Message);
            }
        }
    }
}
