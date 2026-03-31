with open("voice_modulator.py", "r") as f:
    source = f.read()

# Part 1: Signal and UI connections
search_1 = """class EditSoundDialog(QDialog):
    def __init__(self, sound_data, groups, parent=None):
        super().__init__(parent); self.sound_data_original = sound_data; self.sound_data_edited = copy.deepcopy(sound_data); self.groups = groups
        self.setWindowTitle(f"Edit Properties: {sound_data.get('name', '')}"); self.setMinimumWidth(450)
        self.layout = QVBoxLayout(self); form_layout = QFormLayout()
        self.name_input = QLineEdit(self.sound_data_edited.get('name', '')); form_layout.addRow("Sound Name:", self.name_input)
        volume_layout = QHBoxLayout(); self.volume_slider = QSlider(Qt.Orientation.Horizontal); self.volume_slider.setRange(0, 150); self.volume_slider.setValue(int(self.sound_data_edited.get('volume', 1.0) * 100))
        self.volume_label = QLabel(f"{self.sound_data_edited.get('volume', 1.0):.2f}"); self.volume_slider.valueChanged.connect(lambda val: self.volume_label.setText(f"{val / 100.0:.2f}"))
        volume_layout.addWidget(self.volume_slider); volume_layout.addWidget(self.volume_label); form_layout.addRow("Volume:", volume_layout)

        # Pre/Post Effect Routing
        self.routing_combo = QComboBox()
        self.routing_combo.addItem("Mix AFTER Effects (Default)", userData="after")
        self.routing_combo.addItem("Mix BEFORE Effects", userData="before")
        current_routing = self.sound_data_edited.get('loop_routing', 'after')
        self.routing_combo.setCurrentIndex(0 if current_routing == 'after' else 1)
        form_layout.addRow("Loop Routing:", self.routing_combo)

        self.group_combo = QComboBox(); current_group_index = 0
        for i, group in enumerate(self.groups): self.group_combo.addItem(group['name'], userData=group['id']);
        if group['id'] == self.sound_data_edited.get('group_id', 'default'): current_group_index = i
        self.group_combo.setCurrentIndex(current_group_index); form_layout.addRow("Group:", self.group_combo)"""

replace_1 = """class EditSoundDialog(QDialog):
    live_update_signal = Signal(dict)

    def __init__(self, sound_data, groups, parent=None):
        super().__init__(parent); self.sound_data_original = sound_data; self.sound_data_edited = copy.deepcopy(sound_data); self.groups = groups
        self.setWindowTitle(f"Edit Properties: {sound_data.get('name', '')}"); self.setMinimumWidth(450)
        self.layout = QVBoxLayout(self); form_layout = QFormLayout()
        self.name_input = QLineEdit(self.sound_data_edited.get('name', '')); form_layout.addRow("Sound Name:", self.name_input)
        volume_layout = QHBoxLayout(); self.volume_slider = QSlider(Qt.Orientation.Horizontal); self.volume_slider.setRange(0, 150); self.volume_slider.setValue(int(self.sound_data_edited.get('volume', 1.0) * 100))
        self.volume_label = QLabel(f"{self.sound_data_edited.get('volume', 1.0):.2f}"); self.volume_slider.valueChanged.connect(lambda val: self.volume_label.setText(f"{val / 100.0:.2f}"))
        self.volume_slider.valueChanged.connect(self._emit_live_update)
        volume_layout.addWidget(self.volume_slider); volume_layout.addWidget(self.volume_label); form_layout.addRow("Volume:", volume_layout)

        # Pre/Post Effect Routing
        self.routing_combo = QComboBox()
        self.routing_combo.addItem("Mix AFTER Effects (Default)", userData="after")
        self.routing_combo.addItem("Mix BEFORE Effects", userData="before")
        current_routing = self.sound_data_edited.get('loop_routing', 'after')
        self.routing_combo.setCurrentIndex(0 if current_routing == 'after' else 1)
        self.routing_combo.currentIndexChanged.connect(self._emit_live_update)
        form_layout.addRow("Loop Routing:", self.routing_combo)

        self.group_combo = QComboBox(); current_group_index = 0
        for i, group in enumerate(self.groups): self.group_combo.addItem(group['name'], userData=group['id']);
        if group['id'] == self.sound_data_edited.get('group_id', 'default'): current_group_index = i
        self.group_combo.setCurrentIndex(current_group_index); form_layout.addRow("Group:", self.group_combo)"""

