#!/usr/bin/env python3
"""
csv_blaster_cli.py — CSV Blaster, console front end.

CSV Blaster is a quick-and-dirty CSV creator: type cells, close rows,
save. It is not a spreadsheet editor — there's no going back to edit an
arbitrary earlier cell, only undo-the-last-thing operations.

This file contains ONLY the console UI (command loop, prompts, printed
feedback). All data handling lives in csv_blaster_model.py, which this
file imports and drives. The tkinter front end (csv_blaster_gui.py)
drives the exact same model class, so the two front ends never drift
out of sync on how the data actually behaves.

Run directly:
    python3 csv_blaster_cli.py
"""

import os
import sys
from typing import List

from csv_blaster_model import CSVBlasterModel, default_filename


HELP_TEXT = """
COMMAND MODE — commands available at the "csv>" prompt:
  i        enter INSERT MODE to start adding cells
  dl       delete last cell entered
  vl       view last cell entered
  dr       delete current row and restart it
  vr       view current row
  nl       end current row / start a new line, and save the file
  save     save the file now
  h / help show this help text
  q        quit (asks to save first if there are unsaved changes)

INSERT MODE (entered with 'i') — see 'help' inside insert mode for details.
The command-mode commands above (dl, vl, dr, vr, nl, save, q) are NOT
available while in insert mode; press !i first to return to command mode.
"""

INSERT_HELP_TEXT = """
INSERT MODE — you are entering cell text. Type or paste text one line at
a time; a cell can span multiple lines (e.g. text on one line, an
annotation on the next) — just press Enter between lines.

On a line BY ITSELF you can type:
  !n       finish this cell and move on to the next cell
           (stays in insert mode)
  !i       finish this cell and exit insert mode, back to command mode
  help     show this message again

Everything else you type becomes part of the current cell's text,
including blank lines — a cell is only ended by !n or !i.
"""


class CLIEditor:
    """Console command loop. Translates user input into model calls."""

    def __init__(self, model: CSVBlasterModel):
        self.model = model
        self.in_insert_mode = False  # tracked mainly for clarity/prompting

    # -- command handlers -----------------------------------------------------

    def _finish_cell(self, lines: List[str]) -> None:
        """Join the buffered lines into one cell and insert it into the model."""
        text = "\n".join(lines)
        self.model.insert_cell(text)
        preview = text if len(text) <= 60 else text[:57] + "..."
        print(f"  inserted: {preview!r}")

    def cmd_insert(self):
        """
        Enter INSERT MODE. Stays in this mode — prompting for one cell
        after another — until the user types '!i' on its own line.
        '!n' on its own line ends the current cell and starts the next
        one without leaving insert mode.
        """
        self.in_insert_mode = True
        print()
        print("=== INSERT MODE === (type 'help' for insert-mode commands)")
        try:
            while True:
                lines: List[str] = []
                while True:
                    try:
                        line = input("insert> ")
                    except EOFError:
                        # Treat end-of-input like !i: bank whatever was typed
                        # and drop back to command mode.
                        if lines:
                            self._finish_cell(lines)
                        print("\n=== exiting insert mode (end of input) ===")
                        return
                    if line == "!i":
                        if lines:
                            self._finish_cell(lines)
                        print("=== exiting insert mode -> command mode ===")
                        return
                    if line == "!n":
                        self._finish_cell(lines)
                        break  # start the next cell
                    if line.strip().lower() == "help":
                        print(INSERT_HELP_TEXT)
                        continue
                    lines.append(line)
        finally:
            self.in_insert_mode = False

    def cmd_delete_last(self):
        removed = self.model.delete_last_cell()
        if removed is None:
            print("Nothing to delete.")
        else:
            preview = removed if len(removed) <= 60 else removed[:57] + "..."
            print(f"Deleted cell: {preview!r}")

    def cmd_view_last(self):
        cell = self.model.view_last_cell()
        if cell is None:
            print("(no cells entered yet)")
        else:
            print("--- last cell ---")
            print(cell)
            print("-----------------")

    def cmd_delete_row(self):
        self.model.delete_current_row()
        print("Current row cleared.")

    def cmd_view_row(self):
        row = self.model.view_current_row()
        if not row:
            print("(current row is empty)")
            return
        print("--- current row ---")
        for i, cell in enumerate(row, start=1):
            print(f"[{i}] {cell}")
        print("-------------------")

    def cmd_new_line(self):
        self.model.new_line()
        path = self.model.save()
        print(f"Row closed and saved to {path}")

    def cmd_save(self):
        path = self.model.save()
        print(f"Saved to {path}")

    def cmd_quit(self) -> bool:
        """Returns True if the program should exit."""
        if self.model.unsaved_changes:
            answer = input("You have unsaved changes. Save before quitting? [Y/n]: ").strip().lower()
            if answer in ("", "y", "yes"):
                self.model.save()
                print(f"Saved to {self.model.filename}")
        print("Goodbye.")
        return True

    # -- main loop --------------------------------------------------------------

    COMMANDS = {
        "dl": "cmd_delete_last",
        "vl": "cmd_view_last",
        "dr": "cmd_delete_row",
        "vr": "cmd_view_row",
        "nl": "cmd_new_line",
        "save": "cmd_save",
    }

    def run(self):
        print(f"CSV Blaster — editing: {self.model.filename}")
        print("=== COMMAND MODE === Type 'h' or 'help' for a list of commands.\n")
        while True:
            try:
                cmd = input("csv> ").strip().lower()
            except EOFError:
                self.cmd_quit()
                break

            if cmd in ("q", "quit", "exit"):
                if self.cmd_quit():
                    break
            elif cmd in ("h", "help", "?"):
                print(HELP_TEXT)
            elif cmd == "i":
                self.cmd_insert()
            elif cmd in self.COMMANDS:
                getattr(self, self.COMMANDS[cmd])()
            elif cmd == "":
                continue
            else:
                print(f"Unknown command: {cmd!r}. Type 'h' for help.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def choose_model() -> CSVBlasterModel:
    """Ask for a filename and either load an existing file or start fresh."""
    name = input(
        "Filename to use (leave blank for csvcreator_<timestamp>.csv): "
    ).strip()

    if not name:
        filename = default_filename()
    else:
        filename = name if os.path.splitext(name)[1] else name + ".csv"

    if os.path.exists(filename):
        choice = input(
            f"'{filename}' already exists. [L]oad it, [O]verwrite, or "
            f"[C]ancel and pick another name? [L/o/c]: "
        ).strip().lower()
        if choice in ("", "l", "load"):
            return CSVBlasterModel.load(filename)
        elif choice in ("o", "overwrite"):
            return CSVBlasterModel(filename)
        else:
            return None
    return CSVBlasterModel(filename)


def main():
    print("=== CSV Blaster ===")
    print("A quick-and-dirty CSV creator (not a full spreadsheet editor).\n")

    # Make sure the console can actually round-trip Unicode both ways.
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        # reconfigure() doesn't exist on very old Python versions; the
        # platform default is usually fine on modern systems anyway.
        pass

    model = choose_model()
    if model is None:
        print("Cancelled. Restart the program to pick a different filename.")
        return

    CLIEditor(model).run()


if __name__ == "__main__":
    main()
