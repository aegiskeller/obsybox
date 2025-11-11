#!/usr/bin/env python3
"""
NINA Variable Star Target Selector GUI

A graphical interface for selecting and generating variable star targets
for NINA observation sequences. Uses a midnight/dark astronomy theme.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from pathlib import Path
from datetime import date, datetime, timedelta
import threading
import queue
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

# Import the main target finding functionality
from findTargets import (
    fetch_minima_predictions,
    select_targets_for_night,
    export_to_nina_format,
    export_to_nina_json,
    record_scheduled_targets,
    format_target_display_name,
    NINA_EXPORT_BASE_DIR
)

# Import configuration management
try:
    from config import load_config, save_config, update_config_from_gui_values, get_flat_config
    config = get_flat_config()
    LATITUDE = config['LATITUDE']
    LONGITUDE = config['LONGITUDE']
    MAG_MIN = config['MAG_MIN']
    MAG_MAX = config['MAG_MAX']
    MIN_ALTITUDE = config['MIN_ALTITUDE']
    MIN_ALTITUDE_DURING_OBS = config['MIN_ALTITUDE_DURING_OBS']
    MIN_DECLINATION = config['MIN_DECLINATION']
    MAX_DECLINATION = config['MAX_DECLINATION']
    OBSERVATION_WINDOW = config['OBSERVATION_WINDOW']
    TARGET_SPACING = config['TARGET_SPACING']
    CENTER_AFTER_DRIFT_ARCMIN = config['CENTER_AFTER_DRIFT_ARCMIN']
    MAX_TARGETS_PER_NIGHT = config['MAX_TARGETS_PER_NIGHT']
    TIMEZONE_OFFSET = config['TIMEZONE_OFFSET']
    ALLOWED_AZIMUTHS = config['ALLOWED_AZIMUTHS']
    ALLOW_G_TARGETS = config['ALLOW_G_TARGETS']
except ImportError:
    # Fallback to importing from findTargets if config module not available
    from findTargets import (
        LATITUDE, LONGITUDE, MAG_MIN, MAG_MAX, MIN_ALTITUDE,
        ALLOWED_AZIMUTHS, MIN_DECLINATION, MAX_DECLINATION,
        OBSERVATION_WINDOW, MIN_ALTITUDE_DURING_OBS, TARGET_SPACING,
        CENTER_AFTER_DRIFT_ARCMIN, MAX_TARGETS_PER_NIGHT, TIMEZONE_OFFSET
    )
    ALLOW_G_TARGETS = True  # Default fallback value

# Midnight color scheme
COLORS = {
    'bg_dark': '#0a0e27',        # Deep midnight blue
    'bg_medium': '#151b3d',      # Medium dark blue
    'bg_light': '#1e2749',       # Lighter midnight blue
    'accent': '#4a5fb5',         # Soft blue accent
    'accent_hover': '#5d72c9',   # Lighter blue for hover
    'text': '#e0e6ff',           # Light blue-white text
    'text_dim': '#8b95c9',       # Dimmed text
    'success': '#4ecca3',        # Mint green for success
    'warning': '#ffd93d',        # Golden yellow for warnings
    'error': '#ff6b6b',          # Soft red for errors
    'button': '#90ee90',         # Light green button background
    'button_hover': '#7dd87d',   # Darker green for hover
    'button_text': '#000000',    # Black text for buttons
}


class LogHandler:
    """Custom handler to redirect log output to GUI"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        
    def write(self, message):
        self.queue.put(message)
        
    def flush(self):
        pass


class TargetSelectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NINA Variable Star Target Selector")
        self.root.geometry("900x910")  # Increased height by 30% (700 → 910)
        self.root.configure(bg=COLORS['bg_dark'])
        
        # Initialize variables early (before creating UI components that reference them)
        self.all_targets = []
        self.selected_targets = []
        self.observation_date = date.today()  # Current observation date
        
        # Progress animation variables
        self.progress_running = False
        self.progress_frame = 0
        self.star_sizes = ['✦', '✧', '★', '✧', '✦']  # Different star characters for pulsating effect
        
        # Configure style
        self.setup_styles()
        
        # Create main container with padding
        main_container = tk.Frame(root, bg=COLORS['bg_dark'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title row with logo and date
        title_frame = tk.Frame(main_container, bg=COLORS['bg_dark'])
        title_frame.pack(pady=(0, 5), fill='x')
        
        # Logo/Title (smaller, on the left)
        title_label = tk.Label(
            title_frame,
            text="〰️ Variable Star Target Selector",
            font=('Helvetica', 14, 'bold'),  # Reduced from 20 to 14 (30% smaller)
            bg=COLORS['bg_dark'],
            fg='#ff4444'
        )
        title_label.pack(side='left')
        
        # Current observation date (on the right)
        self.main_date_label = tk.Label(
            title_frame,
            text=f"Obs Night: {self.observation_date.strftime('%Y-%m-%d')}",
            font=('Helvetica', 12, 'bold'),
            bg=COLORS['bg_dark'],
            fg=COLORS['success'],  # Use green color to make it stand out
            anchor='e'
        )
        self.main_date_label.pack(side='right', padx=(20, 0))
        
        # Subtitle (centered)
        subtitle_label = tk.Label(
            main_container,
            text="Designed for EB selection from Varastro.cz ephemera",
            font=('Helvetica', 10, 'italic'),
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim']
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.config_frame = self.create_config_tab()
        self.targets_frame = self.create_targets_tab()
        self.airmass_frame = self.create_airmass_tab()
        self.log_frame = self.create_log_tab()
        
        self.notebook.add(self.config_frame, text="  Configuration  ")
        self.notebook.add(self.targets_frame, text="  Targets  ")
        self.notebook.add(self.airmass_frame, text="  Airmass Plot  ")
        self.notebook.add(self.log_frame, text="  Log  ")
        
        # Status bar
        self.status_label = tk.Label(
            main_container,
            text="Ready to generate targets",
            bg=COLORS['bg_medium'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 9),
            anchor='w',
            padx=10,
            pady=5
        )
        self.status_label.pack(fill='x', pady=(10, 0))
        
    def setup_styles(self):
        """Configure ttk styles for midnight theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook style
        style.configure('TNotebook', background=COLORS['bg_dark'], borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=COLORS['bg_medium'],
                       foreground=COLORS['text_dim'],
                       padding=[20, 10],
                       borderwidth=0)
        style.map('TNotebook.Tab',
                 background=[('selected', COLORS['bg_light'])],
                 foreground=[('selected', COLORS['text'])])
        
        # Frame style
        style.configure('TFrame', background=COLORS['bg_dark'])
        style.configure('Card.TFrame', background=COLORS['bg_light'], relief='flat')
        
        # Label style
        style.configure('TLabel',
                       background=COLORS['bg_light'],
                       foreground=COLORS['text'],
                       font=('Helvetica', 10))
        style.configure('Title.TLabel',
                       background=COLORS['bg_light'],
                       foreground=COLORS['text'],
                       font=('Helvetica', 11, 'bold'))
        
        # Entry style
        style.configure('TEntry',
                       fieldbackground=COLORS['bg_medium'],
                       foreground=COLORS['text'],
                       borderwidth=1,
                       relief='flat')
        
    def create_config_tab(self):
        """Create the configuration tab"""
        frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        
        # Create scrollable canvas
        canvas = tk.Canvas(frame, bg=COLORS['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_dark'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add logo at the top
        try:
            from PIL import Image, ImageTk
            logo_path = Path(__file__).parent / "varstar_logo.png"
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                # Resize logo to reasonable size (keeping aspect ratio)
                logo_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label = tk.Label(
                    scrollable_frame,
                    image=self.logo_photo,
                    bg=COLORS['bg_dark']
                )
                logo_label.pack(pady=(10, 20))
        except Exception as e:
            # Silently fail if logo can't be loaded
            pass
        
        # Location settings card
        self.create_card(scrollable_frame, "📍 Observer Location", [
            ("Latitude (°)", "latitude", LATITUDE, "Decimal degrees (-90 to 90)"),
            ("Longitude (°)", "longitude", LONGITUDE, "Decimal degrees (-180 to 180)"),
            ("Timezone Offset (hrs)", "timezone", TIMEZONE_OFFSET, "Hours ahead of UTC (e.g., 10 for UTC+10)")
        ])
        
        # Magnitude settings card
        self.create_card(scrollable_frame, "✨ Magnitude Range", [
            ("Minimum Magnitude", "mag_min", MAG_MIN, "Dimmest stars to include"),
            ("Maximum Magnitude", "mag_max", MAG_MAX, "Brightest stars to include")
        ])
        
        # Altitude settings card
        self.create_card(scrollable_frame, "📐 Altitude Constraints", [
            ("Min Altitude at Minima (°)", "min_alt", MIN_ALTITUDE, "Minimum elevation at minima time"),
            ("Min Altitude During Obs (°)", "min_alt_obs", MIN_ALTITUDE_DURING_OBS, "Minimum altitude during observation window")
        ])
        
        # Declination settings card
        self.create_card(scrollable_frame, "🌐 Declination Range", [
            ("Minimum Declination (°)", "min_dec", MIN_DECLINATION, "Minimum declination to observe"),
            ("Maximum Declination (°)", "max_dec", MAX_DECLINATION, "Maximum declination to observe")
        ])
        
        # Observation settings card
        self.create_card(scrollable_frame, "⏱️ Observation Parameters", [
            ("Observation Window (hrs)", "obs_window", OBSERVATION_WINDOW, "Hours of observation per target"),
            ("Target Spacing (hrs)", "target_spacing", TARGET_SPACING, "Hours between target minima"),
            ("Drift Tolerance (arcmin)", "drift_tolerance", CENTER_AFTER_DRIFT_ARCMIN, "Center after drift threshold"),
            ("Max Targets per Night", "max_targets", MAX_TARGETS_PER_NIGHT, "Maximum number of targets to select")
        ])
        
        # Azimuth settings card (checkboxes)
        self.create_azimuth_card(scrollable_frame)
        
        # Target constraints card (checkboxes)
        self.create_target_constraints_card(scrollable_frame)
        
        # Export paths card
        self.create_export_paths_card(scrollable_frame)
        
        # Date display and Generate button
        button_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_dark'])
        button_frame.pack(fill='x', padx=20, pady=20)
        
        # Current date display with refresh button
        date_frame = tk.Frame(button_frame, bg=COLORS['bg_dark'])
        date_frame.pack(pady=(0, 10))
        
        self.date_label = tk.Label(
            date_frame,
            text=f"Target Date: {self.observation_date.strftime('%Y-%m-%d')}",
            bg=COLORS['bg_dark'],
            fg=COLORS['text'],
            font=('Helvetica', 11, 'bold')
        )
        self.date_label.pack(side='left')
        
        # Small refresh button for date
        refresh_date_button = tk.Button(
            date_frame,
            text="🔄",
            command=self.refresh_date,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            font=('Helvetica', 8),
            relief='flat',
            padx=5,
            pady=2,
            cursor='hand2'
        )
        refresh_date_button.pack(side='left', padx=(10, 0))
        
        # Reset to defaults button
        reset_button = tk.Button(
            button_frame,
            text="⚙️ Reset Defaults",
            command=self.reset_to_defaults,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            font=('Helvetica', 10),
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        reset_button.pack(side='left', padx=(15, 0))
        reset_button.bind('<Enter>', lambda e: reset_button.configure(bg=COLORS['accent_hover']))
        reset_button.bind('<Leave>', lambda e: reset_button.configure(bg=COLORS['bg_medium']))
        
        # Clear cache button  
        cache_button = tk.Button(
            button_frame,
            text="🗑️ Clear Cache",
            command=self.clear_cache,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            font=('Helvetica', 10),
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        cache_button.pack(side='left', padx=(15, 0))
        cache_button.bind('<Enter>', lambda e: cache_button.configure(bg=COLORS['accent_hover']))
        cache_button.bind('<Leave>', lambda e: cache_button.configure(bg=COLORS['bg_medium']))
        
        self.generate_button = tk.Button(
            button_frame,
            text="🎯 Generate Targets",
            command=self.generate_targets,
            bg=COLORS['button'],
            fg=COLORS['button_text'],
            font=('Helvetica', 14, 'bold'),
            relief='flat',
            padx=30,
            pady=15,
            cursor='hand2'
        )
        self.generate_button.pack(side='right')
        
        # Bind hover effects
        self.generate_button.bind('<Enter>', lambda e: self.generate_button.configure(bg=COLORS['button_hover']))
        self.generate_button.bind('<Leave>', lambda e: self.generate_button.configure(bg=COLORS['button']))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return frame
    
    def create_card(self, parent, title, fields):
        """Create a settings card with fields"""
        card = tk.Frame(parent, bg=COLORS['bg_light'], relief='flat')
        card.pack(fill='x', padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            card,
            text=title,
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            font=('Helvetica', 12, 'bold')
        )
        title_label.pack(anchor='w', padx=15, pady=(15, 10))
        
        # Fields
        if not hasattr(self, 'entries'):
            self.entries = {}
            
        for label_text, key, default, tooltip in fields:
            field_frame = tk.Frame(card, bg=COLORS['bg_light'])
            field_frame.pack(fill='x', padx=15, pady=5)
            
            # Label
            label = tk.Label(
                field_frame,
                text=label_text,
                bg=COLORS['bg_light'],
                fg=COLORS['text'],
                font=('Helvetica', 10),
                width=25,
                anchor='w'
            )
            label.pack(side='left', padx=(0, 10))
            
            # Entry
            entry = tk.Entry(
                field_frame,
                bg=COLORS['bg_medium'],
                fg=COLORS['text'],
                font=('Helvetica', 10),
                relief='flat',
                insertbackground=COLORS['text']
            )
            entry.insert(0, str(default))
            entry.pack(side='left', fill='x', expand=True, ipady=5)
            
            self.entries[key] = entry
            
            # Tooltip label
            tooltip_label = tk.Label(
                field_frame,
                text=f"  ⓘ",
                bg=COLORS['bg_light'],
                fg=COLORS['text_dim'],
                font=('Helvetica', 9)
            )
            tooltip_label.pack(side='left', padx=(5, 0))
            
            # Bind tooltip
            self.create_tooltip(tooltip_label, tooltip)
        
        # Bottom padding
        tk.Frame(card, bg=COLORS['bg_light'], height=10).pack()
    
    def create_azimuth_card(self, parent):
        """Create azimuth selection card with checkboxes"""
        card = tk.Frame(parent, bg=COLORS['bg_light'], relief='flat')
        card.pack(fill='x', padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            card,
            text="🧭 Allowed Azimuths",
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            font=('Helvetica', 12, 'bold')
        )
        title_label.pack(anchor='w', padx=15, pady=(15, 10))
        
        # Checkbox frame
        checkbox_frame = tk.Frame(card, bg=COLORS['bg_light'])
        checkbox_frame.pack(fill='x', padx=15, pady=5)
        
        self.azimuth_vars = {}
        azimuths = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        
        for az in azimuths:
            var = tk.BooleanVar(value=az in ALLOWED_AZIMUTHS)
            self.azimuth_vars[az] = var
            
            cb = tk.Checkbutton(
                checkbox_frame,
                text=az,
                variable=var,
                bg=COLORS['bg_light'],
                fg=COLORS['text'],
                selectcolor=COLORS['bg_medium'],
                activebackground=COLORS['bg_light'],
                activeforeground=COLORS['text'],
                font=('Helvetica', 10)
            )
            cb.pack(side='left', padx=10, pady=5)
        
        # Bottom padding
        tk.Frame(card, bg=COLORS['bg_light'], height=10).pack()
    
    def create_target_constraints_card(self, parent):
        """Create target constraints card with checkboxes"""
        card = tk.Frame(parent, bg=COLORS['bg_light'], relief='flat')
        card.pack(fill='x', padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            card,
            text="🎯 Target Constraints",
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            font=('Helvetica', 12, 'bold')
        )
        title_label.pack(anchor='w', padx=15, pady=(15, 10))
        
        # Checkbox frame
        checkbox_frame = tk.Frame(card, bg=COLORS['bg_light'])
        checkbox_frame.pack(fill='x', padx=15, pady=5)
        
        # G-targets checkbox
        self.allow_g_targets_var = tk.BooleanVar(value=ALLOW_G_TARGETS)
        
        g_targets_cb = tk.Checkbutton(
            checkbox_frame,
            text="Allow Gxxxx.yyyyy targets",
            variable=self.allow_g_targets_var,
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            selectcolor=COLORS['bg_medium'],
            activebackground=COLORS['bg_light'],
            activeforeground=COLORS['text'],
            font=('Helvetica', 10)
        )
        g_targets_cb.pack(side='left', padx=10, pady=5)
        
        # Add tooltip for explanation
        self.create_tooltip(g_targets_cb, 
            "When unchecked, excludes catalog targets of the form 'G1234.56789' "
            "from target selection. These are typically WDS double star catalog entries.")
        
        # Bottom padding
        tk.Frame(card, bg=COLORS['bg_light'], height=10).pack()
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(
                tooltip,
                text=text,
                bg=COLORS['bg_medium'],
                fg=COLORS['text'],
                relief='solid',
                borderwidth=1,
                font=('Helvetica', 9),
                padx=10,
                pady=5
            )
            label.pack()
            
            widget.tooltip = tooltip
            
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
                
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def create_export_paths_card(self, parent):
        """Create export paths card"""
        card = tk.Frame(parent, bg=COLORS['bg_light'], relief='flat')
        card.pack(fill='x', padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            card,
            text="📁 Export Paths",
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            font=('Helvetica', 12, 'bold')
        )
        title_label.pack(anchor='w', padx=15, pady=(15, 10))
        
        # Individual targets export path
        targets_frame = tk.Frame(card, bg=COLORS['bg_light'])
        targets_frame.pack(fill='x', padx=15, pady=5)
        
        targets_label = tk.Label(
            targets_frame,
            text="Individual Targets:",
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            font=('Helvetica', 10),
            width=20,
            anchor='w'
        )
        targets_label.pack(side='left', padx=(0, 10))
        
        self.nina_export_base_dir_entry = tk.Entry(
            targets_frame,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            font=('Helvetica', 10),
            relief='flat',
            insertbackground=COLORS['text']
        )
        self.nina_export_base_dir_entry.insert(0, str(NINA_EXPORT_BASE_DIR))
        self.nina_export_base_dir_entry.pack(side='left', fill='x', expand=True, ipady=5)
        
        # Tooltip for individual targets path
        targets_tooltip_label = tk.Label(
            targets_frame,
            text="  ⓘ",
            bg=COLORS['bg_light'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 9)
        )
        targets_tooltip_label.pack(side='left', padx=(5, 0))
        self.create_tooltip(targets_tooltip_label, "Directory for individual target JSON files")
        
        # Bottom padding
        tk.Frame(card, bg=COLORS['bg_light'], height=10).pack()
    
    def create_targets_tab(self):
        """Create the targets display tab"""
        frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        
        # Info label
        info_label = tk.Label(
            frame,
            text="Selected targets will appear here after generation",
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 10)
        )
        info_label.pack(pady=20)
        
        # Targets display area
        self.targets_text = scrolledtext.ScrolledText(
            frame,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            font=('Courier', 10),
            relief='flat',
            padx=20,
            pady=20,
            insertbackground=COLORS['text']
        )
        self.targets_text.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Export path info frame
        export_info_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        export_info_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Export path label
        export_path_text = self.get_export_path_display()
        self.export_path_label = tk.Label(
            export_info_frame,
            text=f"📁 Export Path: {export_path_text}",
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 9),
            anchor='w'
        )
        self.export_path_label.pack(fill='x')

        # Buttons frame
        buttons_frame = tk.Frame(frame, bg=COLORS['bg_dark'])
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.export_button = tk.Button(
            buttons_frame,
            text="💾 Export Individual JSON",
            command=self.export_nina_json,
            bg=COLORS['button'],
            fg=COLORS['button_text'],
            font=('Helvetica', 11, 'bold'),
            relief='flat',
            padx=20,
            pady=10,
            cursor='hand2',
            state='disabled'
        )
        self.export_button.pack(side='left', padx=(0, 5))
        
        self.export_csv_button = tk.Button(
            buttons_frame,
            text="📊 Export CSV",
            command=self.export_csv,
            bg=COLORS['button'],
            fg=COLORS['button_text'],
            font=('Helvetica', 11, 'bold'),
            relief='flat',
            padx=20,
            pady=10,
            cursor='hand2',
            state='disabled'
        )
        self.export_csv_button.pack(side='left')
        
        return frame
    
    def create_airmass_tab(self):
        """Create the airmass plot tab"""
        frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        
        # Info label
        info_label = tk.Label(
            frame,
            text="Airmass curves will appear here after target generation",
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 10)
        )
        info_label.pack(pady=20)
        
        # Container for matplotlib figure
        self.plot_container = tk.Frame(frame, bg=COLORS['bg_dark'])
        self.plot_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        return frame
    
    def create_log_tab(self):
        """Create the log display tab"""
        frame = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        
        # Log display area
        self.log_text = scrolledtext.ScrolledText(
            frame,
            bg=COLORS['bg_medium'],
            fg=COLORS['text_dim'],
            font=('Courier', 9),
            relief='flat',
            padx=20,
            pady=20,
            insertbackground=COLORS['text']
        )
        self.log_text.pack(fill='both', expand=True, padx=20, pady=20)
        
        return frame
    
    def log_message(self, message, level='info'):
        """Add a message to the log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Color based on level
        colors = {
            'info': COLORS['text_dim'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['error']
        }
        color = colors.get(level, COLORS['text_dim'])
        
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.log_text.update()
    
    def update_status(self, message, color=None):
        """Update the status bar"""
        self.status_label.config(
            text=message,
            fg=color or COLORS['text_dim']
        )
        self.root.update()
    
    def start_progress_animation(self):
        """Start the pulsating star progress animation"""
        self.progress_running = True
        self.progress_frame = 0
        self._animate_progress()
    
    def stop_progress_animation(self):
        """Stop the progress animation"""
        self.progress_running = False
    
    def _animate_progress(self):
        """Animate the pulsating star in the status bar"""
        if not self.progress_running:
            return
        
        star = self.star_sizes[self.progress_frame % len(self.star_sizes)]
        self.update_status(f"{star} Fetching minima predictions... {star}", COLORS['warning'])
        self.progress_frame += 1
        
        # Schedule next frame (200ms = 5 frames per second)
        self.root.after(200, self._animate_progress)
    
    def validate_inputs(self):
        """Validate all input fields"""
        try:
            # Validate numeric fields
            lat = float(self.entries['latitude'].get())
            if not -90 <= lat <= 90:
                raise ValueError("Latitude must be between -90 and 90")
            
            lon = float(self.entries['longitude'].get())
            if not -180 <= lon <= 180:
                raise ValueError("Longitude must be between -180 and 180")
            
            mag_min = float(self.entries['mag_min'].get())
            mag_max = float(self.entries['mag_max'].get())
            if mag_min >= mag_max:
                raise ValueError("Minimum magnitude must be less than maximum")
            
            # Validate at least one azimuth is selected
            if not any(var.get() for var in self.azimuth_vars.values()):
                raise ValueError("At least one azimuth direction must be selected")
            
            return True
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return False
    
    def refresh_date(self):
        """Refresh the observation date to current date"""
        self.observation_date = date.today()
        # Update both date labels
        self.date_label.config(text=f"Target Date: {self.observation_date.strftime('%Y-%m-%d')}")
        self.main_date_label.config(text=f"Obs Night: {self.observation_date.strftime('%Y-%m-%d')}")
        # Update export path display
        self.update_export_path_display()
        self.log_message(f"Date refreshed to {self.observation_date.strftime('%Y-%m-%d')}", 'info')
    
    def reset_to_defaults(self):
        """Reset all parameters to default values"""
        try:
            from config import DEFAULT_CONFIG
            
            # Ask for confirmation
            if not messagebox.askyesno("Reset to Defaults", 
                                     "This will reset all parameters to their default values. Continue?"):
                return
            
            # Reset values in GUI
            self.entries['latitude'].delete(0, tk.END)
            self.entries['latitude'].insert(0, str(DEFAULT_CONFIG['observer_location']['latitude']))
            
            self.entries['longitude'].delete(0, tk.END)
            self.entries['longitude'].insert(0, str(DEFAULT_CONFIG['observer_location']['longitude']))
            
            self.entries['mag_min'].delete(0, tk.END)
            self.entries['mag_min'].insert(0, str(DEFAULT_CONFIG['magnitude_limits']['mag_min']))
            
            self.entries['mag_max'].delete(0, tk.END)
            self.entries['mag_max'].insert(0, str(DEFAULT_CONFIG['magnitude_limits']['mag_max']))
            
            self.entries['min_alt'].delete(0, tk.END)
            self.entries['min_alt'].insert(0, str(DEFAULT_CONFIG['altitude_constraints']['min_altitude']))
            
            self.entries['min_alt_obs'].delete(0, tk.END)
            self.entries['min_alt_obs'].insert(0, str(DEFAULT_CONFIG['altitude_constraints']['min_altitude_during_obs']))
            
            self.entries['min_dec'].delete(0, tk.END)
            self.entries['min_dec'].insert(0, str(DEFAULT_CONFIG['declination_limits']['min_declination']))
            
            self.entries['max_dec'].delete(0, tk.END)
            self.entries['max_dec'].insert(0, str(DEFAULT_CONFIG['declination_limits']['max_declination']))
            
            self.entries['obs_window'].delete(0, tk.END)
            self.entries['obs_window'].insert(0, str(DEFAULT_CONFIG['timing_parameters']['observation_window']))
            
            self.entries['target_spacing'].delete(0, tk.END)
            self.entries['target_spacing'].insert(0, str(DEFAULT_CONFIG['timing_parameters']['target_spacing']))
            
            self.entries['drift_tolerance'].delete(0, tk.END)
            self.entries['drift_tolerance'].insert(0, str(DEFAULT_CONFIG['tracking_parameters']['center_after_drift_arcmin']))
            
            self.entries['max_targets'].delete(0, tk.END)
            self.entries['max_targets'].insert(0, str(DEFAULT_CONFIG['timing_parameters']['max_targets_per_night']))
            
            self.entries['timezone'].delete(0, tk.END)
            self.entries['timezone'].insert(0, str(DEFAULT_CONFIG['observer_location']['timezone_offset']))
            
            # Reset azimuth checkboxes
            default_azimuths = DEFAULT_CONFIG['azimuth_preferences']['allowed_azimuths']
            for az, var in self.azimuth_vars.items():
                var.set(az in default_azimuths)
            
            # Reset target constraints checkboxes
            self.allow_g_targets_var.set(DEFAULT_CONFIG['target_constraints']['allow_g_targets'])
            
            # Reset export paths
            self.nina_export_base_dir_entry.delete(0, tk.END)
            self.nina_export_base_dir_entry.insert(0, str(DEFAULT_CONFIG['export_settings']['nina_export_base_dir']))
            
            self.log_message("All parameters reset to defaults", 'info')
            
        except ImportError:
            messagebox.showerror("Error", "Configuration module not available")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset to defaults: {str(e)}")
            self.log_message(f"Error resetting defaults: {str(e)}", 'error')
    
    def clear_cache(self):
        """Clear all cached target data"""
        try:
            from pathlib import Path
            cache_files = list(Path(__file__).parent.glob("cache_raw_targets_*.json"))
            
            if not cache_files:
                self.log_message("No cache files found", 'info')
                messagebox.showinfo("Cache", "No cache files found to clear")
                return
            
            if messagebox.askyesno("Clear Cache", 
                                 f"This will delete {len(cache_files)} cache file(s). Continue?"):
                for cache_file in cache_files:
                    cache_file.unlink()
                    self.log_message(f"Deleted cache file: {cache_file.name}", 'info')
                
                self.log_message(f"Cleared {len(cache_files)} cache file(s)", 'success')
                messagebox.showinfo("Cache", f"Successfully cleared {len(cache_files)} cache file(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear cache: {str(e)}")
            self.log_message(f"Error clearing cache: {str(e)}", 'error')
    
    def generate_targets(self):
        """Generate targets based on current settings"""
        if not self.validate_inputs():
            return
        
        # Update the observation date to current date
        self.observation_date = date.today()
        # Update both date labels
        self.date_label.config(text=f"Target Date: {self.observation_date.strftime('%Y-%m-%d')}")
        self.main_date_label.config(text=f"Obs Night: {self.observation_date.strftime('%Y-%m-%d')}")
        # Update export path display
        self.update_export_path_display()
        
        # Disable button during generation
        self.generate_button.config(state='disabled', text="Generating...")
        
        # Start progress animation
        self.start_progress_animation()
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self._generate_targets_thread, daemon=True)
        thread.start()
    
    def _generate_targets_thread(self):
        """Thread worker for generating targets"""
        try:
            self.log_message("Starting target generation...", 'info')
            
            # Collect current GUI values
            gui_values = {
                'latitude': float(self.entries['latitude'].get()),
                'longitude': float(self.entries['longitude'].get()),
                'mag_min': float(self.entries['mag_min'].get()),
                'mag_max': float(self.entries['mag_max'].get()),
                'min_altitude': float(self.entries['min_alt'].get()),
                'min_altitude_during_obs': float(self.entries['min_alt_obs'].get()),
                'min_declination': float(self.entries['min_dec'].get()),
                'max_declination': float(self.entries['max_dec'].get()),
                'observation_window': float(self.entries['obs_window'].get()),
                'target_spacing': float(self.entries['target_spacing'].get()),
                'max_targets_per_night': int(self.entries['max_targets'].get()),
                'allowed_azimuths': [az for az, var in self.azimuth_vars.items() if var.get()],
                'allow_g_targets': self.allow_g_targets_var.get(),
                'nina_export_base_dir': self.nina_export_base_dir_entry.get()
            }
            
            # Save configuration to persistent storage
            try:
                from config import update_config_from_gui_values
                if update_config_from_gui_values(gui_values):
                    self.log_message("Configuration saved", 'info')
                else:
                    self.log_message("Warning: Could not save configuration", 'warning')
            except ImportError:
                self.log_message("Warning: Config module not available", 'warning')
            
            # Update global variables with user settings
            import findTargets
            findTargets.LATITUDE = gui_values['latitude']
            findTargets.LONGITUDE = gui_values['longitude']
            findTargets.MAG_MIN = gui_values['mag_min']
            findTargets.MAG_MAX = gui_values['mag_max']
            findTargets.MIN_ALTITUDE = gui_values['min_altitude']
            findTargets.MIN_ALTITUDE_DURING_OBS = gui_values['min_altitude_during_obs']
            findTargets.MIN_DECLINATION = gui_values['min_declination']
            findTargets.MAX_DECLINATION = gui_values['max_declination']
            findTargets.OBSERVATION_WINDOW = gui_values['observation_window']
            findTargets.TARGET_SPACING = gui_values['target_spacing']
            findTargets.CENTER_AFTER_DRIFT_ARCMIN = float(self.entries['drift_tolerance'].get())
            findTargets.MAX_TARGETS_PER_NIGHT = gui_values['max_targets_per_night']
            findTargets.TIMEZONE_OFFSET = int(self.entries['timezone'].get())
            findTargets.ALLOWED_AZIMUTHS = gui_values['allowed_azimuths']
            findTargets.ALLOW_G_TARGETS = gui_values['allow_g_targets']
            
            self.log_message(f"Configuration: Lat={findTargets.LATITUDE}, Lon={findTargets.LONGITUDE}", 'info')
            
            # Fetch predictions
            self.log_message(f"Fetching predictions for observation date: {self.observation_date.strftime('%Y-%m-%d')}", 'info')
            self.all_targets = fetch_minima_predictions(obs_date=self.observation_date, use_cache=True)
            
            # Stop progress animation after fetch completes
            self.root.after(0, self.stop_progress_animation)
            
            self.log_message(f"Fetched {len(self.all_targets)} potential targets", 'success')
            
            if not self.all_targets:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Targets",
                    "No targets found matching the criteria. Try adjusting your filters."
                ))
                return
            
            # Select optimal targets
            self.root.after(0, lambda: self.update_status("Selecting optimal targets...", COLORS['warning']))
            self.selected_targets = select_targets_for_night(self.all_targets)
            self.log_message(f"Selected {len(self.selected_targets)} targets for tonight", 'success')
            
            if not self.selected_targets:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Targets Selected",
                    "No suitable targets found for tonight. Try adjusting altitude or declination constraints."
                ))
                return
            
            # Display results
            self.root.after(0, self._display_targets)
            self.log_message("Target generation complete!", 'success')
            
        except Exception as e:
            self.root.after(0, self.stop_progress_animation)
            self.log_message(f"Error: {str(e)}", 'error')
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to generate targets:\n{str(e)}"))
        
        finally:
            self.root.after(0, self.stop_progress_animation)
            self.root.after(0, lambda: self.generate_button.config(state='normal', text="🎯 Generate Targets"))
            self.root.after(0, lambda: self.update_status("Target generation complete", COLORS['success']))
    
    def _display_targets(self):
        """Display selected targets in the targets tab"""
        self.targets_text.delete('1.0', 'end')
        
        if not self.selected_targets:
            self.targets_text.insert('end', "No targets selected.\n")
            return
        
        # Header
        self.targets_text.insert('end', "=" * 80 + "\n")
        self.targets_text.insert('end', f"  TARGETS FOR OBSERVATION NIGHT {self.observation_date.strftime('%Y-%m-%d')}\n")
        self.targets_text.insert('end', f"  (Night of {self.observation_date.strftime('%b %d')} into {(self.observation_date + timedelta(days=1)).strftime('%b %d')})\n")
        self.targets_text.insert('end', "=" * 80 + "\n\n")
        
        # Target details
        for i, target in enumerate(self.selected_targets, 1):
            self.targets_text.insert('end', f"TARGET {i}: {format_target_display_name(target)}\n")
            self.targets_text.insert('end', "-" * 80 + "\n")
            self.targets_text.insert('end', f"  Star ID:           {target.get('id', 'N/A')}\n")
            self.targets_text.insert('end', f"  RA:                {target.get('ra', 'N/A')}\n")
            self.targets_text.insert('end', f"  Dec:               {target.get('dec', 'N/A')}\n")
            self.targets_text.insert('end', f"  Minima (UTC):      {target.get('minimum_time', 'N/A')}\n")
            
            if 'minima_datetime_local' in target:
                local_time = target['minima_datetime_local'].strftime('%H:%M')
                obs_start = (target['minima_datetime_local'] - 
                           __import__('datetime').timedelta(hours=2)).strftime('%H:%M')
                obs_end = (target['minima_datetime_local'] + 
                          __import__('datetime').timedelta(hours=2)).strftime('%H:%M')
                self.targets_text.insert('end', f"  Minima (Local):    {local_time}\n")
                self.targets_text.insert('end', f"  Obs Window:        {obs_start} - {obs_end} local\n")
            
            self.targets_text.insert('end', f"  Magnitude Range:   {target.get('mag_min', 'N/A')} - {target.get('mag_max', 'N/A')}\n")
            self.targets_text.insert('end', f"  Altitude:          {target.get('altitude', 'N/A')}°\n")
            self.targets_text.insert('end', f"  Azimuth:           {target.get('azimuth', 'N/A')}\n")
            self.targets_text.insert('end', f"  Type:              {target.get('variability_type', 'N/A')}\n")
            self.targets_text.insert('end', "\n")
        
        # Enable export buttons
        self.export_button.config(state='normal')
        self.export_csv_button.config(state='normal')
        
        # Plot airmass curves
        self._plot_airmass_curves()
        
        # Switch to targets tab
        self.notebook.select(1)
    
    def _plot_airmass_curves(self):
        """Plot airmass curves for selected targets"""
        if not self.selected_targets:
            return
        
        # Clear any existing plot
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        
        # Import required modules
        import findTargets
        
        # Create figure with dark background
        fig = Figure(figsize=(10, 6), facecolor=COLORS['bg_dark'])
        ax1 = fig.add_subplot(111, facecolor=COLORS['bg_medium'])
        ax2 = ax1.twinx()
        
        # Set up observer location
        location = EarthLocation(
            lat=findTargets.LATITUDE * u.deg,
            lon=findTargets.LONGITUDE * u.deg,
            height=300 * u.m
        )
        
        # Generate time array for the night (sunset to sunrise, roughly 18:00 to 06:00 local)
        start_time = datetime.combine(self.observation_date, datetime.min.time()) + timedelta(hours=18)
        end_time = start_time + timedelta(hours=12)
        
        time_array = []
        current = start_time
        while current <= end_time:
            time_array.append(current)
            current += timedelta(minutes=10)
        
        # Convert to astropy Time (UTC)
        utc_times = [t - timedelta(hours=findTargets.TIMEZONE_OFFSET) for t in time_array]
        astropy_times = Time([t.isoformat() for t in utc_times])
        
        # Plot colors for targets
        colors_list = ['#4ecca3', '#ffd93d', '#ff6b6b', '#4a5fb5']
        
        # Store all target data for tooltips
        all_target_data = []
        
        for idx, target in enumerate(self.selected_targets[:4]):  # Limit to 4 targets
            try:
                # Parse RA/Dec
                ra_str = target.get('ra', '')
                dec_str = target.get('dec', '')
                
                if not ra_str or not dec_str:
                    continue
                
                # Create SkyCoord
                coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
                
                # Calculate altitude and airmass for each time point
                altitudes = []
                airmasses = []
                
                for t in astropy_times:
                    altaz = coord.transform_to(AltAz(obstime=t, location=location))
                    alt = altaz.alt.deg
                    altitudes.append(alt)
                    
                    # Calculate airmass (sec(z) where z is zenith angle)
                    # Only valid for altitudes > 0
                    if alt > 0:
                        zenith_angle = 90 - alt
                        airmass = 1.0 / np.cos(np.radians(zenith_angle))
                        # Clamp airmass to reasonable values
                        airmass = min(airmass, 5.0)
                    else:
                        airmass = np.nan
                    airmasses.append(airmass)
                
                # Store data for this target
                all_target_data.append({
                    'name': format_target_display_name(target),
                    'times': time_array,
                    'airmasses': airmasses,
                    'altitudes': altitudes,
                    'color': colors_list[idx % len(colors_list)]
                })
                
                # Plot airmass curve
                color = colors_list[idx % len(colors_list)]
                line, = ax1.plot(time_array, airmasses, 
                        color=color, 
                        linewidth=2, 
                        label=format_target_display_name(target),
                        alpha=0.8)
                
                # Mark scheduled start and end times (minima ± 2 hours) and minima time
                if 'minima_datetime_local' in target:
                    minima_time = target['minima_datetime_local']
                    scheduled_start_time = minima_time - timedelta(hours=2)
                    scheduled_end_time = minima_time + timedelta(hours=2)
                    
                    # Mark the exact minima time with orange marker
                    if start_time <= minima_time <= end_time:
                        # Find index of closest time for minima
                        time_diffs = [abs((t - minima_time).total_seconds()) for t in time_array]
                        closest_idx = time_diffs.index(min(time_diffs))
                        
                        if closest_idx < len(airmasses) and not np.isnan(airmasses[closest_idx]):
                            ax1.plot(time_array[closest_idx], airmasses[closest_idx],
                                    'o', color='orange', markersize=12, 
                                    markeredgecolor='white', markeredgewidth=2,
                                    zorder=11, label='_nolegend_')  # Don't add to legend
                    
                    # Find closest time points for start/end markers (red)
                    for marker_time in [scheduled_start_time, scheduled_end_time]:
                        if start_time <= marker_time <= end_time:
                            # Find index of closest time
                            time_diffs = [abs((t - marker_time).total_seconds()) for t in time_array]
                            closest_idx = time_diffs.index(min(time_diffs))
                            
                            if closest_idx < len(airmasses) and not np.isnan(airmasses[closest_idx]):
                                ax1.plot(time_array[closest_idx], airmasses[closest_idx],
                                        'o', color='red', markersize=10, 
                                        markeredgecolor='white', markeredgewidth=2,
                                        zorder=10, label='_nolegend_')  # Don't add to legend
            
            except Exception as e:
                self.log_message(f"Error plotting {target.get('name', 'unknown')}: {e}", 'warning')
                continue
        
        # Configure axes
        ax1.set_xlabel('Local Time', color=COLORS['text'], fontsize=11)
        ax1.set_ylabel('Airmass', color=COLORS['text'], fontsize=11)
        ax1.set_ylim(2.4, 1.0)  # 2.4 at bottom (worst), 1.0 at top (best) - inverted Y axis
        ax1.grid(True, alpha=0.2, color=COLORS['text_dim'])
        
        # Configure right axis for altitude
        ax2.set_ylabel('Altitude (°)', color=COLORS['text'], fontsize=11)
        ax2.set_ylim(25, 90)  # 25° at bottom, 90° at top - inverted to match airmass
        
        # Set up time axis formatting
        import matplotlib.dates as mdates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        fig.autofmt_xdate(rotation=45)
        
        # Style the axes
        ax1.tick_params(colors=COLORS['text'], labelsize=9)
        ax2.tick_params(colors=COLORS['text'], labelsize=9)
        ax1.spines['bottom'].set_color(COLORS['text_dim'])
        ax1.spines['top'].set_color(COLORS['text_dim'])
        ax1.spines['left'].set_color(COLORS['text_dim'])
        ax1.spines['right'].set_color(COLORS['text_dim'])
        ax2.spines['right'].set_color(COLORS['text_dim'])
        
        # Add legend with custom entries for markers
        handles, labels = ax1.get_legend_handles_labels()
        
        # Add custom legend entries for markers
        from matplotlib.lines import Line2D
        custom_lines = [
            Line2D([0], [0], marker='o', color='orange', linestyle='None',
                   markersize=10, markeredgecolor='white', markeredgewidth=2,
                   label='Minima Time'),
            Line2D([0], [0], marker='o', color='red', linestyle='None',
                   markersize=8, markeredgecolor='white', markeredgewidth=2,
                   label='Observation Window')
        ]
        
        # Combine target lines with marker explanations
        all_handles = handles + custom_lines
        all_labels = labels + ['Minima Time', 'Observation Window']
        
        ax1.legend(all_handles, all_labels, loc='upper right', 
                  facecolor=COLORS['bg_light'], edgecolor=COLORS['text_dim'], 
                  labelcolor=COLORS['text'], fontsize=9)
        
        # Add title
        fig.suptitle(f'Airmass Curves for {self.observation_date.strftime("%Y-%m-%d")}',
                    color=COLORS['text'], fontsize=13, fontweight='bold')
        
        fig.tight_layout()
        
        # Embed plot in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Add toolbar
        toolbar = NavigationToolbar2Tk(canvas, self.plot_container)
        toolbar.update()
        
        # Enable interactive tooltips
        self._setup_plot_tooltips(fig, ax1, all_target_data)
    
    def _setup_plot_tooltips(self, fig, ax, target_data):
        """Setup interactive tooltips for the plot"""
        import matplotlib.dates as mdates
        
        annot = ax.annotate("", xy=(0, 0), xytext=(15, 15),
                           textcoords="offset points",
                           bbox=dict(boxstyle="round,pad=0.5", fc=COLORS['bg_light'], 
                                   ec=COLORS['text'], alpha=0.95, linewidth=2),
                           color=COLORS['text'],
                           fontsize=10,
                           visible=False,
                           zorder=100)
        
        def hover(event):
            if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
                try:
                    # Convert matplotlib date to datetime
                    hover_time = mdates.num2date(event.xdata)
                    hover_airmass = event.ydata
                    
                    # Find closest point across all targets
                    min_time_diff = float('inf')
                    closest_info = None
                    
                    for tgt in target_data:
                        for i, (t, airmass) in enumerate(zip(tgt['times'], tgt['airmasses'])):
                            if not np.isnan(airmass):
                                # Calculate time difference in minutes
                                time_diff = abs((t - hover_time).total_seconds()) / 60.0
                                
                                # If within 30 minutes, consider it
                                if time_diff < 30:
                                    if time_diff < min_time_diff:
                                        min_time_diff = time_diff
                                        closest_info = {
                                            'time': t,
                                            'airmass': airmass,
                                            'altitude': tgt['altitudes'][i],
                                            'name': tgt['name']
                                        }
                    
                    # Show tooltip if we found a close point
                    if closest_info is not None:
                        time_str = closest_info['time'].strftime('%H:%M')
                        text = (f"{closest_info['name']}\n"
                               f"Time: {time_str}\n"
                               f"Airmass: {closest_info['airmass']:.2f}\n"
                               f"Altitude: {closest_info['altitude']:.1f}°")
                        annot.set_text(text)
                        annot.xy = (event.xdata, event.ydata)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
                
                except Exception as e:
                    self.log_message(f"Tooltip error: {e}", 'warning')
            
            # Hide tooltip if no valid point found or mouse outside axes
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()
        
        fig.canvas.mpl_connect("motion_notify_event", hover)
    
    def get_export_path_display(self):
        """Get the current export path for display in the GUI"""
        from datetime import date
        today = date.today()
        date_str = today.strftime('%Y%m%d')
        full_path = Path(NINA_EXPORT_BASE_DIR) / date_str
        return str(full_path)
    
    def update_export_path_display(self):
        """Update the export path label with current date"""
        if hasattr(self, 'export_path_label'):
            export_path_text = self.get_export_path_display()
            self.export_path_label.config(text=f"📁 Export Path: {export_path_text}")
    
    def export_nina_json(self):
        """Export selected targets as NINA JSON files"""
        if not self.selected_targets:
            messagebox.showwarning("No Targets", "No targets to export. Generate targets first.")
            return
        
        try:
            # Record targets in database before exporting
            self.log_message(f"Recording {len(self.selected_targets)} targets in database for {self.observation_date}...", 'info')
            
            try:
                record_scheduled_targets(self.selected_targets, self.observation_date)
                self.log_message(f"Recorded targets in database", 'success')
            except Exception as e:
                self.log_message(f"Warning: Could not record to database: {str(e)}", 'warning')
                # Continue with export even if database recording fails
            
            # Export NINA JSON files
            export_to_nina_json(self.selected_targets)
            
            # Get the output directory for the success message
            today = date.today()
            date_str = today.strftime('%Y%m%d')
            output_dir = Path(NINA_EXPORT_BASE_DIR) / date_str
            
            self.log_message(f"Exported {len(self.selected_targets)} NINA JSON files to {output_dir}", 'success')
            messagebox.showinfo(
                "Export Successful",
                f"Successfully exported {len(self.selected_targets)} NINA JSON files to:\n"
                f"{output_dir}\n\n"
                f"Targets have been recorded in the database."
            )
        except Exception as e:
            self.log_message(f"Export failed: {str(e)}", 'error')
            messagebox.showerror("Export Error", f"Failed to export NINA JSON:\n{str(e)}")
    
    def export_csv(self):
        """Export selected targets as CSV"""
        if not self.selected_targets:
            messagebox.showwarning("No Targets", "No targets to export. Generate targets first.")
            return
        
        try:
            output_path = Path.cwd() / f"selected_targets_{self.observation_date}.csv"
            export_to_nina_format(self.selected_targets, output_path)
            self.log_message(f"Exported CSV to {output_path}", 'success')
            messagebox.showinfo(
                "Export Successful",
                f"Successfully exported targets to:\n{output_path}"
            )
        except Exception as e:
            self.log_message(f"CSV export failed: {str(e)}", 'error')
            messagebox.showerror("Export Error", f"Failed to export CSV:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TargetSelectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
