with open("voice_modulator.py", "r") as f:
    source = f.read()

# Add self._active_preview_effects
search_init = """        self._active_loops = {} # dict mapping sound_id to {"array": numpy_array, "index": int, "routing": str, "volume": float}
        self._active_effects = {} # dict mapping sound_id to list of pedalboard effect objects
        self._audio_lock = threading.Lock() # To protect state changes during audio callback"""

replace_init = """        self._active_loops = {} # dict mapping sound_id to {"array": numpy_array, "index": int, "routing": str, "volume": float}
        self._active_effects = {} # dict mapping sound_id to list of pedalboard effect objects
        self._active_preview_effects = {} # dict mapping sound_id to the last applied effects config list
        self._audio_lock = threading.Lock() # To protect state changes during audio callback"""

source = source.replace(search_init, replace_init)

# Modify _apply_live_scene_update
search_update = """        if sound_id in self._active_scenes:
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

replace_update = """        if sound_id in self._active_scenes:
            # Check if effects actually changed to avoid expensive rebuilds on just volume/routing changes
            old_effects = self._active_preview_effects.get(sound_id)
            # If not in our preview cache, fallback to checking the original data config
            if old_effects is None:
                original_sound_data = self.find_sound_by_id(sound_id)
                old_effects = original_sound_data.get('effects', []) if original_sound_data else []

            new_effects = updated_data.get('effects', [])

            if old_effects != new_effects:
                self._update_scene_effects(sound_id, updated_data)
                # Store the currently applied preview config so the next volume change
                # does not needlessly rebuild the pedalboard chain, without corrupting the app config
                self._active_preview_effects[sound_id] = copy.deepcopy(new_effects)"""

source = source.replace(search_update, replace_update)

# Clean up in deactivate scene
search_deactivate = """        if sound_id in self._active_effects:
            del self._active_effects[sound_id]
            self._rebuild_pedalboard()"""

replace_deactivate = """        if sound_id in self._active_preview_effects:
            del self._active_preview_effects[sound_id]

        if sound_id in self._active_effects:
            del self._active_effects[sound_id]
            self._rebuild_pedalboard()"""

source = source.replace(search_deactivate, replace_deactivate)

# Clean up in deactivate all scenes
search_deactivate_all = """        self._active_effects.clear()
        self._rebuild_pedalboard()"""

replace_deactivate_all = """        self._active_preview_effects.clear()
        self._active_effects.clear()
        self._rebuild_pedalboard()"""

source = source.replace(search_deactivate_all, replace_deactivate_all)

with open("voice_modulator.py", "w") as f:
    f.write(source)

print("Patched preview cache successfully")
