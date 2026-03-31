with open("voice_modulator.py", "r") as f:
    source = f.read()

search = """    @Slot(dict) # Make it a slot if called from elsewhere potentially
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
        else: print("Edit properties dialog cancelled.")"""

replace = """    @Slot(dict) # Make it a slot if called from elsewhere potentially
    def open_edit_properties_dialog(self, sound_data):
        self.dismiss_current_popup();
        # Pass a copy for editing, original is updated by dialog on accept+changes
        dialog = EditSoundDialog(sound_data, self.config.get('groups', []), self)
        dialog.live_update_signal.connect(lambda updated_data: self._apply_live_scene_update(sound_data['id'], updated_data))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_updated_sound_data() # Returns original dict if changed, else None
            if updated_data:
                print(f"Saving updated properties for {sound_data['id']}");
                # Data was modified in-place by the dialog's accept method
                self.save_config();
                self.populate_groups_and_sounds(); # Refresh UI (group might have changed)
                # Hotkeys don't change here, no need to re-setup unless group logic affects it? No.
            else:
                print("Edit cancelled or no changes made.")
                self._apply_live_scene_update(sound_data['id'], sound_data)
        else:
            print("Edit properties dialog cancelled.")
            self._apply_live_scene_update(sound_data['id'], sound_data)"""

if search in source:
    source = source.replace(search, replace)
    with open("voice_modulator.py", "w") as f:
        f.write(source)
    print("Patched open_edit_properties_dialog successfully")
else:
    print("Search string not found")
