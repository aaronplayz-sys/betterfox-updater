import sys
import os
import ctypes
import queue
import threading
import time
import subprocess
import webbrowser
import tkinter.messagebox as tkmsg
import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Optional
import pystray
from pystray import MenuItem as TrayItem
from update_betterfox import (
    is_firefox_running,
    PSUTIL_AVAILABLE,
    START_WITH_SYSTEM_SUPPORTED,
    get_start_with_system,
    set_start_with_system,
    install_linux_desktop_entry,
    get_base_path,
    get_all_profiles,
    get_latest_app_version,
    get_installed_version,
    get_latest_version,
    load_config,
    save_config,
    is_check_due,
    save_last_checked,
    list_backups,
    restore_backup,
    main as run_update_logic,
)

try:
    from plyer import notification as plyer_notify
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


APP_VERSION   = "1.8.1"
RELEASES_URL  = "https://github.com/aaronplayz-sys/betterfox-updater/releases"

INTERVAL_LABELS = ["On launch only", "Daily", "Weekly", "Every 4 weeks"]
INTERVAL_KEYS   = ["on_launch", "daily", "weekly", "every_4_weeks"]
LABEL_TO_KEY    = dict(zip(INTERVAL_LABELS, INTERVAL_KEYS))
KEY_TO_LABEL    = dict(zip(INTERVAL_KEYS, INTERVAL_LABELS))


# ---------------------------------------------------------------------------
# Thread-safe stdout bridge
# ---------------------------------------------------------------------------

class QueueStream:
    """Redirects print() output from worker threads into a queue."""
    def __init__(self, q: queue.Queue):
        self._queue = q

    def write(self, text: str):
        if text:
            self._queue.put(text)

    def flush(self):
        pass


log_queue: queue.Queue = queue.Queue()


# ---------------------------------------------------------------------------
# Queue poller
# ---------------------------------------------------------------------------

def _poll_queue():
    try:
        while True:
            text = log_queue.get_nowait()
            log_box.insert("end", text)
            log_box.see("end")
    except queue.Empty:
        pass
    app.after(100, _poll_queue)


# ---------------------------------------------------------------------------
# Profile picker helpers
# ---------------------------------------------------------------------------

profile_list: list[dict] = []
backup_paths: list[str]  = []


def _load_profiles():
    profiles = get_all_profiles()
    profile_list.clear()
    profile_list.extend(profiles)

    if not profiles:
        profile_menu.configure(values=["No profiles found"], state="disabled")
        profile_menu.set("No profiles found")
        return

    labels = [
        f"{p['name']}  (default)" if p["is_default"] else p["name"]
        for p in profiles
    ]
    profile_menu.configure(values=labels, state="normal")
    profile_menu.set(labels[0])


def _get_selected_profile() -> dict | None:
    label  = profile_menu.get()
    labels = [
        f"{p['name']}  (default)" if p["is_default"] else p["name"]
        for p in profile_list
    ]
    try:
        return profile_list[labels.index(label)]
    except ValueError:
        return None


def _on_profile_change(_choice: str):
    _refresh_backup_menu()
    _start_version_check()


# ---------------------------------------------------------------------------
# Profile folder
# ---------------------------------------------------------------------------

def _open_profile_folder():
    """Opens the selected Firefox profile directory in the system file manager."""
    import platform as _platform
    profile = _get_selected_profile()
    if not profile:
        return
    path = profile["path"]
    if not os.path.exists(path):
        tkmsg.showerror("Folder Not Found", f"Profile folder does not exist:\n{path}")
        return
    try:
        system = _platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
    except Exception as e:
        tkmsg.showerror("Error", f"Could not open folder:\n{e}")


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def _run_version_check():
    app.after(0, lambda: version_label.configure(
        text="Checking for updates...", text_color="gray"
    ))
    installed = get_installed_version(get_base_path())
    latest    = get_latest_version()

    def _update():
        if not installed and not latest:
            version_label.configure(text="Could not check version", text_color="gray")
        elif not installed:
            version_label.configure(
                text=f"Betterfox not yet installed  (latest: v{latest})",
                text_color="gray",
            )
        elif not latest:
            version_label.configure(
                text=f"Installed: v{installed}  (could not fetch latest)",
                text_color="gray",
            )
        elif installed == latest:
            version_label.configure(
                text=f"Up to date: v{installed} ✓",
                text_color="#50C878",
            )
        else:
            version_label.configure(
                text=f"v{installed} installed  →  v{latest} available",
                text_color="#FFA500",
            )

    app.after(0, _update)


