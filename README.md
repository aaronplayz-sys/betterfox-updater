# Betterfox Updater
A cross-platform, Python-based utility designed to automate the installation of [Betterfox](https://github.com/yokoffing/Betterfox) while preserving custom user overrides.

This project was inspired by [Betterfox Issue #167](https://github.com/yokoffing/Betterfox/issues/167) and aims to solve the "stalled updater" problem by providing a modular, hardware-aware sync tool.

<p align="center">
    <img src="images/BetterfoxUpdater.png" alt="Betterfox Updater"/>
    <img src="images/BetterfoxUpdaterSucess.png" alt="Betterfox Updater Sucess"/>
</p>

## ✨ Key Features

- **Intelligent Profile Detection**: Automatically locates the default-release Firefox profile across Windows, macOS, and Linux.

- **Modular Overrides**: Merges the latest Betterfox user.js with your personal tweaks (common-overrides.js, windows-overrides.js, or mac-overrides.js).

- **Hardware Aware**: Tailors performance settings for specific hardware, such as Nvidia RTX GPUs or Apple Silicon (M3).

- **Safety First**: Automatically creates a .backup of your existing configuration before making changes.

- **Modern GUI**: Includes a simple interface with a live progress log.

## To-do:
- Release Windows executable
- Build MacOS executable
- Build a executable to Linux systems

## How to Use

1. Download the latest release for your system.
2. Place the override files (`common-overrides.js`, `mac-overrides.js`, and `windows-overrides.js`) in the same folder as the updater. Feel free to make modifications to these file to suit your needs.
3. Run the application and click "Sync Now".
4. Restart Firefox to apply changes.

## 🛠 Developer Setup

If you want to run the script manually or contribute to the project:

1. Clone & Setup Environment
```
git clone https://github.com/aaronplayz-sys/betterfox-updater.git
```
```
cd betterfox-updater
```
```
python -m venv .venv
```
2. Activate Virtual Environment and Install Dependencies

Windows: ```.venv\Scripts\activate```

Mac/Linux: ```source .venv/bin/activate```

Dependencies: ```pip install requests customtkinter```

3. Run Application

CLI Version: ```python update_betterfox.py```

GUI Version: ```python gui_test.py```

## Building the Executable

```
pip install pyinstaller
```
```
pyinstaller --noconsole --onefile --collect-all customtkinter gui_test.py
```