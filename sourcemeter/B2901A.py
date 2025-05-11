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


class B2901AInstrument:
    def __init__(self, resource_name):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource_name)
        self.inst.timeout = 5000
        self.inst.write_termination = '\n'
        self.inst.read_termination = '\n'
        # Reset and configure basics for B2901A
        self.inst.write('*RST')
        self.inst.write('SYST:REM')                    # remote
        self.inst.write('OUTP OFF')                    # output off
        # Default source measure setup: voltage source, current measure
        self.inst.write('SOUR:FUNC VOLT')
        self.inst.write('SENS:FUNC "CURR"')
        self.inst.write('SENS:CURR:PROT 1e-3')          # 1 mA compliance
        # Format to return only current
        self.inst.write('FORM:DATA CURR')

    def write(self, cmd):
        return self.inst.write(cmd)

    def query(self, cmd):
        return self.inst.query(cmd)


class SMUGUI(QWidget):
    plot_signal = pyqtSignal(object, object)
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keysight B2901A Control Panel")
        self.setGeometry(100, 100, 1000, 750)

        self.load_config()
        self.simulation_mode = False
        self.instrument = None
        self.measurement_thread = None
        self.stop_flag = False

        self.init_ui()
        self.init_instrument()

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            defaults = {
                'save_path': '', 'delta_v': 0.1, 'delta_t': 0.1,
                'bias_voltage': 1.0, 'aperture_time': 1.0,
                'noise_avg': 1, 'start_v': -3.0, 'end_v': 3.0
            }
            for k, v in defaults.items():
                if k not in self.config:
                    self.config[k] = v
        except FileNotFoundError:
            self.config = {
                'save_path': '', 'delta_v': 0.1, 'delta_t': 0.1,
                'bias_voltage': 1.0, 'aperture_time': 1.0,
                'noise_avg': 1, 'start_v': -3.0, 'end_v': 3.0
            }

    def save_config(self):
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def init_instrument(self):
        try:
            # replace with your B2901A VISA resource string
            resource = "USB0::0x0957::0x8B18::MY12345678::INSTR"
            self.instrument = B2901AInstrument(resource)
            idn = self.instrument.query('*IDN?').strip()
            self.status_label.setText(f"B2901A detected: {idn}")
            self.simulation_checkbox.setChecked(False)
            self.simulation_mode = False
        except Exception as e:
            print(f"Instrument init failed, using simulation. {e}")
            self.instrument = SimulatedInstrument()
            self.simulation_mode = True
            self.simulation_checkbox.setChecked(True)
            self.status_label.setText("Status: Simulation Mode")

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        self.simulation_checkbox = QCheckBox("Simulation Mode (force)")
        self.simulation_checkbox.stateChanged.connect(self.toggle_simulation)
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
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.plot_signal.connect(self.update_plot)
        self.progress_signal.connect(self.update_progress)

        self.setup_sweep_tab()
        self.setup_collect_tab()

    def toggle_simulation(self):
        if self.simulation_checkbox.isChecked():
            self.instrument = SimulatedInstrument()
            self.status_label.setText("Status: Simulation Mode")
            self.simulation_mode = True
        else:
            self.init_instrument()

    def setup_sweep_tab(self):
        # similar layout code
        layout = QVBoxLayout()
        self.start_v_input = QLineEdit(str(self.config['start_v']))
        self.end_v_input = QLineEdit(str(self.config['end_v']))
        self.delta_v_input = QLineEdit(str(self.config['delta_v']))
        self.delta_t_input = QLineEdit(str(self.config['delta_t']))
        layout.addWidget(QLabel("Start Voltage (V):")); layout.addWidget(self.start_v_input)
        layout.addWidget(QLabel("End Voltage (V):")); layout.addWidget(self.end_v_input)
        layout.addWidget(QLabel("Voltage Step (V):")); layout.addWidget(self.delta_v_input)
        layout.addWidget(QLabel("Time Step (s):")); layout.addWidget(self.delta_t_input)
        btn_layout = QVBoxLayout()
        sweep_btn = QPushButton("Start Sweep"); sweep_btn.clicked.connect(self.start_sweep)
        stop_btn = QPushButton("Stop"); stop_btn.clicked.connect(self.stop_measurement)
        btn_layout.addWidget(sweep_btn); btn_layout.addWidget(stop_btn)
        layout.addLayout(btn_layout)
        self.sweep_filepath_input = QLineEdit(self.config['save_path'])
        browse = QPushButton("Browse..."); browse.clicked.connect(self.browse_file_sweep)
        layout.addWidget(QLabel("Save File (Sweep):")); layout.addWidget(self.sweep_filepath_input)
        layout.addWidget(browse)
        self.tab_sweep.setLayout(layout)

    def setup_collect_tab(self):
        layout = QVBoxLayout()
        self.bias_input = QLineEdit(str(self.config['bias_voltage']))
        self.aperture_input = QLineEdit(str(self.config['aperture_time']))
        self.noise_avg_input = QSpinBox(); self.noise_avg_input.setValue(self.config['noise_avg'])
        self.delta_t_collect = QLineEdit(str(self.config['delta_t']))
        self.filepath_input = QLineEdit(self.config['save_path'])
        browse = QPushButton("Browse..."); browse.clicked.connect(self.browse_file)
        layout.addWidget(QLabel("Bias Voltage (V):")); layout.addWidget(self.bias_input)
        layout.addWidget(QLabel("Aperture Time (PLC):")); layout.addWidget(self.aperture_input)
        layout.addWidget(QLabel("Noise-Average Points:")); layout.addWidget(self.noise_avg_input)
        layout.addWidget(QLabel("Δt (s):")); layout.addWidget(self.delta_t_collect)
        layout.addWidget(QLabel("Save File:")); layout.addWidget(self.filepath_input)
        layout.addWidget(browse)
        self.fast_acq_collect_checkbox = QCheckBox("Enable Fast Acquisition (Real-Time Plot)")
        layout.addWidget(self.fast_acq_collect_checkbox)
        start_btn = QPushButton("Start Collection"); start_btn.clicked.connect(self.start_collection)
        stop_btn = QPushButton("Stop"); stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(start_btn); layout.addWidget(stop_btn)
        self.tab_collect.setLayout(layout)

    def update_plot(self, x, y):
        self.ax.clear()
        xlabel = "Voltage (V)" if self.tabs.currentIndex() == 0 else "Time (s)"
        self.ax.set_xlabel(xlabel); self.ax.set_ylabel("Current (A)")
        self.ax.plot(x, y, 'o-')
        self.canvas.draw()

    def update_progress(self, val): self.progress.setValue(val)

    def browse_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel (*.xlsx);;CSV (*.csv)")
        if path: self.filepath_input.setText(path)

    def browse_file_sweep(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Sweep File", "", "Excel (*.xlsx)")
        if path: self.sweep_filepath_input.setText(path)

    def start_sweep(self):
        self.stop_flag = False
        self.ax.clear(); self.ax.set_xlabel("Voltage (V)"); self.ax.set_ylabel("Current (A)")
        self.status_label.setText("Status: Measuring...")
        self.measurement_thread = threading.Thread(target=self.run_sweep)
        self.measurement_thread.start()

    def run_sweep(self):
        # load params
        sv = float(self.start_v_input.text()); ev = float(self.end_v_input.text())
        dv = float(self.delta_v_input.text()); dt = float(self.delta_t_input.text())
        self.config.update({'start_v': sv, 'end_v': ev, 'delta_v': dv, 'delta_t': dt}); self.save_config()
        if dv == 0:
            self.status_label.setText("Error: ΔV cannot be zero."); return
        forward = np.arange(sv, ev+dv, dv); reverse = np.arange(ev, sv-dv, -dv)
        volts = np.concatenate((forward, reverse)); currents=[]
        self.progress_signal.emit(len(volts)); self.status_label.setText("Status: Measuring...")
        for i, v in enumerate(volts):
            if self.stop_flag: break
            self.instrument.write(f"SOUR:VOLT {v}")
            self.instrument.write("INIT")
            time.sleep(dt)
            curr = float(self.instrument.query("MEAS:CURR?").strip())
            currents.append(curr)
            self.progress_signal.emit(i+1)
        self.plot_signal.emit(volts[:len(currents)], currents)
        path = self.sweep_filepath_input.text() or f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        pd.DataFrame({'V': volts[:len(currents)], 'I': currents}).to_excel(path, index=False)
        self.status_label.setText("Status: Sweep Complete")

    def start_collection(self):
        self.stop_flag = False
        self.ax.clear(); self.ax.set_xlabel("Time (s)"); self.ax.set_ylabel("Current (A)")
        self.status_label.setText("Status: Measuring...")
        self.measurement_thread = threading.Thread(target=self.run_collection)
        self.measurement_thread.start()

    def run_collection(self):
        bv = float(self.bias_input.text()); plc = float(self.aperture_input.text())
        avg_p = int(self.noise_avg_input.value()); dt = float(self.delta_t_collect.text())
        sp = self.filepath_input.text() or f"collect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.config.update({'bias_voltage': bv, 'aperture_time': plc, 'noise_avg': avg_p, 'delta_t': dt, 'save_path': sp}); self.save_config()
        self.instrument.write(f"SOUR:VOLT {bv}")
        self.instrument.write(f"SENS:CURR:NPLC {plc}")
        times, currents = [], []
        t0 = time.time()
        while not self.stop_flag:
            readings = []
            for _ in range(avg_p):
                readings.append(float(self.instrument.query("MEAS:CURR?").strip()))
                time.sleep(dt)
            avg_c = np.mean(readings); elapsed = time.time()-t0
            times.append(elapsed); currents.append(avg_c)
            if self.fast_acq_collect_checkbox.isChecked():
                self.plot_signal.emit(times, currents)
        pd.DataFrame({'Time': times, 'Current': currents}).to_excel(sp, index=False)
        if not self.fast_acq_collect_checkbox.isChecked():
            self.plot_signal.emit(times, currents)
        self.status_label.setText("Status: Collection Complete")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = SMUGUI()
    gui.show()
    sys.exit(app.exec())

