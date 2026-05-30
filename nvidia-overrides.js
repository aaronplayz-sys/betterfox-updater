// --- NVIDIA GPU OVERRIDES ---
// Detected and applied automatically on Windows and Linux systems with an NVIDIA GPU.
// Windows: requires GeForce Game Ready or Studio drivers (R520+)
// Linux:   requires nvidia-vaapi-driver and libva for hardware decode

// WebRender GPU compositor — offloads page compositing entirely to the GPU
user_pref("gfx.webrender.all", true);

// Hardware video decode via NVDEC (Windows) or nvidia-vaapi-driver (Linux)
// Significantly reduces CPU usage during video playback
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("media.gpu-process-decoder", true);

// GPU-accelerated Canvas2D — benefits WebGL-heavy pages and web apps
user_pref("gfx.canvas.accelerated", true);

// Larger memory cache suited for dedicated VRAM
// Reduce to 524288 if you have less than 6GB VRAM
user_pref("browser.cache.memory.capacity", 1048576); // 1GB