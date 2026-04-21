import csv
import os
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd


class StatsConfig:
    """Holds configuration constants for the statistics module."""
    STATS_DIR = "data"
    
    CSV_CONFIGS = {
        "accuracy": {
            "file": "stats_accuracy.csv",
            "headers": ["game_number", "player_id", "shots_fired", "shots_hit", "accuracy_pct"],
        },
        "time_per_shot": {
            "file": "stats_time_per_shot.csv",
            "headers": ["game_number", "player_id", "avg_time_per_shot"],
        },
        "damage_per_shell": {
            "file": "stats_damage_per_shell.csv",
            "headers": ["game_number", "shell_type", "damage_dealt"],
        },
        "move_distance": {
            "file": "stats_move_distance.csv",
            "headers": ["game_number", "player_id", "total_distance"],
        },
        "match_duration": {
            "file": "stats_match_duration.csv",
            "headers": ["game_number", "duration_seconds"],
        },
    }

    THEME = {
        "bg":     "#1a1a2e",
        "panel":  "#16213e",
        "title":  "#e0e0e0",
        "text":   "#a0a8b8",
        "grid":   "#2a2a4a",
        "spine":  "#3a3a5a",
        "accent": ["#4e9af1", "#f1a44e", "#4ef1a0", "#f14e4e", "#c44ef1"],
    }

    FONT_SIZE = {"small": 9, "medium": 11, "big": 13}


