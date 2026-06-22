import os
import platform
import configparser
import requests
import shutil
import subprocess
import sys
import glob
import json
import re
from datetime import datetime, timedelta

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False  # Non-Windows

BETTERFOX_URL     = "https://raw.githubusercontent.com/yokoffing/Betterfox/main/user.js"
OVERRIDE_BASE_URL   = "https://raw.githubusercontent.com/aaronplayz-sys/betterfox-updater/main/"
BETTERFOX_API       = "https://api.github.com/repos/yokoffing/Betterfox/releases/latest"
STARTUP_APP_NAME    = "BetterfoxUpdater"
STARTUP_REG_KEY     = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RELEASES_API    = "https://api.github.com/repos/aaronplayz-sys/betterfox-updater/releases/latest"
CONFIG_FILE         = "config.json"
MAX_BACKUPS       = 5  # How many timestamped backups to keep per profile


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_base_path() -> str:
    """Finds the location of the .exe or the script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_linux_firefox_base() -> str | None:
    """Finds the Firefox base directory on Linux, checking Snap and Flatpak paths too."""
    candidates = [
        os.path.expanduser("~/.mozilla/firefox"),                               # Traditional
        os.path.expanduser("~/snap/firefox/common/.mozilla/firefox"),           # Ubuntu Snap
        os.path.expanduser("~/.var/app/org.mozilla.firefox/.mozilla/firefox"),  # Flatpak
    ]
    for path in candidates:
        if os.path.exists(os.path.join(path, "profiles.ini")):
            print(f"  [profile] Found Firefox at: {path}")
            return path

    print("profiles.ini not found in any known location. Checked:")
    for path in candidates:
        print(f"  {path}")
    return None


def get_firefox_profile_path() -> str | None:
    """Finds the 'default-release' profile path based on the OS."""
    system = platform.system()
    if system == "Windows":
        base_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox")
    elif system == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Firefox")
    else:
        base_path = _get_linux_firefox_base()

    if not base_path:
        return None

    ini_path = os.path.join(base_path, "profiles.ini")
    if not os.path.exists(ini_path):
        print("profiles.ini not found. Is Firefox installed?")
        return None

    config = configparser.ConfigParser()
    config.read(ini_path, encoding="utf-8")

    profile_path = None

    # Primary: named 'default-release'
    for section in config.sections():
        if section.startswith("Profile"):
            if config.get(section, "Name", fallback="") == "default-release":
                path = config.get(section, "Path")
                is_relative = config.get(section, "IsRelative", fallback="1")
                profile_path = os.path.join(base_path, path) if is_relative == "1" else path
                break

    # Fallback: Default=1 flag
    if not profile_path:
        for section in config.sections():
            if section.startswith("Profile"):
                if config.get(section, "Default", fallback="0") == "1":
                    path = config.get(section, "Path")
                    is_relative = config.get(section, "IsRelative", fallback="1")
                    profile_path = os.path.join(base_path, path) if is_relative == "1" else path
                    break

    return profile_path


def get_all_profiles() -> list[dict]:
    """Returns all Firefox profiles as a list of {name, path, is_default} dicts.

    Sorted with the default profile first, then alphabetically by name.
    """
    system = platform.system()
    if system == "Windows":
        base_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox")
    elif system == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Firefox")
    else:
        base_path = _get_linux_firefox_base()

    if not base_path:
        return []

    ini_path = os.path.join(base_path, "profiles.ini")
    if not os.path.exists(ini_path):
        return []

    config = configparser.ConfigParser()
    config.read(ini_path, encoding="utf-8")

    profiles = []
    for section in config.sections():
        if not section.startswith("Profile"):
            continue
        name = config.get(section, "Name", fallback="")
        path = config.get(section, "Path", fallback="")
        if not name or not path:
            continue
        is_relative  = config.get(section, "IsRelative", fallback="1")
        is_default   = (
            config.get(section, "Default", fallback="0") == "1"
            or name == "default-release"
        )
        full_path = os.path.join(base_path, path) if is_relative == "1" else path
        profiles.append({"name": name, "path": full_path, "is_default": is_default})

    # Default profile first, then alphabetical
    profiles.sort(key=lambda p: (not p["is_default"], p["name"]))
    return profiles


# ---------------------------------------------------------------------------
# Firefox process detection
# ---------------------------------------------------------------------------

def is_firefox_running() -> bool:
    """Returns True if a Firefox process is currently running."""
    if not PSUTIL_AVAILABLE:
        return False
    for proc in psutil.process_iter(["name"]):
        try:
            if "firefox" in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


# ---------------------------------------------------------------------------
# Backup management
# ---------------------------------------------------------------------------

def _backup_glob(target_file: str) -> list[str]:
    """Returns all timestamped backups for a given user.js, sorted oldest first."""
    return sorted(glob.glob(target_file + ".backup.*"))


def create_backup(target_file: str) -> str | None:
    """Creates a timestamped backup and prunes old ones beyond MAX_BACKUPS."""
    if not os.path.exists(target_file):
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{target_file}.backup.{timestamp}"
    shutil.copy2(target_file, backup_path)
    print(f"Backup created: {os.path.basename(backup_path)}")

    existing = _backup_glob(target_file)
    while len(existing) > MAX_BACKUPS:
        oldest = existing.pop(0)
        os.remove(oldest)
        print(f"Pruned old backup: {os.path.basename(oldest)}")

    return backup_path


def list_backups(profile_path: str) -> list[str]:
    """Returns timestamped backup paths for this profile's user.js, newest first."""
    target_file = os.path.join(profile_path, "user.js")
    return list(reversed(_backup_glob(target_file)))


