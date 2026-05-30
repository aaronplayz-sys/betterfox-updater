// --- APPLE SILICON OVERRIDES ---
// Applied automatically on Macs with M-series chips (M1, M2, M3, and variants).
// These prefs supplement mac-overrides.js and are tuned for the unified memory
// architecture and Apple's GPU/media engine.

// Metal-backed WebRender compositor — fully supported on Apple Silicon
user_pref("gfx.webrender.compositor", true);
user_pref("gfx.webrender.compositor.support-low-power", true); // GPU low-power tier for background tabs
user_pref("gfx.core-animation.specialize-video", true);        // Specialized video layer via Core Animation

// Hardware video decode via VideoToolbox — covers H.264, HEVC, AV1 on M3+
user_pref("media.hardware-video-decoding.force-enabled", true);

// Unified memory — 512MB cache is comfortable for base M1/M2/M3
// Increase to 1048576 (1GB) if you have an M2 Pro/Max/Ultra or higher
user_pref("browser.cache.memory.capacity", 524288); // 512MB

// Limit content processes to reduce pressure on unified memory
user_pref("dom.ipc.processCount", 4);

// Battery efficiency via the GPU low-power mode
user_pref("power.low_power_mode.enabled", true);