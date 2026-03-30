import re

with open('voice_modulator.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Header
code = code.replace('# soundboard_pyside_v5_fixed_indent.py - Python Soundboard using PySide6', '# voice_modulator.py - Live Voice Modulator using PySide6')

# Imports
code = code.replace('from PySide6.QtWidgets import (\n        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,\n        QPushButton, QLabel, QLineEdit, QGridLayout, QScrollArea, QTabWidget,\n        QDialog, QSlider, QComboBox, QDialogButtonBox, QFileDialog, QMenu,\n        QStyleFactory, QMessageBox, QMenuBar, QInputDialog, QListWidget, QListWidgetItem,\n    QSpinBox, QCheckBox, QDoubleSpinBox, QSizePolicy, QFormLayout\n    )', 'from PySide6.QtWidgets import (\n        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,\n        QPushButton, QLabel, QLineEdit, QScrollArea,\n        QDialog, QSlider, QComboBox, QDialogButtonBox, QFileDialog, QMenu,\n        QStyleFactory, QMessageBox, QMenuBar, QInputDialog, QListWidget, QListWidgetItem,\n        QSpinBox, QCheckBox, QDoubleSpinBox, QSizePolicy, QFormLayout\n    )')

# Class Names
code = code.replace('class SoundboardWindow(QMainWindow):', 'class VoiceModulatorWindow(QMainWindow):')
code = code.replace('isinstance(main_window, SoundboardWindow)', 'isinstance(main_window, VoiceModulatorWindow)')
code = code.replace('main_window = SoundboardWindow()', 'main_window = VoiceModulatorWindow()')
code = code.replace('SoundboardWindow.show_critical_error_popup', 'VoiceModulatorWindow.show_critical_error_popup')

# Button Names
code = code.replace('class SoundButton(QPushButton):', 'class SceneButton(QPushButton):')
code = code.replace('btn = SoundButton(sound_data)', 'btn = SceneButton(sound_data)')
code = code.replace('isinstance(widget, SoundButton)', 'isinstance(widget, SceneButton)')

# UI Text
code = code.replace('Manage Sound Groups', 'Manage Scene Groups')
code = code.replace('"Add Sound(s)"', '"Add Scene/Effect"')
code = code.replace('Search sounds...', 'Search scenes/effects...')
code = code.replace('used by Stop All Sounds', 'used by Deactivate All Scenes')
code = code.replace("assigned to 'Stop All Sounds'", "assigned to 'Deactivate All Scenes'")

# Clean up Tab CSS
old_css = """QTabWidget::pane{border-top:1px solid #444;background-color:#282828}QTabBar::tab{background:#444;color:#CCC;border:1px solid #555;border-bottom:none;padding:5px 10px;margin-right:2px}QTabBar::tab:selected{background:#555;color:#FFF;margin-bottom:-1px}QTabBar::tab:hover{background:#5A5A5A}"""
code = code.replace(old_css, '')

with open('voice_modulator.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated voice_modulator.py")
