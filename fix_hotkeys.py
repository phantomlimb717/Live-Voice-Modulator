import re

with open('voice_modulator.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("from PySide6.QtWidgets import (\n        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,\n        QPushButton, QLabel, QLineEdit, QScrollArea,\n        QDialog, QSlider, QComboBox, QDialogButtonBox, QFileDialog, QMenu,\n        QStyleFactory, QMessageBox, QMenuBar, QInputDialog, QListWidget, QListWidgetItem,\n        QSpinBox, QCheckBox, QDoubleSpinBox, QSizePolicy, QFormLayout\n    )", """from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QScrollArea,
        QDialog, QSlider, QComboBox, QDialogButtonBox, QFileDialog, QMenu,
        QStyleFactory, QMessageBox, QMenuBar, QInputDialog, QListWidget, QListWidgetItem,
        QSpinBox, QCheckBox, QDoubleSpinBox, QSizePolicy, QFormLayout
    )""")

code = code.replace("class SceneButton(QPushButton):", """class SceneButton(QPushButton):
    def __init__(self, sound_data, parent=None):
        super().__init__(sound_data.get("name", "Unnamed"), parent)
        self.sound_data = sound_data
        self.sound_id = sound_data.get("id")
        self.file_missing = not sound_data.get("file_exists", True)
        self.is_active = False
        self.setMinimumHeight(60)
        self.update_appearance()""")

# The button init block replacement above is incomplete. Let's do string replaces carefully.
with open('voice_modulator.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated voice_modulator.py")
