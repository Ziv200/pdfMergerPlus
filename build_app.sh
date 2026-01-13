#!/bin/bash
# Build script for creating macOS .app bundle

echo "Installing PyInstaller..."
pip install pyinstaller

echo "Building PDF Merger app..."
pyinstaller --name="PDF Merger" \
    --windowed \
    --noconfirm \
    --clean \
    --add-data="/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/customtkinter:customtkinter" \
    --add-data="/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/tkinterdnd2:tkinterdnd2" \
    --hidden-import=fitz \
    --hidden-import=PIL \
    --hidden-import=PIL.Image \
    --hidden-import=customtkinter \
    --hidden-import=darkdetect \
    --hidden-import=tkinterdnd2 \
    pdf_merger.py

echo ""
echo "Build complete!"
echo "Your app is located at: dist/PDF Merger.app"
echo ""
echo "You can now:"
echo "1. Open it from dist/PDF Merger.app"
echo "2. Move it to your Applications folder"
echo "3. Double-click to run - no IDE needed!"
