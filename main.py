import tkinter as tk
from tkinter import messagebox, font
import subprocess
import os
import webbrowser
#edit by andy
# --- CONFIGURATION & CONSTANTS ---

# Paths to your scripts and output files
GENERATE_IMAGE_SCRIPT = "generate_image.py"
GENERATE_NITRATE_IMAGE_SCRIPT = "generate_image_nitrate.py"
GENERATE_MAPS_SCRIPT = "generate_maps.py"
INTERACTIVE_MAP_HTML = "interactive_map.html"

# UI Styling
BG_COLOR = "#2e2e2e"
FRAME_COLOR = "#3c3c3c"
BUTTON_COLOR = "#5a5a5a"
TEXT_COLOR = "#e0e0e0"
ACCENT_COLOR = "#007acc"
WINDOW_WIDTH = 450
WINDOW_HEIGHT = 300

# --- REPORT GENERATION LOGIC ---

def run_groundwater_report(status_label):
    """
    Runs the subprocesses to generate the groundwater elevation report.
    """
    try:
        # Update status bar to inform the user
        status_label.config(text="Step 1/3: Generating contour image...", fg=ACCENT_COLOR)
        root.update_idletasks() # Force UI update
        subprocess.run(["python", GENERATE_IMAGE_SCRIPT], check=True, capture_output=True, text=True)

        status_label.config(text="Step 2/3: Generating interactive maps...")
        root.update_idletasks()
        subprocess.run(["python", GENERATE_MAPS_SCRIPT], check=True, capture_output=True, text=True)

        status_label.config(text="Step 3/3: Opening report...")
        root.update_idletasks()
        if os.path.exists(INTERACTIVE_MAP_HTML):
            webbrowser.open_new_tab(f"file://{os.path.realpath(INTERACTIVE_MAP_HTML)}")
            messagebox.showinfo(
                "Report Ready",
                f"Groundwater report generated successfully!\n\nThe interactive map '{INTERACTIVE_MAP_HTML}' is opening in your browser."
            )
        else:
            messagebox.showerror("File Not Found", f"Error: Could not find the output file '{INTERACTIVE_MAP_HTML}'.")

    except FileNotFoundError:
        messagebox.showerror("Error", "Python command not found. Please ensure Python is in your system's PATH.")
    except subprocess.CalledProcessError as e:
        # Provide more specific error feedback
        error_message = f"An error occurred while running a script:\n\nScript: {e.cmd}\n\nError:\n{e.stderr}"
        messagebox.showerror("Execution Error", error_message)
    finally:
        # Reset status bar
        status_label.config(text="Ready", fg=TEXT_COLOR)

def run_nitrate_report(status_label):
    """
    Dummy function to simulate generating a nitrate concentration report.
    """
    try:
        # Update status bar to inform the user
        status_label.config(text="Step 1/3: Generating contour image...", fg=ACCENT_COLOR)
        root.update_idletasks() # Force UI update
        subprocess.run(["python", GENERATE_NITRATE_IMAGE_SCRIPT], check=True, capture_output=True, text=True)

        status_label.config(text="Step 2/3: Generating interactive maps...")
        root.update_idletasks()
        subprocess.run(["python", GENERATE_MAPS_SCRIPT], check=True, capture_output=True, text=True)

        status_label.config(text="Step 3/3: Opening report...")
        root.update_idletasks()
        if os.path.exists(INTERACTIVE_MAP_HTML):
            webbrowser.open_new_tab(f"file://{os.path.realpath(INTERACTIVE_MAP_HTML)}")
            messagebox.showinfo(
                "Report Ready",
                f"Groundwater report generated successfully!\n\nThe interactive map '{INTERACTIVE_MAP_HTML}' is opening in your browser."
            )
        else:
            messagebox.showerror("File Not Found", f"Error: Could not find the output file '{INTERACTIVE_MAP_HTML}'.")

    except FileNotFoundError:
        messagebox.showerror("Error", "Python command not found. Please ensure Python is in your system's PATH.")
    except subprocess.CalledProcessError as e:
        # Provide more specific error feedback
        error_message = f"An error occurred while running a script:\n\nScript: {e.cmd}\n\nError:\n{e.stderr}"
        messagebox.showerror("Execution Error", error_message)
    finally:
        # Reset status bar
        status_label.config(text="Ready", fg=TEXT_COLOR)

# --- MAIN APPLICATION UI ---

def main():
    global root # Make root global for the status updates
    root = tk.Tk()
    root.title("Groundwater Report Generator")
    root.configure(bg=BG_COLOR)
    root.resizable(False, False)

    # Center the window on the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_pos = (screen_width // 2) - (WINDOW_WIDTH // 2)
    y_pos = (screen_height // 2) - (WINDOW_HEIGHT // 2)
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x_pos}+{y_pos}")

    # Define custom fonts
    title_font = font.Font(family="Segoe UI", size=18, weight="bold")
    button_font = font.Font(family="Segoe UI", size=12)
    status_font = font.Font(family="Segoe UI", size=10)

    # --- Main Frame ---
    main_frame = tk.Frame(root, bg=FRAME_COLOR, padx=20, pady=20)
    main_frame.pack(expand=True, fill="both", padx=15, pady=15)

    # --- Widgets ---
    # Title Label
    title_label = tk.Label(
        main_frame,
        text="Select Report Type",
        font=title_font,
        bg=FRAME_COLOR,
        fg=TEXT_COLOR
    )
    title_label.pack(pady=(0, 20))

    # Status Label (at the bottom)
    status_label = tk.Label(
        root,
        text="Ready",
        font=status_font,
        bg=BG_COLOR,
        fg=TEXT_COLOR,
        bd=1,
        relief="sunken",
        anchor="w"
    )
    status_label.pack(side="bottom", fill="x")

    # Groundwater Button
    groundwater_button = tk.Button(
        main_frame,
        text="Groundwater Elevation",
        font=button_font,
        bg=BUTTON_COLOR,
        fg=TEXT_COLOR,
        activebackground=ACCENT_COLOR,
        activeforeground=TEXT_COLOR,
        width=25,
        height=2,
        relief="raised",
        borderwidth=2,
        command=lambda: run_groundwater_report(status_label)
    )
    groundwater_button.pack(pady=10)

    # Nitrate Button
    nitrate_button = tk.Button(
        main_frame,
        text="Nitrate Concentration",
        font=button_font,
        bg=BUTTON_COLOR,
        fg=TEXT_COLOR,
        activebackground=ACCENT_COLOR,
        activeforeground=TEXT_COLOR,
        width=25,
        height=2,
        relief="raised",
        borderwidth=2,
        command=lambda: run_nitrate_report(status_label)
    )
    nitrate_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()