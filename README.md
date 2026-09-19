# crispy-guacamole
TLDR: CSV Blaster, a quick-and-dirty Python-based CSV editor

## Usage
python csv_blaster_cli.py

When you first run the program, you will be prompted to enter the CSV filename. If you leave it blank, a default naming convention with a timestamp will be used instead. Again, speed and ease of use.

Type "h" to see a list of available commands.

## Summary

CSV Blaster (AKA crispy-guacamole) is a Python-based CSV editor designed for quick and dirty editing of CSV files. It provides a simple command-line interface to manipulate CSV data efficiently.

I built this applet because working with large amounts of data in Excel can be cumbersome and slow. CSV Blaster allows for rapid editing and manipulation of CSV files without the overhead of a full-fledged spreadsheet application.

Additionally, Excel tends to lack support for exporting of CSV files with proper formatting, especially when dealing with special characters, non-roman alphabets, and other edge cases. Rather than exporting directly to CSV, Excel forces you to export to plaintext with a .txt suffix. Saving extended character sets as CSV from Excel will result in a table full of mojibake at best, or streams of question marks at worst.

What CSV Blaster does not do: Provide robust spreadsheet editing. You can quickly enter data and make simple edits.

## Structure

The code base is divided into three files:

**csv_blaster_model.py**: Contains the core logic for reading, writing, and manipulating CSV files.

**csv_blaster_cli.py**: Implements the command-line interface for user interaction.

**csv_blaster_gui.py**: Provides a graphical user interface using tkinter for use cases better served by a visual approach.

