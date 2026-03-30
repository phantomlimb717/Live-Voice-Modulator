with open('voice_modulator.py', 'r') as f:
    c = f.read()

if 'QTabWidget' in c:
    print('QTabWidget found')
else:
    print('No QTabWidget')

if 'toggle_scene_from_button' in c:
    print('toggle_scene_from_button found')

if 'toggle_scene_from_hotkey_qt' in c:
    print('toggle_scene_from_hotkey_qt found')

print(c.count('QScrollArea'))
