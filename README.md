# Keithley 6517A Control Panel GUI

A Python GUI application to control the **Keithley 6517A Electrometer** for automated voltage sweeps and data collection.

This tool supports:

-  Sweep Mode (Voltage Sweep I-V Measurement)
-  Data Collection Mode (Fixed Bias Time-Based Measurement)
-  Simulation Mode (Test without physical hardware)
-  Real-time plot updates
-  Progress bar and status messages
-  Auto-saving data to Excel

---

## Features

### Sweep Mode

- Configure **Start Voltage**, **End Voltage**, **Voltage Step**, and **Time Step**.
- Perform both **forward** and **reverse** voltage sweeps automatically.
- Visualize the measurement after sweep completion.
- Export collected data to Excel.

### Data Collection Mode

- Apply a constant **bias voltage**.
- Define **Aperture Time**, **Noise Average (number of readings to average)**, and **Acquisition Time Δt**.
- Optional **fast acquisition mode** for real-time plotting.
- Export collected time-based data to Excel.

### Simulation Mode

- Test the GUI without the physical Keithley instrument.
- Simulated measurements behave realistically for development and testing.

### Additional Features

- Live **progress bar** and **status updates**.
- **Config saving**: remembers last used parameters (saved in `config.json`).
- Easy **file saving** with auto-generated filenames if none is provided.

---

## Installation

### Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install pyvisa pyqt6 numpy pandas matplotlib openpyxl
```

> 💡 **Note:**\
> If you encounter errors about `openpyxl`, ensure it is installed as it is required for Excel export.

---

## Usage

1. Run the application:

```bash
python keithley.py
```

2. Use the GUI:

   - **Simulation Mode**: Enable if testing without hardware.
   - **Sweep Mode**:
     - Enter voltage range, steps, and time interval.
     - Click "Start Sweep".
   - **Data Collection Mode**:
     - Enter bias voltage, averaging, and timing parameters.
     - Optional: enable fast acquisition for real-time plotting.
     - Click "Start Collection".
   - **Stop Measurement**: Press "Stop" anytime to halt the measurement safely.
   - **File Saving**: Define your desired save path, or the program will auto-generate an Excel file with a timestamp.

3. Exported files are saved in **Excel (.xlsx)** format to the specified location.

---

## Notes

- The GUI runs measurements in background threads for responsiveness.
- Safe, thread-safe updates ensure no crashes when plotting or updating progress.
- Configurations persist across sessions in `config.json`.

---
