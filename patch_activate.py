with open("voice_modulator.py", "r") as f:
    source = f.read()

search = """        # 2. Add Effects to Master Chain
        if _AUDIO_LIBS_LOADED and pedalboard:
            scene_effects = []
            for fx_config in sound_data.get('effects', []):
                if not fx_config.get('enabled', False):
                    continue

                fx_type = fx_config.get('type')
                params = fx_config.get('params', {})

                try:
                    if fx_type == "Reverb" and _pb_reverb_ok:
                        scene_effects.append(pedalboard.Reverb(room_size=params.get("room_size", 0.5)))
                    elif fx_type == "Delay" and _pb_delay_ok:
                        scene_effects.append(pedalboard.Delay(delay_seconds=params.get("delay_seconds", 0.5), feedback=params.get("feedback", 0.3)))
                    elif fx_type == "Distortion" and _pb_distortion_ok:
                        scene_effects.append(pedalboard.Distortion(drive_db=params.get("drive_db", 25.0)))
                    elif fx_type == "Bitcrush" and _pb_bitcrush_ok:
                        scene_effects.append(pedalboard.Bitcrush(bit_depth=params.get("bit_depth", 8.0)))
                    elif fx_type == "VST3 Plugin":
                        plugin_path = params.get("plugin_path")
                        plugin_state = params.get("plugin_state")
                        if plugin_path and os.path.exists(plugin_path):
                            loaded_vst = pedalboard.load_plugin(plugin_path)
                            if plugin_state:
                                try:
                                    import base64
                                    if isinstance(plugin_state, str):
                                        loaded_vst.raw_state = base64.b64decode(plugin_state)
                                    else:
                                        loaded_vst.raw_state = plugin_state
                                except Exception as e:
                                    print(f"Error restoring VST3 state: {e}")
                            scene_effects.append(loaded_vst)
                except Exception as e:
                    print(f"Error creating effect {fx_type}: {e}")

            if scene_effects:
                self._active_effects[sound_id] = scene_effects
                self._rebuild_pedalboard()"""

replace = """        # 2. Add Effects to Master Chain
        self._update_scene_effects(sound_id, sound_data)

    def _update_scene_effects(self, sound_id, sound_data):
        if not _AUDIO_LIBS_LOADED or not pedalboard:
            return

        scene_effects = []
        for fx_config in sound_data.get('effects', []):
            if not fx_config.get('enabled', False):
                continue

            fx_type = fx_config.get('type')
            params = fx_config.get('params', {})

            try:
                if fx_type == "Reverb" and _pb_reverb_ok:
                    scene_effects.append(pedalboard.Reverb(room_size=params.get("room_size", 0.5)))
                elif fx_type == "Delay" and _pb_delay_ok:
                    scene_effects.append(pedalboard.Delay(delay_seconds=params.get("delay_seconds", 0.5), feedback=params.get("feedback", 0.3)))
                elif fx_type == "Distortion" and _pb_distortion_ok:
                    scene_effects.append(pedalboard.Distortion(drive_db=params.get("drive_db", 25.0)))
                elif fx_type == "Bitcrush" and _pb_bitcrush_ok:
                    scene_effects.append(pedalboard.Bitcrush(bit_depth=params.get("bit_depth", 8.0)))
                elif fx_type == "VST3 Plugin":
                    plugin_path = params.get("plugin_path")
                    plugin_state = params.get("plugin_state")
                    if plugin_path and os.path.exists(plugin_path):
                        loaded_vst = pedalboard.load_plugin(plugin_path)
                        if plugin_state:
                            try:
                                import base64
                                if isinstance(plugin_state, str):
                                    loaded_vst.raw_state = base64.b64decode(plugin_state)
                                else:
                                    loaded_vst.raw_state = plugin_state
                            except Exception as e:
                                print(f"Error restoring VST3 state: {e}")
                        scene_effects.append(loaded_vst)
            except Exception as e:
                print(f"Error creating effect {fx_type}: {e}")

        if scene_effects:
            self._active_effects[sound_id] = scene_effects
        else:
            if sound_id in self._active_effects:
                del self._active_effects[sound_id]

        self._rebuild_pedalboard()"""

if search in source:
    new_source = source.replace(search, replace)
    with open("voice_modulator.py", "w") as f:
        f.write(new_source)
    print("Patched successfully")
else:
    print("Search string not found")
