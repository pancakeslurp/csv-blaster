#!/usr/bin/env python3
"""
csv_blaster_model.py — Shared data model for CSV Blaster.

CSV Blaster is a quick-and-dirty CSV *creator*, not a full spreadsheet
editor: you append cells and rows, you can back out your last cell or
your current row if you made a mistake, and you save. There's no
arbitrary cell editing, sorting, formulas, etc. — if you need that,
open the result in a real spreadsheet program afterward.

This module has zero UI code (no `print`, no `input`, no tkinter) so it
can be shared unchanged by:
  - csv_blaster_cli.py  (console front end)
  - csv_blaster_gui.py  (tkinter front end, "CSV Blaster GUI")

Unicode / Excel notes
----------------------
Cell text is stored internally as ordinary Python str (Unicode), so
Hebrew, CJK, Cyrillic, emoji, etc. all work with no special handling.

For the on-disk format, plain UTF-8 CSV files are opened by Excel on
Windows using the system's legacy code page by default, which garbles
non-ASCII text. The fix that avoids this without changing the file
format is to write UTF-8 with a BOM (encoding "utf-8-sig") — Excel
detects the BOM and opens the file as UTF-8 correctly, while every
other CSV-reading tool (including Python's own csv module, LibreOffice,
Google Sheets, pandas, etc.) still reads it as normal UTF-8. So we just
always save that way; there's no need to pick a different, non-standard
format.
"""

import csv
from datetime import datetime
from typing import List, Optional


def default_filename() -> str:
    """csvcreator_YYYY-MM-DD-HH-MM-SS.csv, per the original naming spec."""
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    return f"csvcreator_{stamp}.csv"


class CSVBlasterModel:
    """Holds the table data and all editing operations."""

    def __init__(self, filename: str):
        self.filename: str = filename
        self.rows: List[List[str]] = []       # rows already "closed" with nl
        self.current_row: List[str] = []      # cells typed since the last nl
        self.unsaved_changes: bool = False

    # -- cell-level operations -------------------------------------------------

    def insert_cell(self, text: str) -> None:
        """Append a new cell to the row currently being built."""
        self.current_row.append(text)
        self.unsaved_changes = True

    def delete_last_cell(self) -> Optional[str]:
        """
        Remove and return the most recently entered cell.

        If the current (in-progress) row has cells, remove from there.
        Otherwise, if a previous row was already closed with `new_line`,
        reopen it and remove its last cell instead (so you can correct a
        mistake even just after closing a row).
        """
        if self.current_row:
            removed = self.current_row.pop()
            self.unsaved_changes = True
            return removed

        if self.rows:
            last_row = self.rows.pop()
            if last_row:
                removed = last_row.pop()
                self.current_row = last_row
                self.unsaved_changes = True
                return removed
            # last row was empty; nothing to remove, put it back
            self.rows.append(last_row)

        return None

    def view_last_cell(self) -> Optional[str]:
        """Return the most recently entered cell without removing it."""
        if self.current_row:
            return self.current_row[-1]
        if self.rows and self.rows[-1]:
            return self.rows[-1][-1]
        return None

    # -- row-level operations ---------------------------------------------------

    def delete_current_row(self) -> None:
        """Discard every cell entered so far in the current row."""
        self.current_row = []
        self.unsaved_changes = True

    def view_current_row(self) -> List[str]:
        """Return the cells entered so far in the current (open) row."""
        return list(self.current_row)

    def recent_rows(self, n: int = 2) -> List[List[str]]:
        """Return the last n *closed* rows, oldest first."""
        if n <= 0:
            return []
        return [list(r) for r in self.rows[-n:]]

    def new_line(self) -> None:
        """
        Close the current row (append it to the finished rows) and start
        a fresh, empty row. A row is only added if it has at least one
        cell, so calling this twice in a row does not insert a blank row.
        """
        if self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []
            self.unsaved_changes = True

    # -- persistence --------------------------------------------------------

    def rows_for_save(self) -> List[List[str]]:
        """
        All finished rows, plus the in-progress row (if any) so nothing
        typed is silently lost on save/quit even if a row was never closed.
        """
        rows = list(self.rows)
        if self.current_row:
            rows.append(list(self.current_row))
        return rows

    def save(self, filename: Optional[str] = None) -> str:
        """
        Write the table to disk as CSV, UTF-8 with a BOM (utf-8-sig) so
        Excel opens non-ASCII text correctly. Returns the path used.
        """
        path = filename or self.filename
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(self.rows_for_save())
        self.filename = path
        self.unsaved_changes = False
        return path

    @classmethod
    def load(cls, filename: str) -> "CSVBlasterModel":
        """Load an existing CSV file into a new model instance."""
        model = cls(filename)
        # utf-8-sig transparently strips a BOM if present, and reads
        # plain UTF-8 fine if there isn't one.
        with open(filename, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            model.rows = [row for row in reader]
        return model
