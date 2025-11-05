// Simple Node-RED Flow for System Monitoring
// Import this into Node-RED to ingest obsybox/system_monitoring data

// 1. MQTT Input Node Configuration:
//    - Topic: obsybox/system_monitoring
//    - Server: 192.168.1.49:1883
//    - QoS: 1
//    - Output: auto-detect (JSON object)

// 2. Function Node - Data Processing:
const data = msg.payload;
const timestamp = new Date();

// Create formatted output for different systems
msg.topic = "system_stats/" + data.hostname;

// For InfluxDB (if using)
msg.influxdb = {
    measurement: "system_stats",
    tags: {
        hostname: data.hostname
    },
    fields: {
        cpu_load: data.cpu_load,
        cpu_temp_c: data.cpu_temp_c || null,
        disk_free_gb: data.disk_free_gb,
        wifi_signal_percent: data.wifi_signal_percent,
        wifi_signal_dbm: data.wifi_signal_dbm
    },
    timestamp: timestamp
};

// For dashboard display
msg.dashboard = {
    hostname: data.hostname,
    cpu_load: data.cpu_load + "%",
    disk_free: data.disk_free_gb + " GB",
    wifi_signal: data.wifi_signal_percent + "% (" + data.wifi_signal_dbm + " dBm)",
    last_update: timestamp.toLocaleString()
};

return msg;

// 3. Output Nodes:
//    - Debug node (to see the data)
//    - InfluxDB out node (for time series storage)
//    - Dashboard template node (for visualization)

// 4. Dashboard Template HTML:
/*
<div style="padding: 10px;">
    <h3>{{msg.payload.hostname}} System Stats</h3>
    <p><strong>CPU Load:</strong> {{msg.payload.cpu_load}}</p>
    <p><strong>Disk Free:</strong> {{msg.payload.disk_free}}</p>
    <p><strong>WiFi Signal:</strong> {{msg.payload.wifi_signal}}</p>
    <p><strong>Last Updated:</strong> {{msg.payload.last_update}}</p>
</div>
*/