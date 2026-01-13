#!/usr/bin/env python3
"""
Advanced PDF Merger Application
Features:
- Drag and drop PDF files
- Modern UI with CustomTkinter
- Page rearrangement via thumbnail grid
- Page notes and marking
- Save/Load project files (.pmproj)
- Export merged PDF
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path

# Set appearance and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PageThumbnail(ctk.CTkFrame):
    def __init__(self, master, file_path, page_index, thumbnail_img, on_click, on_drag_start, **kwargs):
        super().__init__(master, **kwargs)
        self.file_path = file_path
        self.page_index = page_index
        self.on_click = on_click
        self.on_drag_start = on_drag_start
        self.has_note = False
        self.is_marked = False

        # Configure layout for a horizontal "row-like" look in the vertical column
        self.grid_columnconfigure(1, weight=1)

        # Thumbnail Image
        self.img_label = ctk.CTkLabel(self, image=thumbnail_img, text="")
        self.img_label.grid(row=0, column=0, padx=5, pady=5)
        
        # Details text (Filename and page)
        filename = os.path.basename(file_path)
        self.info_label = ctk.CTkLabel(self, text=f"{filename}\nPage {page_index + 1}", 
                                      anchor="w", justify="left", font=("Arial", 11))
        self.info_label.grid(row=0, column=1, padx=10, sticky="w")

        # Bindings
        self._bind_recursive(self, "<Button-1>", lambda e: self.on_click(self))
        
        # Drag bindings
        self.img_label.bind("<B1-Motion>", self._on_drag)
        self.bind("<B1-Motion>", self._on_drag)

    def _bind_recursive(self, widget, event, callback):
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self._bind_recursive(child, event, callback)

    def _on_drag(self, event):
        self.on_drag_start(self, event)

    def set_status(self, has_note, is_marked):
        self.has_note = has_note
        self.is_marked = is_marked
        color = "transparent"
        if is_marked:
            color = "#ffcc00" # Golden/Marked
        elif has_note:
            color = "#4CAF50" # Green/Note
        
        self.configure(fg_color=color)

class PDFMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced PDF Merger")
        self.root.geometry("1000x700")

        self.pdf_files = [] # List of unique file paths
        self.page_order = [] # List of dicts: {'file': path, 'index': idx, 'note': '', 'marked': False}
        self.thumbnails = {} # Cache for thumbnails: (path, idx) -> CTkImage
        self.selected_thumbnail = None
        self.temp_dirs = [] # Track temp dirs for cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()

    def on_closing(self):
        """Cleanup and close"""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        self.root.destroy()

    def create_widgets(self):
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="PDF MERGER", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_btn = ctk.CTkButton(self.sidebar, text="Add Files", command=self.add_files)
        self.add_btn.grid(row=1, column=0, padx=20, pady=10)

        self.clear_btn = ctk.CTkButton(self.sidebar, text="Clear All", fg_color="transparent", border_width=2, command=self.clear_all)
        self.clear_btn.grid(row=2, column=0, padx=20, pady=10)

        self.save_proj_btn = ctk.CTkButton(self.sidebar, text="Save Project", command=self.save_project)
        self.save_proj_btn.grid(row=3, column=0, padx=20, pady=10)

        self.load_proj_btn = ctk.CTkButton(self.sidebar, text="Load Project", command=self.load_project)
        self.load_proj_btn.grid(row=4, column=0, padx=20, pady=10)
        
        self.reorder_label = ctk.CTkLabel(self.sidebar, text="Rearrange Selected", font=ctk.CTkFont(size=12))
        self.reorder_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        
        self.move_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.move_frame.grid(row=6, column=0, padx=20, pady=5)
        
        self.up_btn = ctk.CTkButton(self.move_frame, text="←", width=60, command=lambda: self.move_page(-1))
        self.up_btn.pack(side="left", padx=2)
        
        self.down_btn = ctk.CTkButton(self.move_frame, text="→", width=60, command=lambda: self.move_page(1))
        self.down_btn.pack(side="left", padx=2)

        self.export_btn = ctk.CTkButton(self.sidebar, text="Export Merged PDF", fg_color="#28a745", hover_color="#218838", command=self.export_pdf)
        self.export_btn.grid(row=7, column=0, padx=20, pady=20)

        # Main Content area (Scrollable Thumbnail Grid)
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Pages (Select and use arrows to reorder)")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Registration for drag and drop (files)
        self.scroll_frame._parent_canvas.drop_target_register(DND_FILES)
        self.scroll_frame._parent_canvas.dnd_bind('<<Drop>>', self.on_file_drop)

        # Detail Panel (Right Side)
        self.detail_panel = ctk.CTkFrame(self.root, width=250)
        self.detail_panel.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        self.detail_label = ctk.CTkLabel(self.detail_panel, text="Page Details", font=ctk.CTkFont(weight="bold"))
        self.detail_label.pack(pady=10)

        # Detail Panel (Right Side - Now Annotation Area)
        self.detail_panel = ctk.CTkFrame(self.root)
        self.detail_panel.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        # Tool Bar for Annotations
        self.toolbar = ctk.CTkFrame(self.detail_panel)
        self.toolbar.pack(fill="x", padx=5, pady=5)
        
        self.pen_btn = ctk.CTkButton(self.toolbar, text="Draw", width=60, command=self.set_pen_mode)
        self.pen_btn.pack(side="left", padx=2)
        
        self.text_btn = ctk.CTkButton(self.toolbar, text="Type", width=60, command=self.set_text_mode, fg_color="transparent", border_width=1)
        self.text_btn.pack(side="left", padx=2)
        
        self.clear_ann_btn = ctk.CTkButton(self.toolbar, text="Clear", width=60, fg_color="#d9534f", hover_color="#c9302c", command=self.clear_annotations)
        self.clear_ann_btn.pack(side="right", padx=2)

        # Drawing Canvas
        self.canvas_width = 400
        self.canvas_height = 550
        self.canvas = tk.Canvas(self.detail_panel, width=self.canvas_width, height=self.canvas_height, 
                                bg="gray30", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # Legacy Notes box (optional, maybe keep as page description)
        self.note_label = ctk.CTkLabel(self.detail_panel, text="Page Annotations Description:")
        self.note_label.pack(fill="x", padx=10)
        self.note_text = ctk.CTkTextbox(self.detail_panel, height=60)
        self.note_text.pack(fill="x", padx=10, pady=5)
        self.note_text.bind("<<Modified>>", self.on_note_change)

        self.mark_var = tk.BooleanVar()
        self.mark_check = ctk.CTkCheckBox(self.detail_panel, text="Mark Page", variable=self.mark_var, command=self.on_mark_toggle)
        self.mark_check.pack(pady=5)

        # Annotation State
        self.ann_mode = "pen" # "pen" or "text"
        self.current_draw_path = []
        self.last_x, self.last_y = None, None
        self.active_image = None # Reference to keep current canvas image in memory

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[
            ("PDF and forScore files", "*.pdf *.4ss"),
            ("PDF files", "*.pdf"),
            ("forScore files", "*.4ss"),
            ("All files", "*.*")
        ])
        if files:
            self.process_files(files)

    def on_file_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        self.process_files(files)

    def process_files(self, files):
        for f in files:
            f = f.strip('{}')
            if not os.path.isfile(f):
                continue
                
            if f.lower().endswith('.pdf'):
                if f not in self.pdf_files:
                    self.pdf_files.append(f)
                    self.load_pdf_pages(f)
            elif f.lower().endswith('.4ss'):
                self.handle_4ss(f)
        self.refresh_grid()

    def handle_4ss(self, file_path):
        """Handle forScore setlist files (.4ss)"""
        try:
            if zipfile.is_zipfile(file_path):
                # It's a bundle (ZIP)
                temp_dir = tempfile.mkdtemp(prefix="forscore_")
                self.temp_dirs.append(temp_dir)
                
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Look for XML file in bundle
                xml_files = list(Path(temp_dir).glob("*.xml"))
                if xml_files:
                    self.parse_forscore_xml(xml_files[0], temp_dir)
                else:
                    # No XML? Just add all PDFs found in bundle
                    bundle_pdfs = list(Path(temp_dir).glob("**/*.pdf"))
                    for pdf in bundle_pdfs:
                        pdf_str = str(pdf)
                        if pdf_str not in self.pdf_files:
                            self.pdf_files.append(pdf_str)
                            self.load_pdf_pages(pdf_str)
            else:
                # Assume it's a plain XML file
                self.parse_forscore_xml(file_path, os.path.dirname(file_path))
                
        except Exception as e:
            messagebox.showerror("forScore Error", f"Failed to process .4ss file:\n{e}")

    def parse_forscore_xml(self, xml_path, base_dir):
        """Parse forScore XML setlist and load referenced PDFs"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            if root.tag != 'forScore':
                raise ValueError("Invalid forScore XML format")
            
            setlist_title = root.get('title', 'Untitled Setlist')
            
            # Scores are referenced by 'path' attribute
            for item in root:
                if item.tag == 'score':
                    pdf_filename = item.get('path')
                    if pdf_filename:
                        # Try to find the PDF in base_dir
                        full_path = os.path.join(base_dir, pdf_filename)
                        if os.path.isfile(full_path):
                            if full_path not in self.pdf_files:
                                self.pdf_files.append(full_path)
                                self.load_pdf_pages(full_path)
                        else:
                            print(f"Referenced PDF not found: {full_path}")
                elif item.tag == 'bookmark':
                    # bookmarks also have a 'path' (parent score) and 'title'
                    pdf_filename = item.get('path')
                    # For now, we load the whole score if a bookmark is referenced
                    # In a more advanced version, we could crop to specific pages
                    if pdf_filename:
                        full_path = os.path.join(base_dir, pdf_filename)
                        if os.path.isfile(full_path) and full_path not in self.pdf_files:
                            self.pdf_files.append(full_path)
                            self.load_pdf_pages(full_path)

        except Exception as e:
            raise Exception(f"Error parsing XML: {e}")

    def load_pdf_pages(self, file_path):
        try:
            doc = fitz.open(file_path)
            for i in range(len(doc)):
                self.page_order.append({
                    'file': file_path,
                    'index': i,
                    'note': '',
                    'marked': False,
                    'annotations': [] # List of {'type': 'pen', 'points': []} or {'type': 'text', 'pos': (x,y), 'content': ''}
                })
            doc.close()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load {file_path}:\n{e}")

    def get_thumbnail(self, file_path, page_idx):
        key = (file_path, page_idx)
        if key in self.thumbnails:
            return self.thumbnails[key]
        
        try:
            doc = fitz.open(file_path)
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2)) # Smaller for thumbs
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 110))
            self.thumbnails[key] = ctk_img
            doc.close()
            return ctk_img
        except Exception:
            return None

    def refresh_grid(self):
        # Clear current grid
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Vertical layout: one column
        for i, page_info in enumerate(self.page_order):
            thumb_img = self.get_thumbnail(page_info['file'], page_info['index'])
            if not thumb_img: continue

            frame = PageThumbnail(
                self.scroll_frame, 
                page_info['file'], 
                page_info['index'], 
                thumb_img,
                on_click=self.on_thumbnail_click,
                on_drag_start=self.on_thumbnail_drag
            )
            frame.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            frame.set_status(bool(page_info['note']), page_info['marked'])
            
            # Store index in frame for reordering
            frame.current_pos = i

    def on_thumbnail_click(self, thumb_frame):
        if self.selected_thumbnail:
            self.selected_thumbnail.configure(border_width=0)
        
        self.selected_thumbnail = thumb_frame
        thumb_frame.configure(border_width=2, border_color="#3b8ed0")
        
        # Update detail panel
        page_info = self.page_order[thumb_frame.current_pos]
        
        # Load larger preview and draw on canvas
        try:
            doc = fitz.open(page_info['file'])
            page = doc[page_info['index']]
            
            # Scale to fit canvas
            zoom_x = self.canvas_width / page.rect.width
            zoom_y = self.canvas_height / page.rect.height
            zoom = min(zoom_x, zoom_y)
            
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            self.active_image = ImageTk.PhotoImage(img) # Keep reference
            self.canvas.delete("all")
            # Center image
            self.canvas.create_image(self.canvas_width//2, self.canvas_height//2, image=self.active_image, anchor="center")
            
            # Store zoom for coordinate translation
            self.current_zoom = zoom
            self.img_offset_x = (self.canvas_width - pix.width) // 2
            self.img_offset_y = (self.canvas_height - pix.height) // 2
            
            # Render existing annotations
            self.render_annotations(page_info['annotations'])
            
            doc.close()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(self.canvas_width//2, self.canvas_height//2, text=f"Error: {e}", fill="red")

        # Set note and mark
        self.note_text.edit_modified(False) # Reset before loading
        self.note_text.delete("1.0", tk.END)
        self.note_text.insert("1.0", page_info['note'])
        self.note_text.edit_modified(False) # Reset after loading
        self.mark_var.set(page_info['marked'])

    def render_annotations(self, annotations):
        for ann in annotations:
            if ann['type'] == 'pen':
                points = ann['points']
                if len(points) > 1:
                    # Translate back to canvas coordinates
                    c_points = []
                    for x, y in points:
                        c_points.append(x * self.current_zoom + self.img_offset_x)
                        c_points.append(y * self.current_zoom + self.img_offset_y)
                    self.canvas.create_line(c_points, fill="blue", width=2, capstyle=tk.ROUND, smooth=True)
            elif ann['type'] == 'text':
                x, y = ann['pos']
                cx = x * self.current_zoom + self.img_offset_x
                cy = y * self.current_zoom + self.img_offset_y
                self.canvas.create_text(cx, cy, text=ann['content'], fill="red", font=("Arial", 14, "bold"))
    
    def set_pen_mode(self):
        self.ann_mode = "pen"
        self.pen_btn.configure(fg_color=["#3B8ED0", "#1F538D"]) # Active color
        self.text_btn.configure(fg_color="transparent")

    def set_text_mode(self):
        self.ann_mode = "text"
        self.text_btn.configure(fg_color=["#3B8ED0", "#1F538D"]) # Active color
        self.pen_btn.configure(fg_color="transparent")

    def clear_annotations(self):
        if not self.selected_thumbnail: return
        idx = self.selected_thumbnail.current_pos
        if messagebox.askyesno("Clear", "Clear all drawings on this page?"):
            self.page_order[idx]['annotations'] = []
            self.on_thumbnail_click(self.selected_thumbnail) # Refresh

    def on_canvas_click(self, event):
        if not self.selected_thumbnail: return
        
        # Adjust for image offset and zoom to get PDF coordinates
        pdf_x = (event.x - self.img_offset_x) / self.current_zoom
        pdf_y = (event.y - self.img_offset_y) / self.current_zoom
        
        if self.ann_mode == "pen":
            self.last_x, self.last_y = event.x, event.y
            self.current_draw_path = [(pdf_x, pdf_y)]
        elif self.ann_mode == "text":
            self.add_text_annotation(event.x, event.y, pdf_x, pdf_y)

    def on_canvas_drag(self, event):
        if self.ann_mode == "pen" and self.last_x is not None:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, 
                                    fill="blue", width=2, capstyle=tk.ROUND, smooth=True)
            self.last_x, self.last_y = event.x, event.y
            
            pdf_x = (event.x - self.img_offset_x) / self.current_zoom
            pdf_y = (event.y - self.img_offset_y) / self.current_zoom
            self.current_draw_path.append((pdf_x, pdf_y))

    def on_canvas_release(self, event):
        if self.ann_mode == "pen" and self.current_draw_path:
            idx = self.selected_thumbnail.current_pos
            self.page_order[idx]['annotations'].append({
                'type': 'pen',
                'points': self.current_draw_path
            })
            self.current_draw_path = []
            self.last_x, self.last_y = None, None

    def add_text_annotation(self, cx, cy, px, py):
        # Create a simple entry popup
        popup = tk.Toplevel(self.root)
        popup.title("Enter Text")
        popup.geometry(f"+{self.root.winfo_pointerx()}+{self.root.winfo_pointery()}")
        
        entry = ctk.CTkEntry(popup, width=200)
        entry.pack(padx=10, pady=10)
        entry.focus()
        
        def save_text(e=None):
            text = entry.get()
            if text:
                idx = self.selected_thumbnail.current_pos
                self.page_order[idx]['annotations'].append({
                    'type': 'text',
                    'pos': (px, py),
                    'content': text
                })
                self.on_thumbnail_click(self.selected_thumbnail) # Refresh view
            popup.destroy()
            
        entry.bind("<Return>", save_text)
        ctk.CTkButton(popup, text="OK", command=save_text).pack(pady=5)

    def on_note_change(self, event=None):
        if not self.note_text.edit_modified():
            return
            
        if self.selected_thumbnail:
            idx = self.selected_thumbnail.current_pos
            note = self.note_text.get("1.0", tk.END).strip()
            self.page_order[idx]['note'] = note
            self.selected_thumbnail.set_status(bool(note), self.page_order[idx]['marked'])
        
        self.note_text.edit_modified(False)

    def on_mark_toggle(self):
        if self.selected_thumbnail:
            idx = self.selected_thumbnail.current_pos
            marked = self.mark_var.get()
            self.page_order[idx]['marked'] = marked
            self.selected_thumbnail.set_status(bool(self.page_order[idx]['note']), marked)

    def on_thumbnail_drag(self, thumb_frame, event):
        # Calculate cursor position relative to the scroll_frame
        y = event.y_root - self.scroll_frame.winfo_rooty()
        
        # Determine the target index based on vertical position
        # Each item is roughly 120px high (thumbnail + padding)
        target_idx = max(0, min(len(self.page_order) - 1, y // 120))
        
        if target_idx != thumb_frame.current_pos:
            # Reorder in data
            old_idx = thumb_frame.current_pos
            item = self.page_order.pop(old_idx)
            self.page_order.insert(target_idx, item)
            
            self.refresh_grid()
            # Reselect to keep focus
            for widget in self.scroll_frame.winfo_children():
                if isinstance(widget, PageThumbnail) and widget.current_pos == target_idx:
                    self.on_thumbnail_click(widget)
                    break

    def move_page(self, direction):
        if not self.selected_thumbnail:
            return
        
        idx = self.selected_thumbnail.current_pos
        new_idx = idx + direction
        
        if 0 <= new_idx < len(self.page_order):
            # Swap in data
            self.page_order[idx], self.page_order[new_idx] = self.page_order[new_idx], self.page_order[idx]
            self.refresh_grid()
            # Reselect the moved thumbnail
            for widget in self.scroll_frame.winfo_children():
                if isinstance(widget, PageThumbnail) and widget.current_pos == new_idx:
                    self.on_thumbnail_click(widget)
                    break

    def clear_all(self):
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all files?"):
            self.pdf_files.clear()
            self.page_order.clear()
            self.thumbnails.clear()
            self.refresh_grid()
            self.preview_label.configure(image=None, text="Select a page")
            self.note_text.delete("1.0", tk.END)

    def save_project(self):
        path = filedialog.asksaveasfilename(defaultextension=".pmproj", filetypes=[("PDF Project", "*.pmproj")])
        if path:
            data = {
                'pdf_files': self.pdf_files,
                'page_order': self.page_order
            }
            with open(path, 'w') as f:
                json.dump(data, f)
            messagebox.showinfo("Success", "Project saved successfully.")

    def load_project(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Project", "*.pmproj")])
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
            self.pdf_files = data.get('pdf_files', [])
            self.page_order = data.get('page_order', [])
            self.thumbnails.clear()
            self.refresh_grid()
            messagebox.showinfo("Success", "Project loaded successfully.")

    def export_pdf(self):
        if not self.page_order:
            messagebox.showwarning("No Pages", "No pages to export.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not save_path:
            return

        try:
            out_doc = fitz.open()
            for page_info in self.page_order:
                src_doc = fitz.open(page_info['file'])
                # Create a temporary single-page doc to apply annotations
                temp_page_doc = fitz.open()
                temp_page_doc.insert_pdf(src_doc, from_page=page_info['index'], to_page=page_info['index'])
                page = temp_page_doc[0]
                
                # Apply annotations
                ink_list = []
                for ann in page_info['annotations']:
                    if ann['type'] == 'pen':
                        ink_list.append(ann['points'])
                    elif ann['type'] == 'text':
                        page.insert_text(ann['pos'], ann['content'], color=(1, 0, 0), fontsize=14)
                
                if ink_list:
                    page.add_ink_annot(ink_list)
                
                # Merge into final doc
                out_doc.insert_pdf(temp_page_doc)
                
                # Cleanup
                src_doc.close()
                temp_page_doc.close()

            out_doc.save(save_path)
            out_doc.close()
            messagebox.showinfo("Success", f"Merged PDF saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF:\n{e}")

def main():
    root = TkinterDnD.Tk()
    app = PDFMergerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
