// --- Common Overrides ---
// Allow Firefox to manage passwords and autofill
user_pref("signon.rememberSignons", true);
user_pref("extensions.formautofill.addresses.enabled", true);
user_pref("extensions.formautofill.creditCards.enabled", true);

// Enable geolocation but prompt for permission each time
user_pref("permissions.default.geo", 0);

// Allow shortcuts and top sites on new tab page, but disable sponsored content
user_pref("browser.newtabpage.activity-stream.feeds.topsites", true); // Shortcuts
user_pref("browser.newtabpage.activity-stream.default.sites", ""); // clear default topsites
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false); // Sponsored shortcuts 
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false); // Recommended by Pocket
user_pref("browser.newtabpage.activity-stream.showSponsored", false); // Sponsored Stories

// Disable JavaScript JIT and WebAssembly optimizing compiler for better stability and security
user_pref("javascript.options.ion", false);
user_pref("javascript.options.wasm_optimizingjit", false);