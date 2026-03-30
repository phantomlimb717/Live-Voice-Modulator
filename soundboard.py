# soundboard_pyside_v5_fixed_indent.py - Python Soundboard using PySide6
# FINAL REFACTOR: Uses PYNPUT & QMetaObject.invokeMethod
# Fixes dialog hotkey capture for modifiers.
# Includes revised _key_to_string for Ctrl key capture fix.

import sys
import os
import json
import threading
import time
from functools import partial
import copy
import traceback
import uuid

# --- PySide6 Imports ---
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QGridLayout, QScrollArea, QTabWidget,
        QDialog, QSlider, QComboBox, QDialogButtonBox, QFileDialog, QMenu,
        QStyleFactory, QMessageBox, QMenuBar, QInputDialog, QListWidget, QListWidgetItem,
        QSpinBox, QCheckBox, QDoubleSpinBox
    )
    # Added QMetaObject, Q_ARG, Signal, QThread
    from PySide6.QtCore import Qt, QTimer, QSize, QMetaObject, Slot, Q_ARG, QPoint, QThread, Signal
    from PySide6.QtGui import QAction, QPalette, QColor, QIcon
    _PYSIDE_LOADED = True
except ImportError as e:
    print(f"ERROR: PySide6 not found. Please install it: pip install PySide6\n{e}")
    _PYSIDE_LOADED = False
    try: import tkinter as tk; from tkinter import messagebox; root = tk.Tk(); root.withdraw(); messagebox.showerror("Missing PySide6", f"PySide6 not found:\n{e}\nPlease install: pip install PySide6"); root.destroy()
    except Exception: pass
    sys.exit(1)

# --- Audio & Effects ---
_AUDIO_LIBS_LOADED = False
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError
    try:
        import pedalboard
        _pb_reverb_ok = hasattr(pedalboard, 'Reverb')
        _pb_delay_ok = hasattr(pedalboard, 'Delay')
    except ImportError as pe:
        print(f"ERROR: Failed to import from pedalboard: {pe}. Effects disabled.")
        pedalboard = None
        _pb_reverb_ok = False
        _pb_delay_ok = False
    except Exception as pe_other:
        print(f"ERROR: Unexpected error importing pedalboard: {pe_other}. Effects disabled.")
        pedalboard = None
        _pb_reverb_ok = False
        _pb_delay_ok = False
    _AUDIO_LIBS_LOADED = True
    if pedalboard and not hasattr(pedalboard, 'Pedalboard'):
         print("ERROR: Critical 'Pedalboard' class missing from pedalboard library. Effects disabled.")
except ImportError as e:
     print(f"ERROR: Required audio library (sounddevice, soundfile, numpy, pydub) not found: {e}. Install requirements.")
     pedalboard = None
     _pb_reverb_ok = False
     _pb_delay_ok = False

# --- Hotkeys (Pynput) ---
_HOTKEY_LIB_LOADED = False
try:
    from pynput import keyboard as pynput_kb
    _HOTKEY_LIB_LOADED = True
    print("Info: Using 'pynput' for global hotkeys.")
except ImportError:
    print("Info: Optional 'pynput' library not found. Global hotkeys disabled. (pip install pynput)")
except Exception as e:
    print(f"WARNING: Failed to import 'pynput' library: {e}. Hotkeys disabled.")

# --- Tkinter Fallback ---
_TKINTER_LOADED = False
try: import tkinter as tk; from tkinter import messagebox; _TKINTER_LOADED = True
except ImportError: pass

# --- Configuration ---
CONFIG_FILENAME = "config.json"
DEFAULT_CONFIG = {
    "version": "1.0",
    "settings": { "scan_interval_minutes": 15, "output_device_name": "Default", "stop_all_hotkey": None, "grid_columns": 5 },
    "groups": [ {"id": "default", "name": "Default"} ],
    "sounds": []
}

# --- Utility Functions ---
def get_script_directory():
    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            app_dir = os.path.dirname(sys.executable)
        elif getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(app_dir, exist_ok=True)
        return app_dir
    except Exception as e: print(f"FATAL: Could not determine application directory: {e}"); return None

# --- Custom Widgets ---
class SoundButton(QPushButton):
    def __init__(self, sound_data, parent=None):
        super().__init__(sound_data.get("name", "Unnamed"), parent)
        self.sound_data = sound_data; self.sound_id = sound_data.get("id")
        self.file_missing = not sound_data.get("file_exists", True)
        self.setMinimumHeight(60); self.update_appearance()
    def set_file_missing(self, is_missing):
        if self.file_missing != is_missing: self.file_missing = is_missing; self.update_appearance()
    def update_appearance(self):
        base_style = "QPushButton { color: white; border: 1px solid #666; padding: 14px; font-size: 10pt; }"
        pressed_style = "QPushButton:pressed { background-color: #606060; }"
        hover_style = "QPushButton:hover { background-color: #5A5A5A; }"
        if self.file_missing: self.setStyleSheet(base_style + "QPushButton { background-color: #802020; border: 1px solid red; }" + pressed_style + hover_style)
        else: self.setStyleSheet(base_style + "QPushButton { background-color: #505050; }" + pressed_style + hover_style)
    def contextMenuEvent(self, event):
        main_window = self.window()
        if isinstance(main_window, SoundboardWindow) and hasattr(main_window, 'show_context_menu_for_sound'):
            main_window.show_context_menu_for_sound(self.sound_id, self, event.globalPos())

# --- Dialog Classes ---
class EditSoundDialog(QDialog):
    def __init__(self, sound_data, groups, parent=None):
        super().__init__(parent); self.sound_data_original = sound_data; self.sound_data_edited = copy.deepcopy(sound_data); self.groups = groups
        self.setWindowTitle(f"Edit Properties: {sound_data.get('name', '')}"); self.setMinimumWidth(450)
        self.layout = QVBoxLayout(self); form_layout = QtWidgets.QFormLayout()
        self.name_input = QLineEdit(self.sound_data_edited.get('name', '')); form_layout.addRow("Sound Name:", self.name_input)
        volume_layout = QHBoxLayout(); self.volume_slider = QSlider(Qt.Orientation.Horizontal); self.volume_slider.setRange(0, 150); self.volume_slider.setValue(int(self.sound_data_edited.get('volume', 1.0) * 100))
        self.volume_label = QLabel(f"{self.sound_data_edited.get('volume', 1.0):.2f}"); self.volume_slider.valueChanged.connect(lambda val: self.volume_label.setText(f"{val / 100.0:.2f}"))
        volume_layout.addWidget(self.volume_slider); volume_layout.addWidget(self.volume_label); form_layout.addRow("Volume:", volume_layout)
        self.group_combo = QComboBox(); current_group_index = 0
        for i, group in enumerate(self.groups): self.group_combo.addItem(group['name'], userData=group['id']);
        if group['id'] == self.sound_data_edited.get('group_id', 'default'): current_group_index = i
        self.group_combo.setCurrentIndex(current_group_index); form_layout.addRow("Group:", self.group_combo)
        self.layout.addLayout(form_layout); self.layout.addWidget(QLabel("--- Effects ---")); self.effects_widgets = {}; effects_layout = QVBoxLayout()
        defined_effects = []
        if _AUDIO_LIBS_LOADED:
            if _pb_reverb_ok: defined_effects.append("Reverb")
            if _pb_delay_ok: defined_effects.append("Delay")
        current_effects_list = self.sound_data_edited.get('effects', [])
        current_effects_map = {fx.get('type'): fx for fx in current_effects_list}
        updated_effects_list = []
        for fx_type in defined_effects:
            if fx_type in current_effects_map:
                updated_effects_list.append(current_effects_map[fx_type])
            else:
                default_params = {}
                if fx_type == "Reverb": default_params = {"room_size": 0.5}
                elif fx_type == "Delay": default_params = {"delay_seconds": 0.3, "feedback": 0.4}
                updated_effects_list.append({"type": fx_type, "enabled": False, "params": default_params})
        self.sound_data_edited['effects'] = updated_effects_list
        for effect_data in self.sound_data_edited['effects']:
            fx_type = effect_data.get("type")
            if fx_type not in defined_effects: continue
            fx_box = QHBoxLayout(); fx_enable_cb = QCheckBox(fx_type); fx_enable_cb.setChecked(effect_data.get("enabled", False)); fx_box.addWidget(fx_enable_cb); self.effects_widgets[fx_type] = {'enable': fx_enable_cb, 'params': {}}
            params_layout = QHBoxLayout()
            if fx_type == "Reverb":
                params_layout.addWidget(QLabel("Room Size:")); slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(0, 100); slider.setValue(int(effect_data.get("params", {}).get("room_size", 0.5) * 100)); label = QLabel(f"{slider.value()/100.0:.2f}")
                slider.valueChanged.connect(lambda val, l=label: l.setText(f"{val/100.0:.2f}")); params_layout.addWidget(slider); params_layout.addWidget(label); self.effects_widgets[fx_type]['params']['room_size'] = {'widget': slider, 'label': label}
            elif fx_type == "Delay":
                params_layout.addWidget(QLabel("Delay (s):")); spinbox = QDoubleSpinBox(); spinbox.setRange(0.0, 5.0); spinbox.setSingleStep(0.05); spinbox.setDecimals(2); spinbox.setValue(effect_data.get("params", {}).get("delay_seconds", 0.5)); params_layout.addWidget(spinbox); self.effects_widgets[fx_type]['params']['delay_seconds'] = {'widget': spinbox}
                params_layout.addWidget(QLabel("Feedback:")); slider_fb = QSlider(Qt.Orientation.Horizontal); slider_fb.setRange(0, 95); slider_fb.setValue(int(effect_data.get("params", {}).get("feedback", 0.3) * 100)); label_fb = QLabel(f"{slider_fb.value()/100.0:.2f}")
                slider_fb.valueChanged.connect(lambda val, l=label_fb: l.setText(f"{val/100.0:.2f}")); params_layout.addWidget(slider_fb); params_layout.addWidget(label_fb); self.effects_widgets[fx_type]['params']['feedback'] = {'widget': slider_fb, 'label': label_fb}
            fx_box.addLayout(params_layout); effects_layout.addLayout(fx_box)
        self.layout.addLayout(effects_layout); self.layout.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel); self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject); self.layout.addWidget(self.button_box)
    def accept(self):
        self.sound_data_edited['name'] = self.name_input.text(); self.sound_data_edited['volume'] = round(self.volume_slider.value() / 100.0, 3); self.sound_data_edited['group_id'] = self.group_combo.currentData()
        updated_effects = []
        for effect_data in self.sound_data_edited.get('effects', []):
            fx_type = effect_data.get('type')
            if fx_type in self.effects_widgets:
                widgets = self.effects_widgets[fx_type]
                new_effect_data = copy.deepcopy(effect_data)
                new_effect_data['enabled'] = widgets['enable'].isChecked()
                if fx_type == "Reverb": new_effect_data['params']['room_size'] = round(widgets['params']['room_size']['widget'].value() / 100.0, 3)
                elif fx_type == "Delay":
                    new_effect_data['params']['delay_seconds'] = round(widgets['params']['delay_seconds']['widget'].value(), 3)
                    new_effect_data['params']['feedback'] = round(widgets['params']['feedback']['widget'].value() / 100.0, 3)
                updated_effects.append(new_effect_data)
            else:
                updated_effects.append(effect_data)
        self.sound_data_edited['effects'] = updated_effects
        self.changes_made = (self.sound_data_edited != self.sound_data_original)
        if self.changes_made:
            self.sound_data_original.clear()
            self.sound_data_original.update(self.sound_data_edited)
        super().accept()
    def get_updated_sound_data(self):
        return self.sound_data_original if self.result() == QDialog.DialogCode.Accepted and hasattr(self, 'changes_made') and self.changes_made else None

