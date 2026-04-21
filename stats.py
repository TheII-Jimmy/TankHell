import csv
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

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
    "bg":    "#1a1a2e",
    "panel": "#16213e",
    "title": "#e0e0e0",
    "text":  "#a0a8b8",
    "grid":  "#2a2a4a",
    "spine": "#3a3a5a",
    "accent": ["#4e9af1", "#f1a44e", "#4ef1a0", "#f14e4e", "#c44ef1"],
}

FONT_SIZE = {"small": 9, "medium": 11, "big": 13}


def _ensure_dir():
    if not os.path.exists(STATS_DIR):
        os.makedirs(STATS_DIR)


def _init_csv_files():
    _ensure_dir()
    for key, cfg in CSV_CONFIGS.items():
        path = os.path.join(STATS_DIR, cfg["file"])
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(cfg["headers"])


def _append_row(key, row_dict):
    _ensure_dir()
    cfg = CSV_CONFIGS[key]
    path = os.path.join(STATS_DIR, cfg["file"])
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(cfg["headers"])
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([row_dict.get(h, "") for h in cfg["headers"]])


def _read_csv(key):
    path = os.path.join(STATS_DIR, CSV_CONFIGS[key]["file"])
    if not os.path.exists(path):
        return pd.DataFrame(columns=CSV_CONFIGS[key]["headers"])
    df = pd.read_csv(path)
    return df


def _game_number():
    path = os.path.join(STATS_DIR, CSV_CONFIGS["match_duration"]["file"])
    if not os.path.exists(path):
        return 1
    try:
        df = pd.read_csv(path)
        if df.empty:
            return 1
        return int(df["game_number"].max()) + 1
    except Exception:
        return 1


def record_match(tanks, match_duration, shell_damage_log):
    _init_csv_files()
    game_num = _game_number()

    for tank in tanks:
        shots_fired = max(tank._shots_fired, 1)
        shots_hit   = tank._shots_hit
        acc_pct     = round((shots_hit / shots_fired) * 100, 2)
        avg_time    = round(tank.time_taken / shots_fired, 2)

        _append_row("accuracy", {
            "game_number":   game_num,
            "player_id":     tank.player_id,
            "shots_fired":   shots_fired,
            "shots_hit":     shots_hit,
            "accuracy_pct":  acc_pct,
        })
        _append_row("time_per_shot", {
            "game_number":       game_num,
            "player_id":         tank.player_id,
            "avg_time_per_shot": avg_time,
        })
        _append_row("move_distance", {
            "game_number":   game_num,
            "player_id":     tank.player_id,
            "total_distance": round(tank.movedistance, 2),
        })

    for shell_type, damage in shell_damage_log.items():
        _append_row("damage_per_shell", {
            "game_number": game_num,
            "shell_type":  shell_type,
            "damage_dealt": round(damage, 2),
        })

    _append_row("match_duration", {
        "game_number":      game_num,
        "duration_seconds": round(match_duration, 2),
    })


