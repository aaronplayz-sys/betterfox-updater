// --- WINDOWS SPECIFIC OVERRIDES ---
// GPU & Hardware Acceleration (Nvidia RTX 4060)
user_pref("gfx.webrender.all", true);
user_pref("media.hardware-video-decoding.force-enabled", true);

// Frame Pacing & Display (Match RTSS 74fps limit)
user_pref("layout.frame_rate", 74);
user_pref("gfx.vsync.force-disable-receiver", false); 

// Windows Scrolling Physics 
user_pref("apz.overscroll.enabled", true); // DEFAULT NON-LINUX
user_pref("general.smoothScroll", true); // DEFAULT
user_pref("mousewheel.default.delta_multiplier_y", 275);

user_pref("gfx.font_rendering.cleartype_params.rendering_mode", 5);
user_pref("gfx.font_rendering.cleartype_params.cleartype_level", 100);
user_pref("gfx.font_rendering.directwrite.use_gdi_table_loading", false);