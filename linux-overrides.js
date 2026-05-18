// --- LINUX SPECIFIC OVERRIDES ---

// --- Hardware Video Acceleration (VA-API) ---
// Enables GPU-accelerated video decoding via libva.
// Requires: mesa-va-drivers (AMD/Intel) or nvidia-vaapi-driver (Nvidia)
// and ffmpeg built with VA-API support (standard on most distros).
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("media.ffmpeg.vaapi.enabled", true);

// --- GPU Compositor ---
// WebRender offloads page compositing to the GPU.
user_pref("gfx.webrender.all", true);

// DMA-BUF allows zero-copy GPU texture sharing between Firefox and the compositor.
// Beneficial on both X11 (with EGL) and Wayland.
user_pref("widget.dmabuf.force-enabled", true);

// --- Wayland / XDG Portal Integration ---
// These use the xdg-desktop-portal for OS-native dialogs.
// Value 2 = auto-detect: active on Wayland, gracefully skipped on X11.
user_pref("widget.use-xdg-desktop-portal.file-picker", 2);   // Native open/save dialogs
user_pref("widget.use-xdg-desktop-portal.mime-handler", 2);  // Native "open with" dialogs
user_pref("widget.use-xdg-desktop-portal.settings", 2);      // Respect system color scheme (light/dark)

// --- Desktop Notifications ---
// Routes Firefox alerts through libnotify so they appear in your
// DE's notification center (GNOME, KDE, etc.) instead of a custom popup.
user_pref("alerts.useSystemBackend", true);

// --- GTK Integration ---
// Use GTK overlay scrollbars to match the rest of the desktop UI.
user_pref("widget.gtk.overlay-scrollbars.enabled", true);

// --- Scrolling Physics ---
// Linux lacks OS-level scroll acceleration, so a mid-range multiplier
// gives a comfortable feel across most distros and input devices.
// Adjust upward (e.g. 250) if your scroll wheel feels sluggish.
user_pref("general.smoothScroll", true);
user_pref("apz.overscroll.enabled", false); // Linux default; enable if your WM/DE supports elastic overscroll
user_pref("mousewheel.default.delta_multiplier_y", 200);

// --- Font Rendering ---
// Allows fontconfig to use its full substitution depth, which improves
// fallback rendering for non-Latin scripts and rare Unicode ranges.
user_pref("gfx.font_rendering.fontconfig.max_generic_substitutions", 127);