def _style_ax(ax, title, xlabel, ylabel):
    ax.set_facecolor(THEME["panel"])
    ax.set_title(title, fontsize=FONT_SIZE["big"], color=THEME["title"], pad=8)
    ax.set_xlabel(xlabel, fontsize=FONT_SIZE["medium"], color=THEME["text"])
    ax.set_ylabel(ylabel, fontsize=FONT_SIZE["medium"], color=THEME["text"])
    ax.tick_params(colors=THEME["text"], labelsize=FONT_SIZE["small"])
    ax.grid(color=THEME["grid"], linestyle="--", linewidth=0.6, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color(THEME["spine"])


def _embed(fig, tab):
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def _no_data_label(tab, text="No data available yet.\nPlay some matches first!"):
    lbl = tk.Label(tab, text=text, bg=THEME["bg"], fg=THEME["text"], font=("Helvetica", 12))
    lbl.pack(expand=True)


def _tab_accuracy(notebook):
    tab = tk.Frame(notebook, bg=THEME["bg"])
    notebook.add(tab, text="Accuracy")

    df = _read_csv("accuracy")
    if df.empty:
        _no_data_label(tab)
        return

    df["accuracy_pct"] = pd.to_numeric(df["accuracy_pct"], errors="coerce")
    df["player_id"]    = df["player_id"].astype(str)

    p1 = df[df["player_id"] == "1"]["accuracy_pct"].sum()
    p2 = df[df["player_id"] == "2"]["accuracy_pct"].sum()
    total = p1 + p2
    if total == 0:
        _no_data_label(tab)
        return

    hit_sum   = [p1, p2]
    miss_sum  = [max(0, 100 - p1), max(0, 100 - p2)]
    labels    = ["Player 1", "Player 2"]

    fig, ax = plt.subplots(figsize=(5, 4), facecolor=THEME["bg"])
    ax.set_facecolor(THEME["bg"])

    wedges, texts, autotexts = ax.pie(
        [p1, p2],
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=[THEME["accent"][0], THEME["accent"][3]],
        wedgeprops={"edgecolor": THEME["bg"], "linewidth": 2},
    )
    for t in texts:
        t.set_color(THEME["title"])
        t.set_fontsize(FONT_SIZE["medium"])
    for at in autotexts:
        at.set_color(THEME["bg"])
        at.set_fontsize(FONT_SIZE["small"])

    ax.set_title("Accuracy Share (Hit %)", fontsize=FONT_SIZE["big"], color=THEME["title"], pad=10)
    ax.legend(labels, loc="lower right", fontsize=FONT_SIZE["small"],
              facecolor=THEME["panel"], labelcolor=THEME["text"], edgecolor=THEME["spine"])
    fig.tight_layout()
    _embed(fig, tab)


def _tab_time_per_shot(notebook):
    tab = tk.Frame(notebook, bg=THEME["bg"])
    notebook.add(tab, text="Time per Shot")

    df = _read_csv("time_per_shot")
    if df.empty:
        _no_data_label(tab)
        return

    df["avg_time_per_shot"] = pd.to_numeric(df["avg_time_per_shot"], errors="coerce")
    df["game_number"]       = pd.to_numeric(df["game_number"], errors="coerce")
    df["player_id"]         = df["player_id"].astype(str)

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=THEME["bg"])
    _style_ax(ax, "Avg Time per Shot per Game", "Game Number", "Avg Time (seconds)")

    for pid, color in zip(["1", "2"], [THEME["accent"][0], THEME["accent"][3]]):
        sub = df[df["player_id"] == pid].sort_values("game_number")
        if sub.empty:
            continue
        ax.plot(sub["game_number"], sub["avg_time_per_shot"],
                marker="o", linewidth=2, color=color, label=f"Player {pid}",
                markersize=5)

    ax.legend(facecolor=THEME["panel"], labelcolor=THEME["title"],
              edgecolor=THEME["spine"], fontsize=FONT_SIZE["small"])
    fig.tight_layout()
    _embed(fig, tab)


def _tab_damage_per_shell(notebook):
    tab = tk.Frame(notebook, bg=THEME["bg"])
    notebook.add(tab, text="Damage per Shell")

    df = _read_csv("damage_per_shell")
    if df.empty:
        _no_data_label(tab)
        return

    df["damage_dealt"] = pd.to_numeric(df["damage_dealt"], errors="coerce")
    agg = df.groupby("shell_type")["damage_dealt"].mean().reset_index()
    agg = agg.sort_values("damage_dealt", ascending=False)

    fig, ax = plt.subplots(figsize=(7, 4), facecolor=THEME["bg"])
    _style_ax(ax, "Avg Damage Dealt per Shell Type", "Shell Type", "Avg Damage")

    colors = [THEME["accent"][i % len(THEME["accent"])] for i in range(len(agg))]
    bars = ax.bar(agg["shell_type"], agg["damage_dealt"], color=colors, edgecolor=THEME["spine"])

    ax.set_xticks(range(len(agg["shell_type"])))

    ax.set_xticklabels(agg["shell_type"], rotation=35, ha="right",
                       fontsize=FONT_SIZE["small"], color=THEME["text"])

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                f"{h:.1f}", ha="center", va="bottom",
                color=THEME["text"], fontsize=FONT_SIZE["small"])

    ax.legend(["Avg Damage"], facecolor=THEME["panel"], labelcolor=THEME["title"],
              edgecolor=THEME["spine"], fontsize=FONT_SIZE["small"])
    fig.tight_layout()
    _embed(fig, tab)


