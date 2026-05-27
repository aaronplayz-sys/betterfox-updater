import sys
import os
import queue
import threading
import tkinter.messagebox as tkmsg
import customtkinter as ctk
from update_betterfox import (
    is_firefox_running,
    PSUTIL_AVAILABLE,
    get_firefox_profile_path,
    list_backups,
    restore_backup,
    main as run_update_logic,
)


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
# Queue poller — drains log_queue into the textbox on the main thread
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
# Helpers
# ---------------------------------------------------------------------------

def _set_buttons(state: str):
    sync_button.configure(state=state)
    restore_button.configure(state=state)


def _friendly_backup_name(path: str) -> str:
    """Converts a full backup path to a readable label, e.g. '2025-06-14  14:30:05'."""
    name = os.path.basename(path)          # user.js.backup.20250614-143005
    stamp = name.split(".backup.")[-1]     # 20250614-143005
    try:
        dt = __import__("datetime").datetime.strptime(stamp, "%Y%m%d-%H%M%S")
        return dt.strftime("%Y-%m-%d  %H:%M:%S")
    except ValueError:
        return stamp


def _refresh_backup_menu():
    """Repopulates the restore dropdown with current backups."""
    profile_path = get_firefox_profile_path()
    backups = list_backups(profile_path) if profile_path else []

    backup_paths.clear()
    backup_paths.extend(backups)

    if backups:
        labels = [_friendly_backup_name(p) for p in backups]
        restore_menu.configure(values=labels)
        restore_menu.set(labels[0])
        restore_button.configure(state="normal")
        restore_menu.configure(state="normal")
    else:
        restore_menu.configure(values=["No backups found"])
        restore_menu.set("No backups found")
        restore_button.configure(state="disabled")
        restore_menu.configure(state="disabled")


# ---------------------------------------------------------------------------
# Firefox running banner
# ---------------------------------------------------------------------------

def _check_firefox_on_startup():
    """Shows a warning banner if Firefox is already open when the app launches."""
    if PSUTIL_AVAILABLE and is_firefox_running():
        firefox_banner.configure(
            text="⚠  Firefox is running — changes won't apply until it restarts",
            text_color="#FFA500",
        )
    elif not PSUTIL_AVAILABLE:
        firefox_banner.configure(
            text="psutil not installed — install it to enable Firefox detection",
            text_color="red",
        )


# ---------------------------------------------------------------------------
# Sync worker
# ---------------------------------------------------------------------------

def _run_update():
    old_stdout = sys.stdout
    sys.stdout = QueueStream(log_queue)
    try:
        run_update_logic()
        app.after(0, _on_sync_success)
    except Exception as e:
        log_queue.put(f"\n[ERROR]: {e}\n")
        app.after(0, _on_failure)
    finally:
        sys.stdout = old_stdout


def start_update():
    # If Firefox is running, the migration step (prefs.js cleanup) will be
    # skipped by the backend to avoid being overwritten. Warn the user with a
    # blocking dialog so they can close Firefox first if they want full cleanup.
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
                "Close Firefox and sync again for a complete update.\n\n"
                "Sync anyway?"
            ),
        )
        if not proceed:
            return
    else:
        firefox_banner.configure(text="", text_color="yellow")

    log_box.delete("0.0", "end")
    status_label.configure(text="Status: Updating...", text_color="yellow")
    _set_buttons("disabled")
    threading.Thread(target=_run_update, daemon=True).start()


def _on_sync_success():
    status_label.configure(text="SUCCESS: PLEASE RESTART FIREFOX", text_color="#50C878")
    log_queue.put("\n" + "=" * 30 + "\n")
    log_queue.put("Restart Firefox to apply changes.\n")
    log_queue.put("=" * 30 + "\n")
    _set_buttons("normal")
    _refresh_backup_menu()


# ---------------------------------------------------------------------------
# Restore worker
# ---------------------------------------------------------------------------

def _run_restore(backup_path: str):
    old_stdout = sys.stdout
    sys.stdout = QueueStream(log_queue)
    try:
        profile_path = get_firefox_profile_path()
        if not profile_path:
            log_queue.put("[error] Could not locate Firefox profile.\n")
            app.after(0, _on_failure)
            return
        success = restore_backup(backup_path, profile_path)
        if success:
            app.after(0, _on_restore_success)
        else:
            app.after(0, _on_failure)
    except Exception as e:
        log_queue.put(f"\n[ERROR]: {e}\n")
        app.after(0, _on_failure)
    finally:
        sys.stdout = old_stdout


def start_restore():
    selected_label = restore_menu.get()
    if not backup_paths or selected_label in ("No backups found", ""):
        return

    # Match the selected label back to its path
    labels = [_friendly_backup_name(p) for p in backup_paths]
    try:
        idx = labels.index(selected_label)
        backup_path = backup_paths[idx]
    except ValueError:
        return

    log_box.delete("0.0", "end")
    status_label.configure(text="Status: Restoring...", text_color="yellow")
    _set_buttons("disabled")
    threading.Thread(target=_run_restore, args=(backup_path,), daemon=True).start()


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
# GUI layout
# ---------------------------------------------------------------------------

app = ctk.CTk()
app.geometry("500x560")
app.title("Betterfox Updater")

# Title
ctk.CTkLabel(app, text="Betterfox Updater", font=("Arial", 20)).pack(pady=(14, 4))

# Firefox running banner (hidden by default)
firefox_banner = ctk.CTkLabel(app, text="", font=("Arial", 11))
firefox_banner.pack(pady=(0, 4))

# Status
status_label = ctk.CTkLabel(app, text="Status: Ready", text_color="white", font=("Arial", 12))
status_label.pack(pady=(0, 8))

# Sync button
sync_button = ctk.CTkButton(app, text="Update Now", command=start_update, width=200)
sync_button.pack(pady=4)

# Divider label
ctk.CTkLabel(app, text="── Restore a backup ──", text_color="white", font=("Arial", 11)).pack(pady=(14, 4))

# Backup picker + restore button side by side
restore_frame = ctk.CTkFrame(app, fg_color="transparent")
restore_frame.pack(pady=4)

backup_paths: list[str] = []  # parallel list to the dropdown labels

restore_menu = ctk.CTkOptionMenu(restore_frame, values=["No backups found"], width=260)
restore_menu.pack(side="left", padx=(0, 8))

restore_button = ctk.CTkButton(
    restore_frame, text="Restore", command=start_restore, width=100, state="disabled"
)
restore_button.pack(side="left")

# Log box
log_box = ctk.CTkTextbox(app, width=440, height=200)
log_box.pack(pady=16, padx=20)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

app.after(100, _poll_queue)
app.after(150, _check_firefox_on_startup)
app.after(200, _refresh_backup_menu)
app.mainloop()