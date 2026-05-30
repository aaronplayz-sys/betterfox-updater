// --- WINDOWS SPECIFIC OVERRIDES ---
// Frame Pacing & Display (Match RTSS 72fps limit) // change to 60 if you have a 60Hz monitor or higher if you have a high refresh rate display and want to take advantage of it.
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