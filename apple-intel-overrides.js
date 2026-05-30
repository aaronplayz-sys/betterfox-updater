// --- APPLE INTEL OVERRIDES ---
// Applied automatically on Intel-based Macs (pre-2020 models). Not been tested on Apple Silicon, but should be safe as WebRender is enabled by default there.

// Hardware video decode via VideoToolbox — covers H.264 and HEVC on supported hardware
user_pref("media.hardware-video-decoding.force-enabled", true);

// WebRender is stable on most Intel Mac GPUs
user_pref("gfx.webrender.all", true);

// Disable low power mode — efficiency cores aren't available on Intel Macs,
// making this setting less effective than it is on Apple Silicon
user_pref("power.low_power_mode.enabled", false);

// Conservative cache for Intel Mac discrete/integrated GPU
user_pref("browser.cache.memory.capacity", 262144); // 256MB

// Native macOS momentum scrolling (same as mac-overrides.js, kept here for clarity)
user_pref("apz.mac.enable_scroll_momentum", true);
user_pref("apz.overscroll.enabled", true);