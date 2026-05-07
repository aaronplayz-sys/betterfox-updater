import os
import platform
import configparser
import requests
import shutil
import sys

BETTERFOX_URL = "https://raw.githubusercontent.com/yokoffing/Betterfox/main/user.js"

def get_base_path():
    """Finds the location of the .exe or the script."""
    if getattr(sys, 'frozen', False):
        # If the app is a compiled .exe, look in the folder where the .exe lives
        return os.path.dirname(sys.executable)
    else:
        # If running as a script, look in the current folder
        return os.path.dirname(os.path.abspath(__file__))

def get_firefox_profile_path():
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
    config.read(ini_path)
    
    profile_path = None
    
    # 1. Primary Strategy: Look for the section named 'default-release'
    for section in config.sections():
        if section.startswith("Profile"):
            name = config.get(section, "Name", fallback="")
            if name == "default-release":
                path = config.get(section, "Path")
                is_relative = config.get(section, "IsRelative", fallback="1")
                
                if is_relative == "1":
                    profile_path = os.path.join(base_path, path)
                else:
                    profile_path = path
                break

    # 2. Fallback: If 'default-release' isn't found, look for the 'Default=1' flag
    if not profile_path:
        for section in config.sections():
            if section.startswith("Profile"):
                if config.get(section, "Default", fallback="0") == "1":
                    path = config.get(section, "Path")
                    is_relative = config.get(section, "IsRelative", fallback="1")
                    if is_relative == "1":
                        profile_path = os.path.join(base_path, path)
                    else:
                        profile_path = path
                    break

    return profile_path

def main():

    base_dir = get_base_path()

    profile_path = get_firefox_profile_path()
    if not profile_path:
        print("Could not locate default Firefox profile.")
        return

    print(f"Target Profile: {profile_path}")
    
    # 1. Download latest Betterfox user.js
    print("Downloading latest Betterfox user.js...")
    response = requests.get(BETTERFOX_URL)
    if response.status_code != 200:
        print("Failed to download Betterfox user.js")
        return
        
    user_js_content = response.text

    # 2. Append Common Overrides
    common_path = os.path.join(base_dir, "common-overrides.js")
    if os.path.exists(common_path):
        with open(common_path, "r") as f:
            user_js_content += "\n\n" + f.read()
            print("Appended common-overrides.js")

    # 3. Append OS-Specific Overrides
    system = platform.system()
    target_filename = "windows-overrides.js" if system == "Windows" else "mac-overrides.js"
    target_path = os.path.join(base_dir, target_filename)
    
    if os.path.exists(target_path):
        with open(target_path, "r") as f:
            user_js_content += "\n\n" + f.read()
            print(f"Appended {target_filename}")

    # 4. Write to Firefox profile
    target_file = os.path.join(profile_path, "user.js")
    
    # Optional: Backup existing user.js
    if os.path.exists(target_file):
        shutil.copy(target_file, target_file + ".backup")
        print("Backed up existing user.js")

    with open(target_file, "w") as f:
        f.write(user_js_content)

    print("Successfully updated user.js! Restart Firefox to apply changes.")

if __name__ == "__main__":
    main()