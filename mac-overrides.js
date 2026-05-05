// --- MACOS SPECIFIC OVERRIDES ---
// Apple Silicon Video & UI Rendering
user_pref("gfx.core-animation.specialize-video", true);
user_pref("gfx.webrender.compositor", true);
user_pref("gfx.webrender.compositor.support-low-power", true);
user_pref("media.hardware-video-decoding.force-enabled", true);

// Power Efficiency
user_pref("browser.preferences.defaultPerformanceSettings.isEnabled", true);
user_pref("dom.ipc.processCount", 4); // Limit processes to save RAM/Battery
user_pref("power.low_power_mode.enabled", true);
user_pref("browser.cache.memory.capacity", 524288); 

// Native macOS Scrolling & UI
user_pref("apz.mac.enable_scroll_momentum", true);
user_pref("widget.macos.native-context-menus", true);
user_pref("apz.overscroll.enabled", true); // Enable macOS style overscroll
user_pref("general.smoothScroll", true);
user_pref("mousewheel.default.delta_multiplier_y", 100);
