# Python to Executable Builder

A modern, lightweight graphical desktop utility designed to compile Python scripts into standalone `.exe` executables with automated dependency packaging, real-time logging diagnostics, and customizable output routing.

---

## Key Highlights

- **Flexible Output Routing**: Choose between generating a dedicated `portables/` folder or compiling directly within the script directory.
- **Full PyInstaller Feature Set**:
  - Single executable (`--onefile`) or directory distribution (`--onedir`).
  - Windowed mode (`--windowed`) for GUI applications without terminal popups.
  - Optional UPX compression for smaller binaries.
  - Custom executable naming with character sanitization.
  - Support for custom resource packaging (`--add-data`) and hidden imports (`--hidden-import`).
- **Live Diagnostics Console**:
  - Non-blocking streaming output with categorized color tags (info, warning, error, command).
  - One-click log clipboard export and auto-scroll control.
  - Dedicated scrollbar with responsive auto-resizing.
- **Thread-Safe Architecture**: Asynchronous build queue prevents Tkinter interface freezes during long compilations.
- **Windows Process Tree Control**: Clean cancellation that terminates compiler worker trees to avoid locked directory errors.
- **Config Persistence**: Automatically remembers your favorite flags, window dimensions, and recently built scripts across sessions.

---

## Prerequisites

1. **Python 3.8+** installed on your system.
2. **PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

*(Optional)* Install `pipreqs` if you want automatic generation of `requirements.txt` from imported project modules:
```bash
pip install pipreqs
```

---

## Quick Start

1. Clone or download this repository.
2. Launch the application:
   ```bash
   python main.py
   ```
3. Use the interface to:
   - Select your target `.py` entrypoint.
   - (Optional) Select a `.ico` file.
   - Choose your output destination (`portables/` or script directory).
   - Configure compilation options as needed.
   - Click **Build Executable**.

---

## Output Structure

Depending on your selected output mode:

- **Portables folder (`portables/`)**:
  - **Single-file mode**: `<script_dir>/portables/<app_name>.exe`
  - **Directory mode**: `<script_dir>/portables/<app_name>/` (contains executable and associated runtime assets)
- **Same folder**:
  - Creates `<script_dir>/<app_name>.exe` directly beside your source code.

---

## Project Structure

```text
PY-to-EXE/
├── main.py          # Primary application source code
├── README.md        # Documentation and usage guide
├── requirements.txt # Python dependencies
└── .gitignore       # Git exclusion rules
```
