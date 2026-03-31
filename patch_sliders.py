import re

with open("voice_modulator.py", "r") as f:
    source = f.read()

# For sliders in EditSoundDialog, change slider.valueChanged.connect(self._emit_live_update)
# to slider.sliderReleased.connect(self._emit_live_update).

# Search block for reverb slider
search = """slider.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider);"""
replace = """slider.sliderReleased.connect(self._emit_live_update); params_layout.addWidget(slider);"""
source = source.replace(search, replace)

# Search block for feedback slider
search = """slider_fb.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider_fb);"""
replace = """slider_fb.sliderReleased.connect(self._emit_live_update); params_layout.addWidget(slider_fb);"""
source = source.replace(search, replace)

# Search block for drive slider
search = """slider_drv.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider_drv);"""
replace = """slider_drv.sliderReleased.connect(self._emit_live_update); params_layout.addWidget(slider_drv);"""
source = source.replace(search, replace)

with open("voice_modulator.py", "w") as f:
    f.write(source)

print("Patched sliders successfully")
