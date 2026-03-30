import re

with open('voice_modulator.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace old comments and class names
code = code.replace("class SoundButton(QPushButton):", "class SceneButton(QPushButton):")

code = code.replace("btn = SoundButton(sound_data);", "btn = SceneButton(sound_data);")

code = code.replace("isinstance(widget, SoundButton)", "isinstance(widget, SceneButton)")

# Replace instances of SoundboardWindow
code = code.replace("class SoundboardWindow(QMainWindow):", "class VoiceModulatorWindow(QMainWindow):")
code = code.replace("isinstance(main_window, SoundboardWindow)", "isinstance(main_window, VoiceModulatorWindow)")
code = code.replace("main_window = SoundboardWindow()", "main_window = VoiceModulatorWindow()")
code = code.replace("SoundboardWindow.show_critical_error_popup", "VoiceModulatorWindow.show_critical_error_popup")


# Fix button css
old_style_active = "self.setStyleSheet(base_style + \"QPushButton { background-color: #208020; border: 1px solid #00FF00; }\" + pressed_style + hover_style)"
new_style_active = "self.setStyleSheet(base_style + \"QPushButton { background-color: #30A030; border: 1px solid #50FF50; font-weight: bold; }\" + pressed_style + hover_style)"
code = code.replace(old_style_active, new_style_active)

old_btn_init = "self.setMinimumHeight(60); self.update_appearance()"
new_btn_init = "self.setMinimumHeight(50); self.update_appearance()"
code = code.replace(old_btn_init, new_btn_init)

# Fix dark theme tab CSS string that might have been partially removed
theme_str = 'QTabBar::tab{background:#444;color:#CCC;border:1px solid #555;border-bottom:none;padding:5px 10px;margin-right:2px}QTabBar::tab:selected{background:#555;color:#FFF;margin-bottom:-1px}QTabBar::tab:hover{background:#5A5A5A}'
code = code.replace(theme_str, '')
theme_str2 = 'QTabWidget::pane{border-top:1px solid #444;background-color:#282828}'
code = code.replace(theme_str2, '')


# Update texts
code = code.replace('"Add Sound(s)"', '"Add Scene/Effect"')
code = code.replace('"Search sounds..."', '"Search scenes/effects..."')
code = code.replace('"Manage Sound Groups"', '"Manage Scene Groups"')
code = code.replace('"Soundboard App Stopping"', '"Voice Modulator App Stopping"')
code = code.replace('"Soundboard App Finished."', '"Voice Modulator App Finished."')


with open('voice_modulator.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("done")
