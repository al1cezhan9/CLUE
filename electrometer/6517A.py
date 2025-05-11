
import sys
import json
import threading
import time
from datetime import datetime

import pyvisa
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QTabWidget, QCheckBox, QSpinBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class SimulatedInstrument:
    def __init__(self):
        self.current_voltage = 0

    def write(self, command):
        print(f"Simulated write: {command}")
        if ":SOUR:VOLT" in command:
            try:
                self.current_voltage = float(command.split()[-1])
            except ValueError:
                pass

    def query(self, command):
        print(f"Simulated query: {command}")
        if ":MEAS:CURR?" in command:
            voltage = self.current_voltage
            simulated_current = 1e-9 * (voltage ** 2) + np.random.normal(0, 1e-12)
            return str(simulated_current)
        return "0"

class KeithleyGUI(QWidget):
    plot_signal = pyqtSignal(object, object)
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Keithley 6517A Control Panel")
        self.setGeometry(100, 100, 1000, 750)

        self.load_config()
        self.simulation_mode = False

        self.measurement_thread = None
        self.stop_flag = False

        self.init_ui()
        self.init_instrument()

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            default_config = {
                'save_path': '',
                'delta_v': 0.1,
                'delta_t': 0.1,
                'bias_voltage': 1.0,
                'aperture_time': 1.0,
                'noise_avg': 1,
                'start_v': -3.0,
                'end_v': 3.0
            }
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
        except FileNotFoundError:
            self.config = {
                'save_path': '',
                'delta_v': 0.1,
                'delta_t': 0.1,
                'bias_voltage': 1.0,
                'aperture_time': 1.0,
                'noise_avg': 1,
                'start_v': -3.0,
                'end_v': 3.0
            }

    def save_config(self):
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def init_instrument(self):
        self.instrument = None
        rm = pyvisa.ResourceManager()

        try:
            self.instrument = rm.open_resource("GPIB0::26::INSTR")
            self.instrument.timeout = 5000
            self.instrument.write_termination = '\n'
            self.instrument.read_termination = '\n'

            self.instrument.write("*RST")
            self.instrument.write(":SYST:ZCH OFF")
            self.instrument.write(":SOUR:VOLT:RANG 500")
            self.instrument.write(":SENS:FUNC 'CURR'")
            self.instrument.write(":SENS:CURR:PROT 1e-3")
            self.instrument.write(":FORM:ELEM CURR")

            idn = self.instrument.query("*IDN?").strip()
            self.status_label.setText(f"Keithley 6517A detected: {idn}")
            print(f"Connected to: {idn}")

            self.simulation_checkbox.setChecked(False)
            self.simulation_mode = False

        except Exception as e:
            print(f"Instrument not found. Switching to simulation.\n{e}")
            self.instrument = SimulatedInstrument()
            self.simulation_mode = True
            self.simulation_checkbox.setChecked(True)
            self.status_label.setText("Status: Simulation Mode (instrument not found)")

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.simulation_checkbox = QCheckBox("Simulation Mode (force)")
        self.simulation_checkbox.setChecked(False)
        self.simulation_checkbox.stateChanged.connect(self.toggle_simulation_mode)
        layout.addWidget(self.simulation_checkbox)

        self.tabs = QTabWidget()
        self.tab_sweep = QWidget()
        self.tab_collect = QWidget()

        self.tabs.addTab(self.tab_sweep, "Sweep Mode")
        self.tabs.addTab(self.tab_collect, "Data Collection")

        layout.addWidget(self.tabs)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.figure.tight_layout()

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.plot_signal.connect(self.update_plot)
        self.progress_signal.connect(self.update_progress)

        self.setup_sweep_tab()
        self.setup_collect_tab()

    def toggle_simulation_mode(self):
        self.simulation_mode = self.simulation_checkbox.isChecked()
        if self.simulation_mode:
            self.instrument = SimulatedInstrument()
            self.status_label.setText("Status: Simulation Mode (manual override)")
        else:
            self.init_instrument()

    def setup_sweep_tab(self):
        layout = QVBoxLayout()
        self.start_v_input = QLineEdit(str(self.config['start_v']))
        self.end_v_input = QLineEdit(str(self.config['end_v']))
        self.delta_v_input = QLineEdit(str(self.config['delta_v']))
        self.delta_t_input = QLineEdit(str(self.config['delta_t']))

        layout.addWidget(QLabel("Start Voltage (V):"))
        layout.addWidget(self.start_v_input)
        layout.addWidget(QLabel("End Voltage (V):"))
        layout.addWidget(self.end_v_input)
        layout.addWidget(QLabel("Voltage Step (V):"))
        layout.addWidget(self.delta_v_input)
        layout.addWidget(QLabel("Time Step (s):"))
        layout.addWidget(self.delta_t_input)

        sweep_button = QPushButton("Start Sweep")
        sweep_button.clicked.connect(self.start_sweep)
        layout.addWidget(sweep_button)

        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_measurement)
        layout.addWidget(stop_button)

        self.sweep_filepath_input = QLineEdit(self.config["save_path"])
        sweep_browse_button = QPushButton("Browse...")
        sweep_browse_button.clicked.connect(self.browse_file_sweep)
        layout.addWidget(QLabel("Save File (Sweep):"))
        layout.addWidget(self.sweep_filepath_input)
        layout.addWidget(sweep_browse_button)
        self.tab_sweep.setLayout(layout)

    def setup_collect_tab(self):
        layout = QVBoxLayout()
        self.bias_input = QLineEdit(str(self.config['bias_voltage']))
        self.aperture_input = QLineEdit(str(self.config['aperture_time']))
        self.noise_avg_input = QSpinBox()
        self.noise_avg_input.setValue(self.config['noise_avg'])
        self.delta_t_collect = QLineEdit(str(self.config['delta_t']))
        self.filepath_input = QLineEdit(self.config['save_path'])
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_file)

        layout.addWidget(QLabel("Bias Voltage (V):"))
        layout.addWidget(self.bias_input)
        layout.addWidget(QLabel("Aperture Time (PLC):"))
        layout.addWidget(self.aperture_input)
        layout.addWidget(QLabel("Noise-Reducing Average (points):"))
        layout.addWidget(self.noise_avg_input)
        layout.addWidget(QLabel("Acquisition Time Δt (s):"))
        layout.addWidget(self.delta_t_collect)
        layout.addWidget(QLabel("Save File:"))
        layout.addWidget(self.filepath_input)
        layout.addWidget(browse_button)

        self.fast_acq_collect_checkbox = QCheckBox("Enable Fast Acquisition (Real-Time Plot)")
        layout.addWidget(self.fast_acq_collect_checkbox)

        start_button = QPushButton("Start Collection")
        start_button.clicked.connect(self.start_collection)
        layout.addWidget(start_button)

        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_measurement)
        layout.addWidget(stop_button)

        self.tab_collect.setLayout(layout)

    def update_plot(self, x_data, y_data):
        self.ax.clear()
        self.ax.set_xlabel("Voltage (V)" if self.tabs.currentIndex() == 0 else "Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.ax.plot(x_data, y_data, 'o-')
        self.canvas.draw()

    def update_progress(self, value):
        self.progress.setValue(value)

    def browse_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel Files (*.xlsx);;Text Files (*.txt);;CSV Files (*.csv)")
        if path:
            self.filepath_input.setText(path)

    def browse_file_sweep(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Sweep File", "", "Excel Files (*.xlsx)")
        if path:
            self.sweep_filepath_input.setText(path)
        path, _ = QFileDialog.getSaveFileName(self, "Save Sweep File", "", "Excel Files (*.xlsx)")
        if path:
            self.sweep_filepath_input.setText(path)
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel Files (*.xlsx);;Text Files (*.txt);;CSV Files (*.csv)")
        if path:
            self.filepath_input.setText(path)

    def start_sweep(self):
        self.stop_flag = False
        self.ax.clear()
        self.ax.set_xlabel("Voltage (V)")
        self.ax.set_ylabel("Current (A)")
        self.status_label.setText("Status: Measuring...")

        self.measurement_thread = threading.Thread(target=self.run_sweep)
        self.measurement_thread.start()

    def start_collection(self):
        self.stop_flag = False
        self.ax.clear()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.status_label.setText("Status: Measuring...")

        self.measurement_thread = threading.Thread(target=self.run_collection)
        self.measurement_thread.start()

    def stop_measurement(self):
        self.stop_flag = True
        self.status_label.setText("Status: Stopping...")
        if self.measurement_thread and self.measurement_thread.is_alive():
            self.measurement_thread.join()
        self.progress.setValue(0)
        self.status_label.setText("Status: Ready")

    def run_sweep(self):
        self.config['start_v'] = float(self.start_v_input.text())
        self.config['end_v'] = float(self.end_v_input.text())
        self.config['delta_v'] = float(self.delta_v_input.text())
        self.config['delta_t'] = float(self.delta_t_input.text())
        self.save_config()

        start_v = self.config['start_v']
        end_v = self.config['end_v']
        delta_v = self.config['delta_v']
        delta_t = self.config['delta_t']

        if delta_v == 0:
            self.status_label.setText("Error: Voltage step cannot be zero.")
            return

        forward = np.arange(start_v, end_v + delta_v, delta_v)
        reverse = np.arange(end_v, start_v - delta_v, -delta_v)
        voltages = np.concatenate((forward, reverse))
        currents = []

        self.progress_signal.emit(len(voltages))
        self.status_label.setText("Status: Measuring...")

        for i, v in enumerate(voltages):
            if self.stop_flag:
                break

            self.instrument.write(f":SOUR:VOLT {v}")
            self.instrument.write(":INIT")
            time.sleep(delta_t)
            current = float(self.instrument.query(":MEAS:CURR?").strip())
            currents.append(current)
            self.progress_signal.emit(i + 1)

        self.plot_signal.emit(voltages[:len(currents)], currents)

        save_path = self.sweep_filepath_input.text() or f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df = pd.DataFrame({'Voltage (V)': voltages[:len(currents)], 'Current (A)': currents})
        df.to_excel(save_path, index=False)
        print(f"Sweep complete. Data saved to {save_path}")
        self.status_label.setText("Status: Measurement Complete")

    def run_collection(self):
        self.config['bias_voltage'] = float(self.bias_input.text())
        self.config['aperture_time'] = float(self.aperture_input.text())
        self.config['noise_avg'] = int(self.noise_avg_input.value())
        self.config['delta_t'] = float(self.delta_t_collect.text())
        self.config['save_path'] = self.filepath_input.text()
        self.save_config()

        bias_v = self.config['bias_voltage']
        aperture = self.config['aperture_time']
        avg_points = self.config['noise_avg']
        delta_t = self.config['delta_t']

        save_path = self.config['save_path'] or f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        self.instrument.write(f":SOUR:VOLT {bias_v}")
        self.instrument.write(f":SENS:CURR:NPLC {aperture}")

        times = []
        currents = []
        start_time = time.time()

        while not self.stop_flag:
            readings = []
            for _ in range(avg_points):
                current = float(self.instrument.query(":MEAS:CURR?").strip())
                readings.append(current)
                time.sleep(delta_t)

            avg_current = np.mean(readings)
            elapsed = time.time() - start_time

            times.append(elapsed)
            currents.append(avg_current)

            if self.fast_acq_collect_checkbox.isChecked():
                self.plot_signal.emit(times, currents)

        df = pd.DataFrame({'Time (s)': times, 'Current (A)': currents})
        df.to_excel(save_path, index=False)
        print(f"Data collection complete. Data saved to {save_path}")
        self.status_label.setText("Status: Measurement Complete")

        if not self.fast_acq_collect_checkbox.isChecked():
            self.plot_signal.emit(times, currents)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = KeithleyGUI()
    gui.show()
    sys.exit(app.exec())
