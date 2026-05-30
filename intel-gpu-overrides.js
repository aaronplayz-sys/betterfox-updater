// --- INTEL GPU OVERRIDES ---
// Detected and applied automatically on Windows and Linux systems with an Intel GPU.
// Covers both integrated graphics (UHD, Iris Xe) and discrete Arc GPUs.
// Arc GPUs (Alchemist+) support full acceleration; older integrated GPUs use
// more conservative compositor settings to avoid rendering artifacts.
// Note: Not tested, feedback welcome.

// WebRender is safe on Iris Xe and Arc; generally fine on UHD 600+ series
user_pref("gfx.webrender.all", true);

// Hardware video decode via Intel Quick Sync (Windows) or VA-API with intel-media-driver (Linux)
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("media.gpu-process-decoder", true);

// GPU-accelerated Canvas2D
user_pref("gfx.canvas.accelerated", true);

// Disable the WebRender compositor — some Intel integrated GPUs have driver issues with it.
// Set to true if you have a discrete Arc GPU and want maximum performance.
user_pref("gfx.webrender.compositor", false);

// Smaller memory cache — Intel iGPUs share system RAM, so we stay conservative
user_pref("browser.cache.memory.capacity", 524288); // 512MB