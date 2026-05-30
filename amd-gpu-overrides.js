// --- AMD GPU OVERRIDES ---
// Detected and applied automatically on Windows and Linux systems with an AMD GPU.
// Optimised for RDNA2+ (RX 6000 series and newer). Older GCN cards may benefit
// from setting gfx.webrender.compositor to false if rendering issues occur.

// WebRender GPU compositor — RDNA2+ handles this reliably
user_pref("gfx.webrender.all", true);
user_pref("gfx.webrender.compositor", true);

// Hardware video decode via AMF (Windows) or VA-API with mesa-va-drivers (Linux)
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("media.gpu-process-decoder", true);

// GPU-accelerated Canvas2D
user_pref("gfx.canvas.accelerated", true);

// Larger memory cache suited for dedicated VRAM
// Reduce to 524288 if you have less than 6GB VRAM
user_pref("browser.cache.memory.capacity", 1048576); // 1GB