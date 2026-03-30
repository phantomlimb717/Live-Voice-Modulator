# 🎤 Live-Voice-Modulator

A real-time Python voice modulator and audio routing tool designed for live streaming, gaming, and voice chat. An open-source replacement for VoiceMod, allowing you to route your microphone through a virtual audio cable while applying studio-quality effects and mixing loopable background noises.

![Voice Modulator Concept](https://i.imgur.com/hopqYDF.png) *(Note: UI will be updated in a future release)*

## 📖 Background

Originally starting as a straightforward soundboard, this project has pivoted into a powerful, real-time voice modulation suite. Whether you want to sound like you're talking through a crappy radio, a massive cathedral, or just want to add a loopable bathroom fan sound to your mic feed, this tool has you covered. Built on the robust PySide6 framework, it leverages Spotify's `pedalboard` library for high-performance, low-latency audio processing.

## ✨ Features (Planned & Current)

*   **🎤 Real-Time Voice Processing:** Pipe your microphone audio through a processing chain with ~30-50ms latency, perfect for Discord or OBS.
*   **🎛️ Built-in Effects:** Native support for Reverb, Distortion ("Crappy Mic"), Bitcrushing ("Lossy Compression"), EQ, and more.
*   **🔌 VST3 Plugin Support:** Load your own VST3 plugins and access their native GUI pop-ups for ultimate customization.
*   **🔁 Loopable Background Noises:** Mix your modulated voice with continuous background audio (e.g., ambient room noise, a humming server, or a bathroom fan).
*   **🎧 Flexible Audio Routing:** Output your final mix directly to a virtual audio cable (like VB-Cable) to use as your microphone in any application.
*   **⌨️ System-Wide Hotkeys:** Toggle voice effects, start/stop background loops, and mute your microphone from anywhere on your computer using `pynput`.
*   **💅 Modern Interface:** A sleek, dark-themed PySide6 interface that makes managing complex audio chains simple.

## 🚀 Getting Started

### 1. Install a Virtual Audio Cable

To use this as a microphone replacement in other apps, you *must* install a virtual audio cable. We recommend VB-CABLE, which is free.

1.  **Download:** Go to the [VB-Audio Website](https://vb-audio.com/Cable/) and download the "VB-CABLE Driver Pack".
2.  **Extract:** Unzip the downloaded file.
3.  **Install:** Right-click on `VBCABLE_Setup_x64.exe` (or the 32-bit version if needed) and select **"Run as administrator"**.
4.  **Reboot:** Restart your computer to complete the installation.

### 2. Install Live-Voice-Modulator

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Live-Voice-Modulator.git
    cd Live-Voice-Modulator
    ```

2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    > **Note:** The `pedalboard` package is the core engine for our real-time audio effects. `sounddevice` handles the low-latency audio streams.

3.  **Run the application:**
    ```bash
    python soundboard.py  # (Note: The main entry point will be renamed in a future update)
    ```

## Usage (Audio Routing)

### Discord / Voice Chat Setup

1.  **In Live-Voice-Modulator:**
    *   Set your **Input Device** to your physical microphone (e.g., Blue Yeti, Focusrite).
    *   Set your **Output Device** to your virtual cable input (e.g., `CABLE Input (VB-Audio Virtual Cable)`).
2.  **In Discord (or similar app):**
    *   Set your **Input Device (Microphone)** to your virtual cable output (e.g., `CABLE Output (VB-Audio Virtual Cable)`).
    *   *Tip: Turn off Discord's built-in noise suppression/echo cancellation for the best effect quality.*

## 🛠️ Tech Stack & Acknowledgements

*   **GUI:** PySide6 (Qt for Python)
*   **Audio I/O:** `sounddevice` (PortAudio wrapper) and `numpy`
*   **Effects Engine:** `pedalboard` (C++ based audio processing wrapper developed by Spotify for their Soundtrap DAW and podcasting tools).
*   **Hotkeys:** `pynput`

## 📝 License

This project is licensed under the **GNU Lesser General Public License v3.0**. See the [LICENSE](LICENSE) file for more details.
