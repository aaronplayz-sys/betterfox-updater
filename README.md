# betterfox-updater
A python based updater to automatically update and keep my user overides, aimed to be cross-platform.

This was inspired by an issue opened in the betterfox repository. https://github.com/yokoffing/Betterfox/issues/167.

While this my personal use case, I plan to make something that *could* get intergrated to the Betterfox repositroy.

## How this works

The script determines the the type of operating system (Windows, MacOS, and Linux) and locate the "default-release" profile. If such a profile dose not exist, it will search for a profile with the Default=1 flag listed in a profiles.ini file. After determining the system type and profile, the script will download the user.js file from the Betterfox repository and apply system currated overrides and common overrides specified in common-overrides.js, mac-overrides.js, and windows-overrides.js.


## Install

Download this repository

Go to the folder and create a virtual enviorment

```
python -m venv .venv
```

Activate the virtual environment

```
source .venv/bin/activate
```

Install requests

```
pip install requests
```

## Run the updater

```
python update_betterfox.py
```
