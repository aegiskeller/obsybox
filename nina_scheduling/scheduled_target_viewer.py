#!/usr/bin/env python3
"""
Scheduled Target Viewer GUI

A graphical interface for reviewing and updating scheduled observation targets.
Allows marking targets as observed/not observed/invalid with comments.
Uses the same midnight/dark astronomy theme as target_selector_gui.py.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path("Z:/scheduled_observations.sqlite")

# Midnight color scheme (matching target_selector_gui.py)
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


class ScheduledTargetViewer:
    def __init__(self, root):
        import traceback
        try:
            self.root = root
            self.root.title("Scheduled Target Viewer")
            self.root.geometry("1200x800")
            self.root.configure(bg=COLORS['bg_dark'])
            
            # Data storage
            self.scheduled_targets = []
            self.target_widgets = {}  # Store widgets for each target
            self.changes = {}  # Track changes before committing
            
            self._initialize_ui()
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _initialize_ui(self):
        
        # Configure style
        self.setup_styles()
        
        # Create main container with padding
        main_container = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_container,
            text="📋 Scheduled Target Viewer",
            font=('Helvetica', 14, 'bold'),
            bg=COLORS['bg_dark'],
            fg='#ff4444'
        )
        title_label.pack(pady=(0, 5))
        
        # Subtitle
        subtitle_label = tk.Label(
            main_container,
            text="Review and update scheduled observations",
            font=('Helvetica', 10, 'italic'),
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim']
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Control buttons frame
        control_frame = tk.Frame(main_container, bg=COLORS['bg_dark'])
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Refresh button
        self.refresh_btn = tk.Button(
            control_frame,
            text="🔄 Refresh",
            command=self.load_scheduled_targets,
            bg=COLORS['button'],
            fg=COLORS['button_text'],
            font=('Helvetica', 10, 'bold'),
            relief='raised',
            bd=2,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.refresh_btn.pack(side='left', padx=(0, 10))
        
        # Commit button
        self.commit_btn = tk.Button(
            control_frame,
            text="💾 Commit to DB",
            command=self.commit_changes,
            bg=COLORS['success'],
            fg=COLORS['button_text'],
            font=('Helvetica', 10, 'bold'),
            relief='raised',
            bd=2,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.commit_btn.pack(side='left')
        
        # Search frame
        search_frame = tk.Frame(control_frame, bg=COLORS['bg_dark'])
        search_frame.pack(side='left', padx=(20, 0))
        
        search_label = tk.Label(
            search_frame,
            text="🔍 Search:",
            bg=COLORS['bg_dark'],
            fg=COLORS['text'],
            font=('Helvetica', 10)
        )
        search_label.pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_targets())
        
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            insertbackground=COLORS['text'],
            font=('Helvetica', 10),
            width=30,
            relief='flat',
            bd=1
        )
        search_entry.pack(side='left')
        
        # Clear search button
        clear_btn = tk.Button(
            search_frame,
            text="✕",
            command=lambda: self.search_var.set(''),
            bg=COLORS['bg_medium'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 8),
            relief='flat',
            bd=0,
            padx=5,
            pady=2,
            cursor='hand2'
        )
        clear_btn.pack(side='left', padx=(5, 0))
        
        # Status label
        self.status_label = tk.Label(
            control_frame,
            text="",
            bg=COLORS['bg_dark'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 9)
        )
        self.status_label.pack(side='right')
        
        # Create scrollable frame for targets
        canvas_frame = tk.Frame(main_container, bg=COLORS['bg_dark'])
        canvas_frame.pack(fill='both', expand=True)
        
        # Canvas with scrollbar
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=COLORS['bg_dark'],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=self.canvas.yview
        )
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS['bg_dark'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Enable mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Status bar
        self.status_bar = tk.Label(
            main_container,
            text="Ready",
            bg=COLORS['bg_medium'],
            fg=COLORS['text_dim'],
            font=('Helvetica', 9),
            anchor='w',
            padx=10,
            pady=5
        )
        self.status_bar.pack(fill='x', pady=(10, 0))
        
        # Load initial data
        self.load_scheduled_targets()
        
    def setup_styles(self):
        """Configure ttk styles for midnight theme"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame style
        style.configure('TFrame', background=COLORS['bg_dark'])
        style.configure('Card.TFrame', background=COLORS['bg_light'], relief='flat')
        
        # Label style
        style.configure('TLabel',
                       background=COLORS['bg_light'],
                       foreground=COLORS['text'],
                       font=('Helvetica', 10))
        
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def load_scheduled_targets(self):
        """Load scheduled targets from database, sorted by date (latest first)"""
        if not DB_PATH.exists():
            messagebox.showerror("Error", f"Database not found at {DB_PATH}")
            return
            
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Query scheduled targets with observation night details
            query = """
                SELECT 
                    st.scheduled_target_id,
                    on_.date_obs,
                    on_.telescope,
                    t.target_name,
                    st.scheduled_start_time,
                    st.scheduled_end_time,
                    st.status,
                    st.completion_percentage,
                    st.images_captured,
                    st.notes,
                    COUNT(o.observation_id) as actual_images
                FROM scheduled_targets st
                JOIN targets t ON st.target_id = t.target_id
                JOIN observation_nights on_ ON st.night_id = on_.night_id
                LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
                GROUP BY st.scheduled_target_id
                ORDER BY on_.date_obs DESC, st.scheduled_start_time
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            self.scheduled_targets = []
            for row in rows:
                self.scheduled_targets.append({
                    'scheduled_target_id': row[0],
                    'date_obs': row[1],
                    'telescope': row[2],
                    'target_name': row[3],
                    'scheduled_start_time': row[4],
                    'scheduled_end_time': row[5],
                    'status': row[6],
                    'completion_percentage': row[7],
                    'images_captured': row[8],
                    'notes': row[9],
                    'actual_images': row[10]
                })
            
            conn.close()
            
            # Clear widget references and changes on refresh (new data from DB)
            self.target_widgets = {}
            self.changes = {}
            
            # Update UI
            self.filter_targets()
            self.update_status(f"Loaded {len(self.scheduled_targets)} scheduled targets")
            
        except Exception as e:
            logger.error(f"Error loading scheduled targets: {e}")
            messagebox.showerror("Error", f"Failed to load targets: {e}")
            
    def filter_targets(self):
        """Filter targets based on search query and display them"""
        search_query = self.search_var.get().strip().lower()
        
        if not search_query:
            # No search query, display all targets
            filtered = self.scheduled_targets
        else:
            # Filter targets by name
            filtered = [
                target for target in self.scheduled_targets
                if search_query in target['target_name'].lower()
            ]
        
        # Display the filtered targets
        self.display_targets(filtered)
        
        # Update status if searching
        if search_query:
            if filtered:
                self.update_status(f"Found {len(filtered)} target(s) matching '{search_query}'")
            else:
                self.update_status(f"No targets found matching '{search_query}'")
                
    def display_targets(self, targets_to_display):
        """Display targets in the scrollable frame"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not targets_to_display:
            no_data_label = tk.Label(
                self.scrollable_frame,
                text="No targets found",
                bg=COLORS['bg_dark'],
                fg=COLORS['text_dim'],
                font=('Helvetica', 12)
            )
            no_data_label.pack(pady=50)
            return
        
        # Group targets by date
        targets_by_date = {}
        for target in targets_to_display:
            date_obs = target['date_obs']
            if date_obs not in targets_by_date:
                targets_by_date[date_obs] = []
            targets_by_date[date_obs].append(target)
        
        # Display targets grouped by date
        for date_obs in sorted(targets_by_date.keys(), reverse=True):
            # Date header
            date_frame = tk.Frame(self.scrollable_frame, bg=COLORS['bg_medium'])
            date_frame.pack(fill='x', padx=5, pady=(10, 5))
            
            date_label = tk.Label(
                date_frame,
                text=f"📅 {date_obs}",
                font=('Helvetica', 12, 'bold'),
                bg=COLORS['bg_medium'],
                fg=COLORS['success'],
                anchor='w',
                padx=10,
                pady=5
            )
            date_label.pack(fill='x')
            
            # Targets for this date
            for target in targets_by_date[date_obs]:
                self.create_target_card(target)
                
    def create_target_card(self, target):
        """Create a card widget for a single target"""
        target_id = target['scheduled_target_id']
        
        # Get existing state if available (for preserving during filtering)
        if target_id in self.target_widgets:
            try:
                existing_status = self.target_widgets[target_id]['status_var'].get()
                existing_comments = self.target_widgets[target_id]['comments_text'].get('1.0', 'end-1c')
            except tk.TclError:
                # Widget was destroyed, use default values
                existing_status = target['status'] or 'planned'
                existing_comments = target['notes'] or ''
        else:
            existing_status = target['status'] or 'planned'
            existing_comments = target['notes'] or ''
        
        # Card frame
        card = tk.Frame(
            self.scrollable_frame,
            bg=COLORS['bg_light'],
            relief='ridge',
            bd=2
        )
        card.pack(fill='x', padx=10, pady=5)
        
        # Top row: Target name and telescope
        top_row = tk.Frame(card, bg=COLORS['bg_light'])
        top_row.pack(fill='x', padx=10, pady=(10, 5))
        
        target_label = tk.Label(
            top_row,
            text=f"⭐ {target['target_name']}",
            font=('Helvetica', 11, 'bold'),
            bg=COLORS['bg_light'],
            fg=COLORS['text'],
            anchor='w'
        )
        target_label.pack(side='left')
        
        telescope_label = tk.Label(
            top_row,
            text=f"🔭 {target['telescope']}",
            font=('Helvetica', 10),
            bg=COLORS['bg_light'],
            fg=COLORS['text_dim'],
            anchor='e'
        )
        telescope_label.pack(side='right')
        
        # Info row: Times and current status
        info_row = tk.Frame(card, bg=COLORS['bg_light'])
        info_row.pack(fill='x', padx=10, pady=5)
        
        # Build info text
        start_time = target['scheduled_start_time'] or 'N/A'
        end_time = target['scheduled_end_time'] or 'N/A'
        current_status = target['status'] or 'planned'
        actual_images = target['actual_images'] or 0
        
        info_text = f"Start: {start_time} | End: {end_time} | Current Status: {current_status} | Images: {actual_images}"
        
        info_label = tk.Label(
            info_row,
            text=info_text,
            font=('Helvetica', 9),
            bg=COLORS['bg_light'],
            fg=COLORS['text_dim'],
            anchor='w'
        )
        info_label.pack(fill='x')
        
        # Status selection row
        status_row = tk.Frame(card, bg=COLORS['bg_light'])
        status_row.pack(fill='x', padx=10, pady=5)
        
        status_label = tk.Label(
            status_row,
            text="Update Status:",
            font=('Helvetica', 10),
            bg=COLORS['bg_light'],
            fg=COLORS['text']
        )
        status_label.pack(side='left', padx=(0, 10))
        
        # Use existing state if available
        status_var = tk.StringVar(value=existing_status)
        
        # Status radio buttons
        statuses = [
            ('obs_min', '✅ Obs w/ Minima'),
            ('obs_no_min', '✓ Obs w/o Minima'),
            ('no_obs', '❌ Not Observed'),
            ('invalid', '⚠️ Invalid'),
            ('planned', '📋 Planned')
        ]
        
        for value, label in statuses:
            rb = tk.Radiobutton(
                status_row,
                text=label,
                variable=status_var,
                value=value,
                bg=COLORS['bg_light'],
                fg=COLORS['text'],
                selectcolor=COLORS['bg_medium'],
                activebackground=COLORS['bg_light'],
                activeforeground=COLORS['text'],
                font=('Helvetica', 9),
                command=lambda tid=target_id, var=status_var: self.mark_changed(tid, 'status', var.get())
            )
            rb.pack(side='left', padx=5)
        
        # Comments row
        comments_row = tk.Frame(card, bg=COLORS['bg_light'])
        comments_row.pack(fill='x', padx=10, pady=(5, 10))
        
        comments_label = tk.Label(
            comments_row,
            text="Comments:",
            font=('Helvetica', 10),
            bg=COLORS['bg_light'],
            fg=COLORS['text']
        )
        comments_label.pack(anchor='w')
        
        # Comments text box
        comments_text = tk.Text(
            comments_row,
            height=2,
            width=80,
            bg=COLORS['bg_medium'],
            fg=COLORS['text'],
            insertbackground=COLORS['text'],
            font=('Helvetica', 9),
            relief='flat',
            bd=1
        )
        comments_text.pack(fill='x', pady=(5, 0))
        
        # Pre-fill with existing comments or preserved state
        if existing_comments:
            comments_text.insert('1.0', existing_comments)
        
        # Bind text changes
        comments_text.bind(
            '<KeyRelease>',
            lambda e, tid=target_id, widget=comments_text: self.mark_changed(
                tid, 'notes', widget.get('1.0', 'end-1c')
            )
        )
        
        # Store widgets for this target
        self.target_widgets[target_id] = {
            'status_var': status_var,
            'comments_text': comments_text,
            'card': card
        }
        
    def mark_changed(self, target_id, field, value):
        """Mark a target field as changed"""
        if target_id not in self.changes:
            self.changes[target_id] = {}
        self.changes[target_id][field] = value
        
        # Update status bar
        num_changes = len(self.changes)
        self.update_status(f"{num_changes} target(s) modified (not yet committed)")
        
    def commit_changes(self):
        """Commit all changes to the database"""
        if not self.changes:
            messagebox.showinfo("No Changes", "No changes to commit.")
            return
        
        # Confirm with user
        num_changes = len(self.changes)
        if not messagebox.askyesno(
            "Confirm Commit",
            f"Commit changes for {num_changes} target(s) to the database?"
        ):
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Update each changed target
            for target_id, changes in self.changes.items():
                update_fields = []
                update_values = []
                
                if 'status' in changes:
                    update_fields.append('status = ?')
                    update_values.append(changes['status'])
                
                if 'notes' in changes:
                    update_fields.append('notes = ?')
                    update_values.append(changes['notes'])
                
                if update_fields:
                    update_values.append(target_id)
                    query = f"UPDATE scheduled_targets SET {', '.join(update_fields)} WHERE scheduled_target_id = ?"
                    cursor.execute(query, update_values)
            
            conn.commit()
            conn.close()
            
            # Clear changes
            num_committed = len(self.changes)
            self.changes = {}
            
            # Reload targets
            self.load_scheduled_targets()
            
            messagebox.showinfo("Success", f"Successfully committed changes for {num_committed} target(s).")
            self.update_status("Changes committed successfully")
            
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            messagebox.showerror("Error", f"Failed to commit changes: {e}")
            
    def update_status(self, message):
        """Update the status bar message"""
        self.status_bar.config(text=message)
        self.status_label.config(text=message)


def main():
    import traceback
    try:
        root = tk.Tk()
        app = ScheduledTargetViewer(root)
        root.mainloop()
    except Exception as e:
        # Log the full error with traceback
        logger.error(f"Failed to start application: {e}")
        logger.error(traceback.format_exc())
        
        # Also show error in message box if possible
        try:
            messagebox.showerror("Startup Error", f"Failed to start application:\n\n{e}\n\nSee console for details.")
        except:
            print(f"FATAL ERROR: {e}")
            print(traceback.format_exc())
        
        raise


if __name__ == "__main__":
    main()
