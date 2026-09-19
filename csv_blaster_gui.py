#!/usr/bin/env python3
"""
csv_blaster_gui.py — CSV Blaster GUI, the tkinter front end for CSV Blaster.

Like the console front end, this is a quick-and-dirty CSV *creator*, not
a spreadsheet editor: you type a cell, add it, and move on. There's no
clicking into an arbitrary earlier cell to edit it — only "undo the last
thing" operations (delete last cell / delete current row), same as the
console version.

This file contains ONLY the tkinter UI. All data handling lives in
csv_blaster_model.py, which this file imports and drives — the exact
same model class the console front end (csv_blaster_cli.py) uses, so
both front ends behave identically underneath.

Two windows, per spec:
  - InsertWindow — where you type and commit new cells, close out rows,
                   delete the last cell/row, and save.
  - ViewWindow   — read-only. Shows the last two completed rows plus
                   whatever's in the current (not-yet-closed) row, and
                   refreshes automatically every time InsertWindow
                   changes something.

Run directly:
    python3 csv_blaster_gui.py
"""

import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Optional

from csv_blaster_model import CSVBlasterModel, default_filename


# ---------------------------------------------------------------------------
# Startup: ask for a filename before either window opens
# ---------------------------------------------------------------------------

def choose_model_gui(root: tk.Tk) -> Optional[CSVBlasterModel]:
    """
    Ask for a filename via dialogs and return a ready-to-use model, or
    None if the user backed out entirely.
    """
    while True:
        name = simpledialog.askstring(
            "CSV Blaster",
            "Filename to use (leave blank for a timestamped name):",
            parent=root,
        )
        if name is None:
            return None  # user hit Cancel on the filename prompt

        name = name.strip()
        filename = name if name else default_filename()
        if not os.path.splitext(filename)[1]:
            filename += ".csv"

        if os.path.exists(filename):
            resp = messagebox.askyesnocancel(
                "File already exists",
                f"'{filename}' already exists.\n\n"
                f"Yes = load it and continue adding to it\n"
                f"No = overwrite it and start empty\n"
                f"Cancel = pick a different filename",
                parent=root,
            )
            if resp is True:
                return CSVBlasterModel.load(filename)
            elif resp is False:
                return CSVBlasterModel(filename)
            else:
                continue  # back to the filename prompt
        else:
            return CSVBlasterModel(filename)


# ---------------------------------------------------------------------------
# Window 1: read-only preview of recent rows
# ---------------------------------------------------------------------------

class ViewWindow(tk.Toplevel):
    """Shows the last two completed rows and the current in-progress row."""

    def __init__(self, master: tk.Misc, model: CSVBlasterModel):
        super().__init__(master)
        self.model = model
        self.title("CSV Blaster GUI — Preview")
        self.geometry("520x420")
        self.minsize(360, 260)

        ttk.Label(
            self,
            text="Previous 2 rows and current row",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 0))

        self.text = tk.Text(self, wrap="word", state="disabled")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)

        self.refresh()

    def refresh(self) -> None:
        """Rebuild the display from the model's current state."""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")

        recent = self.model.recent_rows(2)
        first_row_number = len(self.model.rows) - len(recent) + 1

        if not recent:
            self.text.insert("end", "(no completed rows yet)\n\n")
        for offset, row in enumerate(recent):
            row_number = first_row_number + offset
            self.text.insert("end", f"Row {row_number}:\n")
            if row:
                for i, cell in enumerate(row, start=1):
                    self.text.insert("end", f"  [{i}] {cell}\n")
            else:
                self.text.insert("end", "  (empty row)\n")
            self.text.insert("end", "\n")

        self.text.insert("end", "Current row (not yet saved as a line):\n")
        current = self.model.view_current_row()
        if current:
            for i, cell in enumerate(current, start=1):
                self.text.insert("end", f"  [{i}] {cell}\n")
        else:
            self.text.insert("end", "  (empty)\n")

        self.text.configure(state="disabled")


# ---------------------------------------------------------------------------
# Window 2: where cells actually get typed and committed
# ---------------------------------------------------------------------------

