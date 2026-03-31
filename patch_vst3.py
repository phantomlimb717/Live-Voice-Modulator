with open("voice_modulator.py", "r") as f:
    source = f.read()

search = """                        # Save the new state back to the widget's temporary state once closed
                        import base64
                        state_bytes = plugin.raw_state
                        if state_bytes:
                            # Encode as base64 string to be JSON serializable
                            widget_state_dict['current_state'] = base64.b64encode(state_bytes).decode('utf-8')

                        QMetaObject.invokeMethod(dialog_instance, "_emit_live_update", Qt.ConnectionType.QueuedConnection)
                    except Exception as e:
                        print(f"Error in VST3 editor thread: {e}")"""

replace = """                        # Save the new state back to the widget's temporary state once closed
                        import base64
                        state_bytes = plugin.raw_state
                        if state_bytes:
                            # Encode as base64 string to be JSON serializable
                            widget_state_dict['current_state'] = base64.b64encode(state_bytes).decode('utf-8')

                        try:
                            # Check if dialog_instance has been garbage collected or closed in C++
                            dialog_instance.objectName()
                            QMetaObject.invokeMethod(dialog_instance, "_emit_live_update", Qt.ConnectionType.QueuedConnection)
                        except RuntimeError:
                            # The C++ object was destroyed (user closed the edit dialog before closing VST gui)
                            pass
                    except Exception as e:
                        print(f"Error in VST3 editor thread: {e}")"""

if search in source:
    source = source.replace(search, replace)
    with open("voice_modulator.py", "w") as f:
        f.write(source)
    print("Patched VST3 thread successfully")
else:
    print("Search string not found")