def restore_backup(backup_path: str, profile_path: str) -> bool:
    """Overwrites user.js with the contents of backup_path. Returns True on success."""
    target_file = os.path.join(profile_path, "user.js")
    try:
        shutil.copy2(backup_path, target_file)
        print(f"Restored: {os.path.basename(backup_path)} → user.js")
        return True
    except OSError as e:
        print(f"[error] Restore failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

def _detect_windows_gpu() -> str | None:
    """Returns a hardware override filename based on the detected Windows GPU."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name'],
            capture_output=True, text=True, timeout=10
        )
        name = result.stdout.upper()
        if 'NVIDIA' in name:
            return 'nvidia-overrides.js'
        if 'AMD' in name or 'RADEON' in name:
            return 'amd-overrides.js'
        if 'INTEL' in name:
            return 'intel-gpu-overrides.js'
    except Exception as e:
        print(f"  [warn]  GPU detection failed: {e}")
    return None


def _detect_linux_gpu() -> str | None:
    """Returns a hardware override filename based on the detected Linux GPU."""
    try:
        result = subprocess.run(
            ['lspci'], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.upper().splitlines():
            if 'VGA' in line or '3D CONTROLLER' in line or 'DISPLAY' in line:
                if 'NVIDIA' in line:
                    return 'nvidia-overrides.js'
                if 'AMD' in line or 'RADEON' in line or 'ATI' in line:
                    return 'amd-overrides.js'
                if 'INTEL' in line:
                    return 'intel-gpu-overrides.js'
    except FileNotFoundError:
        print("  [warn]  lspci not found — install pciutils for GPU detection.")
    except Exception as e:
        print(f"  [warn]  GPU detection failed: {e}")
    return None


def get_hardware_override_filename() -> str | None:
    """Detects the current GPU/CPU and returns the appropriate override filename.

    macOS uses platform.machine() to distinguish Apple Silicon from Intel.
    Windows queries Win32_VideoController via PowerShell.
    Linux parses lspci output (requires pciutils).
    Returns None if detection fails or hardware is unrecognized.
    """
    system = platform.system()

    if system == 'Darwin':
        # arm64 = Apple Silicon (M1/M2/M3+), x86_64 = Intel Mac
        return 'apple-silicon-overrides.js' if platform.machine() == 'arm64' else 'apple-intel-overrides.js'

    if system == 'Windows':
        return _detect_windows_gpu()

    if system == 'Linux':
        return _detect_linux_gpu()

    return None


# ---------------------------------------------------------------------------
# Migration — stale pref cleanup
# ---------------------------------------------------------------------------

def parse_pref_names(user_js_content: str) -> set[str]:
    """Extracts all pref names from a user.js content string."""
    return set(re.findall(r'user_pref\("([^"]+)"', user_js_content))


def clean_stale_prefs(old_content: str, new_content: str, profile_path: str) -> None:
    """Removes from prefs.js any prefs that existed in the old user.js but not the new one.

    Firefox writes user.js values into prefs.js on startup but never removes them
    when prefs are dropped from user.js. This function performs that cleanup so
    removed prefs actually revert to Firefox defaults rather than lingering silently.
    """
    removed = parse_pref_names(old_content) - parse_pref_names(new_content)

    if not removed:
        print("Migration: no removed prefs to clean up.")
        return

    print(f"Migration: {len(removed)} pref(s) removed in this update.")

    prefs_js_path = os.path.join(profile_path, "prefs.js")
    if not os.path.exists(prefs_js_path):
        print("  [warn]  prefs.js not found, skipping cleanup.")
        return

    with open(prefs_js_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned_lines = []
    cleaned_count = 0
    for line in lines:
        match = re.match(r'\s*user_pref\("([^"]+)"', line)
        if match and match.group(1) in removed:
            print(f"  [removed] {match.group(1)}")
            cleaned_count += 1
        else:
            cleaned_lines.append(line)

    if cleaned_count > 0:
        # Guard: if Firefox is running it will overwrite prefs.js on next save,
        # undoing the cleanup entirely. Skip the write and tell the user explicitly.
        if is_firefox_running():
            print(f"  [warn]  {cleaned_count} stale pref(s) found but Firefox is running.")
            print("          Close Firefox and sync again to complete the migration.")
            return

        shutil.copy2(prefs_js_path, prefs_js_path + ".backup")
        with open(prefs_js_path, "w", encoding="utf-8") as f:
            f.writelines(cleaned_lines)
        print(f"  Cleaned {cleaned_count} stale pref(s) from prefs.js. (prefs.js.backup created)")
    else:
        print("  No stale prefs found in prefs.js.")


# ---------------------------------------------------------------------------
# Version tracking
# ---------------------------------------------------------------------------

def get_latest_version() -> str | None:
    """Returns the latest Betterfox release tag from the GitHub Releases API.

    Betterfox does not embed a version number in user.js itself, so the
    Releases API is the authoritative source. Returns a clean string like
    "133.0" (leading "v" stripped) or None on failure.
    """
    try:
        response = requests.get(BETTERFOX_API, timeout=10)
        if response.status_code == 200:
            tag = response.json().get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except requests.exceptions.RequestException:
        pass
    return None


def get_installed_version(base_dir: str) -> str | None:
    """Reads the installed Betterfox version from config.json."""
    return load_config(base_dir).get("installed_betterfox_version")


def save_installed_version(base_dir: str, version: str) -> None:
    """Saves the installed Betterfox version into config.json after a successful sync."""
    config = load_config(base_dir)
    config["installed_betterfox_version"] = version
    save_config(base_dir, config)


def get_latest_app_version() -> str | None:
    """Returns the latest Betterfox Updater release tag from the GitHub Releases API."""
    try:
        response = requests.get(APP_RELEASES_API, timeout=10)
        if response.status_code == 200:
            tag = response.json().get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except requests.exceptions.RequestException:
        pass
    return None


# ---------------------------------------------------------------------------
# Override loading
# ---------------------------------------------------------------------------

def fetch_override(filename: str, base_dir: str) -> str | None:
    """Returns override file content, downloading from the repo if not found locally."""
    local_path = os.path.join(base_dir, filename)

    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            print(f"  [local]  {filename}")
            return f.read()

    url = OVERRIDE_BASE_URL + filename
    print(f"  [local]  {filename} not found — downloading from repo...")
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        print(f"  [error]  Timed out downloading {filename}, skipping.")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  [error]  Connection failed downloading {filename}, skipping.")
        return None

    if response.status_code == 200:
        file_content = response.text

        # Save to base_dir so the user can find and customise it
        try:
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(file_content)
            print(f"  [repo]   {filename} downloaded and saved to {base_dir}")
        except OSError as e:
            print(f"  [warn]   {filename} downloaded but could not be saved: {e}")

        return file_content

    print(f"  [error]  {filename} not found in repo (HTTP {response.status_code}), skipping.")
    return None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_DEFAULTS = {
    "_comments": {
        "first_run": (
            "Controls whether the welcome screen is shown on launch. "
            "Set to false after first use."
        ),
        "installed_betterfox_version": (
            "The Betterfox release version last synced by this app. "
            "Used for the version status display."
        ),
        "check_interval": (
            "How often to check for Betterfox updates while running in the system tray. "
            "Options: on_launch, daily, weekly, every_4_weeks. Default: weekly."
        ),
        "last_checked": (
            "ISO 8601 timestamp of the last background update check. "
            "Managed automatically — do not edit manually."
        ),
        "start_minimized": (
            "If true, the app launches directly to the system tray "
            "without showing the main window."
        ),
    },
    "first_run": True,
    "installed_betterfox_version": None,
    "check_interval": "weekly",
    "last_checked": None,
    "start_minimized": False,
}


def load_config(base_dir: str) -> dict:
    """Reads config.json and merges with defaults for any missing keys."""
    config_path = os.path.join(base_dir, CONFIG_FILE)
    config = dict(_CONFIG_DEFAULTS)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except (OSError, json.JSONDecodeError):
            pass
    return config


def save_config(base_dir: str, config: dict) -> None:
    """Writes the config dict to config.json."""
    config_path = os.path.join(base_dir, CONFIG_FILE)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"  [warn]  Could not save config: {e}")


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

_INTERVAL_DELTAS = {
    "daily":        timedelta(days=1),
    "weekly":       timedelta(weeks=1),
    "every_4_weeks": timedelta(weeks=4),
}


def is_check_due(base_dir: str) -> bool:
    """Returns True if a background update check should run now.

    Always returns False for "on_launch" since that interval only checks
    at startup. For all other intervals, compares last_checked against
    the configured delta.
    """
    config       = load_config(base_dir)
    interval     = config.get("check_interval", "weekly")
    last_checked = config.get("last_checked")

    if interval == "on_launch":
        return False

    if not last_checked:
        return True  # Never checked before

    try:
        last_dt = datetime.fromisoformat(last_checked)
    except ValueError:
        return True  # Malformed timestamp — check now

    delta = _INTERVAL_DELTAS.get(interval, timedelta(weeks=1))
    return datetime.now() - last_dt >= delta


def save_last_checked(base_dir: str) -> None:
    """Writes the current timestamp to config as the last check time."""
    config = load_config(base_dir)
    config["last_checked"] = datetime.now().isoformat()
    save_config(base_dir, config)


# ---------------------------------------------------------------------------
# Startup registration (Windows + Linux)
# ---------------------------------------------------------------------------

_SYSTEM = platform.system()
START_WITH_SYSTEM_SUPPORTED = _SYSTEM in ("Windows", "Linux")


def _get_startup_command() -> str:
    """Returns the executable command for autostart registration."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    return f'"{sys.executable}" "{app_path}"'


# --- Windows ---

def _set_start_with_system_windows(enabled: bool) -> bool:
    """Writes or removes the HKCU Run registry entry. No admin required."""
    if not WINREG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        if enabled:
            winreg.SetValueEx(key, STARTUP_APP_NAME, 0, winreg.REG_SZ, _get_startup_command())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"  [warn]  Could not update startup registry: {e}")
        return False