class InsertWindow(tk.Toplevel):
    """Where the user types cell text and commits it to the model."""

    def __init__(
        self,
        master: tk.Misc,
        model: CSVBlasterModel,
        view_window: ViewWindow,
        on_quit,
    ):
        super().__init__(master)
        self.model = model
        self.view_window = view_window
        self.on_quit = on_quit

        self.title(f"CSV Blaster GUI — Insert ({model.filename})")
        self.geometry("480x420")
        self.minsize(360, 300)
        self.protocol("WM_DELETE_WINDOW", self._quit)

        ttk.Label(self, text="Cell text (multi-line is fine):").pack(
            anchor="w", padx=8, pady=(8, 0)
        )

        self.cell_text = tk.Text(self, height=10, wrap="word", undo=True)
        self.cell_text.pack(fill="both", expand=True, padx=8, pady=4)
        self.cell_text.focus_set()
        # Ctrl+Enter is a shortcut for "Add Cell -> Next"; plain Enter
        # stays a normal newline so multi-line cells are easy to type.
        self.cell_text.bind("<Control-Return>", lambda _event: self.add_cell())

        row1 = ttk.Frame(self)
        row1.pack(fill="x", padx=8, pady=4)
        ttk.Button(row1, text="Add Cell -> Next (Ctrl+Enter)", command=self.add_cell).pack(
            side="left"
        )
        ttk.Button(row1, text="Finish Row / New Line", command=self.finish_row).pack(
            side="left", padx=4
        )

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=8, pady=4)
        ttk.Button(row2, text="Delete Last Cell", command=self.delete_last_cell).pack(
            side="left"
        )
        ttk.Button(row2, text="Delete Current Row", command=self.delete_row).pack(
            side="left", padx=4
        )

        row3 = ttk.Frame(self)
        row3.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(row3, text="Save Now", command=self.save_now).pack(side="left")
        ttk.Button(row3, text="Quit", command=self._quit).pack(side="right")

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=8, pady=(0, 8)
        )
        self._set_status(f"Editing {self.model.filename}")

    # -- helpers -----------------------------------------------------------

    def _set_status(self, message: str) -> None:
        star = "  *unsaved changes*" if self.model.unsaved_changes else ""
        self.status_var.set(f"{message}{star}")

    @staticmethod
    def _preview(text: str, limit: int = 40) -> str:
        return text if len(text) <= limit else text[: limit - 3] + "..."

    # -- button handlers -----------------------------------------------------

    def add_cell(self):
        text = self.cell_text.get("1.0", "end-1c")
        if text == "":
            messagebox.showinfo(
                "CSV Blaster", "Nothing typed — enter some text first.", parent=self
            )
            return
        self.model.insert_cell(text)
        self.cell_text.delete("1.0", "end")
        self.cell_text.focus_set()
        self.view_window.refresh()
        self._set_status(f"Added cell: {self._preview(text)!r}")

    def finish_row(self):
        # If there's unsent text sitting in the box, commit it as one
        # last cell before closing the row, so nothing typed is lost.
        text = self.cell_text.get("1.0", "end-1c")
        if text != "":
            self.model.insert_cell(text)
            self.cell_text.delete("1.0", "end")
        self.model.new_line()
        path = self.model.save()
        self.view_window.refresh()
        self._set_status(f"Row saved to {path}")

    def delete_last_cell(self):
        removed = self.model.delete_last_cell()
        self.view_window.refresh()
        if removed is None:
            self._set_status("Nothing to delete")
        else:
            self._set_status(f"Deleted cell: {self._preview(removed)!r}")

    def delete_row(self):
        self.model.delete_current_row()
        self.cell_text.delete("1.0", "end")
        self.view_window.refresh()
        self._set_status("Current row cleared")

    def save_now(self):
        path = self.model.save()
        self._set_status(f"Saved to {path}")

    def _quit(self):
        if self.model.unsaved_changes:
            resp = messagebox.askyesnocancel(
                "CSV Blaster",
                "You have unsaved changes. Save before quitting?",
                parent=self,
            )
            if resp is None:
                return  # user cancelled the quit
            if resp:
                self.model.save()
        self.on_quit()


# ---------------------------------------------------------------------------
# App controller
# ---------------------------------------------------------------------------

class CSVBlasterGUI:
    """Owns the hidden root window and wires the two visible windows together."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # the root itself is never shown

        self.model = choose_model_gui(self.root)
        if self.model is None:
            self.root.destroy()
            return

        self.view_window = ViewWindow(self.root, self.model)
        self.insert_window = InsertWindow(
            self.root, self.model, self.view_window, on_quit=self._quit
        )
        # Closing the preview window quits the whole app too, going
        # through the same unsaved-changes check as the Insert window.
        self.view_window.protocol("WM_DELETE_WINDOW", self.insert_window._quit)

    def _quit(self):
        self.root.destroy()

    def run(self):
        if self.model is None:
            return
        self.root.mainloop()


def main():
    CSVBlasterGUI().run()


if __name__ == "__main__":
    main()