def _tab_move_distance(notebook):
    tab = tk.Frame(notebook, bg=THEME["bg"])
    notebook.add(tab, text="Move Distance")

    df = _read_csv("move_distance")
    if df.empty:
        _no_data_label(tab)
        return

    df["total_distance"] = pd.to_numeric(df["total_distance"], errors="coerce")
    df["game_number"]    = pd.to_numeric(df["game_number"], errors="coerce")
    df["player_id"]      = df["player_id"].astype(str)

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=THEME["bg"])
    _style_ax(ax, "Total Distance Moved per Game", "Game Number", "Distance (pixels)")

    for pid, color in zip(["1", "2"], [THEME["accent"][0], THEME["accent"][3]]):
        sub = df[df["player_id"] == pid].sort_values("game_number")
        if sub.empty:
            continue
        ax.plot(sub["game_number"], sub["total_distance"],
                marker="s", linewidth=2, color=color, label=f"Player {pid}",
                markersize=5)

    ax.legend(facecolor=THEME["panel"], labelcolor=THEME["title"],
              edgecolor=THEME["spine"], fontsize=FONT_SIZE["small"])
    fig.tight_layout()
    _embed(fig, tab)


def _tab_match_duration(notebook):
    tab = tk.Frame(notebook, bg=THEME["bg"])
    notebook.add(tab, text="Match Duration")

    df = _read_csv("match_duration")
    if df.empty:
        _no_data_label(tab)
        return

    df["duration_seconds"] = pd.to_numeric(df["duration_seconds"], errors="coerce")
    df["game_number"]      = pd.to_numeric(df["game_number"], errors="coerce")
    df = df.sort_values("game_number")

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=THEME["bg"])
    _style_ax(ax, "Match Duration per Game", "Game Number", "Duration (seconds)")

    ax.plot(df["game_number"], df["duration_seconds"],
            marker="D", linewidth=2, color=THEME["accent"][2],
            markersize=5, label="Duration")
    ax.fill_between(df["game_number"], df["duration_seconds"],
                    alpha=0.15, color=THEME["accent"][2])

    ax.legend(facecolor=THEME["panel"], labelcolor=THEME["title"],
              edgecolor=THEME["spine"], fontsize=FONT_SIZE["small"])
    fig.tight_layout()
    _embed(fig, tab)


def open_stats_window():
    win = tk.Tk()
    win.title("TankHell — Statistics")
    win.configure(bg=THEME["bg"])
    win.geometry("760x580")
    win.resizable(True, True)

    header = tk.Label(win, text="TankHell Statistics",
                      bg=THEME["bg"], fg=THEME["title"],
                      font=("Helvetica", 16, "bold"))
    header.pack(pady=(10, 0))

    container = tk.Frame(win, bg=THEME["bg"])
    container.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

    def load_content():
        for widget in container.winfo_children():
            widget.destroy()

        style = ttk.Style(win)
        style.theme_use("default")
        style.configure("TNotebook", background=THEME["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=THEME["panel"], foreground=THEME["text"],
                        padding=[10, 4], font=("Helvetica", 10))
        style.map("TNotebook.Tab", background=[("selected", THEME["grid"])],
                  foreground=[("selected", THEME["title"])])

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        _tab_accuracy(notebook)
        _tab_time_per_shot(notebook)
        _tab_damage_per_shell(notebook)
        _tab_move_distance(notebook)
        _tab_match_duration(notebook)

    load_content()

    btn_frame = tk.Frame(win, bg=THEME["bg"])
    btn_frame.pack(pady=(0, 15))

    refresh_btn = tk.Button(btn_frame, text="Refresh Data", command=load_content,
                            bg="#27ae60", fg="white", font=("Helvetica", 11, "bold"),
                            relief="flat", padx=16, pady=6, cursor="hand2")
    refresh_btn.pack(side=tk.LEFT, padx=10)

    close_btn = tk.Button(btn_frame, text="Close", command=win.destroy,
                          bg="#c0392b", fg="white", font=("Helvetica", 11, "bold"),
                          relief="flat", padx=16, pady=6, cursor="hand2")
    close_btn.pack(side=tk.LEFT, padx=10)

    win.mainloop()
