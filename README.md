# 🔊 Live-Soundboard

A straightforward soundboard for live streaming, gaming, and voice chat. Play sounds and easily route them to any application like OBS or Discord using a virtual audio cable.

![Soundboard Screenshot](https://i.imgur.com/hopqYDF.png)

## 📖 Background

This project started with a simple goal: to have the perfect sound effect ready for any moment in a multiplayer game with friends. It has since evolved into a more powerful tool for streamers and content creators, but at its heart, it's about adding a bit of fun and personality to your online interactions.

## ✨ Features

*   **🎧 Flexible Audio Routing:** Directly output audio to any playback device, including virtual audio cables like VB-Cable, allowing for easy integration with streaming software like OBS or voice chat applications.
*   **⌨️ System-Wide Hotkeys:** Trigger sounds from anywhere on your computer, even when the soundboard is minimized or you're in a full-screen game. (Requires `pynput`)
*   **🎛️ Sound Customization:** Adjust the volume for each sound individually and apply audio effects like Reverb and Delay.
*   **📂 Sound Organization:** Group your sounds into tabs for better organization and quick access.
*   **🔍 Quick Search:** Easily find the sound you're looking for with a built-in search bar that filters sounds in the current tab.
*   **💅 Modern Interface:** A sleek, dark-themed interface that is easy to navigate.

## 🚀 Getting Started

### 1. Install a Virtual Audio Cable

This soundboard requires a virtual audio cable to route audio to other applications. We recommend VB-CABLE, which is free.

1.  **Download:** Go to the [VB-Audio Website](https://vb-audio.com/Cable/) and download the "VB-CABLE Driver Pack".
2.  **Extract:** Unzip the downloaded file.
3.  **Install:** Right-click on `VBCABLE_Setup_x64.exe` (or the 32-bit version if needed) and select **"Run as administrator"**.
4.  **Reboot:** Restart your computer to complete the installation.

### 2. Install Live-Soundboard

Once you have a virtual audio cable installed, you can install the soundboard.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Live-Soundboard.git
    cd Live-Soundboard
    ```

2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    > **Note:** The `pedalboard` and `pynput` packages are optional but included in `requirements.txt` for a full-featured experience. `pedalboard` is for audio effects, and `pynput` is for global hotkey support.

3.  **Download the sound pack:**
    A starter sound pack is available [here](https://files.catbox.moe/qvrvbo.zip). Download and extract the `sounds` folder into the root directory of the project.

4.  **Run the application:**
    ```bash
    python soundboard.py
    ```

## Usage

### OBS Integration

The integration with OBS is not automatic, but it is straightforward. Here's how to set it up:

1.  **In the Soundboard Application:**
    *   Go to `File > Settings`.
    *   In the `Audio Output Device` dropdown, select your virtual audio cable's **input** device (e.g., `CABLE Input (VB-Audio Virtual Cable)`).
    *   Click `OK` to save.

2.  **In OBS Studio:**
    *   In the `Sources` panel, click the `+` button and add an `Audio Input Capture` source.
    *   Name it something descriptive, like "Soundboard".
    *   In the properties for the new source, select your virtual audio cable's **output** device (e.g., `CABLE Output (VB-Audio Virtual Cable)`) from the `Device` dropdown.
    *   Click `OK`.

Now, any sound played from the soundboard will be routed through the virtual cable and captured by OBS as a separate audio source, which you can then mix into your stream.

### Adding and Managing Sounds

*   **Add Sounds:** Click the "Add Sound(s)" button to open a file dialog and select one or more audio files. They will be added to the "Default" group.
*   **Edit Sounds:** Right-click on any sound button to open a context menu where you can:
    *   **Edit Properties:** Change the sound's name, volume, and group. You can also enable and configure effects here.
    *   **Assign Hotkey:** Set a global hotkey for the sound.
    *   **Relink Missing File:** If a sound file has been moved, you can relink it to its new location.
    *   **Delete Sound:** Remove the sound from the soundboard.
*   **Manage Groups:** Go to `Edit > Manage Groups` to add, rename, or delete sound groups (tabs).

## Advanced Usage

### Using Your OBS Audio Mix as a Microphone

This advanced guide explains how to send the  audio mix from OBS (including your microphone and soundboard sounds) as a single microphone input to other applications like Discord, Zoom, or in-game voice chat.

**Prerequisite:** This requires a second virtual audio cable. This guide assumes you have downloaded and installed the **VB-CABLE A+B** pack from VB-Audio.

#### 1. OBS Setup

1.  **Add All Audio Sources to OBS:** Make sure your microphone and the soundboard (as configured in the guide above) are all active audio sources in your OBS Audio Mixer.

2.  **Set Your Monitoring Device:**
    *   Go to `File > Settings > Audio`.
    *   Under the "Advanced" section, find the `Monitoring Device` dropdown.
    *   Set this to your second virtual cable, for example, **`CABLE-A Input (VB-Audio Cable A)`**.
    *   Click `OK`.

3.  **Enable Audio Monitoring for All Sources:**
    *   In the `Audio Mixer` panel in OBS, click the gear icon for **every** audio source you want to include in your mix (your mic, the soundboard, etc.).
    *   Select `Advanced Audio Properties`.
    *   For each source, change the `Audio Monitoring` dropdown from "Monitor Off" to **"Monitor and Output"**.

#### 2. Windows Setup

1.  **Set Your Default Microphone:**
    *   Open your Windows Sound settings (right-click the speaker icon in your taskbar and select "Sounds").
    *   Go to the `Recording` tab.
    *   Find the output of your second virtual cable, for example, **`CABLE-A Output (VB-Audio Cable A)`**.
    *   Right-click on it and select **"Set as Default Device"** and **"Set as Default Communication Device"**.

Now, any application on your computer that uses your default microphone will receive the full audio mix from OBS. Enjoy annoying your friends and teammates!

## 📝 License

This project is licensed under the **GNU Lesser General Public License v3.0**. See the [LICENSE](LICENSE) file for more details.