def _get_start_with_system_windows() -> bool:
    if not WINREG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, STARTUP_APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


# --- Linux (XDG autostart) ---

_AUTOSTART_DIR  = os.path.expanduser("~/.config/autostart")
_AUTOSTART_FILE = os.path.join(_AUTOSTART_DIR, "betterfox-updater.desktop")

_DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name=Betterfox Updater
Exec={exec_cmd}
Comment=Automatically update Betterfox user.js for Firefox
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""


def _set_start_with_system_linux(enabled: bool) -> bool:
    """Writes or removes the XDG autostart .desktop file."""
    if enabled:
        try:
            os.makedirs(_AUTOSTART_DIR, exist_ok=True)
            with open(_AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(_DESKTOP_TEMPLATE.format(exec_cmd=_get_startup_command()))
            return True
        except OSError as e:
            print(f"  [warn]  Could not create autostart file: {e}")
            return False
    else:
        try:
            if os.path.exists(_AUTOSTART_FILE):
                os.remove(_AUTOSTART_FILE)
            return True
        except OSError as e:
            print(f"  [warn]  Could not remove autostart file: {e}")
            return False


def _get_start_with_system_linux() -> bool:
    return os.path.exists(_AUTOSTART_FILE)


# --- Platform-agnostic wrappers (used by the GUI) ---

def set_start_with_system(enabled: bool) -> bool:
    """Registers or unregisters the app for system startup on the current platform."""
    if _SYSTEM == "Windows":
        return _set_start_with_system_windows(enabled)
    if _SYSTEM == "Linux":
        return _set_start_with_system_linux(enabled)
    return False


def get_start_with_system() -> bool:
    """Returns True if the app is currently registered for system startup."""
    if _SYSTEM == "Windows":
        return _get_start_with_system_windows()
    if _SYSTEM == "Linux":
        return _get_start_with_system_linux()
    return False


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------

def main(profile_path: str | None = None):
    base_dir = get_base_path()

    # Firefox running check
    if is_firefox_running():
        print("[warn] Firefox is currently running.")
        print("       Changes will apply, but won't take effect until Firefox restarts.\n")
    elif not PSUTIL_AVAILABLE:
        print("[warn] psutil not installed — cannot check if Firefox is running.")
        print("       Run: pip install psutil\n")

    # Profile detection — use provided path or auto-detect
    if not profile_path:
        profile_path = get_firefox_profile_path()
    if not profile_path:
        print("Could not locate default Firefox profile.")
        return
    print(f"Target profile: {profile_path}\n")

    # Download Betterfox
    print("Downloading latest Betterfox user.js...")
    try:
        response = requests.get(BETTERFOX_URL, timeout=15)
    except requests.exceptions.Timeout:
        print("Download timed out. Check your internet connection and try again.")
        return
    except requests.exceptions.ConnectionError:
        print("Connection failed. Check your internet connection and try again.")
        return

    if response.status_code != 200:
        print(f"Download failed (HTTP {response.status_code}).")
        return

    user_js_content = response.text

    # Version comparison
    latest_version    = get_latest_version()
    installed_version = get_installed_version(base_dir)

    if latest_version and installed_version:
        if latest_version == installed_version:
            print(f"Version: up to date (v{latest_version})")
        else:
            print(f"Version: v{installed_version} → v{latest_version}")
    elif latest_version:
        print(f"Version: installing v{latest_version} for the first time")
    print()

    # Append overrides: common → OS-specific → hardware-specific
    system = platform.system()
    os_override_map = {
        "Windows": "windows-overrides.js",
        "Darwin":  "mac-overrides.js",
        "Linux":   "linux-overrides.js",
    }
    os_filename = os_override_map.get(system)

    if not os_filename:
        print(f"  [warn]  Unrecognized OS '{system}', no OS-specific overrides available.")

    print("Detecting hardware...")
    hw_filename = get_hardware_override_filename()
    if hw_filename:
        print(f"  [hw]     {hw_filename}")
    else:
        print("  [warn]  Could not identify hardware, skipping hardware overrides.")
    print()

    print("Loading overrides:")
    for filename in filter(None, ["common-overrides.js", os_filename, hw_filename]):
        content = fetch_override(filename, base_dir)
        if content:
            user_js_content += "\n\n" + content
    print()

    # Read existing user.js for migration diff before overwriting
    target_file = os.path.join(profile_path, "user.js")
    old_user_js_content = ""
    if os.path.exists(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            old_user_js_content = f.read()

    # Clean up prefs removed in this update
    print("Running migration...")
    clean_stale_prefs(old_user_js_content, user_js_content, profile_path)
    print()

    # Backup then write
    create_backup(target_file)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(user_js_content)

    if latest_version:
        save_installed_version(base_dir, latest_version)
        print(f"\nSuccessfully updated to v{latest_version}! Restart Firefox to apply changes.")
    else:
        print("\nSuccessfully updated user.js! Restart Firefox to apply changes.")


if __name__ == "__main__":
    main()