if search_1 in source:
    source = source.replace(search_1, replace_1)
    print("Patched EditSoundDialog part 1")
else:
    print("Search 1 failed")

# Part 2: Add _emit_live_update signals to effect widgets
search_2 = """        for effect_data in self.sound_data_edited['effects']:
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
            elif fx_type == "Distortion":
                params_layout.addWidget(QLabel("Drive (dB):")); slider_drv = QSlider(Qt.Orientation.Horizontal); slider_drv.setRange(0, 500); slider_drv.setValue(int(effect_data.get("params", {}).get("drive_db", 25.0) * 10)); label_drv = QLabel(f"{slider_drv.value()/10.0:.1f}")
                slider_drv.valueChanged.connect(lambda val, l=label_drv: l.setText(f"{val/10.0:.1f}")); params_layout.addWidget(slider_drv); params_layout.addWidget(label_drv); self.effects_widgets[fx_type]['params']['drive_db'] = {'widget': slider_drv, 'label': label_drv}
            elif fx_type == "Bitcrush":
                params_layout.addWidget(QLabel("Bit Depth:")); spinbox_bc = QSpinBox(); spinbox_bc.setRange(1, 32); spinbox_bc.setValue(int(effect_data.get("params", {}).get("bit_depth", 8.0))); params_layout.addWidget(spinbox_bc); self.effects_widgets[fx_type]['params']['bit_depth'] = {'widget': spinbox_bc}"""

replace_2 = """        for effect_data in self.sound_data_edited['effects']:
            fx_type = effect_data.get("type")
            if fx_type not in defined_effects: continue
            fx_box = QHBoxLayout(); fx_enable_cb = QCheckBox(fx_type); fx_enable_cb.setChecked(effect_data.get("enabled", False)); fx_box.addWidget(fx_enable_cb); self.effects_widgets[fx_type] = {'enable': fx_enable_cb, 'params': {}}
            fx_enable_cb.toggled.connect(self._emit_live_update)
            params_layout = QHBoxLayout()
            if fx_type == "Reverb":
                params_layout.addWidget(QLabel("Room Size:")); slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(0, 100); slider.setValue(int(effect_data.get("params", {}).get("room_size", 0.5) * 100)); label = QLabel(f"{slider.value()/100.0:.2f}")
                slider.valueChanged.connect(lambda val, l=label: l.setText(f"{val/100.0:.2f}")); slider.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider); params_layout.addWidget(label); self.effects_widgets[fx_type]['params']['room_size'] = {'widget': slider, 'label': label}
            elif fx_type == "Delay":
                params_layout.addWidget(QLabel("Delay (s):")); spinbox = QDoubleSpinBox(); spinbox.setRange(0.0, 5.0); spinbox.setSingleStep(0.05); spinbox.setDecimals(2); spinbox.setValue(effect_data.get("params", {}).get("delay_seconds", 0.5)); spinbox.valueChanged.connect(self._emit_live_update); params_layout.addWidget(spinbox); self.effects_widgets[fx_type]['params']['delay_seconds'] = {'widget': spinbox}
                params_layout.addWidget(QLabel("Feedback:")); slider_fb = QSlider(Qt.Orientation.Horizontal); slider_fb.setRange(0, 95); slider_fb.setValue(int(effect_data.get("params", {}).get("feedback", 0.3) * 100)); label_fb = QLabel(f"{slider_fb.value()/100.0:.2f}")
                slider_fb.valueChanged.connect(lambda val, l=label_fb: l.setText(f"{val/100.0:.2f}")); slider_fb.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider_fb); params_layout.addWidget(label_fb); self.effects_widgets[fx_type]['params']['feedback'] = {'widget': slider_fb, 'label': label_fb}
            elif fx_type == "Distortion":
                params_layout.addWidget(QLabel("Drive (dB):")); slider_drv = QSlider(Qt.Orientation.Horizontal); slider_drv.setRange(0, 500); slider_drv.setValue(int(effect_data.get("params", {}).get("drive_db", 25.0) * 10)); label_drv = QLabel(f"{slider_drv.value()/10.0:.1f}")
                slider_drv.valueChanged.connect(lambda val, l=label_drv: l.setText(f"{val/10.0:.1f}")); slider_drv.valueChanged.connect(self._emit_live_update); params_layout.addWidget(slider_drv); params_layout.addWidget(label_drv); self.effects_widgets[fx_type]['params']['drive_db'] = {'widget': slider_drv, 'label': label_drv}
            elif fx_type == "Bitcrush":
                params_layout.addWidget(QLabel("Bit Depth:")); spinbox_bc = QSpinBox(); spinbox_bc.setRange(1, 32); spinbox_bc.setValue(int(effect_data.get("params", {}).get("bit_depth", 8.0))); spinbox_bc.valueChanged.connect(self._emit_live_update); params_layout.addWidget(spinbox_bc); self.effects_widgets[fx_type]['params']['bit_depth'] = {'widget': spinbox_bc}"""

