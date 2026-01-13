# PDF Merger

A simple drag-and-drop application to merge multiple PDF files into one.

## Quick Start - Build Native App (Recommended)

To create a standalone macOS app that runs without Python:

```bash
# Install dependencies
pip install -r requirements.txt

# Build the app
./build_app.sh
```

Your app will be at `dist/PDF Merger.app` - just double-click to run!
You can move it to your Applications folder for easy access.

## Alternative - Run with Python

If you prefer to run with Python directly:

```bash
pip install -r requirements.txt
python pdf_merger.py
```

## How to Use

1. Drag and drop PDF files into the application window
2. Files will appear in the list
3. Click "Merge PDFs" button
4. Choose where to save the merged PDF file
5. Done!

## Features

- Drag and drop multiple PDF files
- Visual list of files to be merged
- Clear all files option
- Choose custom save location
- Simple and intuitive interface