class AssignHotkeyDialog(QDialog):
    hotkey_captured_signal = Signal(str)

    def __init__(self, sound_data, parent=None):
        super().__init__(parent)
        self._main_window = parent
        self.sound_data = sound_data
        self.captured_hotkey_str = None
        self._dialog_listener = None
        self._dialog_current_modifiers = set()
        self._dialog_captured_key_obj = None # Store only the non-modifier key object

        self.setWindowTitle(f"Assign Hotkey: {sound_data.get('name', '')}")
        self.setFixedSize(350, 200)
        self.layout = QVBoxLayout(self)

        current_hk_str = sound_data.get('hotkey')
        self.current_label = QLabel(f"Current Hotkey: {current_hk_str or 'None'}")
        self.layout.addWidget(self.current_label)

        self.capture_label = QLabel("Click 'Set' then press desired key combination...")
        self.layout.addWidget(self.capture_label)

        self.live_capture_label = QLabel("")
        self.live_capture_label.setStyleSheet("QLabel { color: #AAAAAA; }")
        self.layout.addWidget(self.live_capture_label)
        self.layout.addStretch(1)

        button_layout = QHBoxLayout()
        self.set_button = QPushButton("Set Hotkey")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.clear_button = QPushButton("Clear Hotkey")
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.set_button); button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button); button_layout.addWidget(self.clear_button)
        self.layout.addLayout(button_layout)

        self.set_button.clicked.connect(self.start_capture)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.clear_button.clicked.connect(self.clear_hotkey)
        self.hotkey_captured_signal.connect(self._on_hotkey_captured)

    def _update_live_label(self):
        if not self._dialog_listener or not self._dialog_listener.is_alive():
            self.live_capture_label.setText("")
            return
        mods_str = '+'.join(sorted(list(self._dialog_current_modifiers)))
        # Use the *last captured non-modifier* key object for display
        key_str = self._main_window._key_to_string(self._dialog_captured_key_obj) if self._dialog_captured_key_obj else ""
        display_str = mods_str
        # Only add key_str if it's not empty and not itself a modifier we already listed
        if key_str and key_str not in self._dialog_current_modifiers:
            if display_str: display_str += f"+{key_str}"
            else: display_str = key_str
        self.live_capture_label.setText(f"Capturing: {display_str}...")

    def _dialog_on_press(self, key):
        try:
            if key == pynput_kb.Key.esc:
                print("[DialogHotkey] Esc pressed, cancelling capture.")
                if self._dialog_listener: self._dialog_listener.stop() # Stop listener first
                # Ensure UI updates happen after listener might have stopped
                QTimer.singleShot(0, lambda: self.capture_label.setText("Capture cancelled."))
                QTimer.singleShot(0, self.live_capture_label.clear)
                QTimer.singleShot(0, lambda: self.set_button.setEnabled(True))
                QTimer.singleShot(0, lambda: self.ok_button.setEnabled(False))
                return False # Stop listener processing

            # Use the REVISED _key_to_string from the main window
            key_str = self._main_window._key_to_string(key)
            if not key_str:
                # The revised _key_to_string might return "vk_XXX", don't ignore those
                if key_str is None: # Only ignore if it explicitly returned None
                    print(f"[DialogHotkey] Ignored unknown key (returned None): {key}")
                    return # Ignore unknown keys, keep listener running
                # Else: If key_str is like "vk_XXX", we'll proceed below

            # Use canonical names for checking if it's a modifier
            is_modifier = self._main_window.MODIFIER_MAP.get(key_str, key_str) in self._main_window.CANONICAL_MODIFIERS

            if is_modifier:
                mod_name = self._main_window.MODIFIER_MAP.get(key_str, key_str)
                self._dialog_current_modifiers.add(mod_name)
                self._dialog_captured_key_obj = None # Reset main key if only modifier pressed
                print(f"[DialogHotkey] Modifier pressed: {mod_name}, Current: {self._dialog_current_modifiers}")
            else:
                # --- Non-modifier key pressed: THIS IS THE CAPTURE MOMENT ---
                self._dialog_captured_key_obj = key # Store the non-modifier key object
                print(f"[DialogHotkey] Non-modifier pressed: {key_str}, Modifiers held: {self._dialog_current_modifiers}")

                # Generate the canonical string using CURRENT modifiers and the key just pressed
                canonical_str = self._main_window._hotkey_to_string(
                    self._dialog_current_modifiers,
                    self._dialog_captured_key_obj
                )
                print(f"[DialogHotkey] Attempting Combination capture: {canonical_str}")

                if canonical_str: # Ensure a valid string was generated (e.g., not just modifier)
                    # Emit signal TO main thread for UI update and conflict check
                    self.hotkey_captured_signal.emit(canonical_str)
                else:
                    # This can happen if _key_to_string returned "vk_XXX" and _hotkey_to_string rejected it
                    # or if only modifiers were somehow involved in the key_obj check
                    print(f"[DialogHotkey] Invalid key combination generated from key '{key_str}' (Result: {canonical_str}).")
                    QTimer.singleShot(0, lambda: self.capture_label.setText("Invalid combination. Press keys again..."))
                    QTimer.singleShot(0, self.live_capture_label.clear)
                    # Don't stop listener here, let user try again or press Esc

                # Stop the listener *only if* a valid non-modifier was captured resulting in a canonical string
                if canonical_str:
                    return False # Stop listener processing

            # Update live label if listener is still running
            if self._dialog_listener and self._dialog_listener.is_alive():
                self._update_live_label()

        except Exception as e:
            print(f"[DialogHotkey] Error in _dialog_on_press: {e}")
            traceback.print_exc()
            if self._dialog_listener:
                try: self._dialog_listener.stop()
                except: pass
            # Use QTimer for UI updates from potential exceptions
            QTimer.singleShot(0, lambda: self.capture_label.setText(f"Error: {e}"))
            QTimer.singleShot(0, self.live_capture_label.clear)
            QTimer.singleShot(0, lambda: self.set_button.setEnabled(True))


    def _dialog_on_release(self, key):
        try:
            # Use the REVISED _key_to_string from the main window
            key_str = self._main_window._key_to_string(key)
            if not key_str: return # Includes None case

            # Use canonical name for checking/removing from the set
            mod_name = self._main_window.MODIFIER_MAP.get(key_str, key_str)
            self._dialog_current_modifiers.discard(mod_name) # Use discard

            # If the listener is still alive (i.e. we haven't captured the non-modifier yet)
            # update the live label to show released modifiers
            if self._dialog_listener and self._dialog_listener.is_alive():
                self._update_live_label()

            if key == pynput_kb.Key.esc: return False # Should be caught by on_press
        except Exception as e:
            print(f"[DialogHotkey] Error in _dialog_on_release: {e}")

    def start_capture(self):
        if not _HOTKEY_LIB_LOADED:
            self.capture_label.setText("Error: pynput library not loaded!"); return
        self.stop_capture_listener()
        self.capture_label.setText("Press desired key combination... (Esc to cancel)");
        self.live_capture_label.setText("Capturing...")
        self.set_button.setEnabled(False)
        self.ok_button.setEnabled(False)
        self.captured_hotkey_str = None
        self._dialog_current_modifiers = set()
        self._dialog_captured_key_obj = None
        QTimer.singleShot(50, self._start_listener_thread)

    def _start_listener_thread(self):
         try:
             self._dialog_listener = pynput_kb.Listener(
                 on_press=self._dialog_on_press,
                 on_release=self._dialog_on_release,
                 suppress=False # Do not suppress keys globally while dialog is open
             )
             self._dialog_listener.start()
             print("[DialogHotkey] Temporary listener started.")
         except Exception as e:
             print(f"[DialogHotkey] Failed to start listener: {e}")
             self.capture_label.setText("Error starting listener!")
             self.live_capture_label.setText("")
             self.set_button.setEnabled(True)

    def stop_capture_listener(self):
        if self._dialog_listener:
            print("[DialogHotkey] Stopping temporary listener...")
            try:
                # Stop the listener. No need to join typically.
                self._dialog_listener.stop()
            except Exception as e:
                print(f"[DialogHotkey] Error stopping listener: {e}")
            self._dialog_listener = None
            print("[DialogHotkey] Temporary listener stopped.")

    @Slot(str)
    def _on_hotkey_captured(self, canonical_str):
        # Ensure listener stopped (should be already by returning False)
        self.stop_capture_listener()
        self.captured_hotkey_str = canonical_str
        conflict = self._main_window.check_hotkey_conflict(self.captured_hotkey_str, self.sound_data.get('id'))
        if conflict:
            if conflict['type'] == 'sound':
                self.capture_label.setText(f"Conflict: '{canonical_str}' used by '{conflict['name']}'")
            elif conflict['type'] == 'stop_all':
                self.capture_label.setText(f"Conflict: '{canonical_str}' used by Stop All Sounds")
            self.ok_button.setEnabled(False)
            self.captured_hotkey_str = None # Prevent saving conflicting key
        else:
            self.capture_label.setText(f"Captured: {self.captured_hotkey_str}")
            self.ok_button.setEnabled(True)
        self.live_capture_label.setText("")
        self.set_button.setEnabled(True) # Re-enable Set button

    def clear_hotkey(self):
        self.stop_capture_listener()
        self.captured_hotkey_str = None
        self.capture_label.setText("Hotkey will be cleared.")
        self.live_capture_label.setText("")
        self.ok_button.setEnabled(True)
        self.set_button.setEnabled(True)

    def get_captured_hotkey(self):
        if self.result() == QDialog.DialogCode.Accepted:
            return self.captured_hotkey_str
        else:
            return "NO_CHANGE" # Special value indicating no acceptance/change

    def reject(self):
        print("[DialogHotkey] Dialog rejected.")
        self.stop_capture_listener()
        super().reject()

    def closeEvent(self, event):
        print("[DialogHotkey] Dialog close event.")
        self.stop_capture_listener()
        super().closeEvent(event)