if search_2 in source:
    source = source.replace(search_2, replace_2)
    print("Patched EditSoundDialog part 2")
else:
    print("Search 2 failed")

# Part 3: Add _emit_live_update, _build_current_data, and simplify accept
search_3 = """    def accept(self):
        self.sound_data_edited['name'] = self.name_input.text(); self.sound_data_edited['volume'] = round(self.volume_slider.value() / 100.0, 3); self.sound_data_edited['group_id'] = self.group_combo.currentData()
        self.sound_data_edited['loop_routing'] = self.routing_combo.currentData()
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
                elif fx_type == "Distortion": new_effect_data['params']['drive_db'] = round(widgets['params']['drive_db']['widget'].value() / 10.0, 1)
                elif fx_type == "Bitcrush": new_effect_data['params']['bit_depth'] = float(widgets['params']['bit_depth']['widget'].value())
                elif fx_type == "VST3 Plugin":
                    new_effect_data['params']['plugin_path'] = widgets['params']['plugin_path']['current_path']
                    new_effect_data['params']['plugin_state'] = widgets['params']['plugin_path']['current_state']
                updated_effects.append(new_effect_data)
            else:
                updated_effects.append(effect_data)
        self.sound_data_edited['effects'] = updated_effects
        self.changes_made = (self.sound_data_edited != self.sound_data_original)
        if self.changes_made:
            self.sound_data_original.clear()
            self.sound_data_original.update(self.sound_data_edited)
        super().accept()"""

replace_3 = """    @Slot()
    def _emit_live_update(self, *args):
        self.live_update_signal.emit(self._build_current_data())

    def _build_current_data(self):
        current_data = copy.deepcopy(self.sound_data_edited)
        current_data['name'] = self.name_input.text()
        current_data['volume'] = round(self.volume_slider.value() / 100.0, 3)
        current_data['group_id'] = self.group_combo.currentData()
        current_data['loop_routing'] = self.routing_combo.currentData()
        updated_effects = []
        for effect_data in current_data.get('effects', []):
            fx_type = effect_data.get('type')
            if fx_type in self.effects_widgets:
                widgets = self.effects_widgets[fx_type]
                new_effect_data = copy.deepcopy(effect_data)
                new_effect_data['enabled'] = widgets['enable'].isChecked()
                if fx_type == "Reverb": new_effect_data['params']['room_size'] = round(widgets['params']['room_size']['widget'].value() / 100.0, 3)
                elif fx_type == "Delay":
                    new_effect_data['params']['delay_seconds'] = round(widgets['params']['delay_seconds']['widget'].value(), 3)
                    new_effect_data['params']['feedback'] = round(widgets['params']['feedback']['widget'].value() / 100.0, 3)
                elif fx_type == "Distortion": new_effect_data['params']['drive_db'] = round(widgets['params']['drive_db']['widget'].value() / 10.0, 1)
                elif fx_type == "Bitcrush": new_effect_data['params']['bit_depth'] = float(widgets['params']['bit_depth']['widget'].value())
                elif fx_type == "VST3 Plugin":
                    new_effect_data['params']['plugin_path'] = widgets['params']['plugin_path']['current_path']
                    new_effect_data['params']['plugin_state'] = widgets['params']['plugin_path']['current_state']
                updated_effects.append(new_effect_data)
            else:
                updated_effects.append(effect_data)
        current_data['effects'] = updated_effects
        return current_data

    def accept(self):
        self.sound_data_edited = self._build_current_data()
        self.changes_made = (self.sound_data_edited != self.sound_data_original)
        if self.changes_made:
            self.sound_data_original.clear()
            self.sound_data_original.update(self.sound_data_edited)
        super().accept()"""

