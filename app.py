import sys
import os
import queue
import threading
import tkinter.messagebox as tkmsg
import customtkinter as ctk
from update_betterfox import (
    is_firefox_running,
    PSUTIL_AVAILABLE,
    get_all_profiles,
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

# Parallel lists: labels shown in the dropdown <-> full profile dicts
profile_list:  list[dict] = []
backup_paths:  list[str]  = []


def _load_profiles():
    """Populates profile_list and the profile dropdown on startup."""
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
    """Returns the profile dict for the currently selected dropdown entry."""
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
    """Called when the user picks a different profile — refreshes the backup list."""
    _refresh_backup_menu()


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
            text_color="gray",
        )


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
        firefox_banner.configure(text="", text_color="gray")

    log_box.delete("0.0", "end")
    status_label.configure(text="Status: Updating...", text_color="gray")
    _set_buttons("disabled")
    threading.Thread(target=_run_update, args=(profile["path"],), daemon=True).start()


def _on_update_success():
    status_label.configure(text="SUCCESS: PLEASE RESTART FIREFOX", text_color="#50C878")
    log_queue.put("\n" + "=" * 30 + "\n")
    log_queue.put("Restart Firefox to apply changes.\n")
    log_queue.put("=" * 30 + "\n")
    _set_buttons("normal")
    _refresh_backup_menu()


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
    status_label.configure(text="Status: Restoring...", text_color="gray")
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
# GUI layout
# ---------------------------------------------------------------------------

app = ctk.CTk()
app.geometry("500x600")
app.title("Betterfox Updater")

# Title
ctk.CTkLabel(app, text="Betterfox Updater", font=("Arial", 20)).pack(pady=(14, 4))

# Firefox running banner
firefox_banner = ctk.CTkLabel(app, text="", font=("Arial", 11))
firefox_banner.pack(pady=(0, 4))

# Profile picker
profile_frame = ctk.CTkFrame(app, fg_color="transparent")
profile_frame.pack(pady=(4, 2))

ctk.CTkLabel(profile_frame, text="Profile:", font=("Arial", 12)).pack(side="left", padx=(0, 8))
profile_menu = ctk.CTkOptionMenu(
    profile_frame,
    values=["Loading..."],
    command=_on_profile_change,
    width=300,
)
profile_menu.pack(side="left")

# Status
status_label = ctk.CTkLabel(app, text="Status: Ready", text_color="gray")
status_label.pack(pady=(8, 4))

# Update button
update_button = ctk.CTkButton(app, text="Update Now", command=start_update, width=200)
update_button.pack(pady=4)

# Restore section
ctk.CTkLabel(app, text="── Restore a backup ──", text_color="gray", font=("Arial", 11)).pack(pady=(14, 4))

restore_frame = ctk.CTkFrame(app, fg_color="transparent")
restore_frame.pack(pady=4)

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
app.after(200, _load_profiles)
app.after(300, _refresh_backup_menu)
app.mainloop()
