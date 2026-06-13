# Contributing to Betterfox Updater

Thanks for your interest. Contributions of all kinds are welcome — you don't need to write Python to be useful here.

## Before You Start

Open an issue before submitting a PR. This keeps effort from going to waste if something is already in progress, out of scope, or being approached differently. For small typo fixes or comment corrections, a PR without an issue is fine.

---

## Ways to Contribute

### Override Files (no Python required)

The most accessible way to contribute. Override files are plain JavaScript (`user_pref()` calls) that the updater merges into Betterfox's `user.js` automatically.

**What's needed:**
- Improved settings for existing hardware (better Nvidia/AMD/Intel tuning, Apple Silicon variants)
- New GPU families — new Intel Arc generations, AMD RDNA3+, Nvidia RTX 50 series
- Linux distro-specific tweaks (e.g. KDE vs GNOME scrolling behaviour, specific VA-API driver quirks)

**How to write one:**

Every override file follows the same format. Use comments to explain *why* a pref is set, not just what it does — future contributors need context:

```javascript
// --- YOUR HARDWARE OVERRIDES ---
// Brief description of what hardware this targets and any requirements.

// WebRender GPU compositor — offloads compositing to GPU
user_pref("gfx.webrender.all", true);

// Disable if you see rendering artifacts on older driver versions
user_pref("gfx.webrender.compositor", true);
```

Each pref should have at least a short comment. Prefs without any explanation won't be merged.

**Naming convention:**

| Scope | Pattern | Example |
|---|---|---|
| GPU vendor (cross-platform) | `{vendor}-overrides.js` | `nvidia-overrides.js` |
| OS-specific | `{os}-overrides.js` | `linux-overrides.js` |
| Hardware + OS | `{os}-{hardware}-overrides.js` | `linux-amd-overrides.js` |
| Apple chip | `apple-{chip}-overrides.js` | `apple-silicon-overrides.js` |

---

### Bug Reports and Hardware Testing

Bug reports are most useful when they include:

- Your OS, Firefox version, and install method (standard, Snap, Flatpak, etc.)
- Your GPU and driver version
- The full log output from the app
- What you expected to happen vs what actually happened

If the updater fails to detect your Firefox profile, include the output of:

**Windows:** `echo %APPDATA%\Mozilla\Firefox`

**macOS:** `ls ~/Library/Application\ Support/Firefox`

**Linux:** `ls ~/.mozilla/firefox && ls ~/snap/firefox/common/.mozilla/firefox 2>/dev/null && ls ~/.var/app/org.mozilla.firefox/.mozilla/firefox 2>/dev/null`

Hardware testing reports (confirming things work correctly on a specific GPU/distro/chip) are also genuinely useful — open an issue with the label `hardware-confirmed` and include your setup details.

---

### Code Contributions

The codebase has two files worth knowing:

- **`update_betterfox.py`** — all backend logic: profile detection, downloading, override merging, backup, migration, hardware detection
- **`app.py`** — the GUI, built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)

**Setup:**

```bash
git clone https://github.com/aaronplayz-sys/betterfox-updater.git
cd betterfox-updater
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install requests customtkinter psutil
```

**A few things to keep in mind:**

- Backend functions should print status messages using the `[tag]` format already in use (`[local]`, `[repo]`, `[warn]`, `[error]`) so GUI log output stays consistent
- New hardware detection should follow the existing pattern: a private `_detect_*` function per platform, called from `get_hardware_override_filename()`
- The GUI runs the backend on a worker thread and communicates via a `queue.Queue` — don't update any widget directly from background code
- Test against Firefox installed via Snap on Ubuntu if your change touches profile detection

---

## Pull Request Checklist

Before submitting:

- [ ] An issue exists and is linked in the PR description
- [ ] Override files include a comment on every pref
- [ ] Code changes follow the existing print tag format
- [ ] Tested locally on the target platform
- [ ] README updated if you've added new override files or changed behaviour
