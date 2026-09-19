# PY-to-EXE
A clean, modern desktop tool that compiles any Python script into a standalone executable using PyInstaller.

# App Builder

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyInstaller](https://img.shields.io/badge/Built%20with-PyInstaller-orange.svg)](https://pyinstaller.org/)

A clean, modern desktop tool that turns any Python script into a **standalone executable** with one click.

---

## ✨ Features

- **One-click build** – Select a `.py` file and get a ready-to-run executable
- **Automatic dependency handling** – Detects packages with `pipreqs` and optionally installs them
- **Clean output structure** – Creates a timestamped folder inside your project and places **only** the final executable there
- **Automatic cleanup** – Removes all temporary files (`build/`, `dist/`, `.spec`, etc.) after success
- **Real-time log** – Live streaming of the entire build process with color coding
- **Progress bar** – Lightweight visual progress without slowing the build
- **Cancel support** – Stop an ongoing build at any time
- **Flexible options**
  - One-file or one-directory mode
  - Windowed (no console) mode
  - Custom executable name
  - Optional UPX compression
  - Auto-run after successful build
- **Recent files** – Quick access to previously built scripts
- **Open Output / Copy Path** – Convenient post-build actions
- **Persistent settings** – Remembers window size and last used options

---

## 📁 Output Structure

After a successful build you get a clean result:


All intermediate files are automatically deleted.

---

## 📸 Screenshots

> <img width="900" height="837" alt="image" src="https://github.com/user-attachments/assets/0b56d47c-d8af-4d8d-8c77-baca3d6d64b9" />

---

## 🚀 Requirements

- Python **3.8+**
- Packages:
  ```bash
  pip install pyinstaller pipreqs

How to Run
```bash
python app_builder.py
```


