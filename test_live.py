from PySide6.QtWidgets import QApplication
from voice_modulator import VoiceModulatorWindow
import sys
import os

app = QApplication(sys.argv)
win = VoiceModulatorWindow()

win.config = {
    "settings": {"input_device_name": "Default", "output_device_name": "Default"},
    "groups": [{"id": "default", "name": "Default"}],
    "sounds": [{
        "id": "snd_123",
        "name": "Test Sound",
        "relative_path": "test.wav",
        "volume": 1.0,
        "group_id": "default",
        "hotkey": None,
        "loop_routing": "after",
        "effects": []
    }]
}

# Add loop to active loops
win._active_loops["snd_123"] = {
    "array": [1, 2, 3],
    "index": 0,
    "routing": "after",
    "volume": 1.0
}
win._active_scenes.add("snd_123")

print("Before Update:", win._active_loops["snd_123"])

# Apply update
updated_data = {
    "volume": 0.5,
    "loop_routing": "before"
}
win._apply_live_scene_update("snd_123", updated_data)

print("After Update:", win._active_loops["snd_123"])
assert win._active_loops["snd_123"]["volume"] == 0.5
assert win._active_loops["snd_123"]["routing"] == "before"
print("Success!")
