# Betterfox Updater
A cross-platform, Python-based utility designed to automate the installation of [Betterfox](https://github.com/yokoffing/Betterfox) while preserving custom user overrides.

This project was inspired by [Betterfox Issue #167](https://github.com/yokoffing/Betterfox/issues/167) and aims to solve the "stalled updater" problem by providing a modular, hardware-aware sync tool.

Images below is a preview of what the app looks like on Windows 11, looks are simular with MacOS and Linux.

<p align="center">
    <img src="images/BetterfoxUpdater.png" alt="Betterfox Updater"/>
    <img src="images/BetterfoxUpdaterSucess.png" alt="Betterfox Updater Success"/>
</p>

## ⚠️ Antivirus Notice

The macOS executable may be flagged by Microsoft Defender as a false positive. This is a known issue with unsigned Python executables built with PyInstaller — the binary is not malicious. The Windows executable has been patched in attempt to avoid this. If you are concerned, you can verify the build yourself by running from source via the developer setup below, or inspect the full source code in this repo.

## ✨ Key Features

- **Intelligent Profile Detection**: Automatically locates the default-release Firefox profile across Windows, MacOS, and Linux.

- **Modular Overrides**: Merges the latest Betterfox user.js with your personal tweaks (`common-overrides.js`, `windows-overrides.js`, `mac-overrides.js`, or `linux-overrides.js`). Missing override files are automatically downloaded from the repo as a fallback.

- **Hardware Aware**: Automatically detects your GPU or CPU and applies the right override file. Covers NVIDIA, AMD, and Intel GPUs on Windows and Linux; Apple Silicon vs Intel on MacOS.

- **Firefox Running Detection**: Warns you if Firefox is open before syncing, so you know to restart it after the update applies.

- **Backup & Restore**: Automatically creates a timestamped backup before every sync and keeps the last 5. A built-in restore menu lets you roll back to any previous configuration without touching the file system.

- **Modern GUI**: Includes a simple interface with a live progress log.

- **Scheduled Checks**: Automatically check upstream user.js changes with a specified interval.

- **Start on system boot**: Have the app run automatically in the background when you start your system.

## To-do
- [x] Add an app icon
- [x] Hardware detection to match override files to detected GPU/CPU
- [x] Notify user that user.js has been updated and suggest to update
- [x] Notify user that the app has been updated and suggest to update.
- [x] Tray icon / minimize to tray (MacOS needs a diffrent solution)
- [x] Scheduled auto-checks
- [x] Start with System
- [x] First-run welcome screen
- [x] Open profile folder button
- [x] Diff view in the log
- [ ] Replace Linux binary with an AppImage
- [ ] MacOS tray (proper native implementation)
- [ ] Localization, would need help

## How to Use

1. Download the latest release for your system from the [Releases](../../releases) page.
2. Place any override files you want to customize in the same folder as the updater. If a file isn't found locally, it will be downloaded automatically.

   | File | Applied when |
   |---|---|
   | `common-overrides.js` | Always |
   | `windows-overrides.js` / `mac-overrides.js` / `linux-overrides.js` | Matches your OS |
   | `nvidia-overrides.js` / `amd-overrides.js` / `intel-gpu-overrides.js` | Matches your GPU (Windows / Linux) |
   | `apple-silicon-overrides.js` / `apple-intel-overrides.js` | Matches your Mac chip (macOS) |
3. Run the application and click **Sync Now**.
4. Restart Firefox to apply changes.

To roll back a sync, select a backup from the **Restore a backup** dropdown and click **Restore**, then restart Firefox.

## 🛠 Developer Setup

If you want to run the script manually or contribute to the project:

**1. Clone & set up environment**
```
git clone https://github.com/aaronplayz-sys/betterfox-updater.git
cd betterfox-updater
python -m venv .venv
```

**2. Activate virtual environment**

Windows: `.venv\Scripts\activate`

macOS / Linux: `source .venv/bin/activate`

**3. Install dependencies**
```
pip install -r requirements.txt
```

> `psutil` is optional but recommended — it enables Firefox running detection. The app works without it.

**4. Run the application**

CLI: `python update_betterfox.py`

GUI: `python app.py`

## 🔨 Building the Executable

Releases are built automatically via GitHub Actions when a version tag is pushed. To build manually:

```
pip install pyinstaller
```
```
pyinstaller --noconsole --onefile --collect-all customtkinter --hidden-import psutil --icon assets/favicon.ico --add-data "assets/favicon.ico;." --name BetterfoxUpdater app.py
```

> **Linux only**: tkinter and tray dependencies must be installed separately before building.
> ```
> sudo apt install python3-tk python3-gi gir1.2-ayatanaappindicator3-0.1
> ```

## 🚀 Releasing a New Version

Push a version tag and GitHub Actions will build all three platform executables and attach them to a GitHub Release automatically:

```
git tag v1.0.0
git push --tags
```

The workflow builds on `windows-latest`, `macos-latest`, and `ubuntu-latest` in parallel. The release will appear under the [Releases](../../releases) tab once all three jobs complete.
