import os
import platform
import configparser
import requests
import shutil
import sys
import glob
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

BETTERFOX_URL     = "https://raw.githubusercontent.com/yokoffing/Betterfox/main/user.js"
OVERRIDE_BASE_URL = "https://raw.githubusercontent.com/aaronplayz-sys/betterfox-updater/main/"
MAX_BACKUPS       = 5  # How many timestamped backups to keep per profile


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_base_path() -> str:
    """Finds the location of the .exe or the script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_firefox_profile_path() -> str | None:
    """Finds the 'default-release' profile path based on the OS."""
    system = platform.system()
    if system == "Windows":
        base_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox")
    elif system == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support/Firefox")
    else:
        base_path = os.path.expanduser("~/.mozilla/firefox")

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
        print(f"  [repo]   {filename} downloaded successfully.")
        return response.text

    print(f"  [error]  {filename} not found in repo (HTTP {response.status_code}), skipping.")
    return None


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------

def main():
    base_dir = get_base_path()

    # Firefox running check
    if is_firefox_running():
        print("[warn] Firefox is currently running.")
        print("       Changes will apply, but won't take effect until Firefox restarts.\n")
    elif not PSUTIL_AVAILABLE:
        print("[warn] psutil not installed — cannot check if Firefox is running.")
        print("       Run: pip install psutil\n")

    # Profile detection
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
    print("Download complete.\n")

    # Append overrides
    system = platform.system()
    os_override_map = {
        "Windows": "windows-overrides.js",
        "Darwin":  "mac-overrides.js",
        "Linux":   "linux-overrides.js",
    }
    os_filename = os_override_map.get(system)

    if not os_filename:
        print(f"  [warn]  Unrecognized OS '{system}', no OS-specific overrides available.")

    print("Loading overrides:")
    for filename in filter(None, ["common-overrides.js", os_filename]):
        content = fetch_override(filename, base_dir)
        if content:
            user_js_content += "\n\n" + content
    print()

    # Backup then write
    target_file = os.path.join(profile_path, "user.js")
    create_backup(target_file)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(user_js_content)

    print("\nSuccessfully updated user.js! Restart Firefox to apply changes.")


if __name__ == "__main__":
    main()