if search_3 in source:
    source = source.replace(search_3, replace_3)
    print("Patched EditSoundDialog part 3")
else:
    print("Search 3 failed")

# Part 4: Add _emit_live_update to show_vst3_gui and load_vst3
search_4 = """                # show_editor() blocks the thread until closed. We must run it in a background thread.
                def _run_editor(plugin, widget_state_dict):
                    try:
                        plugin.show_editor()

                        # Save the new state back to the widget's temporary state once closed
                        import base64
                        state_bytes = plugin.raw_state
                        if state_bytes:
                            # Encode as base64 string to be JSON serializable
                            widget_state_dict['current_state'] = base64.b64encode(state_bytes).decode('utf-8')
                    except Exception as e:
                        print(f"Error in VST3 editor thread: {e}")

                editor_thread = threading.Thread(
                    target=_run_editor,
                    args=(temp_plugin, self.effects_widgets["VST3 Plugin"]['params']['plugin_path']),
                    daemon=True
                )
                editor_thread.start()"""

replace_4 = """                # show_editor() blocks the thread until closed. We must run it in a background thread.
                def _run_editor(plugin, widget_state_dict, dialog_instance):
                    try:
                        plugin.show_editor()

                        # Save the new state back to the widget's temporary state once closed
                        import base64
                        state_bytes = plugin.raw_state
                        if state_bytes:
                            # Encode as base64 string to be JSON serializable
                            widget_state_dict['current_state'] = base64.b64encode(state_bytes).decode('utf-8')

                        QMetaObject.invokeMethod(dialog_instance, "_emit_live_update", Qt.ConnectionType.QueuedConnection)
                    except Exception as e:
                        print(f"Error in VST3 editor thread: {e}")

                editor_thread = threading.Thread(
                    target=_run_editor,
                    args=(temp_plugin, self.effects_widgets["VST3 Plugin"]['params']['plugin_path'], self),
                    daemon=True
                )
                editor_thread.start()"""

if search_4 in source:
    source = source.replace(search_4, replace_4)
    print("Patched EditSoundDialog part 4")
else:
    print("Search 4 failed")

search_5 = """            # Re-enable the Show GUI button
            gui_btn = self.effects_widgets["VST3 Plugin"]['params']['plugin_path']['show_gui_button']
            gui_btn.setEnabled(_AUDIO_LIBS_LOADED and pedalboard is not None)

            # Optional: Test load it right now so we can show its UI immediately from the edit dialog
            try:
                if _AUDIO_LIBS_LOADED and pedalboard:
                    # Just to test if it loads
                    temp_plugin = pedalboard.load_plugin(selected_file)
            except Exception as e:"""

replace_5 = """            # Re-enable the Show GUI button
            gui_btn = self.effects_widgets["VST3 Plugin"]['params']['plugin_path']['show_gui_button']
            gui_btn.setEnabled(_AUDIO_LIBS_LOADED and pedalboard is not None)
            self._emit_live_update()

            # Optional: Test load it right now so we can show its UI immediately from the edit dialog
            try:
                if _AUDIO_LIBS_LOADED and pedalboard:
                    # Just to test if it loads
                    temp_plugin = pedalboard.load_plugin(selected_file)
            except Exception as e:"""

if search_5 in source:
    source = source.replace(search_5, replace_5)
    print("Patched EditSoundDialog part 5")
else:
    print("Search 5 failed")

with open("voice_modulator.py", "w") as f:
    f.write(source)
