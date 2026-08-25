# Changelog

All notable changes to Betterfox Updater are documented here. Dates and specifics for versions prior to v1.4.0 are approximate, as formal changelogs began partway through development.

## v1.9.0
### Added
- Settings window consolidating update interval, start minimized, and start with system controls.
- "Last checked" timestamp displayed in Settings, refreshed after every check.
- Quit App button in Settings — an in-GUI way to exit that doesn't depend on the system tray.
### Fixed
- Minimizing to tray on Linux now uses `iconify()` instead of `withdraw()`, keeping a taskbar entry as a fallback if the tray icon is unresponsive on some desktop environments (reported on XFCE).
- Added `[tray]` diagnostic logging (desktop environment, pystray backend) to help triage future tray-related bug reports.

## v1.8.2
### Fixed
- AppImage builds now write `config.json` and override files to the writable directory containing the `.AppImage` itself, instead of failing inside the read-only mount.
- Notifications under the AppImage build now fail gracefully instead of crashing when plyer's platform detection breaks inside the read-only mount. Scheduled checks continue to work; only the native popup is affected.

## v1.8.1
### Added
- Linux builds are now also packaged as a self-contained `.AppImage`, alongside the existing raw binary.

## v1.8.0
### Added
- Open profile folder button next to the profile dropdown.
- Pref diff view in the sync log — shows a summary of added/changed/removed prefs after every update instead of a generic success message.

## v1.7.0
### Added
- System tray support on Windows and Linux — closing the window minimizes to tray instead of quitting.
- Scheduled background update checks with a configurable interval (On launch only / Daily / Weekly / Every 4 weeks).
- Native OS notifications when a new Betterfox version is found.
- Start with System — registers the app to launch at login (Windows registry, Linux XDG autostart, macOS LaunchAgent).
- Start minimized to tray option.
- Linux taskbar icon via a `.desktop` entry and WM_CLASS matching.

## v1.6.0
### Added
- First-run welcome screen explaining what Betterfox and the updater do.
- Downloaded override files are now saved locally instead of being used once and discarded.
### Changed
- Consolidated the separate version-cache file into `config.json`, with inline `_comments` documenting each field.

## v1.5.0
### Added
- Version tracking — compares your installed Betterfox version against the latest release and shows the status in the main window.
- Self-update check — notifies you when a newer version of the updater itself is available.

## v1.4.0
### Added
- App icon across all three platforms, including proper Windows taskbar integration.
- Multi-profile support — select which Firefox profile to update from a dropdown instead of only targeting `default-release`.
### Fixed
- GitHub Actions workflow updated for the Node.js 24 runner deprecation.

## v1.0.0 – v1.3.0
Initial development. Core sync logic, modular override files (common / OS / hardware-specific), Firefox profile auto-detection across Windows/macOS/Linux (including Snap and Flatpak Firefox on Linux), timestamped backup and restore, stale pref migration on update, and the first GitHub Actions release workflow.
