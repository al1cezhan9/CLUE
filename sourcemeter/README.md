# Keysight B2901A Control Panel GUI

This repository provides a PyQt6-based graphical user interface (GUI) for controlling the Keysight (Agilent) B2901A Precision Source/Measure Unit (SMU). It supports both voltage sweeps and continuous current measurements with real‑time plotting, data logging, and simulation mode.

---

## Features

* **Sweep Mode**: Perform voltage sweeps from a start to end voltage and back, measure current at each step, and save the results to an Excel file.
* **Data Collection Mode**: Apply a constant bias voltage, set integration (NPLC) for noise averaging, and record current vs. time. Optionally plot in real time.
* **Simulation Mode**: Fall back to a simulated instrument if no B2901A is detected or if manually enabled.
* **Config Persistence**: Save and load measurement parameters (voltages, timing, averages, file paths) in `config.json`.
* **Progress Indicator**: Visual progress bar during long sweeps.
* **Matplotlib Plotting**: Embedded plots for visual feedback.

---

## Prerequisites

* Python 3.8+
* [PyVISA](https://pypi.org/project/PyVISA/)
* [NumPy](https://pypi.org/project/numpy/)
* [Pandas](https://pypi.org/project/pandas/)
* [PyQt6](https://pypi.org/project/PyQt6/)
* [Matplotlib](https://pypi.org/project/matplotlib/)

Install dependencies via:

```bash
pip install pyvisa numpy pandas pyqt6 matplotlib
```

You will also need the VISA backend (e.g., NI-VISA or Keysight VISA) installed on your system.

---

## Setup

1. **Clone this repository**:

   ```bash
   ```

git clone [https://https://github.com/al1cezhan9/CLUE)
cd sourcemeter

````

2. **Edit the VISA resource string** in `B2901A.py`:

   ```python
   resource = "USB0::0x0957::0x8B18::MY12345678::INSTR"
````

Replace the USB ID with the one shown by Keysight Connection Expert or NI-MAX.

3. **Optional**: If you prefer simulation mode for development, check the "Simulation Mode" box in the GUI or run without a connected instrument.

---

## Usage

```bash
python B2901A.py
```

1. **Sweep Mode**

   * Enter **Start Voltage**, **End Voltage**, **Voltage Step**, and **Time Step**.
   * Click **Start Sweep**. The SMU will source each voltage, measure current, and plot and save the results.

2. **Data Collection Mode**

   * Enter **Bias Voltage**, **Aperture Time (NPLC)**, **Noise‑Reducing Average**, and **Acquisition Interval (Δt)**.
   * Optionally enable **Fast Acquisition** for real‑time plotting.
   * Click **Start Collection** to begin continuous measurement.

3. **Stopping**

   * Click **Stop** in either mode to safely terminate the measurement thread and finalize file saving.

4. **Output Files**

   * Measurements are saved as `.xlsx` by default (you can also choose `.csv`).

---

## Configuration

A `config.json` file stores your last-used parameters:

```json
{
  "save_path": "",
  "delta_v": 0.1,
  "delta_t": 0.1,
  "bias_voltage": 1.0,
  "aperture_time": 1.0,
  "noise_avg": 1,
  "start_v": -3.0,
  "end_v": 3.0
}
```

Modify this file directly or via the GUI; settings are auto-saved on start/stop actions.

---

## Extending & Troubleshooting

* **Compliance Limits**: Change `SENS:CURR:PROT` in the constructor of `B2901AInstrument` for different current limits.
* **Triggering & Burst Sweeps**: Implement segmented sweeps or trigger configurations via SCPI commands.
* **Data Logging**: Hook into the Pandas DataFrame before saving for custom file formats or additional annotations.
* **GUI Styling**: Tweak PyQt6 stylesheets or replace Matplotlib with PyQtGraph for higher performance.

If you encounter VISA errors, verify your VISA library installation and instrument connectivity.

