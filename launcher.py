"""
CardioSight Shunt Digital Twin Launcher
GUI interface for running HFrEF and HFpEF shunt simulations
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import sys
import os
from pathlib import Path
import threading

class ShuntSimulatorLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("CardioSight Shunt Digital Twin Simulator")
        self.root.geometry("900x700")

        # Get project directory
        self.project_dir = Path(__file__).parent

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        """Setup main user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="CardioSight Shunt Digital Twin Simulator",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))

        subtitle_label = ttk.Label(main_frame,
                                  text="HFrEF and HFpEF Interatrial Shunt Simulations",
                                  font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, pady=(0, 20))

        # Simulation controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Simulation Controls", padding="10")
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        # Shunt diameter
        ttk.Label(controls_frame, text="Shunt Diameter (mm):", font=('Arial', 10)).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.diameter_var = tk.StringVar(value="6")
        diameter_entry = ttk.Entry(controls_frame, textvariable=self.diameter_var, width=10)
        diameter_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(controls_frame, text="(default: 6 mm)", font=('Arial', 9)).grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5)

        # Simulation selection
        ttk.Label(controls_frame, text="Select Simulation:", font=('Arial', 10, 'bold')).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(15, 5))

        # Simulation buttons
        simulations = [
            ("test_baseline.py", "Test Baseline", "Verify installation (~15s)"),
            ("run_acute.py", "Acute Effects at Rest", "Baseline vs shunt, both twins (~15s)"),
            ("run_rv_compliance.py", "RV Compliance Study", "Right-heart compliance effects (few min)"),
            ("run_scenarios.py", "Exercise & Disease Scenarios", "Exercise, PVD, volume retention (few min)"),
            ("run_reflex.py", "Reflex Mechanisms", "Cardiac vs volume arm gain sweep (few min)"),
            ("run_echo_matrix.py", "Echo Matrix Analysis", "Match trial echocardiograms (few min)")
        ]

        row = 2
        for script, name, description in simulations:
            btn = ttk.Button(controls_frame, text=name,
                           command=lambda s=script: self.run_simulation(s),
                           width=30)
            btn.grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
            ttk.Label(controls_frame, text=description, font=('Arial', 9)).grid(
                row=row, column=1, columnspan=2, sticky=tk.W, padx=10, pady=3)
            row += 1

        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Simulation Output", padding="10")
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        main_frame.rowconfigure(3, weight=1)

        # Output text area
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD,
                                                     font=('Consolas', 9), height=15)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Initial message
        self.output_text.insert(tk.END, "CardioSight Shunt Digital Twin Simulator\n")
        self.output_text.insert(tk.END, "=" * 70 + "\n\n")
        self.output_text.insert(tk.END, "Select a simulation above to begin.\n")
        self.output_text.insert(tk.END, "Results will be saved to the 'results/' directory.\n")
        self.output_text.insert(tk.END, "\nProject directory: " + str(self.project_dir) + "\n")

    def run_simulation(self, script):
        """Run selected simulation in background thread"""
        # Get diameter
        try:
            diameter = self.diameter_var.get().strip()
            if diameter and script != "test_baseline.py":
                # Validate diameter
                float(diameter)
        except ValueError:
            messagebox.showerror("Invalid Input", "Shunt diameter must be a number")
            return

        # Clear output
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Running {script}...\n")
        self.output_text.insert(tk.END, "=" * 70 + "\n\n")

        self.status_var.set(f"Running {script}...")
        self.root.update()

        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self._run_subprocess, args=(script, diameter))
        thread.daemon = True
        thread.start()

    def _run_subprocess(self, script, diameter):
        """Run simulation subprocess"""
        try:
            # Build command
            cmd = [sys.executable, str(self.project_dir / script)]
            if diameter and script != "test_baseline.py":
                cmd.append(diameter)

            # Run process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.project_dir),
                bufsize=1
            )

            # Stream output
            for line in process.stdout:
                self.root.after(0, self._append_output, line)

            process.wait()

            if process.returncode == 0:
                self.root.after(0, self._append_output, "\n" + "=" * 70 + "\n")
                self.root.after(0, self._append_output, "✓ Simulation completed successfully!\n")
                self.root.after(0, self._append_output, f"Results saved to: {self.project_dir / 'results'}\n")
                self.root.after(0, self.status_var.set, "Simulation completed successfully")
            else:
                self.root.after(0, self._append_output, "\n✗ Simulation failed\n")
                self.root.after(0, self.status_var.set, "Simulation failed")

        except Exception as e:
            self.root.after(0, self._append_output, f"\nError: {str(e)}\n")
            self.root.after(0, self.status_var.set, f"Error: {str(e)}")

    def _append_output(self, text):
        """Append text to output window (called from main thread)"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ShuntSimulatorLauncher(root)
    root.mainloop()
