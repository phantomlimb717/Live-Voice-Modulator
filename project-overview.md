# 🎙️ Live-Voice-Modulator: Project Overview & Roadmap

This document serves as a high-level roadmap and architectural guide for pivoting the `Live-Soundboard` codebase into a real-time voice modulation application (`Live-Voice-Modulator`).

## 🎯 Project Vision

The goal is to create an open-source, highly customizable replacement for commercial voice modulators like VoiceMod. The application will take microphone input, apply low-latency real-time effects (like Reverb, Distortion, or Bitcrushing), mix in loopable background audio (e.g., ambient room noise, a humming server), and output the final mix to a virtual audio cable for use in Discord, OBS, or in-game voice chat.

We are leveraging the existing PySide6 UI and `pynput` hotkey system from the soundboard project to accelerate development.

## 🏗️ Core Architecture (The "Processing Chain")

The new architecture requires shifting from *playing static files on demand* to *continuously processing an active audio stream*.

```text
[ Physical Microphone (Input Device) ]
       │
       ▼
[ sounddevice InputStream (Chunked Audio) ]
       │
       ▼ (numpy float32 arrays)
[ Pedalboard Processing Chain ] ────────────────────────┐
   ├─ Noise Gate (Optional but recommended)             │
   ├─ VST3 Plugins (GUI popup support needed)           │
   ├─ Distortion ("Crappy Mic")                         │
   ├─ Bitcrush ("Lossy Compression")                    │
   └─ Reverb                                            │
       │                                                │
       ▼                                                ▼
[ Audio Mixer (numpy addition) ] ◄────────────── [ Loopable Background Noise Player ]
       │                                         (e.g., "Bathroom Fan.mp3")
       ▼
[ sounddevice OutputStream (Virtual Cable) ]
       │
       ▼
[ Discord / OBS / Game ]
```

## 🛠️ Tech Stack & Rationale

*   **UI:** `PySide6`. The existing robust UI will be refactored. The "grid of buttons" will transition from triggering one-shot sounds to toggling specific effects chains or background noise loops.
*   **Audio I/O:** `sounddevice` and `numpy`. We need low-level access to the audio buffer. `sounddevice` allows us to open a simultaneous `InputStream` and `OutputStream` (or a combined `Stream`) to process audio in chunks (blocks).
*   **Audio Effects:** `pedalboard`.
    *   *Why Pedalboard?* Developed by Spotify for their online Soundtrap DAW, `pedalboard` is a Python wrapper around heavily optimized C++ JUCE framework code. It is significantly faster and lower latency than trying to write native Python audio effects.
    *   *Features:* It natively supports the effects we need (Reverb, Distortion, Bitcrush) and crucially, it supports loading third-party `VST3` plugins, which is a massive feature for advanced users.
*   **Hotkeys:** `pynput`. The global hotkey listener will remain to toggle effects or mute the mic while the app is minimized.

## 🗺️ Development Roadmap

### Phase 1: Core Audio Engine Refactor (The "Plumbing")
*   [x] Rename core files (`soundboard.py` -> `voice_modulator.py`).
*   [x] Rip out the one-shot `pydub` playback threads.
*   [x] Implement a continuous `sounddevice.Stream` that reads from the selected Input Device and writes to the selected Output Device.
*   [x] Establish the basic `pedalboard` `Pedalboard([])` object in the stream callback to prove audio passes through.
*   [x] Implement a basic UI to select the Input (Microphone) and Output (VB-Cable) devices and save them to `config.json`.

### Phase 2: Effects & Loop Implementation (The "Fun Stuff")
*   [x] Create UI controls (sliders/toggles) for native `pedalboard` effects (Reverb, Distortion/Drive, Bitcrush).
*   [x] Implement the logic to dynamically update the `Pedalboard` chain while the stream is running without causing audio dropouts.
*   [x] Implement the "Background Noise Mixer". Allow a user to select an audio file, loop it continuously in a separate thread/generator, and add its numpy array to the microphone's processed numpy array before sending it to the OutputStream.
*   [x] Wire existing PySide6 buttons to toggle these effects/loops on and off.

### Phase 3: VST3 Support & Advanced UI
*   [x] Add a file picker in the UI to load `.vst3` files.
*   [x] Integrate the VST3 plugin into the `pedalboard` chain.
*   [x] **Crucial:** Implement the `plugin.show_editor()` method provided by `pedalboard` to open the VST3's native GUI window. Note: This window runs in a separate process/thread handled by the OS/JUCE, so we need to ensure it doesn't block our PySide6 event loop.

### Phase 4: Polish & Performance
*   [ ] Refine the global hotkey system to map to the new toggle actions instead of one-shot playback.
*   [ ] Optimize numpy array slicing and mixing for the background loops to minimize CPU overhead.
*   [ ] Finalize the dark-themed UI layout (moving away from the "soundboard tabs" to a more "rack-mount" or "mixer channel" look).

---

## 👨‍💻 Developer Notes (For Jules & User)

*   **Latency vs. Stability:** The biggest challenge will be the `blocksize` (chunk size) in `sounddevice`.
    *   Smaller blocksize (e.g., 128, 256) = Lower latency (better for real-time), but higher CPU usage and risk of audio dropouts/crackling (buffer underruns).
    *   Larger blocksize (e.g., 1024, 2048) = Extremely stable audio, but noticeable latency (echo).
    *   *Goal:* We are aiming for roughly 512 frames at 48000Hz, which yields about ~10ms of algorithmic latency. Combined with OS buffers, this should hit our target of 30-50ms round-trip.
*   **The Stream Callback:** The `sounddevice` callback function must be *lightning fast*. We cannot do any heavy lifting, file I/O, or UI updates inside the callback. It should strictly:
    1. Read the input numpy array.
    2. Pass it through the pre-configured `pedalboard` object.
    3. Add the pre-loaded background loop chunk (if active).
    4. Write to the output numpy array.
*   **State Management:** When a user toggles an effect in the PySide6 UI, we must carefully update the `pedalboard` object that the audio thread is currently using. We may need to use threading locks (`threading.Lock`) or construct a new `Pedalboard` object and atomically swap it out to prevent crashing the audio stream.