def _start_version_check():
    threading.Thread(target=_run_version_check, daemon=True).start()


# ---------------------------------------------------------------------------
# Backup menu helpers
# ---------------------------------------------------------------------------

def _friendly_backup_name(path: str) -> str:
    name  = os.path.basename(path)
    stamp = name.split(".backup.")[-1]
    try:
        dt = __import__("datetime").datetime.strptime(stamp, "%Y%m%d-%H%M%S")
        return dt.strftime("%Y-%m-%d  %H:%M:%S")
    except ValueError:
        return stamp


def _refresh_backup_menu():
    profile = _get_selected_profile()
    backups = list_backups(profile["path"]) if profile else []

    backup_paths.clear()
    backup_paths.extend(backups)

    if backups:
        labels = [_friendly_backup_name(p) for p in backups]
        restore_menu.configure(values=labels, state="normal")
        restore_menu.set(labels[0])
        restore_button.configure(state="normal")
    else:
        restore_menu.configure(values=["No backups found"], state="disabled")
        restore_menu.set("No backups found")
        restore_button.configure(state="disabled")


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _set_buttons(state: str):
    update_button.configure(state=state)
    restore_button.configure(state=state)
    open_folder_button.configure(state=state)
    profile_menu.configure(state="disabled" if state == "disabled" else "normal")


def _check_firefox_on_startup():
    if PSUTIL_AVAILABLE and is_firefox_running():
        firefox_banner.configure(
            text="⚠  Firefox is running — migration will be skipped if you update now",
            text_color="#FFA500",
        )
    elif not PSUTIL_AVAILABLE:
        firefox_banner.configure(
            text="psutil not installed — install it to enable Firefox detection",
            text_color="orange",
        )


# ---------------------------------------------------------------------------
# Self-update check
# ---------------------------------------------------------------------------

def _run_app_update_check():
    latest = get_latest_app_version()
    if not latest:
        return
    if latest != APP_VERSION:
        app.after(0, lambda: _show_app_update_banner(latest))


def _show_app_update_banner(latest: str):
    app_update_button.configure(
        text=f"⬆  Updater v{latest} available — click to download",
        text_color="#FFA500",
    )
    app_update_button.pack(pady=(0, 4))


def _open_releases():
    webbrowser.open(RELEASES_URL)


# ---------------------------------------------------------------------------
# Tray icon
# ---------------------------------------------------------------------------

_tray_icon: Optional[pystray.Icon] = None
_quit_event = threading.Event()


