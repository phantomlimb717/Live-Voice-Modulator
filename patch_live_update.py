with open("voice_modulator.py", "r") as f:
    source = f.read()

search = """    def _apply_live_scene_update(self, sound_id, updated_data):
        with self._audio_lock:
            if sound_id in self._active_loops:
                self._active_loops[sound_id]['volume'] = updated_data.get('volume', 1.0)
                self._active_loops[sound_id]['routing'] = updated_data.get('loop_routing', 'after')

        if sound_id in self._active_scenes:
            self._update_scene_effects(sound_id, updated_data)"""

replace = """    def _apply_live_scene_update(self, sound_id, updated_data):
        with self._audio_lock:
            if sound_id in self._active_loops:
                self._active_loops[sound_id]['volume'] = updated_data.get('volume', 1.0)
                self._active_loops[sound_id]['routing'] = updated_data.get('loop_routing', 'after')

        if sound_id in self._active_scenes:
            # Check if effects actually changed to avoid expensive rebuilds on just volume/routing changes
            original_sound_data = self.find_sound_by_id(sound_id)
            if original_sound_data:
                old_effects = original_sound_data.get('effects', [])
                new_effects = updated_data.get('effects', [])
                # Perform a basic check. Because effects are dictionaries with lists/dicts,
                # we can compare their string representations or deep equality.
                # In Python, list of dicts can be compared directly for deep equality.
                if old_effects != new_effects:
                    self._update_scene_effects(sound_id, updated_data)
                    # We also need to keep the live config somewhat in sync for the next comparison
                    # during the active edit session, but the final save happens on accept.
                    # We update it temporarily here so the next volume change doesn't trigger a rebuild.
                    original_sound_data['effects'] = copy.deepcopy(new_effects)"""

if search in source:
    source = source.replace(search, replace)
    with open("voice_modulator.py", "w") as f:
        f.write(source)
    print("Patched apply_live_scene_update successfully")
else:
    print("Search string not found")