class SettingsDialog(QDialog):
    hotkey_captured_signal = Signal(str)

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.settings_original = current_settings; self.settings_edited = copy.deepcopy(current_settings)
        self._main_window = parent
        self._dialog_listener = None
        self._dialog_current_modifiers = set()
        self._dialog_captured_key_obj = None
        self._capturing_stop_all = False

        self.setWindowTitle("Settings"); self.setMinimumWidth(400)
        self.layout = QVBoxLayout(self); form_layout = QtWidgets.QFormLayout()

        self.device_combo = QComboBox(); self.populate_devices(); form_layout.addRow("Audio Output Device:", self.device_combo)
        self.scan_spinbox = QSpinBox(); self.scan_spinbox.setRange(0, 1440); self.scan_spinbox.setValue(self.settings_edited.get('scan_interval_minutes', 15)); self.scan_spinbox.setSuffix(" minutes (0=disabled)"); form_layout.addRow("File Scan Interval:", self.scan_spinbox)
        self.columns_spinbox = QSpinBox(); self.columns_spinbox.setRange(1, 20); self.columns_spinbox.setValue(self.settings_edited.get('grid_columns', 5)); form_layout.addRow("Grid Columns:", self.columns_spinbox)

        self.stop_hotkey_layout = QHBoxLayout()
        current_stop_hk = self.settings_edited.get('stop_all_hotkey')
        self.stop_hotkey_label = QLabel(current_stop_hk or "None")
        self.set_stop_hk_button = QPushButton("Set Stop Hotkey"); self.set_stop_hk_button.clicked.connect(self.start_capture_stop_all)
        self.clear_stop_hk_button = QPushButton("Clear"); self.clear_stop_hk_button.clicked.connect(self.clear_stop_all_hotkey)
        self.stop_hotkey_layout.addWidget(self.stop_hotkey_label, 1); self.stop_hotkey_layout.addWidget(self.set_stop_hk_button); self.stop_hotkey_layout.addWidget(self.clear_stop_hk_button); form_layout.addRow("Stop All Hotkey:", self.stop_hotkey_layout)

        self.capture_status_label = QLabel("")
        self.capture_status_label.setStyleSheet("QLabel { color: #AAAAAA; }")
        form_layout.addRow(self.capture_status_label) # Add it below the hotkey row

        self.layout.addLayout(form_layout); self.layout.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject); self.layout.addWidget(self.button_box)

        self.hotkey_captured_signal.connect(self._on_stop_all_captured)

    def populate_devices(self):
        self.device_combo.clear(); self.device_combo.addItem("Default", userData=None); current_name = self.settings_edited.get('output_device_name', 'Default'); current_index = 0
        try:
            if not _AUDIO_LIBS_LOADED: raise RuntimeError("Audio library (sounddevice) not loaded.")
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_output_channels'] > 0:
                    self.device_combo.addItem(dev['name'], userData=dev['name']);
                    if dev['name'] == current_name: current_index = self.device_combo.count() - 1
        except Exception as e:
            print(f"Error querying audio devices: {e}"); self.device_combo.clear(); self.device_combo.addItem("Error loading devices", userData=None); self.device_combo.setEnabled(False)
        self.device_combo.setCurrentIndex(current_index)

    # Uses the same logic structure as AssignHotkeyDialog._dialog_on_press
    def _dialog_stop_all_on_press(self, key):
        if not self._capturing_stop_all: return

        try:
            if key == pynput_kb.Key.esc:
                if self._dialog_listener: self._dialog_listener.stop()
                QTimer.singleShot(0, lambda: self.capture_status_label.setText("Capture cancelled."))
                QTimer.singleShot(1500, self.capture_status_label.clear) # Clear after delay
                QTimer.singleShot(0, lambda: self.set_stop_hk_button.setEnabled(True))
                self._capturing_stop_all = False
                return False # Stop listener

            # Use the REVISED _key_to_string from the main window
            key_str = self._main_window._key_to_string(key)
            if not key_str:
                if key_str is None: # Only ignore if it explicitly returned None
                    print(f"[SettingsDialogHotkey] Ignored unknown key (returned None): {key}")
                    return
                # Else: proceed with "vk_XXX"

            # Use canonical names for checking if it's a modifier
            is_modifier = self._main_window.MODIFIER_MAP.get(key_str, key_str) in self._main_window.CANONICAL_MODIFIERS
            if is_modifier:
                mod_name = self._main_window.MODIFIER_MAP.get(key_str, key_str)
                self._dialog_current_modifiers.add(mod_name)
                self._dialog_captured_key_obj = None
                print(f"[SettingsDialogHotkey] Modifier pressed: {mod_name}, Current: {self._dialog_current_modifiers}")
                # Update live feedback
                mods_str = '+'.join(sorted(list(self._dialog_current_modifiers)))
                self.capture_status_label.setText(f"Capturing: {mods_str}...")
            else:
                # --- Non-modifier key pressed: CAPTURE MOMENT ---
                self._dialog_captured_key_obj = key
                print(f"[SettingsDialogHotkey] Non-modifier pressed: {key_str}, Modifiers held: {self._dialog_current_modifiers}")

                # Generate the canonical string using CURRENT modifiers and the key just pressed
                canonical_str = self._main_window._hotkey_to_string(
                    self._dialog_current_modifiers, self._dialog_captured_key_obj
                )
                print(f"[SettingsDialogHotkey] Attempting Combination capture: {canonical_str}")

                if canonical_str:
                    # Emit signal TO main thread for UI update and conflict check
                    self.hotkey_captured_signal.emit(canonical_str)
                else:
                    print(f"[SettingsDialogHotkey] Invalid key combination generated from key '{key_str}'.")
                    QTimer.singleShot(0, lambda: self.capture_status_label.setText("Invalid combination. Press keys again..."))
                    QTimer.singleShot(1500, self.capture_status_label.clear) # Clear message later
                    # Don't stop listener

                # Stop listener only if valid non-modifier captured resulting in a canonical string
                if canonical_str:
                    return False # Stop listener processing

            # Update live label if listener is still running (only shows modifiers)
            if self._dialog_listener and self._dialog_listener.is_alive():
                 mods_str = '+'.join(sorted(list(self._dialog_current_modifiers)))
                 self.capture_status_label.setText(f"Capturing: {mods_str}...")

        except Exception as e:
            print(f"[SettingsDialogHotkey] Error in _dialog_stop_all_on_press: {e}")
            traceback.print_exc()
            if self._dialog_listener:
                try: self._dialog_listener.stop()
                except: pass
            QTimer.singleShot(0, lambda: self.capture_status_label.setText(f"Capture Error: {e}"))
            QTimer.singleShot(0, lambda: self.set_stop_hk_button.setEnabled(True))
            self._capturing_stop_all = False


    # Uses the same logic structure as AssignHotkeyDialog._dialog_on_release
    def _dialog_stop_all_on_release(self, key):
        if not self._capturing_stop_all: return
        try:
            # Use the REVISED _key_to_string from the main window
            key_str = self._main_window._key_to_string(key)
            if not key_str: return

            mod_name = self._main_window.MODIFIER_MAP.get(key_str, key_str)
            self._dialog_current_modifiers.discard(mod_name)

            if key == pynput_kb.Key.esc: return False

            # Update live label if needed
            if self._dialog_listener and self._dialog_listener.is_alive():
                 mods_str = '+'.join(sorted(list(self._dialog_current_modifiers)))
                 # Only update if there are still modifiers held
                 if mods_str:
                    self.capture_status_label.setText(f"Capturing: {mods_str}...")
                 else:
                    self.capture_status_label.setText(f"Capturing: ...")


        except Exception as e:
            print(f"[SettingsDialogHotkey] Error in _dialog_stop_all_on_release: {e}")

    def start_capture_stop_all(self):
        if not _HOTKEY_LIB_LOADED:
            self.capture_status_label.setText("Error: pynput library not loaded!"); return
        self.stop_capture_listener() # Ensure any previous listener is stopped
        self._capturing_stop_all = True
        self.capture_status_label.setText("Press desired key combination... (Esc to cancel)");
        self.set_stop_hk_button.setEnabled(False)
        self._dialog_current_modifiers = set()
        self._dialog_captured_key_obj = None
        # Use a short delay before starting listener to avoid capturing the click
        QTimer.singleShot(50, self._start_listener_thread_stop_all)

    def _start_listener_thread_stop_all(self):
        try:
            self._dialog_listener = pynput_kb.Listener(
                on_press=self._dialog_stop_all_on_press,
                on_release=self._dialog_stop_all_on_release,
                suppress=False # Don't suppress keys
            )
            self._dialog_listener.start()
            print("[SettingsDialogHotkey] Temporary listener started for Stop All.")
        except Exception as e:
            print(f"[SettingsDialogHotkey] Failed to start listener: {e}")
            self.capture_status_label.setText("Error starting listener!")
            self.set_stop_hk_button.setEnabled(True)
            self._capturing_stop_all = False

    def stop_capture_listener(self):
        # Important: Always reset the capturing flag
        self._capturing_stop_all = False
        if self._dialog_listener:
            print("[SettingsDialogHotkey] Stopping temporary listener...")
            try:
                self._dialog_listener.stop()
            except Exception as e:
                print(f"[SettingsDialogHotkey] Error stopping listener: {e}")
            self._dialog_listener = None
            print("[SettingsDialogHotkey] Temporary listener stopped.")
        # Always ensure the button is re-enabled after stopping or attempting to stop
        self.set_stop_hk_button.setEnabled(True)


    @Slot(str)
    def _on_stop_all_captured(self, canonical_str):
        print(f"[SettingsDialogHotkey] Captured '{canonical_str}' via signal.")
        self.stop_capture_listener() # Ensure listener is stopped
        conflict = self._main_window.check_hotkey_conflict(canonical_str, None) # Check against sounds only
        if conflict and conflict['type'] == 'sound': # Only care about sound conflicts here
             QMessageBox.warning(self, "Hotkey Conflict", f"Hotkey '{canonical_str}' is already assigned to '{conflict['name']}'.")
             self.capture_status_label.setText(f"Conflict with '{conflict['name']}'!")
             QTimer.singleShot(2500, self.capture_status_label.clear)
        else:
             self.settings_edited['stop_all_hotkey'] = canonical_str
             self.stop_hotkey_label.setText(canonical_str)
             self.capture_status_label.setText(f"Stop All Hotkey set to: {canonical_str}")
             QTimer.singleShot(2500, self.capture_status_label.clear)
        # Button should be re-enabled by stop_capture_listener already

    def clear_stop_all_hotkey(self):
        self.stop_capture_listener() # Ensure listener stops if running
        self.settings_edited['stop_all_hotkey'] = None
        self.stop_hotkey_label.setText("None")
        self.capture_status_label.setText("Stop All hotkey cleared.")
        QTimer.singleShot(2000, self.capture_status_label.clear)

    def accept(self):
        self.stop_capture_listener() # Stop listener on accept
        selected_device_name = self.device_combo.currentData(); self.settings_edited['output_device_name'] = selected_device_name or "Default"; self.settings_edited['scan_interval_minutes'] = self.scan_spinbox.value(); self.settings_edited['grid_columns'] = self.columns_spinbox.value()
        self.changes_made = (self.settings_edited != self.settings_original);
        if self.changes_made:
            self.settings_original.clear()
            self.settings_original.update(self.settings_edited)
        super().accept()

    def get_updated_settings(self):
        return self.settings_original if self.result() == QDialog.DialogCode.Accepted and hasattr(self, 'changes_made') and self.changes_made else None

    def reject(self):
        print("[SettingsDialogHotkey] Dialog rejected.")
        self.stop_capture_listener()
        super().reject()

    def closeEvent(self, event):
        print("[SettingsDialogHotkey] Dialog close event.")
        self.stop_capture_listener()
        super().closeEvent(event)