class StatsManager:
    """Handles data storage, retrieval, and CSV formatting."""
    def __init__(self, config=StatsConfig):
        self.config = config
        self._init_csv_files()

    def _ensure_dir(self):
        if not os.path.exists(self.config.STATS_DIR):
            os.makedirs(self.config.STATS_DIR)

    def _init_csv_files(self):
        self._ensure_dir()
        for key, cfg in self.config.CSV_CONFIGS.items():
            path = os.path.join(self.config.STATS_DIR, cfg["file"])
            if not os.path.exists(path):
                with open(path, "w", newline="") as f:
                    csv.writer(f).writerow(cfg["headers"])

    def append_row(self, key, row_dict):
        self._ensure_dir()
        cfg = self.config.CSV_CONFIGS[key]
        path = os.path.join(self.config.STATS_DIR, cfg["file"])
        
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(cfg["headers"])
                
        with open(path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([row_dict.get(h, "") for h in cfg["headers"]])

    def read_csv(self, key):
        path = os.path.join(self.config.STATS_DIR, self.config.CSV_CONFIGS[key]["file"])
        if not os.path.exists(path):
            return pd.DataFrame(columns=self.config.CSV_CONFIGS[key]["headers"])
        return pd.read_csv(path)

    def get_game_number(self):
        path = os.path.join(self.config.STATS_DIR, self.config.CSV_CONFIGS["match_duration"]["file"])
        if not os.path.exists(path):
            return 1
        try:
            df = pd.read_csv(path)
            if df.empty:
                return 1
            return int(df["game_number"].max()) + 1
        except Exception:
            return 1

    def record_match(self, tanks, match_duration, shell_damage_log):
        self._init_csv_files()
        game_num = self.get_game_number()

        for tank in tanks:
            shots_fired = max(getattr(tank, '_shots_fired', 1), 1)
            shots_hit   = getattr(tank, '_shots_hit', 0)
            acc_pct     = round((shots_hit / shots_fired) * 100, 2)
            avg_time    = round(getattr(tank, 'time_taken', 0) / shots_fired, 2)

            self.append_row("accuracy", {
                "game_number":   game_num,
                "player_id":     tank.player_id,
                "shots_fired":   shots_fired,
                "shots_hit":     shots_hit,
                "accuracy_pct":  acc_pct,
            })
            self.append_row("time_per_shot", {
                "game_number":       game_num,
                "player_id":         tank.player_id,
                "avg_time_per_shot": avg_time,
            })
            self.append_row("move_distance", {
                "game_number":    game_num,
                "player_id":      tank.player_id,
                "total_distance": round(getattr(tank, 'movedistance', 0), 2),
            })

        for shell_type, damage in shell_damage_log.items():
            self.append_row("damage_per_shell", {
                "game_number":  game_num,
                "shell_type":   shell_type,
                "damage_dealt": round(damage, 2),
            })

        self.append_row("match_duration", {
            "game_number":      game_num,
            "duration_seconds": round(match_duration, 2),
        })


class StatsGUI:
    """Manages the Tkinter interface and Matplotlib visualizations."""
    def __init__(self, data_manager: StatsManager, config=StatsConfig):
        self.data_manager = data_manager
        self.config = config
        self.win = None
        self.container = None

    def _style_ax(self, ax, title, xlabel, ylabel):
        ax.set_facecolor(self.config.THEME["panel"])
        ax.set_title(title, fontsize=self.config.FONT_SIZE["big"], color=self.config.THEME["title"], pad=8)
        ax.set_xlabel(xlabel, fontsize=self.config.FONT_SIZE["medium"], color=self.config.THEME["text"])
        ax.set_ylabel(ylabel, fontsize=self.config.FONT_SIZE["medium"], color=self.config.THEME["text"])
        ax.tick_params(colors=self.config.THEME["text"], labelsize=self.config.FONT_SIZE["small"])
        ax.grid(color=self.config.THEME["grid"], linestyle="--", linewidth=0.6, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color(self.config.THEME["spine"])

    def _embed(self, fig, tab):
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _no_data_label(self, tab, text="No data available yet.\nPlay some matches first!"):
        lbl = tk.Label(tab, text=text, bg=self.config.THEME["bg"], fg=self.config.THEME["text"], font=("Helvetica", 12))
        lbl.pack(expand=True)

    def _create_pie_tab(self, notebook, title, key):
        tab = tk.Frame(notebook, bg=self.config.THEME["bg"])
        notebook.add(tab, text=title)

        df = self.data_manager.read_csv(key)
        if df.empty:
            self._no_data_label(tab)
            return

        # Ensure correct datatypes
        df["shots_fired"] = pd.to_numeric(df["shots_fired"], errors="coerce").fillna(0)
        df["shots_hit"]   = pd.to_numeric(df["shots_hit"], errors="coerce").fillna(0)
        df["player_id"]   = df["player_id"].astype(str)
        
        # Check if there is any data at all before plotting
        if df["shots_fired"].sum() == 0:
            self._no_data_label(tab)
            return

        # Create 1 row, 2 columns for the two pie charts
        fig, axes = plt.subplots(1, 2, figsize=(8, 4), facecolor=self.config.THEME["bg"])
        
        # We will use Green (index 2) for Hits and Red (index 3) for Misses from the Theme
        colors = [self.config.THEME["accent"][2], self.config.THEME["accent"][3]]

        for idx, pid in enumerate(["1", "2"]):
            ax = axes[idx]
            ax.set_facecolor(self.config.THEME["bg"])

            p_data = df[df["player_id"] == pid]
            fired = p_data["shots_fired"].sum()
            hit = p_data["shots_hit"].sum()

            # Handle if one of the players didn't fire any shots
            if fired == 0:
                ax.text(0.5, 0.5, f"No data for\nPlayer {pid}", ha="center", va="center",
                        color=self.config.THEME["text"], fontsize=self.config.FONT_SIZE["medium"])
                ax.axis("off")
                continue

            miss = fired - hit
            hit_pct = (hit / fired) * 100 if fired > 0 else 0
            miss_pct = (miss / fired) * 100 if fired > 0 else 0

            # If percentage is < 10%, append it to the label outside the pie.
            labels = ["Hits", "Misses"]
            if hit_pct < 10:
                labels[0] = f"Hits ({hit_pct:.1f}%)"
            if miss_pct < 10:
                labels[1] = f"Misses ({miss_pct:.1f}%)"

            # Custom autopct function: only show text inside if >= 10%
            def custom_autopct(pct):
                return f"{pct:.1f}%" if pct >= 10 else ""

            wedges, texts, autotexts = ax.pie(
                [hit, miss],
                labels=labels,
                autopct=custom_autopct,
                startangle=90,
                colors=colors,
                wedgeprops={"edgecolor": self.config.THEME["bg"], "linewidth": 2},
            )
            
            # Styling the text inside and outside the pie chart
            for t in texts:
                t.set_color(self.config.THEME["title"])
                t.set_fontsize(self.config.FONT_SIZE["medium"])
            for at in autotexts:
                at.set_color(self.config.THEME["bg"])
                at.set_fontsize(self.config.FONT_SIZE["small"])
                at.set_weight("bold")

            ax.set_title(f"Player {pid}({'red' if pid == '1' else 'blue'}) Accuracy", fontsize=self.config.FONT_SIZE["big"], color=self.config.THEME["title"], pad=10)

        fig.tight_layout()
        self._embed(fig, tab)

    def _create_line_tab(self, notebook, title, key, y_col, ax_title, y_label, marker="o"):
        tab = tk.Frame(notebook, bg=self.config.THEME["bg"])
        notebook.add(tab, text=title)

        df = self.data_manager.read_csv(key)
        if df.empty:
            self._no_data_label(tab)
            return

        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df["game_number"] = pd.to_numeric(df["game_number"], errors="coerce")
        df["player_id"]   = df["player_id"].astype(str)

        fig, ax = plt.subplots(figsize=(6, 4), facecolor=self.config.THEME["bg"])
        self._style_ax(ax, ax_title, "Game Number", y_label)

        for pid, color in zip(["1", "2"], [self.config.THEME["accent"][3], self.config.THEME["accent"][0]]):
            sub = df[df["player_id"] == pid].sort_values("game_number")
            if sub.empty:
                continue
            ax.plot(sub["game_number"], sub[y_col],
                    marker=marker, linewidth=2, color=color, label=f"Player {pid}",
                    markersize=5)

        ax.legend(facecolor=self.config.THEME["panel"], labelcolor=self.config.THEME["title"],
                  edgecolor=self.config.THEME["spine"], fontsize=self.config.FONT_SIZE["small"])
        fig.tight_layout()
        self._embed(fig, tab)

    def _create_bar_tab(self, notebook):
        tab = tk.Frame(notebook, bg=self.config.THEME["bg"])
        notebook.add(tab, text="Damage per Shell")

        df = self.data_manager.read_csv("damage_per_shell")
        if df.empty:
            self._no_data_label(tab)
            return

        df["damage_dealt"] = pd.to_numeric(df["damage_dealt"], errors="coerce")
        agg = df.groupby("shell_type")["damage_dealt"].mean().reset_index()
        agg = agg.sort_values("damage_dealt", ascending=False)

        fig, ax = plt.subplots(figsize=(7, 4), facecolor=self.config.THEME["bg"])
        self._style_ax(ax, "Avg Damage Dealt per Shell Type", "Shell Type", "Avg Damage")

        colors = [self.config.THEME["accent"][i % len(self.config.THEME["accent"])] for i in range(len(agg))]
        bars = ax.bar(agg["shell_type"], agg["damage_dealt"], color=colors, edgecolor=self.config.THEME["spine"])

        ax.set_xticks(range(len(agg["shell_type"])))
        ax.set_xticklabels(agg["shell_type"], rotation=35, ha="right",
                           fontsize=self.config.FONT_SIZE["small"], color=self.config.THEME["text"])
        ax.set_ylim(top=int(max(agg["damage_dealt"])) + 10)

        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                    f"{h:.1f}", ha="center", va="bottom",
                    color=self.config.THEME["text"], fontsize=self.config.FONT_SIZE["small"])

        fig.tight_layout()
        self._embed(fig, tab)

    def _create_area_tab(self, notebook):
        tab = tk.Frame(notebook, bg=self.config.THEME["bg"])
        notebook.add(tab, text="Match Duration")

        df = self.data_manager.read_csv("match_duration")
        if df.empty:
            self._no_data_label(tab)
            return

        df["duration_seconds"] = pd.to_numeric(df["duration_seconds"], errors="coerce")
        df["game_number"]      = pd.to_numeric(df["game_number"], errors="coerce")
        df = df.sort_values("game_number")

        fig, ax = plt.subplots(figsize=(6, 4), facecolor=self.config.THEME["bg"])
        self._style_ax(ax, "Match Duration per Game", "Game Number", "Duration (seconds)")

        ax.plot(df["game_number"], df["duration_seconds"],
                marker="D", linewidth=2, color=self.config.THEME["accent"][2],
                markersize=5, label="Duration")
        ax.fill_between(df["game_number"], df["duration_seconds"],
                        alpha=0.15, color=self.config.THEME["accent"][2])

        ax.legend(facecolor=self.config.THEME["panel"], labelcolor=self.config.THEME["title"],
                  edgecolor=self.config.THEME["spine"], fontsize=self.config.FONT_SIZE["small"])
        fig.tight_layout()
        self._embed(fig, tab)

    def _load_content(self):
        plt.close('all')

        for widget in self.container.winfo_children():
            widget.destroy()

        style = ttk.Style(self.win)
        style.theme_use("default")
        style.configure("TNotebook", background=self.config.THEME["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.config.THEME["panel"], foreground=self.config.THEME["text"],
                        padding=[10, 4], font=("Helvetica", 10))
        style.map("TNotebook.Tab", background=[("selected", self.config.THEME["grid"])],
                  foreground=[("selected", self.config.THEME["title"])])

        notebook = ttk.Notebook(self.container)
        notebook.pack(fill=tk.BOTH, expand=True)

        self._create_pie_tab(notebook, "Accuracy", "accuracy")
        self._create_line_tab(notebook, "Time per Shot", "time_per_shot", "avg_time_per_shot", 
                              "Avg Time per Shot per Game", "Avg Time (seconds)", marker="o")
        self._create_bar_tab(notebook)
        self._create_line_tab(notebook, "Move Distance", "move_distance", "total_distance", 
                              "Total Distance Moved per Game", "Distance (pixels)", marker="s")
        self._create_area_tab(notebook)

    def _on_close(self):
            """Cleans up matplotlib figures from memory before destroying the window."""
            plt.close('all')
            self.win.destroy()

    def open_window(self):
        self.win = tk.Tk()
        self.win.title("TankHell — Statistics")
        self.win.configure(bg=self.config.THEME["bg"])
        self.win.geometry("760x580")
        self.win.resizable(True, True)

        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        header = tk.Label(self.win, text="TankHell Statistics",
                          bg=self.config.THEME["bg"], fg=self.config.THEME["title"],
                          font=("Helvetica", 16, "bold"))
        header.pack(pady=(10, 0))

        self.container = tk.Frame(self.win, bg=self.config.THEME["bg"])
        self.container.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        self._load_content()

        btn_frame = tk.Frame(self.win, bg=self.config.THEME["bg"])
        btn_frame.pack(pady=(0, 15))

        refresh_btn = tk.Button(btn_frame, text="Refresh Data", command=self._load_content,
                                bg="#27ae60", fg="white", font=("Helvetica", 11, "bold"),
                                relief="flat", padx=16, pady=6, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=10)

        close_btn = tk.Button(btn_frame, text="Close", command=self._on_close,
                              bg="#c0392b", fg="white", font=("Helvetica", 11, "bold"),
                              relief="flat", padx=16, pady=6, cursor="hand2")
        close_btn.pack(side=tk.LEFT, padx=10)

        self.win.mainloop()
