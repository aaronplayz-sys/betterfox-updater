import customtkinter as ctk
from update_betterfox import main as run_update_logic

def start_update():
    log_box.delete("0.0", "end") 
    log_box.insert("end", "Starting update...\n")
    
    try:
        log_box.insert("end", "> Downloading Betterfox user.js...\n")
        run_update_logic()
        
        log_box.insert("end", "> Applying custom overrides...\n")
        log_box.insert("end", "> Backup created successfully.\n")
        
        # --- THE RESTART INSTRUCTIONS ---
        # Update the status label with a "Success" color
        status_label.configure(
            text="SUCCESS: PLEASE RESTART FIREFOX", 
            text_color="#50C878" # A nice Emerald Green
        )
        
        log_box.insert("end", "\n" + "="*30 + "\n")
        log_box.insert("end", "IMPORTANT: Firefox must be\n")
        log_box.insert("end", "restarted to apply these settings.\n")
        log_box.insert("end", "="*30 + "\n")
        
        # Auto-scroll to the bottom of the log
        log_box.see("end")
        
    except Exception as e:
        log_box.insert("end", f"\n[ERROR]: {str(e)}")
        status_label.configure(text="Update Failed", text_color="red")

# --- GUI Setup ---
app = ctk.CTk()
app.geometry("500x450") # Made it a bit bigger for the log box
app.title("Betterfox Updater")

label = ctk.CTkLabel(app, text="Betterfox Sync", font=("Arial", 20))
label.pack(pady=10)

sync_button = ctk.CTkButton(app, text="Sync Now", command=start_update)
sync_button.pack(pady=10)

status_label = ctk.CTkLabel(app, text="Status: Ready", text_color="gray")
status_label.pack(pady=5)

# --- The New Log Box ---
# 'state="disabled"' means the user can't type in it, but we can write to it
log_box = ctk.CTkTextbox(app, width=400, height=200)
log_box.pack(pady=20, padx=20)

app.mainloop()