def _find_icon_path(filename: str) -> str | None:
    """Finds an icon file in _MEIPASS (frozen) or assets/ (dev)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p = os.path.join(meipass, filename)
        if os.path.exists(p):
            return p
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)
    return p if os.path.exists(p) else None


def _load_tray_image() -> Image.Image:
    """Returns a PIL Image for the tray icon, falling back to a plain square."""
    for name in ("AppIcon1024.png", "favicon.ico"):
        path = _find_icon_path(name)
        if path:
            return Image.open(path).resize((64, 64), Image.LANCZOS)
    # Fallback: plain blue square
    return Image.new("RGB", (64, 64), color="#5865F2")


def _restore_from_tray():
    """Shows the main window and brings it to focus. Thread-safe."""
    app.after(0, lambda: (
        app.deiconify(),
        app.lift(),
        app.focus_force(),
    ))


def _tray_check_now():
    """Triggered from the tray menu — runs a background update check."""
    threading.Thread(target=_background_check, daemon=True).start()


def _quit_app():
    """Cleanly shuts down the schedule loop, tray icon, and main window."""
    _quit_event.set()
    if _tray_icon:
        _tray_icon.stop()
    app.after(0, app.destroy)


def _minimize_to_tray():
    """Hides the window and ensures the tray icon is running."""
    app.withdraw()


def _setup_tray():
    """Creates and starts the pystray icon in a background thread.

    Skipped on macOS — pystray's AppKit backend conflicts with tkinter's
    main thread ownership of the NSApplication run loop, causing EXC_BREAKPOINT.
    The close button exits normally on macOS as a result.
    """
    import platform as _platform
    if _platform.system() == "Darwin":
        # Revert to normal close behaviour on macOS
        app.protocol("WM_DELETE_WINDOW", _quit_app)
        return

    global _tray_icon

    image = _load_tray_image()
    menu  = pystray.Menu(
        TrayItem("Betterfox Updater", None, enabled=False),
        pystray.Menu.SEPARATOR,
        TrayItem("Open", lambda icon, item: _restore_from_tray()),
        TrayItem("Check for Updates Now", lambda icon, item: _tray_check_now()),
        pystray.Menu.SEPARATOR,
        TrayItem("Quit", lambda icon, item: _quit_app()),
    )

    _tray_icon = pystray.Icon(
        "BetterfoxUpdater",
        image,
        "Betterfox Updater",
        menu,
    )

    # Left-click restores the window
    _tray_icon.default_action = lambda icon, item: _restore_from_tray()

    threading.Thread(target=_tray_icon.run, daemon=True).start()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def _send_notification(title: str, message: str):
    """Sends a native OS notification via plyer."""
    if not PLYER_AVAILABLE:
        return
    try:
        icon_path = _find_icon_path("favicon.ico") or _find_icon_path("AppIcon1024.png")
        plyer_notify.notify(
            title=title,
            message=message,
            app_name="Betterfox Updater",
            app_icon=icon_path or "",
            timeout=10,
        )
    except Exception:
        pass  # Never crash over a notification


# ---------------------------------------------------------------------------
# Background schedule loop
# ---------------------------------------------------------------------------

def _background_check():
    """Checks for a Betterfox update and notifies if one is found."""
    base_dir  = get_base_path()
    installed = get_installed_version(base_dir)
    latest    = get_latest_version()
    save_last_checked(base_dir)

    if not latest:
        return

    # Refresh the version label on the main thread
    app.after(0, _start_version_check)

    if not installed:
        _send_notification(
            "Betterfox Updater",
            f"Betterfox v{latest} is available. Open the app to install it.",
        )
    elif latest != installed:
        _send_notification(
            "Betterfox Update Available",
            f"v{installed} → v{latest} is ready. Open Betterfox Updater to update.",
        )


def _schedule_loop():
    """Runs in a background thread, waking every 60 seconds to check if a
    scheduled update check is due."""
    while not _quit_event.wait(timeout=60):
        if is_check_due(get_base_path()):
            _background_check()


# ---------------------------------------------------------------------------
# Interval selector
# ---------------------------------------------------------------------------

def _on_interval_change(choice: str):
    cfg = load_config(get_base_path())
    cfg["check_interval"] = LABEL_TO_KEY.get(choice, "weekly")
    save_config(get_base_path(), cfg)


def _load_interval_setting():
    cfg      = load_config(get_base_path())
    interval = cfg.get("check_interval", "weekly")
    interval_menu.set(KEY_TO_LABEL.get(interval, "Weekly"))


# ---------------------------------------------------------------------------
# Start minimized toggle
# ---------------------------------------------------------------------------

def _on_start_minimized_toggle():
    cfg = load_config(get_base_path())
    cfg["start_minimized"] = bool(start_minimized_var.get())
    save_config(get_base_path(), cfg)


def _load_start_minimized_setting():
    cfg = load_config(get_base_path())
    start_minimized_var.set(1 if cfg.get("start_minimized", False) else 0)


# ---------------------------------------------------------------------------
# Start with system
# ---------------------------------------------------------------------------

def _on_start_with_system_toggle():
    enabled = bool(start_with_system_var.get())
    success = set_start_with_system(enabled)
    if not success:
        # Revert checkbox if registry write failed
        start_with_system_var.set(0)
        tkmsg.showerror(
            "Registry Error",
            "Could not update the startup registry entry. "
            "Try running the app as administrator."
        )
        return
    # Auto-enable start minimized when enabling start with system
    if enabled and not start_minimized_var.get():
        start_minimized_var.set(1)
        _on_start_minimized_toggle()


def _load_start_with_system_setting():
    if START_WITH_SYSTEM_SUPPORTED:
        start_with_system_var.set(1 if get_start_with_system() else 0)
        start_with_system_check.configure(state="normal")
    else:
        start_with_system_check.configure(state="disabled")


# ---------------------------------------------------------------------------
# Update worker
# ---------------------------------------------------------------------------

def _run_update(profile_path: str):
    old_stdout = sys.stdout
    sys.stdout = QueueStream(log_queue)
    try:
        run_update_logic(profile_path=profile_path)
        app.after(0, _on_update_success)
    except Exception as e:
        log_queue.put(f"\n[ERROR]: {e}\n")
        app.after(0, _on_failure)
    finally:
        sys.stdout = old_stdout


def start_update():
    profile = _get_selected_profile()
    if not profile:
        tkmsg.showerror("No Profile", "No Firefox profile selected.")
        return

    if PSUTIL_AVAILABLE and is_firefox_running():
        firefox_banner.configure(
            text="⚠  Firefox is running — migration will be skipped",
            text_color="#FFA500",
        )
        proceed = tkmsg.askyesno(
            title="Firefox is Running",
            message=(
                "Firefox is currently open.\n\n"
                "The migration step — which removes stale preferences left over "
                "from previous Betterfox versions — requires Firefox to be closed. "
                "If you continue now, that step will be skipped and your prefs.js "
                "will not be fully cleaned up.\n\n"
                "Close Firefox and update again for a complete update.\n\n"
                "Update anyway?"
            ),
        )
        if not proceed:
            return
    else:
        firefox_banner.configure(text="", text_color="yellow")

    log_box.delete("0.0", "end")
    status_label.configure(text="Status: Updating...", text_color="blue")
    _set_buttons("disabled")
    threading.Thread(target=_run_update, args=(profile["path"],), daemon=True).start()


def _on_update_success():
    status_label.configure(text="SUCCESS: PLEASE RESTART FIREFOX", text_color="#50C878")
    log_queue.put("\n" + "=" * 30 + "\n")
    log_queue.put("Restart Firefox to apply changes.\n")
    log_queue.put("=" * 30 + "\n")
    _set_buttons("normal")
    _refresh_backup_menu()
    _start_version_check()


# ---------------------------------------------------------------------------
# Restore worker
# ---------------------------------------------------------------------------

def _run_restore(backup_path: str, profile_path: str):
    old_stdout = sys.stdout
    sys.stdout = QueueStream(log_queue)
    try:
        success = restore_backup(backup_path, profile_path)
        app.after(0, _on_restore_success if success else _on_failure)
    except Exception as e:
        log_queue.put(f"\n[ERROR]: {e}\n")
        app.after(0, _on_failure)
    finally:
        sys.stdout = old_stdout


def start_restore():
    profile = _get_selected_profile()
    if not profile:
        tkmsg.showerror("No Profile", "No Firefox profile selected.")
        return

    selected_label = restore_menu.get()
    if not backup_paths or selected_label in ("No backups found", ""):
        return

    labels = [_friendly_backup_name(p) for p in backup_paths]
    try:
        backup_path = backup_paths[labels.index(selected_label)]
    except ValueError:
        return

    log_box.delete("0.0", "end")
    status_label.configure(text="Status: Restoring...", text_color="blue")
    _set_buttons("disabled")
    threading.Thread(
        target=_run_restore, args=(backup_path, profile["path"]), daemon=True
    ).start()


def _on_restore_success():
    status_label.configure(text="RESTORED: PLEASE RESTART FIREFOX", text_color="#50C878")
    log_queue.put("\n" + "=" * 30 + "\n")
    log_queue.put("Backup restored. Restart Firefox\nto apply the previous settings.\n")
    log_queue.put("=" * 30 + "\n")
    _set_buttons("normal")


def _on_failure():
    status_label.configure(text="Operation Failed", text_color="red")
    _set_buttons("normal")


# ---------------------------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------------------------

BETTERFOX_REPO_URL = "https://github.com/yokoffing/Betterfox"


def show_welcome_screen():
    """Displays a first-run welcome window. Blocks the main window until dismissed."""
    win = ctk.CTkToplevel(app)
    win.title("Welcome to Betterfox Updater")
    win.geometry("480x520")
    win.resizable(False, False)
    win.grab_set()

    app.update_idletasks()
    x = app.winfo_x() + (app.winfo_width()  - 480) // 2
    y = app.winfo_y() + (app.winfo_height() - 520) // 2
    win.geometry(f"+{x}+{y}")

    scroll = ctk.CTkScrollableFrame(win, width=440, height=410)
    scroll.pack(padx=20, pady=(20, 10), fill="both", expand=True)

    def section_header(text: str):
        ctk.CTkLabel(
            scroll, text=text, font=("Arial", 14, "bold"), anchor="w"
        ).pack(fill="x", pady=(12, 2))

    def body_text(text: str):
        ctk.CTkLabel(
            scroll, text=text, font=("Arial", 13),
            wraplength=400, justify="left", anchor="w"
        ).pack(fill="x", pady=(0, 4))

    def link_button(text: str, url: str):
        ctk.CTkButton(
            scroll, text=text, font=("Arial", 13),
            fg_color="transparent", hover_color="gray",
            border_width=0, anchor="w",
            command=lambda: webbrowser.open(url),
        ).pack(anchor="w", pady=(0, 4))

    ctk.CTkLabel(
        scroll, text="Welcome to Betterfox Updater",
        font=("Arial", 18, "bold")
    ).pack(pady=(4, 12))

    section_header("What is Betterfox?")
    body_text(
        "Betterfox is a user.js template that improves Firefox's default settings "
        "for better privacy, performance, and security. It's maintained by yokoffing "
        "and updated with each Firefox release."
    )
    link_button("→  View Betterfox on GitHub", BETTERFOX_REPO_URL)

    section_header("What does this updater do?")
    body_text(
        "It downloads the latest Betterfox user.js, merges it with your personal "
        "override files, cleans up preferences removed in newer versions, and creates "
        "a timestamped backup before every change so you can always roll back."
    )

    section_header("Override files")
    body_text(
        "You can customize Firefox's behaviour by editing the override files placed "
        "next to this app. Your hardware and OS are detected automatically — the right "
        "file is applied without any configuration."
    )
    body_text("  •  common-overrides.js — applied on all platforms")
    body_text("  •  windows / mac / linux-overrides.js — your OS")
    body_text("  •  nvidia / amd / intel / apple-silicon-overrides.js — your GPU")
    body_text(
        "Any missing override files are downloaded from the repo automatically "
        "on your first sync and saved next to this app — open them in any text "
        "editor to customise your settings."
    )

    section_header("Getting started")
    body_text(
        "Select your Firefox profile from the dropdown, then click Update Now. "
        "Restart Firefox when prompted to apply the changes. "
        "Closing the window minimizes the app to the system tray so it can "
        "notify you when updates are available."
    )

    def on_get_started():
        cfg = load_config(get_base_path())
        cfg["first_run"] = False
        save_config(get_base_path(), cfg)
        win.destroy()

    ctk.CTkButton(
        win, text="Get Started", font=("Arial", 14),
        width=200, height=40, command=on_get_started,
    ).pack(pady=12)


# ---------------------------------------------------------------------------
# Window icon
# ---------------------------------------------------------------------------

def _set_window_icon():
    import platform as _platform

    try:
        if _platform.system() == "Windows":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "Betterfox.Updater"
                )
            except Exception:
                pass
            path = _find_icon_path("favicon.ico")
            if path:
                app.iconbitmap(path)
        else:
            path = _find_icon_path("AppIcon1024.png")
            if path:
                img   = Image.open(path).resize((64, 64), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                app.iconphoto(True, photo)
                app._icon_ref = photo
    except Exception:
        pass


# ---------------------------------------------------------------------------
# GUI layout
# ---------------------------------------------------------------------------

app = ctk.CTk()
_set_window_icon()

# Withdraw before the event loop if start_minimized is configured —
# prevents the window from flashing briefly on startup
_startup_cfg = load_config(get_base_path())
if _startup_cfg.get("start_minimized", False):
    app.withdraw()

app.geometry("500x680")
app.title("Betterfox Updater")

# Intercept close button — minimize to tray instead of quitting
app.protocol("WM_DELETE_WINDOW", _minimize_to_tray)

# Title
ctk.CTkLabel(app, text="Betterfox Updater", font=("Arial", 20)).pack(pady=(14, 4))

# Self-update banner
app_update_button = ctk.CTkButton(
    app, text="", font=("Arial", 13),
    fg_color="transparent", hover_color="gray",
    border_width=0, command=_open_releases,
)

# Firefox running banner
firefox_banner = ctk.CTkLabel(app, text="", font=("Arial", 13))
firefox_banner.pack(pady=(0, 4))

# Version status
version_label = ctk.CTkLabel(app, text="", font=("Arial", 13))
version_label.pack(pady=(0, 4))

# Profile picker
profile_frame = ctk.CTkFrame(app, fg_color="transparent")
profile_frame.pack(pady=(4, 2))
ctk.CTkLabel(profile_frame, text="Profile:", font=("Arial", 13)).pack(side="left", padx=(0, 8))
profile_menu = ctk.CTkOptionMenu(
    profile_frame, values=["Loading..."],
    command=_on_profile_change, width=300,
)
profile_menu.pack(side="left")

open_folder_button = ctk.CTkButton(
    profile_frame,
    text="📂",
    width=36,
    font=("Arial", 14),
    fg_color="transparent",
    hover_color="gray",
    border_width=0,
    command=_open_profile_folder,
)
open_folder_button.pack(side="left", padx=(6, 0))

# Status
status_label = ctk.CTkLabel(app, text="Status: Ready", text_color="white")
status_label.pack(pady=(8, 4))

# Update button
update_button = ctk.CTkButton(app, text="Update Now", command=start_update, width=200)
update_button.pack(pady=4)

# Restore section
ctk.CTkLabel(app, text="── Restore a backup ──", text_color="white", font=("Arial", 13)).pack(pady=(14, 4))

restore_frame = ctk.CTkFrame(app, fg_color="transparent")
restore_frame.pack(pady=4)
restore_menu = ctk.CTkOptionMenu(restore_frame, values=["No backups found"], width=260)
restore_menu.pack(side="left", padx=(0, 8))
restore_button = ctk.CTkButton(
    restore_frame, text="Restore", command=start_restore, width=100, state="disabled"
)
restore_button.pack(side="left")

# Check interval selector
ctk.CTkLabel(app, text="── Update check interval ──", text_color="white", font=("Arial", 13)).pack(pady=(14, 4))
interval_frame = ctk.CTkFrame(app, fg_color="transparent")
interval_frame.pack(pady=4)
ctk.CTkLabel(interval_frame, text="Check for updates:", font=("Arial", 13)).pack(side="left", padx=(0, 8))
interval_menu = ctk.CTkOptionMenu(
    interval_frame, values=INTERVAL_LABELS,
    command=_on_interval_change, width=200,
)
interval_menu.pack(side="left")

# Start minimized checkbox
start_minimized_var = ctk.IntVar(value=0)
start_minimized_check = ctk.CTkCheckBox(
    app,
    text="Start minimized to tray",
    font=("Arial", 13),
    variable=start_minimized_var,
    command=_on_start_minimized_toggle,
)
start_minimized_check.pack(pady=(4, 8))

# Start with system checkbox — disabled on unsupported platforms (e.g. macOS)
start_with_system_var = ctk.IntVar(value=0)
start_with_system_check = ctk.CTkCheckBox(
    app,
    text="Start with system",
    font=("Arial", 13),
    variable=start_with_system_var,
    command=_on_start_with_system_toggle,
    state="disabled",  # Enabled after _load_start_with_system_setting runs
)
start_with_system_check.pack(pady=(0, 8))

# Log box
log_box = ctk.CTkTextbox(app, width=440, height=160)
log_box.pack(pady=16, padx=20)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

app.after(100, _poll_queue)
app.after(150, _check_firefox_on_startup)
app.after(200, _load_profiles)
app.after(300, _refresh_backup_menu)
app.after(400, _start_version_check)
app.after(450, _load_interval_setting)
app.after(460, _load_start_minimized_setting)
app.after(470, _load_start_with_system_setting)
app.after(500, lambda: threading.Thread(target=_run_app_update_check, daemon=True).start())
app.after(600, _setup_tray)
app.after(700, lambda: threading.Thread(target=_schedule_loop, daemon=True).start())

# Show welcome screen on first run
_cfg = load_config(get_base_path())
if _cfg.get("first_run", True):
    app.after(800, show_welcome_screen)

app.mainloop()