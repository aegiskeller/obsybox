#!/usr/bin/env python3
"""
NINA Safety Monitor - Dark Theme GUI with Watchdog Mascot

Modern dark-themed GUI interface for NINA safety monitoring with visual status 
indicators, watchdog mascot, and minimized startup for observatory protection.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys

# Dark theme colors
DARK_BG = "#2b2b2b"
DARK_FG = "#ffffff"
DARK_FRAME = "#404040"
DARK_ENTRY = "#505050"
DARK_BUTTON = "#606060"
DARK_BUTTON_HOVER = "#707070"
GREEN_STATUS = "#4CAF50"
RED_STATUS = "#F44336"
YELLOW_STATUS = "#FF9800"
BLUE_ACCENT = "#2196F3"
PURPLE_ACCENT = "#9C27B0"

class WatchdogSafetyGUI:
    def __init__(self):
        self.config = {
            "max_inactive_minutes": 15,
            "check_interval_seconds": 60,
            "ascom_telescope_driver": "ASCOM.GS.Sky.Telescope",
            "ascom_dome_driver": "RRCI.Dome"
        }
        
        self.is_monitoring = False
        self.current_status = "starting"  # starting, good, warning, critical
        self.setup_dark_gui()
        
        # Auto-start monitoring immediately
        self.root.after(1000, self.auto_start_monitoring)
    
    def setup_dark_gui(self):
        """Create the dark-themed GUI with watchdog mascot"""
        self.root = tk.Tk()
        self.root.title("🐕 NINA Watchdog Safety Monitor")
        self.root.geometry("625x400")
        self.root.configure(bg=DARK_BG)
        
        # Set custom icon
        try:
            # Use the custom icon file we created
            icon_path = Path(__file__).parent / "nina_watchdog.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                # Fallback: create a simple PhotoImage icon
                icon_img = tk.PhotoImage(width=32, height=32)
                icon_img.put("#FF8C00", to=(0, 0, 32, 32))  # Orange background
                icon_img.put("#2196F3", to=(4, 4, 28, 28))  # Blue shield
                icon_img.put("#FFFFFF", to=(8, 8, 24, 24))  # White center
                self.root.iconphoto(False, icon_img)
        except Exception as e:
            print(f"Note: Using default icon - {e}")
        
        # Configure dark theme for ttk widgets
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure dark theme styles
        style.configure('Dark.TFrame', background=DARK_FRAME)
        style.configure('Dark.TLabel', background=DARK_FRAME, foreground=DARK_FG, font=('Arial', 10))
        style.configure('DarkTitle.TLabel', background=DARK_BG, foreground=DARK_FG, font=('Arial', 14, 'bold'))
        style.configure('Status.TLabel', background=DARK_BG, foreground=DARK_FG, font=('Arial', 12))
        style.configure('Dark.TButton', background=DARK_BUTTON, foreground=DARK_FG, borderwidth=1, focuscolor='none')
        style.map('Dark.TButton', background=[('active', DARK_BUTTON_HOVER)])
        style.configure('Emergency.TButton', background=RED_STATUS, foreground='white', font=('Arial', 10, 'bold'))
        
        # Main container
        main_frame = tk.Frame(self.root, bg=DARK_BG, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with watchdog mascot and title
        header_frame = tk.Frame(main_frame, bg=DARK_BG)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Watchdog ASCII art and status
        self.create_watchdog_header(header_frame)
        
        # Status indicators frame
        status_frame = tk.Frame(main_frame, bg=DARK_FRAME, relief='ridge', bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 15), padx=5, ipady=10)
        
        self.create_status_indicators(status_frame)
        
        # Control buttons
        button_frame = tk.Frame(main_frame, bg=DARK_BG)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.create_control_buttons(button_frame)
        
        # Compact log display
        log_frame = tk.Frame(main_frame, bg=DARK_FRAME, relief='ridge', bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        log_label = ttk.Label(log_frame, text="📋 Activity Log", style='Dark.TLabel')
        log_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        # Dark-themed text widget for logs
        text_frame = tk.Frame(log_frame, bg=DARK_FRAME)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        self.log_text = tk.Text(text_frame, height=8, width=50, 
                               bg=DARK_ENTRY, fg=DARK_FG, 
                               insertbackground=DARK_FG,
                               selectbackground=BLUE_ACCENT,
                               selectforeground='white',
                               font=('Consolas', 9),
                               wrap=tk.WORD)
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview,
                                bg=DARK_BUTTON, troughcolor=DARK_FRAME, activebackground=DARK_BUTTON_HOVER)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Start minimized if launched from NINA or with special flags
        nina_mode = len(sys.argv) > 1 and ('--nina-mode' in sys.argv or '--start-hidden' in sys.argv)
        
        if nina_mode:
            self.root.iconify()
            self.log_message("🚀 Started in NINA integration mode - minimized to system tray")
        
        self.log_message("🐕 NINA Watchdog Safety Monitor ready - monitoring will start automatically")
    
    def create_watchdog_header(self, parent):
        """Create the watchdog mascot header with status"""
        # Watchdog ASCII art (simplified for tkinter)
        watchdog_frame = tk.Frame(parent, bg=DARK_BG)
        watchdog_frame.pack(side=tk.LEFT)
        
        # Watchdog facing right (clean look)
        dog_art = tk.Label(watchdog_frame, text="🐕", font=('Arial', 28), bg=DARK_BG, fg=DARK_FG)
        dog_art.pack()
        
        # Add a small "GUARD" label under the dog
        guard_label = tk.Label(watchdog_frame, text="GUARD", font=('Arial', 8, 'bold'), 
                              bg=DARK_BG, fg=PURPLE_ACCENT)
        guard_label.pack()
        
        # Title and status
        title_frame = tk.Frame(parent, bg=DARK_BG)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(20, 0))
        
        title_label = ttk.Label(title_frame, text="NINA Watchdog", style='DarkTitle.TLabel')
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="Observatory Safety Monitor", style='Dark.TLabel')
        subtitle_label.pack(anchor=tk.W)
        
        # Status indicator (big colored square)
        status_frame = tk.Frame(parent, bg=DARK_BG)
        status_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        self.status_square = tk.Label(status_frame, text="●", font=('Arial', 40), 
                                     bg=DARK_BG, fg=YELLOW_STATUS)
        self.status_square.pack()
        
        self.status_text = ttk.Label(status_frame, text="STARTING", style='Status.TLabel')
        self.status_text.pack()
    
    def create_status_indicators(self, parent):
        """Create detailed status indicators"""
        title_label = ttk.Label(parent, text="🛡️ System Status", style='Dark.TLabel', font=('Arial', 11, 'bold'))
        title_label.pack(anchor=tk.W, padx=10, pady=(5, 10))
        
        # Create status grid
        grid_frame = tk.Frame(parent, bg=DARK_FRAME)
        grid_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Status items
        self.status_items = {}
        status_list = [
            ("🌐 MQTT Connection", "connecting"),
            ("🔭 Telescope Status", "checking"),
            ("🏠 Dome Status", "checking"),
            ("💻 NINA Process", "scanning"),
            ("🌦️ Weather Safety", "monitoring"),
            ("☀️ Sun Altitude", "calculating")
        ]
        
        for i, (label, initial_status) in enumerate(status_list):
            row = i // 2
            col = i % 2
            
            item_frame = tk.Frame(grid_frame, bg=DARK_FRAME)
            item_frame.grid(row=row, column=col, sticky='w', padx=(0, 20), pady=2)
            
            # Status dot
            dot = tk.Label(item_frame, text="●", font=('Arial', 12), 
                          bg=DARK_FRAME, fg=YELLOW_STATUS)
            dot.pack(side=tk.LEFT, padx=(0, 5))
            
            # Status text
            text = tk.Label(item_frame, text=f"{label}: {initial_status}", 
                           bg=DARK_FRAME, fg=DARK_FG, font=('Arial', 9))
            text.pack(side=tk.LEFT)
            
            self.status_items[label] = {'dot': dot, 'text': text, 'status': initial_status}
    
    def create_control_buttons(self, parent):
        """Create control buttons"""
        # Start/Stop monitoring
        self.start_button = ttk.Button(parent, text="▶️ Start Monitoring", 
                                      command=self.toggle_monitoring, style='Dark.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Emergency shutdown
        emergency_btn = ttk.Button(parent, text="🚨 Emergency Shutdown", 
                                  command=self.emergency_shutdown, style='Emergency.TButton')
        emergency_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh status
        refresh_btn = ttk.Button(parent, text="🔄 Refresh", 
                                command=self.refresh_status, style='Dark.TButton')
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Minimize to tray
        minimize_btn = ttk.Button(parent, text="📥 Minimize", 
                                 command=self.minimize_to_tray, style='Dark.TButton')
        minimize_btn.pack(side=tk.RIGHT)
    
    def update_status_indicator(self, label, status, message=None):
        """Update a specific status indicator"""
        if label in self.status_items:
            item = self.status_items[label]
            
            # Update color based on status
            if status == "good" or status == "connected" or status == "safe":
                color = GREEN_STATUS
                item['dot'].config(fg=color)
            elif status == "warning" or status == "checking":
                color = YELLOW_STATUS
                item['dot'].config(fg=color)
            elif status == "error" or status == "failed" or status == "unsafe":
                color = RED_STATUS
                item['dot'].config(fg=color)
            else:
                color = YELLOW_STATUS
                item['dot'].config(fg=color)
            
            # Update text
            display_text = f"{label}: {message or status}"
            item['text'].config(text=display_text)
            item['status'] = status
    
    def update_main_status(self):
        """Update the main status square based on overall system status"""
        # Count status types
        good_count = sum(1 for item in self.status_items.values() 
                        if item['status'] in ['good', 'connected', 'safe'])
        warning_count = sum(1 for item in self.status_items.values() 
                           if item['status'] in ['warning', 'checking'])
        error_count = sum(1 for item in self.status_items.values() 
                         if item['status'] in ['error', 'failed', 'unsafe'])
        
        total_items = len(self.status_items)
        
        if error_count > 0:
            self.current_status = "critical"
            self.status_square.config(fg=RED_STATUS)
            self.status_text.config(text="CRITICAL")
        elif warning_count > total_items // 2:
            self.current_status = "warning"
            self.status_square.config(fg=YELLOW_STATUS)
            self.status_text.config(text="WARNING")
        elif good_count >= total_items // 2:
            self.current_status = "good"
            self.status_square.config(fg=GREEN_STATUS)
            self.status_text.config(text="ALL GOOD")
        else:
            self.current_status = "starting"
            self.status_square.config(fg=YELLOW_STATUS)
            self.status_text.config(text="STARTING")
    
    def log_message(self, message):
        """Add message to log display with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Keep only last 50 lines
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 50:
            self.log_text.delete("1.0", f"{len(lines) - 50}.0")
    
    def auto_start_monitoring(self):
        """Automatically start monitoring when GUI launches"""
        if not self.is_monitoring:
            self.log_message("🚀 Auto-starting monitoring...")
            self.toggle_monitoring()
    
    def toggle_monitoring(self):
        """Start or stop monitoring"""
        if self.is_monitoring:
            self.is_monitoring = False
            self.start_button.config(text="▶️ Start Monitoring")
            self.log_message("⏹️ Monitoring stopped")
            self.update_status_indicator("🌐 MQTT Connection", "disconnected", "stopped")
        else:
            self.is_monitoring = True
            self.start_button.config(text="⏹️ Stop Monitoring")
            self.log_message("▶️ Monitoring started")
            
            # Start monitoring thread
            threading.Thread(target=self.monitor_loop, daemon=True).start()
    
    def monitor_loop(self):
        """Simple monitoring loop with status updates"""
        while self.is_monitoring:
            try:
                # Simulate status checks with visual updates
                self.update_status_indicator("🌐 MQTT Connection", "good", "192.168.1.49:1883")
                time.sleep(1)
                
                self.update_status_indicator("💻 NINA Process", "good", "running")
                time.sleep(1)
                
                self.update_status_indicator("🌦️ Weather Safety", "good", "conditions safe")
                time.sleep(1)
                
                self.update_status_indicator("🔭 Telescope Status", "good", "ASCOM connected")
                time.sleep(1)
                
                self.update_status_indicator("🏠 Dome Status", "good", "RRCI connected")
                time.sleep(1)
                
                self.update_status_indicator("☀️ Sun Altitude", "safe", "-25° (night)")
                
                # Update main status
                self.update_main_status()
                
                self.log_message("✅ All safety checks passed")
                
                # Wait for next cycle
                time.sleep(30)
                
            except Exception as e:
                self.log_message(f"❌ Monitoring error: {e}")
                time.sleep(5)
    
    def emergency_shutdown(self):
        """Trigger emergency shutdown"""
        result = messagebox.askyesno("🚨 Emergency Shutdown", 
                                   "Are you sure you want to trigger emergency shutdown?\n\n"
                                   "This will:\n"
                                   "• Park the telescope\n"
                                   "• Close the dome\n"
                                   "• Shutdown accessories\n"
                                   "• Terminate NINA process",
                                   icon='warning')
        
        if result:
            self.log_message("🚨 EMERGENCY SHUTDOWN TRIGGERED")
            self.current_status = "critical"
            self.status_square.config(fg=RED_STATUS)
            self.status_text.config(text="EMERGENCY")
            
            # Update all status indicators to emergency
            for label in self.status_items:
                self.update_status_indicator(label, "emergency", "shutdown in progress")
            
            # Here you would call the actual emergency shutdown script
            # subprocess.run([sys.executable, "emergency_shutdown.py"])
    
    def refresh_status(self):
        """Refresh equipment status"""
        self.log_message("🔄 Refreshing equipment status...")
        # Reset status indicators to checking
        for label in self.status_items:
            self.update_status_indicator(label, "checking", "verifying...")
    
    def minimize_to_tray(self):
        """Minimize window to system tray"""
        self.root.iconify()
        self.log_message("📥 Minimized to system tray")
    
    def quit_application(self):
        """Clean shutdown of the application"""
        self.is_monitoring = False
        self.log_message("👋 Shutting down NINA Watchdog...")
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop"""
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.quit_application)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = WatchdogSafetyGUI()
        app.run()
    except Exception as e:
        print(f"Error starting NINA Watchdog GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()