class ManageGroupsDialog(QDialog):
    def __init__(self, current_groups, parent=None):
        super().__init__(parent); self.groups_original = current_groups; self.groups_edited = copy.deepcopy(current_groups); self._main_window = parent
        self.setWindowTitle("Manage Sound Groups"); self.setMinimumSize(350, 400); self.layout = QVBoxLayout(self); self.list_widget = QListWidget(); self.populate_list(); self.layout.addWidget(self.list_widget)
        button_layout = QHBoxLayout(); add_button = QPushButton("Add Group"); rename_button = QPushButton("Rename Selected"); delete_button = QPushButton("Delete Selected")
        button_layout.addWidget(add_button); button_layout.addWidget(rename_button); button_layout.addWidget(delete_button); self.layout.addLayout(button_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); self.layout.addWidget(self.button_box)
        add_button.clicked.connect(self.add_group); rename_button.clicked.connect(self.rename_group); delete_button.clicked.connect(self.delete_group); self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
    def populate_list(self):
        self.list_widget.clear()
        for group in self.groups_edited:
            item = QListWidgetItem(group.get('name', 'Unnamed')); item.setData(Qt.ItemDataRole.UserRole, group.get('id'))
            if group.get('id') == 'default': item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable & ~Qt.ItemFlag.ItemIsEnabled); item.setForeground(QColor("grey"))
            self.list_widget.addItem(item)
    def add_group(self):
        text, ok = QInputDialog.getText(self, "Add Group", "Enter new group name:");
        if ok and text: name = text.strip();
        if name and not any(g['name'].lower() == name.lower() for g in self.groups_edited): new_id = f"group_{uuid.uuid4().hex[:8]}"; self.groups_edited.append({"id": new_id, "name": name}); self.populate_list()
        elif name: QMessageBox.warning(self, "Add Group", "Group name already exists.")
    def rename_group(self):
        currentItem = self.list_widget.currentItem()
        if not currentItem or currentItem.data(Qt.ItemDataRole.UserRole) == 'default': QMessageBox.warning(self, "Rename Group", "Cannot rename default or no group selected."); return
        current_id = currentItem.data(Qt.ItemDataRole.UserRole); current_name = currentItem.text(); text, ok = QInputDialog.getText(self, "Rename Group", "Enter new name:", QLineEdit.EchoMode.Normal, current_name)
        if ok and text: new_name = text.strip();
        if new_name and new_name.lower() != 'default' and not any(g['name'].lower() == new_name.lower() and g['id'] != current_id for g in self.groups_edited):
            for group in self.groups_edited:
                if group['id'] == current_id: group['name'] = new_name; break
            self.populate_list()
        elif not new_name: QMessageBox.warning(self, "Rename Group", "Group name cannot be empty.")
        elif new_name.lower() == 'default': QMessageBox.warning(self, "Rename Group", "Cannot rename group to 'Default'.")
        else: QMessageBox.warning(self, "Rename Group", "Group name already exists.")
    def delete_group(self):
        currentItem = self.list_widget.currentItem()
        if not currentItem or currentItem.data(Qt.ItemDataRole.UserRole) == 'default': QMessageBox.warning(self, "Delete Group", "Cannot delete default or no group selected."); return
        current_id = currentItem.data(Qt.ItemDataRole.UserRole); current_name = currentItem.text(); reply = QMessageBox.question(self, 'Confirm Delete', f"Delete group '{current_name}'?\nSounds in this group will move to 'Default'.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.groups_edited = [g for g in self.groups_edited if g['id'] != current_id]; self.populate_list()
            if not hasattr(self, 'deleted_group_ids'): self.deleted_group_ids = set()
            self.deleted_group_ids.add(current_id)
    def accept(self):
        deleted_ids = getattr(self, 'deleted_group_ids', set())
        self.changes_made = (self.groups_edited != self.groups_original or bool(deleted_ids))
        if self.changes_made and bool(deleted_ids) and self._main_window and hasattr(self._main_window, 'config'):
            print(f"Moving sounds from deleted groups {deleted_ids} to default...")
            main_app_sounds = self._main_window.config.get('sounds', [])
            for sound in main_app_sounds:
                if sound.get('group_id') in deleted_ids:
                    print(f" -> Moving sound '{sound.get('name')}'")
                    sound['group_id'] = 'default'
        super().accept()
    def get_updated_groups(self):
        return self.groups_edited if self.result() == QDialog.DialogCode.Accepted and hasattr(self, 'changes_made') and self.changes_made else None


# --- Main Application Window ---
class SoundboardWindow(QMainWindow):

    # --- Constants for Hotkey Handling ---
    MODIFIER_KEYS = { # Used to identify modifier keys by their canonical string
        'alt', 'ctrl', 'shift', 'cmd' # Canonical names only
    }
    MODIFIER_MAP = { # Map variants to a single canonical name
        'alt_l': 'alt', 'alt_r': 'alt', 'alt_gr': 'alt',
        'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
        'shift_l': 'shift', 'shift_r': 'shift',
        'cmd_l': 'cmd', 'cmd_r': 'cmd', 'win_l': 'cmd', 'win_r': 'cmd', 'win': 'cmd'
    }
    CANONICAL_MODIFIERS = frozenset(MODIFIER_MAP.values())

    def __init__(self):
        super().__init__()
        self.config = {}; self.active_playback_threads = []; self.sound_buttons = {}
        self._pynput_listener = None
        self._current_modifiers = set()
        self._hotkey_map = {}
        self._stop_all_hotkey_str = None
        self._file_check_event = None; self._current_popup = None
        self._tk_root = None
        self.load_config()
        self.setWindowTitle("Live Soundboard v1.0"); self.setGeometry(100, 100, 800, 600); self.setMinimumSize(600, 400)
        self._setup_ui()
        self.apply_dark_theme()
        self.file_check_timer = QTimer(self); self.file_check_timer.timeout.connect(self.check_files)
        self.populate_groups_and_sounds()
        self.start_file_integrity_check()
        self.setup_hotkeys()
        self.update_status("Ready.")

    def _setup_ui(self):
        self.menu_bar = self.menuBar(); file_menu = self.menu_bar.addMenu("&File")
        settings_action = QAction("&Settings", self); settings_action.triggered.connect(self.open_settings_dialog)
        backup_action = QAction("&Backup Config", self); backup_action.triggered.connect(self.backup_config)
        restore_action = QAction("&Restore Config", self); restore_action.triggered.connect(self.restore_config)
        exit_action = QAction("&Exit", self); exit_action.triggered.connect(self.close)
        file_menu.addAction(settings_action); file_menu.addSeparator(); file_menu.addAction(backup_action); file_menu.addAction(restore_action); file_menu.addSeparator(); file_menu.addAction(exit_action)
        edit_menu = self.menu_bar.addMenu("&Edit"); manage_groups_action = QAction("Manage &Groups", self); manage_groups_action.triggered.connect(self.open_manage_groups_dialog); edit_menu.addAction(manage_groups_action)
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget); self.main_layout = QVBoxLayout(self.central_widget); self.main_layout.setContentsMargins(5, 5, 5, 5); self.main_layout.setSpacing(5)
        top_bar_layout = QHBoxLayout(); self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search sounds in current tab...")
        self.search_input.textChanged.connect(self.filter_sounds); self.add_button = QPushButton("Add Sound(s)"); self.add_button.setFixedWidth(120); self.add_button.clicked.connect(self.add_sound_dialog)
        top_bar_layout.addWidget(self.search_input); top_bar_layout.addWidget(self.add_button); self.main_layout.addLayout(top_bar_layout)
        self.tab_widget = QTabWidget(); self.tab_widget.setMinimumHeight(200); self.tab_widget.currentChanged.connect(self.on_tab_changed); self.main_layout.addWidget(self.tab_widget, stretch=1)
        self.status_label = QLabel("Status: Initializing..."); self.statusBar().addPermanentWidget(self.status_label)
        self.stop_button = QPushButton("Stop All Sounds"); self.stop_button.setStyleSheet("background-color: #A03030; color: white;"); self.stop_button.clicked.connect(self.stop_all_sounds)
        self.main_layout.addWidget(self.stop_button)

    def apply_dark_theme(self):
        # Apply a dark theme using QSS
        self.setStyleSheet(""" QWidget{background-color:#222;color:#DDD}QMainWindow::separator{background-color:#444;width:1px;height:1px}QMenuBar,QMenu{background-color:#333;color:#DDD}QMenuBar::item:selected,QMenu::item:selected{background-color:#555}QPushButton{background-color:#505050;color:#FFF;border:1px solid #666;padding:5px;min-height:20px}QPushButton:hover{background-color:#5A5A5A}QPushButton:pressed{background-color:#606060}QLineEdit,QTextEdit,QPlainTextEdit,QSpinBox,QDoubleSpinBox{background-color:#333;color:#DDD;border:1px solid #666}QTabWidget::pane{border-top:1px solid #444;background-color:#282828}QTabBar::tab{background:#444;color:#CCC;border:1px solid #555;border-bottom:none;padding:5px 10px;margin-right:2px}QTabBar::tab:selected{background:#555;color:#FFF;margin-bottom:-1px}QTabBar::tab:hover{background:#5A5A5A}QScrollArea{border:none}QScrollBar:vertical{border:none;background:#282828;width:10px;margin:0}QScrollBar::handle:vertical{background:#555;min-height:20px}QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px}QScrollBar:horizontal{border:none;background:#282828;height:10px;margin:0}QScrollBar::handle:horizontal{background:#555;min-width:20px}QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0px}QSlider::groove:horizontal{border:1px solid #555;height:8px;background:#333}QSlider::handle:horizontal{background:#777;border:1px solid #555;width:18px;margin:-2px 0;border-radius:3px}QComboBox{border:1px solid #666;background-color:#333;padding: 2px;}QComboBox::drop-down{border:none;background-color:#505050;width: 15px;}QComboBox::down-arrow{image: url(noimg.png); width: 10px; height: 10px;} QComboBox QAbstractItemView{border:1px solid #666;background-color:#333;color:#DDD;selection-background-color:#555}QStatusBar{background-color:#333;color:#DDD}QMenu{border:1px solid #555}QDialog{background-color:#282828}QListWidget{border:1px solid #666;background-color:#333;} QListWidget::item{padding: 3px;} QListWidget::item:selected{background-color:#555;} """)

    # --- Slots and Methods ---
    @Slot()
    def filter_sounds(self):
        search_term = self.search_input.text().lower(); current_tab_widget = self.tab_widget.currentWidget();
        if not current_tab_widget: return
        scroll_area = current_tab_widget.findChild(QScrollArea);
        if not scroll_area or not scroll_area.widget(): return
        grid_container = scroll_area.widget(); grid_layout = grid_container.layout()
        if not isinstance(grid_layout, QGridLayout): return
        for i in range(grid_layout.count()):
            widget = grid_layout.itemAt(i).widget()
            if isinstance(widget, SoundButton): widget.setVisible(not search_term or search_term in widget.sound_data.get('name', '').lower())

    @Slot(int)
    def on_tab_changed(self, index):
        self.filter_sounds() # Re-apply filter when tab changes

    @Slot()
    def open_settings_dialog(self):
        print("Attempting to open Settings dialog...")
        # Pass a copy for editing, original is updated only on accept+changes
        dialog = SettingsDialog(copy.deepcopy(self.config.get('settings', {})), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_settings = dialog.get_updated_settings()
            if updated_settings:
                print("Applying updated settings...");
                self.config['settings'] = updated_settings # Update main config dict
                self.save_config();
                self.start_file_integrity_check(); # Restart timer if interval changed
                self.populate_groups_and_sounds(); # Repopulate if columns changed
                self.setup_hotkeys() # Re-setup if stop_all hotkey changed
            else:
                print("Settings dialog accepted, but no changes detected.")
        else:
            print("Settings dialog cancelled.")

    @Slot()
    def open_manage_groups_dialog(self):
        # Pass a copy for editing
        dialog = ManageGroupsDialog(copy.deepcopy(self.config.get('groups', [])), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_groups = dialog.get_updated_groups()
            if updated_groups:
                print("Applying updated groups...");
                self.config['groups'] = updated_groups # Update main config dict
                # Note: Moving sounds from deleted groups is handled within the Dialog's accept()
                self.save_config();
                self.populate_groups_and_sounds() # Repopulate tabs
            else:
                print("Manage Groups dialog accepted, but no changes detected.")
        else:
            print("Manage Groups dialog cancelled.")

    @Slot()
    def backup_config(self):
        dialog = QFileDialog(self); dialog.setWindowTitle("Backup Configuration"); dialog.setFileMode(QFileDialog.FileMode.AnyFile); dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave); dialog.setNameFilter("JSON Files (*.json)"); dialog.setDefaultSuffix("json"); current_time_str = time.strftime("%Y%m%d_%H%M%S"); dialog.selectFile(f"soundboard_backup_{current_time_str}.json")
        if dialog.exec():
            filepath = dialog.selectedFiles()[0]; print(f"Backing up config to: {filepath}")
            try:
                config_to_save = self._prepare_config_for_saving()
                with open(filepath, 'w', encoding='utf-8') as f: json.dump(config_to_save, f, indent=4, ensure_ascii=False)
                self.update_status(f"Backup successful: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"Error during backup: {e}"); self.show_error_popup("Backup Error", f"Could not save backup to\n{filepath}\n\nError: {e}")

    @Slot()
    def restore_config(self):
        reply = QMessageBox.warning(self, 'Confirm Restore', "Restore config?\nThis will overwrite current settings and sounds!", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return
        dialog = QFileDialog(self); dialog.setWindowTitle("Restore Configuration"); dialog.setFileMode(QFileDialog.FileMode.ExistingFile); dialog.setNameFilter("JSON Files (*.json)")
        if dialog.exec():
            filepath = dialog.selectedFiles()[0]; print(f"Attempting restore from: {filepath}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f: loaded_config = json.load(f)
                # Basic validation
                if not isinstance(loaded_config, dict) or "version" not in loaded_config or "settings" not in loaded_config or "groups" not in loaded_config or "sounds" not in loaded_config:
                    raise ValueError("Invalid or incomplete config file format.")

                self._stop_hotkey_listener() # Stop listener before changing config
                self.stop_all_sounds() # Stop sounds
                time.sleep(0.1) # Brief pause

                self.config = loaded_config; # Replace current config

                # Ensure default settings exist if missing in loaded config
                temp_settings = copy.deepcopy(DEFAULT_CONFIG.get("settings", {}))
                temp_settings.update(self.config.get("settings", {})) # Overwrite defaults with loaded
                self.config["settings"] = temp_settings

                # Ensure default group exists
                if not any(g.get('id') == 'default' for g in self.config.get('groups', [])):
                    self.config.setdefault('groups', []).insert(0, {"id": "default", "name": "Default"})

                self.config.setdefault("sounds", []) # Ensure sounds list exists

                self._resolve_sound_paths() # Resolve paths for the newly loaded config
                self.save_config(); # Save the potentially modified restored config immediately
                self.populate_groups_and_sounds(); # Refresh UI
                self.setup_hotkeys(); # Setup hotkeys based on new config
                self.start_file_integrity_check() # Restart file checker
                self.update_status(f"Config restored from {os.path.basename(filepath)}")
            except json.JSONDecodeError as e_json:
                print(f"Error during restore (JSON Decode): {e_json}"); self.show_error_popup("Restore Error", f"Could not decode JSON config from\n{filepath}\n\nError: {e_json}")
            except ValueError as e_val:
                 print(f"Error during restore (Validation): {e_val}"); self.show_error_popup("Restore Error", f"Invalid config file format in\n{filepath}\n\nError: {e_val}")
            except Exception as e:
                 print(f"Error during restore: {e}"); traceback.print_exc(); self.show_error_popup("Restore Error", f"Could not restore config from\n{filepath}\n\nError: {e}")

    # --- Config Handling ---
    def load_config(self):
        print("Loading configuration...")
        config_path = self._get_config_path(); loaded_config = None
        if not config_path: print("ERROR: Config path could not be determined."); loaded_config = copy.deepcopy(DEFAULT_CONFIG)
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f: loaded_config = json.load(f)
                print(f"Config loaded successfully from {config_path}")
            except FileNotFoundError:
                print(f"Config file not found at {config_path}. Using default."); loaded_config = copy.deepcopy(DEFAULT_CONFIG)
                try: # Attempt to save the default config if it didn't exist
                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    with open(config_path, 'w', encoding='utf-8') as f: json.dump(loaded_config, f, indent=4, ensure_ascii=False)
                    print("Saved default config file.")
                except Exception as e_save: print(f"Error saving initial default config: {e_save}");
            except json.JSONDecodeError as e: print(f"Error decoding JSON from {config_path}: {e}. Using default."); loaded_config = copy.deepcopy(DEFAULT_CONFIG)
            except Exception as e: print(f"Error loading config from {config_path}: {e}. Using default."); loaded_config = copy.deepcopy(DEFAULT_CONFIG)

        # Ensure essential keys exist and merge settings with defaults
        loaded_config.setdefault("settings", copy.deepcopy(DEFAULT_CONFIG["settings"]))
        loaded_config.setdefault("groups", copy.deepcopy(DEFAULT_CONFIG["groups"]))
        loaded_config.setdefault("sounds", copy.deepcopy(DEFAULT_CONFIG["sounds"]))

        # Ensure all default settings keys are present
        default_settings = DEFAULT_CONFIG.get("settings", {})
        current_settings = loaded_config.get("settings", {})
        for key, default_value in default_settings.items():
            current_settings.setdefault(key, default_value)
        loaded_config["settings"] = current_settings

        # Ensure default group exists
        if not any(g.get('id') == 'default' for g in loaded_config.get('groups', [])):
            loaded_config.setdefault('groups', []).insert(0, {"id": "default", "name": "Default"})

        self.config = loaded_config;
        self._resolve_sound_paths() # Resolve paths after loading

    def save_config(self):
        if not self.config: return
        print("Saving configuration..."); config_path = self._get_config_path()
        if not config_path: print("ERROR: Cannot save config, path unknown."); return
        try:
            config_to_save = self._prepare_config_for_saving()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f: json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            print(f"Config saved successfully to {config_path}")
        except PermissionError: print(f"ERROR: Permission denied saving config to {config_path}"); self.update_status(f"Error: Permission denied saving config!")
        except Exception as e: print(f"Error saving config: {e}"); traceback.print_exc(); self.update_status(f"Error: Could not save config! {e}")

    def _get_config_path(self):
        app_dir = get_script_directory()
        return os.path.join(app_dir, CONFIG_FILENAME) if app_dir else None

    def _resolve_sound_paths(self):
        config_path = self._get_config_path();
        if not config_path: return
        config_dir = os.path.dirname(config_path)
        sounds = self.config.get("sounds", [])
        if not sounds: return
        print(f"Resolving sound paths relative to: {config_dir}")
        for sound in sounds:
            sound_id = sound.get("id", "unknown"); relative_path = sound.get("relative_path"); abs_path_resolved = None
            if relative_path:
                try:
                    # Normalize slashes from config to native OS slashes
                    native_rel_path = os.path.normpath(relative_path)

                    # Try path relative to config first
                    path_try1 = os.path.join(config_dir, native_rel_path)
                    # Try path as absolute if it is
                    path_try2 = native_rel_path if os.path.isabs(native_rel_path) else None

                    if os.path.exists(path_try1):
                        abs_path_resolved = os.path.abspath(path_try1)
                    elif path_try2 and os.path.exists(path_try2):
                        abs_path_resolved = os.path.abspath(path_try2)
                    else:
                        # If neither exists, still store the absolute path relative to config for checking later
                        abs_path_resolved = os.path.abspath(path_try1)
                except Exception as e: print(f"Err resolving path for sound {sound_id} ('{relative_path}'): {e}"); abs_path_resolved = os.path.abspath(os.path.join(config_dir, relative_path)) # Fallback
            else:
                print(f" -> Sound '{sound.get('name')}' has no relative_path defined.")

            sound["absolute_path"] = abs_path_resolved;
            # Update file_exists status based on resolved path
            sound["file_exists"] = os.path.exists(abs_path_resolved) if abs_path_resolved else False


    def _prepare_config_for_saving(self):
        # Create a deep copy to avoid modifying the live config object
        if not self.config: return {}
        config_copy = copy.deepcopy(self.config)
        # Remove runtime state from sounds before saving
        if "sounds" in config_copy:
            for sound in config_copy["sounds"]:
                sound.pop("absolute_path", None) # Don't save absolute path
                sound.pop("file_exists", None)   # Don't save runtime file status

                # Normalize relative path to forward slashes for cross-platform
                if "relative_path" in sound and sound["relative_path"]:
                    sound["relative_path"] = sound["relative_path"].replace('\\', '/')
        return config_copy

    # --- UI Population ---
    def populate_groups_and_sounds(self, *args): # Added *args to handle potential signals sending arguments
        print("Populating UI...")
        if not self.central_widget: print("ERROR: Central widget not ready in populate!"); return
        try:
            current_tab_index = self.tab_widget.currentIndex()
            self.tab_widget.clear(); self.sound_buttons.clear() # Clear tabs and button references

            # Ensure default group exists in config before populating
            if not any(g.get('id') == 'default' for g in self.config.get('groups', [])):
                self.config.setdefault('groups', []).insert(0, {"id": "default", "name": "Default"})

            group_widgets = {} # Store {'group_id': {'tab': QWidget, 'grid': QGridLayout, 'container': QWidget}}
            tab_index_map = {} # Store {'group_id': tab_index}
            idx = 0
            for group in self.config.get("groups", []):
                group_id = group.get("id"); group_name = group.get("name", "Unnamed")
                if not group_id: continue # Skip groups without ID

                tab_content_widget = QWidget(); tab_layout = QVBoxLayout(tab_content_widget); tab_layout.setContentsMargins(0,0,0,0)
                scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setObjectName(f"scrollArea_{group_id}")
                grid_container = QWidget(); grid_container.setObjectName(f"gridContainer_{group_id}"); grid_layout = QGridLayout(grid_container); grid_layout.setSpacing(5)
                scroll_area.setWidget(grid_container); tab_layout.addWidget(scroll_area)

                self.tab_widget.addTab(tab_content_widget, group_name);
                group_widgets[group_id] = {'tab': tab_content_widget, 'grid': grid_layout, 'container': grid_container}
                tab_index_map[group_id] = idx; idx += 1

            num_columns = max(1, self.config.get('settings', {}).get('grid_columns', 5))

            # Prepare sounds per group
            sounds_in_groups = {group_id: [] for group_id in group_widgets}
            default_group_id_exists = "default" in group_widgets

            for sound_data in self.config.get("sounds", []):
                group_id = sound_data.get("group_id", "default");

                # Ensure sound path is resolved if missing (can happen if added then immediately populated)
                if "absolute_path" not in sound_data and sound_data.get("relative_path"):
                    self._resolve_sound_paths() # Re-resolve might be needed here, inefficient but safe

                target_group_id = group_id if group_id in group_widgets else "default"

                if target_group_id in sounds_in_groups:
                    sounds_in_groups[target_group_id].append(sound_data)
                elif default_group_id_exists: # If target group doesn't exist, fallback to default
                    print(f"Warning: Sound '{sound_data.get('name')}' assigned to non-existent group '{group_id}', moving to Default.")
                    sounds_in_groups["default"].append(sound_data)
                    sound_data['group_id'] = 'default' # Fix in live config for consistency
                else: # Should not happen if default group check above works
                    print(f"ERROR: Cannot assign sound '{sound_data.get('name')}' - group '{group_id}' missing and no Default group found!")

            # Populate grids
            for group_id, group_info in group_widgets.items():
                grid_layout = group_info['grid']; grid_container = group_info['container']; col = 0; row = 0

                # Clear existing widgets in the grid layout safely
                while grid_layout.count():
                    layout_item = grid_layout.takeAt(0)
                    if layout_item and layout_item.widget(): layout_item.widget().deleteLater()

                # Sort sounds alphabetically by name within each group
                sorted_sounds = sorted(sounds_in_groups.get(group_id, []), key=lambda s: s.get('name', '').lower())

                for sound_data in sorted_sounds:
                    sound_id = sound_data.get("id");
                    if not sound_id: continue # Skip sounds without ID

                    # Ensure file_exists status is up-to-date
                    if "absolute_path" in sound_data and "file_exists" not in sound_data:
                        sound_data["file_exists"] = os.path.exists(sound_data["absolute_path"]) if sound_data["absolute_path"] else False

                    btn = SoundButton(sound_data);
                    btn.set_file_missing(not sound_data.get("file_exists", False))
                    # Connect button click to the slot designed for button presses
                    btn.clicked.connect(partial(self.play_sound_from_button, sound_id))
                    grid_layout.addWidget(btn, row, col);
                    self.sound_buttons[sound_id] = btn # Store reference

                    col += 1;
                    if col >= num_columns: col = 0; row += 1

                # Add stretch to push buttons to the top-left
                grid_layout.setRowStretch(row + 1, 1); grid_layout.setColumnStretch(num_columns, 1)

            # Restore previous tab index if valid
            if 0 <= current_tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(current_tab_index)

            self.filter_sounds() # Apply search filter to the newly populated tabs
            self.update_status("UI Populated.")
        except Exception as e: print(f"Error populating UI: {e}"); traceback.print_exc(); self.update_status(f"Error: Failed to populate UI! {e}")

    # --- Sound Management ---
    @Slot()
    def add_sound_dialog(self):
        dialog = QFileDialog(self); dialog.setWindowTitle("Select Sound Files"); dialog.setFileMode(QFileDialog.FileMode.ExistingFiles); dialog.setNameFilter("Audio Files (*.wav *.mp3 *.ogg *.flac *.aac *.m4a *.opus);;All Files (*)")
        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                added_count = 0; config_dir = get_script_directory()
                if not config_dir: self.show_error_popup("Error", "Cannot determine application directory to calculate relative paths."); return

                for file_path in selected_files:
                    try:
                        abs_path = os.path.abspath(file_path)
                        try: relative_path = os.path.relpath(abs_path, config_dir)
                        except ValueError: relative_path = abs_path # Use absolute if on different drive (Windows)

                        # Normalize path for cross-platform compatibility
                        relative_path = relative_path.replace('\\', '/')

                        # Check for duplicates based on relative path
                        if any(s.get('relative_path') == relative_path for s in self.config.get('sounds', [])): print(f"Skipping duplicate: {relative_path}"); continue

                        sound_id = f"snd_{uuid.uuid4().hex[:12]}"; sound_name = os.path.splitext(os.path.basename(file_path))[0]
                        # Basic sound data structure
                        new_sound_data = {
                            "id": sound_id,
                            "name": sound_name,
                            "relative_path": relative_path, # Store path relative to config
                            "volume": 1.0,
                            "group_id": "default", # Add to default group initially
                            "hotkey": None,
                            "effects": []
                        }
                        # Add default effect structures if pedalboard is loaded
                        if _AUDIO_LIBS_LOADED and pedalboard:
                            if _pb_reverb_ok: new_sound_data["effects"].append({"type": "Reverb", "enabled": False, "params": {"room_size": 0.5}})
                            if _pb_delay_ok: new_sound_data["effects"].append({"type": "Delay", "enabled": False, "params": {"delay_seconds": 0.3, "feedback": 0.4}})

                        self.config.setdefault("sounds", []).append(new_sound_data); added_count += 1
                    except Exception as e: print(f"Error processing file {file_path}: {e}"); traceback.print_exc(); self.show_error_popup("Add Sound Error", f"Could not process file:\n{os.path.basename(file_path)}\n\nError: {e}")

                if added_count > 0:
                    self._resolve_sound_paths(); # Resolve paths for newly added sounds
                    self.save_config();
                    self.populate_groups_and_sounds(); # Refresh UI
                    self.setup_hotkeys(); # Update hotkey map if needed (though unlikely here)
                    self.update_status(f"Added {added_count} sound(s).")
                else:
                    self.update_status("No new sounds added (duplicates or errors).")
            else: # No files selected
                self.update_status("File selection cancelled.")

    def find_sound_by_id(self, sound_id):
        for sound in self.config.get("sounds", []):
            if sound.get("id") == sound_id: return sound
        return None

    @Slot(str)
    def delete_sound(self, sound_id):
        sound_data = self.find_sound_by_id(sound_id)
        if not sound_data: print(f"Delete Error: Sound ID {sound_id} not found."); return
        name = sound_data.get('name', 'Unknown')
        reply = QtWidgets.QMessageBox.question(self, 'Confirm Delete', f"Are you sure you want to delete '{name}'?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            print(f"Deleting sound: {name} ({sound_id})");
            original_hotkey_str = sound_data.get('hotkey')
            # Remove the sound from the list
            self.config['sounds'] = [s for s in self.config.get('sounds', []) if s.get('id') != sound_id]

            # If it had a hotkey, potentially update the hotkey map
            if original_hotkey_str:
                if self._hotkey_map.pop(original_hotkey_str, None) == sound_id:
                    print(f" -> Removing hotkey mapping: {original_hotkey_str}")
                    # Re-run setup_hotkeys to ensure listener consistency if needed
                    # Although removing from map might be sufficient if listener is robust
                    self.setup_hotkeys() # Safer to just re-setup
                elif original_hotkey_str in self._hotkey_map:
                     print(f" -> Hotkey {original_hotkey_str} was assigned to sound ID ({sound_id}) but map mismatch? Map: {self._hotkey_map.get(original_hotkey_str)}")
                     self.setup_hotkeys() # Re-setup to be safe

            self.save_config();
            self.populate_groups_and_sounds(); # Refresh UI
            self.update_status(f"Deleted sound: {name}")
        else: print("Deletion cancelled.")


    @Slot(str)
    def relink_sound(self, sound_id):
        sound_data = self.find_sound_by_id(sound_id);
        if not sound_data: print(f"Relink Error: Sound ID {sound_id} not found."); return
        name = sound_data.get('name', 'Unknown')
        print(f"Attempting to relink sound: {name}"); self.update_status(f"Select new file for {name}...")
        dialog = QFileDialog(self); dialog.setWindowTitle(f"Select New Location for '{name}'"); dialog.setFileMode(QFileDialog.FileMode.ExistingFile); dialog.setNameFilter("Audio Files (*.wav *.mp3 *.ogg *.flac *.aac *.m4a *.opus);;All Files (*)")
        # Try to start in the directory of the old file
        old_abs_path = sound_data.get("absolute_path")
        if old_abs_path and os.path.exists(os.path.dirname(old_abs_path)):
            dialog.setDirectory(os.path.dirname(old_abs_path))
        elif old_abs_path: # If path exists but not dir, try base dir of config
             config_dir = get_script_directory()
             if config_dir: dialog.setDirectory(config_dir)

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                selected_file = selected_files[0]; print(f"New file selected: {selected_file}"); config_dir = get_script_directory()
                if not config_dir: self.show_error_popup("Error", "Cannot determine application directory to calculate relative path."); return

                was_missing = not sound_data.get("file_exists", True)

                abs_path = os.path.abspath(selected_file)
                try: relative_path = os.path.relpath(abs_path, config_dir)
                except ValueError: relative_path = abs_path # Use absolute if on different drive
                # Normalize path for cross-platform compatibility
                relative_path = relative_path.replace('\\', '/')

                new_sound_name = os.path.splitext(os.path.basename(abs_path))[0]

                # Update the sound data in the main config list
                sound_data["name"] = new_sound_name
                sound_data["relative_path"] = relative_path;
                sound_data["absolute_path"] = abs_path; # Update runtime path
                sound_data["file_exists"] = True # Assume it exists since we just selected it

                # Update the corresponding button's appearance
                button_widget = self.sound_buttons.get(sound_id)
                if button_widget:
                    button_widget.sound_data = sound_data # Update button's internal data ref
                    button_widget.setText(new_sound_name) # Update the text directly to be safe
                    button_widget.set_file_missing(False) # Update visual state

                # BATCH RELINKING LOGIC
                new_dir = os.path.dirname(abs_path)
                batch_relinked_count = 0
                if was_missing:
                    for other_sound in self.config.get('sounds', []):
                        if other_sound.get('id') == sound_id:
                            continue # Skip the one we just relinked

                        if not other_sound.get('file_exists', True): # It's missing
                            old_other_path = other_sound.get('absolute_path') or other_sound.get('relative_path')
                            if old_other_path:
                                # Extract just the filename
                                filename = os.path.basename(old_other_path)
                                potential_new_path = os.path.join(new_dir, filename)

                                if os.path.exists(potential_new_path):
                                    try: other_rel_path = os.path.relpath(potential_new_path, config_dir)
                                    except ValueError: other_rel_path = potential_new_path
                                    # Normalize path
                                    other_rel_path = other_rel_path.replace('\\', '/')

                                    other_sound["relative_path"] = other_rel_path
                                    other_sound["absolute_path"] = potential_new_path
                                    other_sound["file_exists"] = True

                                    # Update UI button
                                    other_button = self.sound_buttons.get(other_sound.get('id'))
                                    if other_button:
                                        other_button.sound_data = other_sound
                                        other_button.set_file_missing(False)

                                    batch_relinked_count += 1
                                    print(f"Auto-relinked: {other_sound.get('name')} to {potential_new_path}")

                self.save_config(); # Save the updated relative path
                if batch_relinked_count > 0:
                    msg = f"Changed '{name}' to '{new_sound_name}' and auto-relinked {batch_relinked_count} other missing files in the same folder."
                    self.update_status(msg)
                    QMessageBox.information(self, "Batch Relink Successful", msg)
                else:
                    self.update_status(f"Changed '{name}' to '{new_sound_name}'.")

            else: # No file selected
                self.update_status("Relink cancelled - no file selected.")
        else: # Dialog cancelled
            self.update_status("Relink cancelled.")

    # --- Playback ---

    # Slot specifically for button clicks
    @Slot(str)
    def play_sound_from_button(self, sound_id):
        """Slot called directly by button clicks."""
        self._play_sound_internal(sound_id, source='button')

    # Slot specifically for invokeMethod from hotkey
    @Slot(str, str)
    def play_sound_from_hotkey_qt(self, sound_id, source):
        """Slot called via QMetaObject.invokeMethod from hotkey trigger."""
        # We expect source to be 'hotkey' here
        self._play_sound_internal(sound_id, source=source)

    # Internal playback logic
    def _play_sound_internal(self, sound_id, source='unknown'):
        """Internal logic to play sound, called by button or hotkey slots."""
        print(f"-> _play_sound_internal: ID={sound_id}, Triggered by={source}")
        if not _AUDIO_LIBS_LOADED:
            print(f"  - Playback aborted: Audio libs not loaded.")
            self.update_status("ERROR: Audio libraries not loaded!");
            print(f"<- _play_sound_internal finished early (no audio libs) for ID={sound_id}")
            return

        sound_data = self.find_sound_by_id(sound_id)
        if not sound_data:
            print(f"  - Playback aborted: Sound ID {sound_id} not found.");
            print(f"<- _play_sound_internal finished early (sound not found) for ID={sound_id}")
            return

        # Ensure runtime path info is up-to-date
        if "absolute_path" not in sound_data and sound_data.get("relative_path"):
            self._resolve_sound_paths() # May be slightly inefficient, but ensures path is calculated
            sound_data = self.find_sound_by_id(sound_id) # Re-fetch in case list was modified

        abs_path = sound_data.get("absolute_path")
        print(f"  - Checking file: {abs_path}")

        # Check existence using os.path.exists
        file_exists_now = os.path.exists(abs_path) if abs_path else False

        if not file_exists_now:
            sound_data["file_exists"] = False # Update live status
            button = self.sound_buttons.get(sound_id)
            if button: QTimer.singleShot(0, partial(button.set_file_missing, True)) # Update UI thread-safely
            print(f"  - Playback aborted: Sound file missing for {sound_data.get('name')}")
            self.update_status(f"Error: Cannot find file for {sound_data.get('name')}")
            # Only prompt to relink if triggered by a button press
            if source == 'button':
                reply = QtWidgets.QMessageBox.question(self, 'File Missing', f"Sound file for '{sound_data.get('name')}' is missing or inaccessible.\nWould you like to relink it?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if reply == QtWidgets.QMessageBox.StandardButton.Yes: self.relink_sound(sound_id)
            print(f"<- _play_sound_internal finished early (file missing) for ID={sound_id}")
            return

        # If file exists now, update status if it was previously marked missing
        if not sound_data.get("file_exists", False):
             sound_data["file_exists"] = True
             button = self.sound_buttons.get(sound_id)
             if button: QTimer.singleShot(0, partial(button.set_file_missing, False))

        print(f"  - File exists. Preparing playback for: {sound_data['name']}")
        self.update_status(f"Playing: {sound_data['name']}")

        stop_event = threading.Event();
        # Pass a copy of sound_data to the thread to avoid race conditions if edited
        thread_data = copy.deepcopy(sound_data)
        thread_info = {'thread': None, 'stop_event': stop_event, 'sound_id': sound_id}
        self.active_playback_threads.append(thread_info) # Add BEFORE starting thread

        try:
            print(f"  - Creating playback thread...")
            playback_thread = threading.Thread(target=self._play_sound_thread_func, args=(thread_data, stop_event, thread_info), daemon=True)
            thread_info['thread'] = playback_thread # Store thread object in the dict
            print(f"  - Starting playback thread...")
            playback_thread.start()
            print(f"  - Playback thread started.")
        except Exception as e:
            print(f"  - ERROR starting playback thread: {e}");
            # If thread failed to start, remove its info from the active list
            try: self.active_playback_threads.remove(thread_info)
            except ValueError: pass # Might have already been removed somehow
            self.update_status(f"Error starting playback: {e}")

        print(f"<- _play_sound_internal finished for ID={sound_id}")

    def _play_sound_thread_func(self, sound_data, stop_event, thread_info_ref):
        # This function runs in a separate thread
        if not _AUDIO_LIBS_LOADED: return

        sound_id = sound_data.get("id", "unknown"); file_path = sound_data.get("absolute_path"); volume = sound_data.get("volume", 1.0); sound_name = sound_data.get("name", "Unknown"); stream = None
        print(f"[Thread-{sound_id}] Starting playback for '{sound_name}' ({file_path})")

        try:
            # Load audio file
            try: audio_segment = AudioSegment.from_file(file_path)
            except FileNotFoundError: print(f"[Thread-{sound_id}] Error: File disappeared: {file_path}"); QTimer.singleShot(0, partial(self._mark_file_missing, sound_id)); return # Mark missing on main thread
            except CouldntDecodeError as e: print(f"[Thread-{sound_id}] Error: Cannot decode '{sound_name}': {e}"); QTimer.singleShot(0, partial(self.update_status, f"Error: Cannot decode {sound_name}")); return
            except Exception as e: print(f"[Thread-{sound_id}] Error loading file '{sound_name}': {e}"); traceback.print_exc(); QTimer.singleShot(0, partial(self.update_status, f"Error loading {sound_name}: {e}")); return

            # Convert to numpy array (float32 for sounddevice)
            samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32);
            # Normalize samples to [-1.0, 1.0]
            samples /= (2**(audio_segment.sample_width * 8 - 1));
            sample_rate = audio_segment.frame_rate

            # Reshape for multi-channel if necessary
            if audio_segment.channels > 1: samples = samples.reshape((-1, audio_segment.channels))
            elif audio_segment.channels == 1: samples = samples.reshape((-1, 1)) # Ensure it's 2D even for mono
            else: print(f"[Thread-{sound_id}] Warning: Audio segment reports 0 channels for '{sound_name}'"); samples = samples.reshape((-1, 1)) # Treat as mono if unknown

            # Apply effects using Pedalboard if available and enabled
            board = None
            if pedalboard and hasattr(pedalboard, 'Pedalboard'): board = pedalboard.Pedalboard([])

            if board is not None and "effects" in sound_data:
                for fx_cfg in sound_data["effects"]:
                    if fx_cfg.get("enabled", False):
                        fx_type = fx_cfg.get("type"); params = fx_cfg.get("params", {})
                        try:
                            if hasattr(pedalboard, fx_type):
                                effect_instance = getattr(pedalboard, fx_type)(**params);
                                board.append(effect_instance);
                                print(f"[Thread-{sound_id}] Added effect: {fx_type} with params {params}")
                            else: print(f"[Thread-{sound_id}] Warn: Unknown or unavailable effect type '{fx_type}'")
                        except Exception as e: print(f"[Thread-{sound_id}] Error creating effect '{fx_type}' with params {params}: {e}"); traceback.print_exc()

            if board and len(board) > 0: # Only process if effects were actually added
                print(f"[Thread-{sound_id}] Applying effects: {board}")
                try: processed_samples = board(samples, sample_rate); print(f"[Thread-{sound_id}] Effects applied successfully.")
                except Exception as e: print(f"[Thread-{sound_id}] Error applying effects: {e}"); traceback.print_exc(); processed_samples = samples # Fallback to original samples
            else:
                processed_samples = samples # No effects to apply

            # Apply volume adjustment and clipping
            processed_samples = np.clip(processed_samples * volume, -1.0, 1.0).astype(np.float32)

            # Get output device index
            output_dev_name = self.config.get("settings", {}).get("output_device_name", "Default"); output_dev_idx = None; actual_device_name = "Default"
            if output_dev_name != "Default":
                try:
                    devices = sd.query_devices(); found = False
                    for i, dev in enumerate(devices):
                        if dev['name'] == output_dev_name and dev['max_output_channels'] > 0: output_dev_idx = i; actual_device_name = output_dev_name; found = True; break
                    if not found: print(f"[Thread-{sound_id}] Warn: Output device '{output_dev_name}' not found/available. Using default.")
                except Exception as e_dev: print(f"[Thread-{sound_id}] Error querying audio devices: {e_dev}. Using default."); traceback.print_exc()

            num_channels = processed_samples.shape[1] if processed_samples.ndim > 1 else 1
            if processed_samples.ndim == 1: processed_samples = processed_samples.reshape(-1, 1) # Ensure 2D for stream

            print(f"[Thread-{sound_id}] Sending {num_channels}-ch audio @ {sample_rate}Hz to device: '{actual_device_name}' (Index: {output_dev_idx})")

            # --- Playback using sounddevice stream ---
            current_frame = 0; total_frames = len(processed_samples)
            if total_frames == 0: print(f"[Thread-{sound_id}] Warning: Processed audio has zero frames for '{sound_name}'. Skipping playback."); return

            # Define the callback function for the audio stream
            def callback(outdata, frames, time_info, status):
                nonlocal current_frame
                if status: print(f"[Thread-{sound_id}] Stream status: {status}")
                if stop_event.is_set(): print(f"[Thread-{sound_id}] Stop event detected in callback."); outdata.fill(0); raise sd.CallbackStop # Stop playback

                chunk_end = current_frame + frames
                remaining_frames = total_frames - current_frame

                if remaining_frames <= frames:
                    # Last chunk
                    if remaining_frames > 0: outdata[:remaining_frames] = processed_samples[current_frame : current_frame + remaining_frames]
                    outdata[remaining_frames:].fill(0) # Fill rest with silence
                    current_frame += remaining_frames
                    print(f"[Thread-{sound_id}] Reached end of audio data.");
                    raise sd.CallbackStop # Signal stream completion
                else:
                    # Full chunk
                    outdata[:] = processed_samples[current_frame:chunk_end];
                    current_frame = chunk_end

            # Create and start the output stream
            stream = sd.OutputStream(samplerate=sample_rate, device=output_dev_idx, channels=num_channels, dtype=np.float32, callback=callback, finished_callback=lambda: print(f"[Thread-{sound_id}] Stream finished_callback executed."))
            with stream:
                print(f"[Thread-{sound_id}] Stream started. Playing {total_frames / sample_rate:.2f} seconds...")
                # Wait for the stream to finish or stop_event to be set
                while stream.active:
                    if stop_event.wait(timeout=0.1): # Check stop event periodically
                         print(f"[Thread-{sound_id}] Stop event detected while stream active.");
                         # Stream will be stopped by the CallbackStop exception raised in the callback
                         break
                if not stream.active:
                    print(f"[Thread-{sound_id}] Playback finished naturally (stream inactive).")

        except sd.PortAudioError as pae: print(f"[Thread-{sound_id}] PortAudio Error playing '{sound_name}': {pae}"); traceback.print_exc(); QTimer.singleShot(0, partial(self.update_status, f"Audio Error: {pae}"))
        except Exception as e: print(f"[Thread-{sound_id}] Generic error during playback of '{sound_name}': {e}"); traceback.print_exc(); QTimer.singleShot(0, partial(self.update_status, f"Playback Error: {e}"))
        finally:
            # Ensure the thread info is removed from the main list ON THE MAIN THREAD
            QTimer.singleShot(0, partial(self._remove_active_thread, thread_info_ref))
            print(f"[Thread-{sound_id}] Playback thread finished.")


    @Slot()
    def stop_all_sounds(self):
        if not self.active_playback_threads: return
        print(f"Stopping all sounds! ({len(self.active_playback_threads)} active)"); self.update_status("Stopping all sounds...")
        # Iterate over a copy of the list as setting the event might trigger removal
        for thread_info in list(self.active_playback_threads):
            thread = thread_info.get('thread'); stop_event = thread_info.get('stop_event'); sound_id = thread_info.get('sound_id', 'unknown')
            if stop_event: # Check if stop_event exists
                 print(f"Signaling stop for sound ID: {sound_id}");
                 stop_event.set()
            # No need to join here, the thread will finish and remove itself

    @Slot(dict)
    def _remove_active_thread(self, thread_info_to_remove):
        # This slot runs on the main thread, called by QTimer from the playback thread
        initial_count = len(self.active_playback_threads)
        try:
            self.active_playback_threads.remove(thread_info_to_remove)
            final_count = len(self.active_playback_threads)
            sound_id = thread_info_to_remove.get('sound_id', 'unknown')
            print(f"Playback thread reference removed for sound ID: {sound_id}. Remaining: {final_count}")
        except ValueError:
            sound_id = thread_info_to_remove.get('sound_id', 'unknown')
            print(f"Attempted to remove thread reference for {sound_id}, but it was not found (likely already finished/removed).")

    @Slot(str)
    def _mark_file_missing(self, sound_id):
        # This slot runs on the main thread, called by QTimer from playback thread
        sound_data = self.find_sound_by_id(sound_id)
        if sound_data and sound_data.get('file_exists', True):
            sound_data['file_exists'] = False;
            button = self.sound_buttons.get(sound_id)
            if button: button.set_file_missing(True) # Update button visual state
            self.update_status(f"Error: File missing for {sound_data.get('name', 'Unknown')}")

    # --- File Integrity ---
    @Slot()
    def start_file_integrity_check(self):
        if self.file_check_timer.isActive(): self.file_check_timer.stop()
        interval_minutes = self.config.get("settings", {}).get("scan_interval_minutes", 15)
        if interval_minutes > 0:
            print(f"Starting file integrity check timer ({interval_minutes} min)...");
            self.file_check_timer.setInterval(interval_minutes * 60 * 1000);
            self.file_check_timer.start();
            # Run check once shortly after start
            QTimer.singleShot(1000, self.check_files)
        else:
            print("File integrity check timer disabled (interval 0).")

    @Slot()
    def check_files(self):
        if not self.config: return
        print("Checking file integrity...")
        config_dir = get_script_directory()
        if not config_dir: print("Warning: Cannot check files, config directory unknown."); return

        all_ok = True; changes_detected = False
        for sound in self.config.get("sounds", []):
            sound_id = sound.get("id"); current_status = sound.get("file_exists", False); absolute_path = sound.get("absolute_path")

            # If absolute path isn't stored, resolve it first (should generally be resolved already)
            if not absolute_path and sound.get("relative_path"):
                self._resolve_sound_paths() # This is inefficient if called often
                sound = self.find_sound_by_id(sound_id) # Re-get sound data
                if not sound: continue
                absolute_path = sound.get("absolute_path")

            new_status = os.path.exists(absolute_path) if absolute_path else False

            if new_status != current_status:
                sound["file_exists"] = new_status; changes_detected = True;
                button = self.sound_buttons.get(sound_id)
                # Use QTimer to update button from potentially different thread (though timer usually runs on main)
                if button: QTimer.singleShot(0, partial(button.set_file_missing, not new_status))

                if not new_status: print(f"File missing detected: {sound.get('name')} at {absolute_path}")
                else: print(f"File found: {sound.get('name')} at {absolute_path}")

            if not new_status: all_ok = False

        if changes_detected:
             status_text = "Status: OK" if all_ok else "Status: WARNING - Some files missing!";
             self.update_status(status_text) # Update status bar only if changes found
        else:
             print("File integrity check: No changes detected.")

    # --- Pynput Hotkey Helper Functions ---

    # --- REVISED Helper Function ---
    def _key_to_string(self, key):
        """Converts a pynput key object to a canonical string component.
           Handles non-printable chars by attempting VK mapping for common keys.
        """
        if isinstance(key, pynput_kb.KeyCode):
            # 1. Try printable character first
            if hasattr(key, 'char') and key.char and key.char.isprintable():
                return key.char.lower()
            # 2. If char fails, try using vk for common ranges (A-Z, 0-9)
            elif hasattr(key, 'vk'):
                vk = key.vk
                # Check common VK ranges - Note: This is OS-dependent mapping generally,
                # but these ranges are fairly standard via ASCII/VK codes.
                if 65 <= vk <= 90: # VK_A to VK_Z
                    return chr(vk).lower()
                if 48 <= vk <= 57: # VK_0 to VK_9 (main keyboard)
                    return chr(vk)
                # Numpad keys often have different VK codes (e.g., 96-105 for 0-9)
                if 96 <= vk <= 105: # VK_NUMPAD0 to VK_NUMPAD9
                    return f"num_{chr(vk - 48)}" # Represent as num_0, num_1 etc.
                # Add more specific VK mappings here if needed (e.g., punctuation, F-keys if char fails)
                # See: https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes

                # Fallback for unmapped VKs (provides some representation)
                print(f"[KeyToString] Warning: Unmapped VKCode {vk}. Using vk representation.")
                # Return a representation that _hotkey_to_string is likely to reject, preventing accidental assignment
                # return f"vk_{vk}" # Avoid using this directly as a hotkey component
                return None # Treat unmapped VK as None to avoid bad hotkeys
            else:
                # No char, no vk? Should be rare.
                print(f"[KeyToString] Warning: KeyCode without char or vk: {key}")
                return None
        elif isinstance(key, pynput_kb.Key):
            # Handle special keys (like modifiers, F-keys, space, etc.)
            name = key.name
            # Map variants (e.g., ctrl_l) to canonical name ('ctrl')
            return self.MODIFIER_MAP.get(name, name) # Returns canonical name or original if not mapped
        return None # Unknown key type

    def _hotkey_to_string(self, modifier_set, key_obj):
        """Generates the canonical hotkey string."""
        main_key_str = self._key_to_string(key_obj)
        if not main_key_str: return None # Cannot form hotkey without main key

        # Check if the main key itself is a modifier (invalid hotkey)
        # Need to use the canonical name of the main key for this check
        main_key_canonical_check = self.MODIFIER_MAP.get(main_key_str, main_key_str)
        if main_key_canonical_check in self.CANONICAL_MODIFIERS:
            # E.g., user pressed Ctrl then Shift. 'shift' is the key_obj, but it's a modifier.
            print(f"[HotkeyToString] Main key '{main_key_str}' is a modifier. Invalid combination.")
            return None

        if not modifier_set: return main_key_str # No modifiers, just the key
        else:
             # Sort canonical modifiers alphabetically and join with main key
             sorted_mods = sorted(list(modifier_set));
             return "+".join(sorted_mods + [main_key_str])

    def _string_to_parts(self, hotkey_string):
        """Parses a canonical hotkey string back into modifiers and main key."""
        if not hotkey_string or not isinstance(hotkey_string, str): return None, None
        parts = hotkey_string.lower().split('+')
        if not parts: return None, None
        main_key = parts[-1]
        mods = frozenset(p for p in parts[:-1] if p in self.CANONICAL_MODIFIERS)

        # Validate: main key should not be a canonical modifier itself
        if main_key in self.CANONICAL_MODIFIERS:
            print(f"[StringToParts] Error: Invalid format, main key '{main_key}' is a modifier in '{hotkey_string}'")
            return None, None
        # Validate: all parts before the last should be known canonical modifiers
        if len(parts) > 1 and len(mods) != len(parts) - 1:
            print(f"[StringToParts] Error: Invalid format, unknown modifier part in '{hotkey_string}'")
            return None, None

        return mods, main_key

    # --- Hotkeys using Pynput ---
    def _on_press(self, key):
        # This runs in the pynput listener thread
        try:
            key_str = self._key_to_string(key) # Get canonical string part
            if not key_str: return # Ignore keys we can't represent

            is_modifier = self.MODIFIER_MAP.get(key_str, key_str) in self.CANONICAL_MODIFIERS

            if is_modifier:
                mod_name = self.MODIFIER_MAP.get(key_str, key_str) # Ensure we add the canonical name
                self._current_modifiers.add(mod_name)
                # print(f"Global Mod Press: {mod_name}, Current: {self._current_modifiers}") # Debug
            else:
                # Non-modifier key pressed - check for match
                current_combo_str = self._hotkey_to_string(self._current_modifiers, key)
                # print(f"Global Combo Check: {current_combo_str}") # Debug

                if not current_combo_str: return # Invalid combo (e.g., main key was modifier)

                # Check against sound hotkeys
                if current_combo_str in self._hotkey_map:
                    sound_id = self._hotkey_map[current_combo_str]
                    print(f"[Hotkey Listener] Sound hotkey '{current_combo_str}' detected for ID: {sound_id}")
                    self.trigger_sound_from_hotkey(sound_id) # Schedules via invokeMethod

                # Check against stop_all hotkey
                if self._stop_all_hotkey_str and current_combo_str == self._stop_all_hotkey_str:
                    print(f"[Hotkey Listener] Stop All hotkey '{current_combo_str}' detected.")
                    # Use QTimer for stop all, as it's less critical than sound trigger timing
                    # and avoids potential invokeMethod complexity if stop_all itself takes time.
                    QTimer.singleShot(0, self.stop_all_sounds)

        except Exception as e:
            print(f"ERROR in pynput _on_press: {e}"); traceback.print_exc()

    def _on_release(self, key):
        # This runs in the pynput listener thread
        try:
            key_str = self._key_to_string(key) # Get canonical string part
            if not key_str: return

            mod_name = self.MODIFIER_MAP.get(key_str, key_str) # Get canonical name
            # Use discard to safely remove the modifier if it exists
            self._current_modifiers.discard(mod_name)
            # print(f"Global Mod Release: {mod_name}, Current: {self._current_modifiers}") # Debug

        except Exception as e:
            print(f"ERROR in pynput _on_release: {e}"); traceback.print_exc()

    def setup_hotkeys(self):
        if not _HOTKEY_LIB_LOADED: print("pynput library not loaded, skipping hotkey setup."); return

        print("Setting up pynput hotkeys..."); self._stop_hotkey_listener() # Stop existing listener first

        self._hotkey_map = {}; self._stop_all_hotkey_str = None; has_valid_hotkeys = False

        # Build the map from config
        config_sounds = self.config.get("sounds", [])
        config_stop_all = self.config.get('settings', {}).get('stop_all_hotkey')

        # 1. Map sound hotkeys, checking for internal conflicts
        temp_sound_map = {}
        sound_conflicts = set()
        for sound in config_sounds:
            hotkey_str = sound.get("hotkey"); sound_id = sound.get("id")
            if hotkey_str and sound_id:
                 mods, main_key = self._string_to_parts(hotkey_str)
                 if main_key is None: # Validate format using our parser
                     print(f"WARN: Invalid hotkey format in config for sound '{sound.get('name')}': '{hotkey_str}'. Skipping."); continue

                 # Check for conflict with already processed sound hotkeys
                 if hotkey_str in temp_sound_map:
                     conflicting_id = temp_sound_map[hotkey_str]; conflicting_sound = self.find_sound_by_id(conflicting_id); conflicting_name = conflicting_sound.get('name', '?') if conflicting_sound else '?'
                     print(f"WARN: Duplicate sound hotkey '{hotkey_str}' defined for '{sound.get('name')}' (ID: {sound_id}). It conflicts with '{conflicting_name}' (ID: {conflicting_id}). Both will be disabled.")
                     sound_conflicts.add(hotkey_str) # Mark this hotkey as conflicted
                 else:
                     temp_sound_map[hotkey_str] = sound_id

        # 2. Process stop_all hotkey
        valid_stop_all_str = None
        if config_stop_all:
            mods, main_key = self._string_to_parts(config_stop_all)
            if main_key is None: print(f"WARN: Invalid Stop All hotkey format in config: '{config_stop_all}'. It will not be registered.")
            else: valid_stop_all_str = config_stop_all # Format seems valid

        # 3. Finalize maps, checking cross-conflicts and previously found duplicates
        self._hotkey_map = {}
        for hotkey_str, sound_id in temp_sound_map.items():
            if hotkey_str in sound_conflicts: continue # Skip hotkeys that conflicted with other sounds

            # Check conflict with stop_all
            if valid_stop_all_str and hotkey_str == valid_stop_all_str:
                 sound_name = self.find_sound_by_id(sound_id).get('name', '?')
                 print(f"WARN: Hotkey '{hotkey_str}' for sound '{sound_name}' conflicts with Stop All hotkey. Sound hotkey will be disabled.")
                 continue # Skip this sound hotkey

            # If no conflicts, add to the final map
            sound_name = self.find_sound_by_id(sound_id).get('name', '?')
            self._hotkey_map[hotkey_str] = sound_id;
            print(f"Map: '{hotkey_str}' -> '{sound_name}' (ID: '{sound_id}')");
            has_valid_hotkeys = True

        # 4. Activate stop_all if valid and not conflicting
        if valid_stop_all_str:
            if valid_stop_all_str in self._hotkey_map:
                 # This case should have been caught above, but double-check
                 print(f"WARN: Stop All hotkey '{valid_stop_all_str}' conflicts with a sound hotkey. It will not be registered.")
            else:
                 self._stop_all_hotkey_str = valid_stop_all_str;
                 print(f"Stop All Hotkey: '{self._stop_all_hotkey_str}' will be active.");
                 has_valid_hotkeys = True

        # Start listener only if there are any active hotkeys
        if has_valid_hotkeys:
            try:
                print("Starting pynput listener thread..."); self._current_modifiers = set() # Reset modifier state
                self._pynput_listener = pynput_kb.Listener(on_press=self._on_press, on_release=self._on_release)
                self._pynput_listener.start(); print("pynput listener thread started.")
            except Exception as e: print(f"ERROR: Failed to start pynput listener: {e}"); traceback.print_exc(); self._pynput_listener = None; self.show_error_popup("Hotkey Listener Error", f"Could not start hotkey listener:\n{e}")
        else:
            print("No valid non-conflicting hotkeys configured. Listener not started.")

    def _stop_hotkey_listener(self):
        if self._pynput_listener:
            print("Stopping pynput listener thread...");
            try: self._pynput_listener.stop()
            except Exception as e: print(f"Error stopping pynput listener: {e}")
            # No need to join, stop() is usually sufficient
            self._pynput_listener = None; self._current_modifiers = set(); print("pynput listener stopped.")

    # --- MODIFIED: Use QMetaObject.invokeMethod ---
    def trigger_sound_from_hotkey(self, sound_id):
        """Schedules sound playback on the main thread using invokeMethod."""
        print(f"---- Scheduling playback for hotkey sound ID: {sound_id} via invokeMethod")
        try:
            # Target the specific slot designed for this on the main window object (self)
            QMetaObject.invokeMethod(
                self,
                "play_sound_from_hotkey_qt", # Name (as string) of the target @Slot
                Qt.ConnectionType.QueuedConnection, # Ensures execution in the main event loop
                Q_ARG(str, sound_id), # Argument 1 for the slot
                Q_ARG(str, 'hotkey')  # Argument 2 for the slot
            )
            # print(f"---- invokeMethod called successfully for {sound_id}") # Optional success log
        except Exception as e:
            print(f"---- ERROR calling invokeMethod for {sound_id}: {e}")
            traceback.print_exc()


    def check_hotkey_conflict(self, new_hotkey_str, current_sound_id=None):
        """Checks if a proposed hotkey conflicts with existing sound or stop_all hotkeys.
           Returns dict with conflict info or None.
           Uses the live _hotkey_map and _stop_all_hotkey_str.
        """
        if not new_hotkey_str: return None

        # Check against other sounds in the live map
        for mapped_str, sound_id in self._hotkey_map.items():
            if mapped_str == new_hotkey_str and sound_id != current_sound_id:
                conflict_sound = self.find_sound_by_id(sound_id);
                return {"type": "sound", "id": sound_id, "name": conflict_sound.get('name', '?') if conflict_sound else '?'}

        # Check against stop_all hotkey
        if self._stop_all_hotkey_str and new_hotkey_str == self._stop_all_hotkey_str:
            # Conflict only if we are checking for a sound (current_sound_id is not None)
            # If current_sound_id is None, we are checking for the stop_all key itself in Settings
            if current_sound_id is not None:
                return {"type": "stop_all"}

        return None

    # --- Context Menu & Popups ---
    @Slot(str, QWidget, QPoint)
    def show_context_menu_for_sound(self, sound_id, button_instance, global_pos):
        self.dismiss_current_popup(); # Close any existing popup first
        print(f"Context menu for sound: {sound_id}")
        menu = QMenu(self); sound_data = self.find_sound_by_id(sound_id)
        if not sound_data: print("Error: Sound data not found for context menu"); return

        action_edit = QAction("Edit Properties", self);
        action_hotkey = QAction("Assign Hotkey", self);
        action_relink = QAction("Relink/Change File...", self);
        action_delete = QAction("Delete Sound", self)

        # Use lambda to pass parameters to the handler slot
        action_edit.triggered.connect(lambda: self.handle_context_menu_option(sound_id, "Edit Properties"));
        action_hotkey.triggered.connect(lambda: self.handle_context_menu_option(sound_id, "Assign Hotkey"));
        action_relink.triggered.connect(lambda: self.handle_context_menu_option(sound_id, "Relink/Change File..."));
        action_delete.triggered.connect(lambda: self.handle_context_menu_option(sound_id, "Delete Sound"));

        menu.addAction(action_edit);

        # Only enable hotkey assignment if library loaded
        if _HOTKEY_LIB_LOADED: menu.addAction(action_hotkey)
        else: action_hotkey.setEnabled(False); menu.addAction(action_hotkey)

        menu.addAction(action_relink)

        menu.addSeparator(); menu.addAction(action_delete);

        self._current_popup = menu; # Store reference to dismiss later if needed
        menu.exec(global_pos); # Show the menu at the cursor position
        self._current_popup = None # Clear reference after menu closes

    @Slot(str, str) # Slot to handle actions from the context menu
    def handle_context_menu_option(self, sound_id, option):
        print(f"Context action '{option}' for {sound_id}");
        sound_data = self.find_sound_by_id(sound_id) # Get fresh data
        if not sound_data: print(f"Error: Sound {sound_id} not found for action '{option}'"); return

        if option == "Edit Properties": self.open_edit_properties_dialog(sound_data)
        elif option == "Assign Hotkey":
            if _HOTKEY_LIB_LOADED: self.open_assign_hotkey_dialog(sound_data)
            else: self.show_error_popup("Hotkey Error", "pynput library is not available.")
        elif option == "Relink/Change File...": self.relink_sound(sound_id)
        elif option == "Delete Sound": self.delete_sound(sound_id)

    @Slot(dict) # Make it a slot if called from elsewhere potentially
    def open_edit_properties_dialog(self, sound_data):
        self.dismiss_current_popup();
        # Pass a copy for editing, original is updated by dialog on accept+changes
        dialog = EditSoundDialog(sound_data, self.config.get('groups', []), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_updated_sound_data() # Returns original dict if changed, else None
            if updated_data:
                print(f"Saving updated properties for {sound_data['id']}");
                # Data was modified in-place by the dialog's accept method
                self.save_config();
                self.populate_groups_and_sounds(); # Refresh UI (group might have changed)
                # Hotkeys don't change here, no need to re-setup unless group logic affects it? No.
            else: print("Edit cancelled or no changes made.")
        else: print("Edit properties dialog cancelled.")

    @Slot(dict) # Make it a slot
    def open_assign_hotkey_dialog(self, sound_data):
        if not _HOTKEY_LIB_LOADED: self.show_error_popup("Hotkey Error", "pynput library is not available."); return
        self.dismiss_current_popup();
        dialog = AssignHotkeyDialog(sound_data, self)
        dialog.exec() # Show modally

        captured_str = dialog.get_captured_hotkey() # Returns canonical string, None (cleared), or "NO_CHANGE"

        if captured_str != "NO_CHANGE": # Only proceed if OK was clicked
            new_hotkey_canonical = captured_str # This will be the canonical string or None

            # Re-check conflict just before applying (though dialog should prevent OK on conflict)
            conflict = self.check_hotkey_conflict(new_hotkey_canonical, sound_data.get('id'))
            if conflict:
                if conflict['type'] == 'sound': self.show_error_popup("Hotkey Conflict", f"Hotkey '{new_hotkey_canonical}' is already assigned to '{conflict['name']}'.")
                elif conflict['type'] == 'stop_all': self.show_error_popup("Hotkey Conflict", f"Hotkey '{new_hotkey_canonical}' is assigned to 'Stop All Sounds'.")
                print("Hotkey assignment cancelled due to conflict detected after dialog close.");
                self.update_status("Hotkey assignment cancelled due to conflict.")
            else:
                # Apply the change
                print(f"Applying hotkey '{new_hotkey_canonical or 'None'}' to sound {sound_data['id']}");
                sound_data['hotkey'] = new_hotkey_canonical # Update the live config dict
                self.save_config(); # Save changes
                self.setup_hotkeys() # Rebuild map and restart listener with new/cleared hotkey
                self.update_status(f"Hotkey for '{sound_data.get('name')}' set to '{new_hotkey_canonical or 'None'}'.")
        else: # Dialog was cancelled or rejected
            print("Assign hotkey cancelled or no change.")

    @Slot() # Make it a slot
    def dismiss_current_popup(self):
        if self._current_popup:
            try: self._current_popup.close()
            except Exception as e: print(f"Error dismissing popup: {e}")
            self._current_popup = None

    # --- App Lifecycle & Status ---
    # Make update_status a Slot
    @Slot(str)
    def update_status(self, message):
        """Updates the status bar label; callable from any thread."""
        def _update_ui():
            # Ensure status_label exists before trying to set text
            if hasattr(self, 'status_label') and self.status_label:
                try:
                    self.status_label.setText(str(message))
                except RuntimeError as e: # Handle cases where widget might be deleted
                    print(f"Warn: Could not update status label (RuntimeError: {e})")
            else: print("Warn: self.status_label widget not available for status update.")
            print(f"Status Update: {message}") # Log status update regardless

        # Check if we are already in the main thread
        if threading.current_thread() is threading.main_thread():
            _update_ui()
        else:
            # If called from another thread, schedule the update on the main thread
            QTimer.singleShot(0, _update_ui)


    def show_error_popup(self, title, message):
        """Shows a non-critical warning popup; callable from any thread."""
        print(f"ERROR POPUP: {title} - {message}")
        # Use QTimer.singleShot to ensure the message box is shown from the main thread
        try:
             QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))
        except Exception as e:
             print(f"Error scheduling Qt error box: {e}")


    # Static method potentially, or ensure self exists if called early
    # Making it a class method requires `cls` instead of `self`
    # Let's keep it instance for now, assuming it's called after __init__
    def show_critical_error_popup(self, title, message):
        """Shows a critical error popup; attempts Tkinter fallback if Qt fails."""
        print(f"CRITICAL ERROR POPUP: {title} - {message}")
        app_instance = QApplication.instance()
        if app_instance: # Check if QApplication exists
            try:
                # Use QTimer.singleShot for safety, show relative to main window if possible
                QTimer.singleShot(0, lambda: QMessageBox.critical(self if self else None, title, message))
            except Exception as e_qt:
                print(f"Error showing critical Qt error box: {e_qt}")
                # Fallback if Qt message box fails
                if _TKINTER_LOADED:
                    try: print("Attempting Tkinter fallback for critical error."); root = tk.Tk(); root.withdraw(); messagebox.showerror(title, message); root.destroy()
                    except Exception as e_tk: print(f"Error showing critical tkinter error box: {e_tk}")
        elif _TKINTER_LOADED: # If Qt app doesn't exist, try Tkinter directly
            try: print("Attempting Tkinter fallback for critical error (no Qt app)."); root = tk.Tk(); root.withdraw(); messagebox.showerror(title, message); root.destroy()
            except Exception as e_tk: print(f"Error showing critical tkinter error box: {e_tk}")
        else: # Absolute fallback
            input(f"\n--- CRITICAL ERROR ---\n{title}\n{message}\n\nPress Enter to exit...")


    def closeEvent(self, event):
        print("Close event triggered");
        reply = QMessageBox.question(self, 'Confirm Exit', 'Are you sure you want to exit?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_stop(); # Perform cleanup
            event.accept() # Allow window to close
        else:
            event.ignore() # Prevent window from closing

    def on_stop(self):
        """Cleanup actions performed before the application exits."""
        print("Soundboard App Stopping");
        self._stop_hotkey_listener() # Stop listening for hotkeys

        if self.file_check_timer.isActive(): print("Stopping file check timer."); self.file_check_timer.stop()

        print("Signaling active playback threads to stop..."); self.stop_all_sounds() # Signal threads

        print("Waiting briefly for playback threads..."); start_wait = time.time(); join_timeout = 0.5 # Short timeout per thread
        # Iterate over a copy, as threads remove themselves from the list
        threads_to_wait_for = list(self.active_playback_threads)
        waited_count = 0
        # Give threads a chance to exit gracefully after being signaled
        # Don't explicitly join here, rely on them being daemons and the stop_event
        # wait briefly instead
        max_wait_time = 1.0 # Max total wait time
        while self.active_playback_threads and (time.time() - start_wait) < max_wait_time:
            time.sleep(0.05)

        active_threads_final = list(self.active_playback_threads) # Check again
        if active_threads_final: print(f"Warn: {len(active_threads_final)} playback threads might still be active after shutdown wait.")
        else: print("All playback threads stopped or finished.")

        self.save_config(); # Save current state
        print("Soundboard App Finished.")


# --- Main Execution ---
if __name__ == '__main__':
    # Ensure PySide6 is loaded before proceeding
    if not _PYSIDE_LOADED:
        # Error message already shown or attempted
        sys.exit(1)

    # Check for essential audio libraries AFTER PySide6 check
    try: import sounddevice; import soundfile; import numpy; import pydub
    except ImportError as core_audio_err:
        error_message = (f"ERROR: Missing critical core audio libraries!\n\nMissing library: {core_audio_err.name}\n\nPlease ensure sounddevice, soundfile, numpy, pydub are installed.\nTry: pip install sounddevice soundfile numpy pydub")
        print("\n" + "="*60 + f"\n{error_message}\n" + "="*60);
        # Attempt to show critical error popup (might use Tkinter)
        SoundboardWindow.show_critical_error_popup(None, "Missing Core Audio Libraries", error_message)
        sys.exit(1)

    # Warnings for optional libraries (after critical checks pass)
    if not pedalboard:
        warning_message = ("WARNING: Effects library ('pedalboard') not found or failed to load.\nAudio effects functionality will be disabled.\nInstall it with: pip install pedalboard")
        print("\n" + "="*60 + f"\n{warning_message}\n" + "="*60)
    if not _HOTKEY_LIB_LOADED:
        warning_message = ("WARNING: Global Hotkey library ('pynput') not found or failed to load.\nGlobal hotkey functionality will be disabled.\nInstall it with: pip install pynput")
        print("\n" + "="*60 + f"\n{warning_message}\n" + "="*60)

    app = QApplication(sys.argv)
    # Set a fallback application name if needed elsewhere
    app.setApplicationName("PySideSoundboard")

    try:
        main_window = SoundboardWindow()
        main_window.show()
    except Exception as e_init:
        print(f"FATAL ERROR during application initialization: {e_init}"); traceback.print_exc();
        # Attempt to show critical error popup
        SoundboardWindow.show_critical_error_popup(None,"Application Initialization Error", f"Could not start the soundboard.\n\nError: {e_init}")
        sys.exit(1)

    sys.exit(app.exec())
