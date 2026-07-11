#!/usr/bin/env python3
"""GUI to select eclipsing binary minima targets from varcz_eb database."""

import threading
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from findEBTargets import (
    DEFAULT_DB_PATH,
    DEFAULT_TABLE,
    compute_airmass_at_local_time,
    estimate_culmination_local,
    export_targets_nina_individual,
    find_eb_targets_for_night,
    get_nina_targets_export_dir,
    get_dark_night_bounds_local,
    select_partitioned_targets,
)


class EBTargetSelector:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EBTargetSelector")
        self.root.geometry("980x700")
        self.root.configure(bg="#0b1220")

        self.targets = []
        self.selected_targets = []
        self.last_inputs = {}

        self._setup_dark_theme()
        self._build_ui()

    def _setup_dark_theme(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Dark.TFrame", background="#0b1220")
        style.configure("Dark.TLabel", background="#0b1220", foreground="#e5e7eb")
        style.configure("Dark.TButton", background="#1f2937", foreground="#e5e7eb")
        style.map("Dark.TButton", background=[("active", "#374151")])
        style.configure(
            "Dark.TEntry",
            fieldbackground="#111827",
            foreground="#e5e7eb",
            insertcolor="#e5e7eb",
            bordercolor="#334155",
        )
        style.configure("Dark.TRadiobutton", background="#0b1220", foreground="#e5e7eb")
        style.configure("Dark.TCheckbutton", background="#0b1220", foreground="#e5e7eb")
        style.configure(
            "Dark.Treeview",
            background="#111827",
            fieldbackground="#111827",
            foreground="#e5e7eb",
            bordercolor="#334155",
        )
        style.configure(
            "Dark.Treeview.Heading",
            background="#1f2937",
            foreground="#f3f4f6",
            bordercolor="#334155",
        )
        style.map("Dark.Treeview", background=[("selected", "#2563eb")])

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12, style="Dark.TFrame")
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="EBTargetSelector", font=("Segoe UI", 16, "bold"), style="Dark.TLabel")
        title.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        ttk.Label(main, text="Observation Date (YYYY-MM-DD)", style="Dark.TLabel").grid(row=1, column=0, sticky="w")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(main, textvariable=self.date_var, width=16, style="Dark.TEntry").grid(row=1, column=1, sticky="w", padx=(8, 12))

        ttk.Label(main, text="DB Path", style="Dark.TLabel").grid(row=1, column=2, sticky="w")
        self.db_path_var = tk.StringVar(value=str(DEFAULT_DB_PATH))
        ttk.Entry(main, textvariable=self.db_path_var, width=44, style="Dark.TEntry").grid(row=1, column=3, sticky="ew", padx=(8, 6))
        ttk.Button(main, text="Browse", command=self._browse_db, style="Dark.TButton").grid(row=1, column=4, sticky="w")

        ttk.Label(main, text="Table", style="Dark.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.table_var = tk.StringVar(value=DEFAULT_TABLE)
        ttk.Entry(main, textvariable=self.table_var, width=16, style="Dark.TEntry").grid(row=2, column=1, sticky="w", padx=(8, 12), pady=(8, 0))

        ttk.Label(main, text="Latitude", style="Dark.TLabel").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.lat_var = tk.StringVar(value="-35.0")
        ttk.Entry(main, textvariable=self.lat_var, width=10, style="Dark.TEntry").grid(row=2, column=3, sticky="w", padx=(8, 6), pady=(8, 0))

        ttk.Label(main, text="Longitude", style="Dark.TLabel").grid(row=2, column=4, sticky="w", pady=(8, 0))
        self.lon_var = tk.StringVar(value="149.08")
        ttk.Entry(main, textvariable=self.lon_var, width=10, style="Dark.TEntry").grid(row=2, column=5, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Label(main, text="UTC Offset", style="Dark.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.tz_var = tk.StringVar(value="10")
        ttk.Entry(main, textvariable=self.tz_var, width=10, style="Dark.TEntry").grid(row=3, column=1, sticky="w", padx=(8, 12), pady=(8, 0))

        ttk.Label(main, text="Azimuth Sectors", style="Dark.TLabel").grid(row=3, column=2, sticky="w", pady=(8, 0))
        sector_frame = ttk.Frame(main, style="Dark.TFrame")
        sector_frame.grid(row=3, column=3, columnspan=3, sticky="w", padx=(8, 0), pady=(8, 0))

        # Broad sector multi-selection for scheduling filters.
        sectors = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
        self.az_sector_vars = {}
        for idx, sector in enumerate(sectors):
            var = tk.BooleanVar(value=True)
            self.az_sector_vars[sector] = var
            ttk.Checkbutton(
                sector_frame,
                text=sector,
                variable=var,
                style="Dark.TCheckbutton",
            ).grid(row=idx // 4, column=idx % 4, sticky="w", padx=(0, 10))

        ttk.Label(main, text="Min Alt During Obs (deg)", style="Dark.TLabel").grid(row=4, column=2, sticky="w", pady=(8, 0))
        self.min_alt_obs_var = tk.StringVar(value="30")
        ttk.Entry(main, textvariable=self.min_alt_obs_var, width=10, style="Dark.TEntry").grid(row=4, column=3, sticky="w", padx=(8, 6), pady=(8, 0))

        ttk.Label(main, text="Telescope", style="Dark.TLabel").grid(row=5, column=2, sticky="w", pady=(4, 0))
        self.telescope_var = tk.StringVar(value="SCT")
        telescope_combo = ttk.Combobox(
            main,
            textvariable=self.telescope_var,
            values=["SCT", "S50"],
            width=8,
            state="readonly",
        )
        telescope_combo.grid(row=5, column=3, sticky="w", padx=(8, 6), pady=(4, 0))

        ttk.Label(main, text="Max Targets", style="Dark.TLabel").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.max_targets_var = tk.StringVar(value="2")
        ttk.Entry(main, textvariable=self.max_targets_var, width=10, style="Dark.TEntry").grid(row=4, column=1, sticky="w", padx=(8, 12), pady=(8, 0))

        self.generate_button = ttk.Button(main, text="Find EB Targets", command=self.generate_targets, style="Dark.TButton")
        self.generate_button.grid(row=4, column=4, sticky="w", pady=(8, 0))

        ttk.Button(main, text="Export Selected", command=self.export_selected, style="Dark.TButton").grid(row=4, column=5, sticky="w", pady=(8, 0))
        ttk.Button(main, text="Airmass Plot", command=self.show_airmass_plot, style="Dark.TButton").grid(row=5, column=5, sticky="w", pady=(4, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var, style="Dark.TLabel").grid(row=5, column=0, columnspan=6, sticky="w", pady=(8, 6))

        columns = (
            "name",
            "ra",
            "dec",
            "minima_type",
            "minimum_time",
            "local_time",
            "transit_local",
            "azimuth_deg",
            "azimuth",
            "variability_type",
            "constellation",
        )
        self.tree = ttk.Treeview(main, columns=columns, show="headings", height=18, style="Dark.Treeview")
        headings = {
            "name": "Target",
            "ra": "RA",
            "dec": "Dec",
            "minima_type": "Minima",
            "minimum_time": "UTC Min Time",
            "local_time": "Local Min Time",
            "transit_local": "Transit Local",
            "azimuth_deg": "Az (deg)",
            "azimuth": "Az",
            "variability_type": "Var Type",
            "constellation": "Const",
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            if key == "name":
                width = 180
            elif key in {"ra", "dec"}:
                width = 110
            else:
                width = 100
            self.tree.column(key, width=width, anchor="w")

        self.tree.grid(row=6, column=0, columnspan=6, sticky="nsew")

        yscroll = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=6, column=6, sticky="ns")

        main.columnconfigure(3, weight=1)
        main.rowconfigure(6, weight=1)

    def _browse_db(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select varcz_eb database",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
        )
        if selected:
            self.db_path_var.set(selected)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _clear_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def _parse_inputs(self):
        obs_date = date.fromisoformat(self.date_var.get().strip())
        db_path = Path(self.db_path_var.get().strip()).expanduser()
        table_name = self.table_var.get().strip() or DEFAULT_TABLE
        latitude = float(self.lat_var.get().strip())
        longitude = float(self.lon_var.get().strip())
        timezone_offset = float(self.tz_var.get().strip())
        az_sectors = [sector for sector, flag in self.az_sector_vars.items() if flag.get()]
        min_alt_obs = float(self.min_alt_obs_var.get().strip())
        max_targets = int(self.max_targets_var.get().strip())

        if max_targets < 1:
            raise ValueError("Max Targets must be at least 1")

        if not az_sectors:
            raise ValueError("Select at least one azimuth sector")

        if min_alt_obs < 0 or min_alt_obs > 90:
            raise ValueError("Min Alt During Obs must be between 0 and 90 degrees")

        telescope = self.telescope_var.get().strip().upper()
        if telescope not in {"SCT", "S50"}:
            raise ValueError("Telescope must be SCT or S50")

        return {
            "obs_date": obs_date,
            "db_path": db_path,
            "table_name": table_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone_offset": timezone_offset,
            "az_sectors": az_sectors,
            "min_alt_obs": min_alt_obs,
            "max_targets": max_targets,
            "telescope": telescope,
        }

    def generate_targets(self) -> None:
        try:
            inputs = self._parse_inputs()
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.generate_button.configure(state="disabled")
        self._set_status("Searching EB minima from database...")

        thread = threading.Thread(target=self._generate_targets_worker, args=(inputs,), daemon=True)
        thread.start()

    def _generate_targets_worker(self, inputs: dict) -> None:
        try:
            targets = find_eb_targets_for_night(
                observation_date=inputs["obs_date"],
                db_path=inputs["db_path"],
                table_name=inputs["table_name"],
                latitude=inputs["latitude"],
                longitude=inputs["longitude"],
                timezone_offset=inputs["timezone_offset"],
                az_sectors=inputs["az_sectors"],
                min_altitude_during_obs=inputs["min_alt_obs"],
            )
            selected = select_partitioned_targets(
                targets=targets,
                max_targets=inputs["max_targets"],
                observation_date=inputs["obs_date"],
                latitude=inputs["latitude"],
                longitude=inputs["longitude"],
            )
            self.root.after(0, lambda: self._update_results(targets, selected, inputs))
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Search failed", str(exc)))
            self.root.after(0, lambda: self._set_status("Search failed"))
            self.root.after(0, lambda: self.generate_button.configure(state="normal"))

    def _update_results(self, targets, selected, inputs) -> None:
        self.targets = targets
        self.selected_targets = selected
        self.last_inputs = dict(inputs)

        self._clear_tree()
        for item in selected:
            local_time = item["minima_datetime_local"].strftime("%Y-%m-%d %H:%M")
            try:
                ra_deg = float(item.get("ra", 0.0))
                dec_deg = float(item.get("dec", 0.0))
                transit_local_dt = estimate_culmination_local(
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    observation_date=inputs["obs_date"],
                    latitude=inputs["latitude"],
                    longitude=inputs["longitude"],
                    timezone_offset=inputs["timezone_offset"],
                )
                transit_local = transit_local_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                transit_local = ""
            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("name", ""),
                    item.get("ra_sexagesimal", item.get("ra", "")),
                    item.get("dec_sexagesimal", item.get("dec", "")),
                    item.get("minima_type", ""),
                    item.get("minimum_time", ""),
                    local_time,
                    transit_local,
                    item.get("azimuth_deg", ""),
                    item.get("azimuth", ""),
                    item.get("variability_type", ""),
                    item.get("constellation", ""),
                ),
            )

        sectors_text = ",".join(self.last_inputs.get("az_sectors", []))
        self._set_status(f"Found {len(targets)} matching events for [{sectors_text}], showing {len(selected)} target(s)")
        self.generate_button.configure(state="normal")

        if not selected:
            self._set_status(
                f"No targets matched filters: sectors={','.join(inputs.get('az_sectors', []))}, min-alt-obs={inputs.get('min_alt_obs', 30)}"
            )
            messagebox.showwarning(
                "No targets",
                "No EB minima matched all filters. Try lowering Min Alt During Obs or selecting more azimuth sectors.",
            )
            return

        # Auto-create plot after selection so the schedule can be inspected immediately.
        self.show_airmass_plot()

    def show_airmass_plot(self) -> None:
        if not self.selected_targets:
            messagebox.showwarning("No targets", "Generate targets first to plot airmass.")
            return

        if not self.last_inputs:
            messagebox.showwarning("Missing context", "No schedule context available for plotting.")
            return

        obs_date = self.last_inputs["obs_date"]
        latitude = self.last_inputs["latitude"]
        longitude = self.last_inputs["longitude"]
        timezone_offset = self.last_inputs["timezone_offset"]

        night_start, night_end = get_dark_night_bounds_local(obs_date, latitude, longitude)

        plot_window = tk.Toplevel(self.root)
        plot_window.title("EB Airmass Schedule")
        plot_window.geometry("1100x700")
        plot_window.configure(bg="#0b1220")

        fig = Figure(figsize=(12, 6), dpi=100, facecolor="#0b1220")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#111827")

        colors = ["#60a5fa", "#f59e0b", "#34d399", "#f87171", "#a78bfa", "#f472b6"]

        any_curve = False
        all_airmass_values = []

        for idx, target in enumerate(self.selected_targets):
            minima_local = target["minima_datetime_local"]
            start_local = max(minima_local - timedelta(hours=2), night_start)
            end_local = min(minima_local + timedelta(hours=2), night_end)
            if end_local <= start_local:
                continue

            # Draw full-night airmass curve so plot remains informative.
            time_samples = []
            airmass_samples = []
            current_time = night_start
            ra_deg = float(target.get("ra", 0.0))
            dec_deg = float(target.get("dec", 0.0))

            while current_time <= night_end:
                airmass = compute_airmass_at_local_time(
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    local_time=current_time,
                    timezone_offset=timezone_offset,
                    latitude=latitude,
                    longitude=longitude,
                )
                if airmass is not None:
                    time_samples.append(current_time)
                    airmass_samples.append(airmass)
                current_time += timedelta(minutes=10)

            if not time_samples:
                continue

            color = colors[idx % len(colors)]
            label = f"{target.get('name', 'Target')} ({target.get('minima_type', '?')})"
            ax.plot(time_samples, airmass_samples, color=color, linewidth=1.8, label=label)
            any_curve = True
            all_airmass_values.extend(airmass_samples)

            start_am = compute_airmass_at_local_time(ra_deg, dec_deg, start_local, timezone_offset, latitude, longitude)
            min_am = compute_airmass_at_local_time(ra_deg, dec_deg, minima_local, timezone_offset, latitude, longitude)
            end_am = compute_airmass_at_local_time(ra_deg, dec_deg, end_local, timezone_offset, latitude, longitude)

            if start_am is not None:
                ax.scatter([start_local], [start_am], color=color, marker="o", s=28)
            if min_am is not None:
                ax.scatter([minima_local], [min_am], color=color, marker="*", s=90)
                ax.annotate(
                    target.get("name", "Target"),
                    xy=(minima_local, min_am),
                    xytext=(6, -10),
                    textcoords="offset points",
                    fontsize=8,
                    color=color,
                )
            if end_am is not None:
                ax.scatter([end_local], [end_am], color=color, marker="s", s=28)

            ax.axvline(minima_local, color=color, linestyle="--", alpha=0.25)

        ax.axvline(night_start, color="black", linestyle=":", linewidth=1.2, label="Night start")
        ax.axvline(night_end, color="black", linestyle="-.", linewidth=1.2, label="Night end")
        ax.set_xlim(night_start, night_end)
        ax.set_ylim(1.0, 2.4)
        ax.invert_yaxis()
        ax.set_ylabel("Airmass", color="#e5e7eb")
        ax.set_xlabel("Local Time", color="#e5e7eb")
        ax.set_title("Partitioned EB Schedule: Start, Minimum, End and Airmass", color="#f9fafb")
        ax.grid(True, alpha=0.25, color="#475569")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.tick_params(axis="x", colors="#d1d5db")
        ax.tick_params(axis="y", colors="#d1d5db")
        for spine in ax.spines.values():
            spine.set_color("#94a3b8")
        fig.autofmt_xdate()
        legend = ax.legend(fontsize=8, loc="upper right", facecolor="#0f172a", edgecolor="#334155")
        for text in legend.get_texts():
            text.set_color("#e2e8f0")

        if not any_curve:
            ax.text(
                0.5,
                0.5,
                "No airmass curve above horizon for selected targets",
                transform=ax.transAxes,
                ha="center",
                va="center",
                color="#fbbf24",
                fontsize=12,
            )

        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar = NavigationToolbar2Tk(canvas, plot_window)
        toolbar.update()
        toolbar.pack(fill="x")

    def export_selected(self) -> None:
        if not self.selected_targets:
            messagebox.showwarning("No data", "No selected targets to export.")
            return

        try:
            obs_date = date.fromisoformat(self.date_var.get().strip())
        except Exception:
            obs_date = date.today()

        try:
            telescope = self.last_inputs.get("telescope", "SCT")
            out_path = get_nina_targets_export_dir(obs_date, telescope=telescope)
            nina_target_paths = export_targets_nina_individual(
                self.selected_targets,
                output_dir=out_path,
                telescope=telescope,
                observation_date=obs_date,
            )
            saved_paths = [str(path) for path in nina_target_paths]
            messagebox.showinfo("Export complete", "Saved:\n" + "\n".join(saved_paths))
            self._set_status(f"Export complete to {out_path} ({telescope})")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    app = EBTargetSelector(root)
    root.mainloop()
