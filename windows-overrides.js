// --- WINDOWS SPECIFIC OVERRIDES ---
// GPU & Hardware Acceleration (Nvidia RTX 4060)
// WebRender GPU compositor — offloads page compositing entirely to the GPU
user_pref("gfx.webrender.all", true);
// Hardware video decode via NVDEC (Windows) or nvidia-vaapi-driver (Linux)
// Significantly reduces CPU usage during video playback
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("media.gpu-process-decoder", true);
// Larger memory cache suited for dedicated VRAM
// Reduce to 524288 if you have less than 6GB VRAM
// 1048576 KB = 1 GB, which is a reasonable default for modern GPUs with 8GB+ VRAM
user_pref("browser.cache.memory.capacity", 1048576);
// GPU-accelerated Canvas2D — benefits WebGL-heavy pages and web apps
user_pref("gfx.canvas.accelerated", true);

// Frame Pacing & Display (Match RTSS 72fps limit)
user_pref("layout.frame_rate", 72);
user_pref("gfx.vsync.force-disable-receiver", false); 

// Windows Scrolling Physics 
user_pref("apz.overscroll.enabled", true); // DEFAULT NON-LINUX
user_pref("general.smoothScroll", true); // DEFAULT
user_pref("mousewheel.default.delta_multiplier_y", 275);

// Font Rendering (DirectWrite with optimized settings)
user_pref("gfx.font_rendering.cleartype_params.rendering_mode", 5);
user_pref("gfx.font_rendering.cleartype_params.cleartype_level", 100);
user_pref("gfx.font_rendering.directwrite.use_gdi_table_loading", false);