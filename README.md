# KAIROS-STT

**System-wide offline Speech-to-Text for Windows**

[![Python](https://img.shields.io/badge/Python-3.11.9-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Offline](https://img.shields.io/badge/STT-100%25%20Offline-green)](https://github.com/ss10ss/KAIROS-STT)

Hold a hotkey, speak anywhere on your desktop, and have transcribed text pasted at your cursor — no cloud, no browser tab, no copy-paste step.

**Developer:** [Shashank Srivastava](https://github.com/ss10ss)  
**Repository:** [github.com/ss10ss/KAIROS-STT](https://github.com/ss10ss/KAIROS-STT)

---

## ✨ Features

| | |
|---|---|
| 🎙️ **Push-to-talk** | Press and hold **Ctrl+Alt+Space** to record voice anywhere on Windows |
| ⚡ **Instant paste** | Release the hotkey to transcribe and auto-paste text at the active cursor |
| 🪟 **Works everywhere** | Dictate into any application — editors, browsers, chat apps, and more |
| 🟢 **Tray status** | System tray icon shows **green** when idle, **red** when recording |
| 🌐 **Multilingual** | English and Hindi out of the box, with an architecture ready for more languages |
| 🔒 **Private & offline** | 100% offline after the first model download — your audio never leaves your machine |
| 🖱️ **Tray controls** | Right-click the tray icon for language selection and quit |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11.9 |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`small` model) |
| Audio capture | [sounddevice](https://python-sounddevice.readthedocs.io/) |
| Global hotkeys | [keyboard](https://github.com/boppreh/keyboard) |
| Clipboard & paste | [pyperclip](https://pypi.org/project/pyperclip/), [PyAutoGUI](https://pyautogui.readthedocs.io/) |
| System tray | [pystray](https://pystray.readthedocs.io/) + [Pillow](https://python-pillow.org/) |
| Packaging | [PyInstaller](https://pyinstaller.org/) |

---

## 📋 Requirements

- **OS:** Windows 10 or 11 (64-bit)
- **RAM:** 4 GB minimum
- **Internet:** Required **only on first run** to download the Whisper model (~500 MB)
- **Microphone:** Any standard input device
- **Permissions:** Administrator rights may be required for global hotkey capture

---

## 📥 Installation

### Pre-built executable (recommended)

1. Download **`KairosSTT.exe`** from the [Releases](https://github.com/ss10ss/KAIROS-STT/releases) page.
2. Run the executable — no installer or setup wizard needed.
3. On first launch, the app downloads the Whisper `small` model automatically to:
   ```
   %LOCALAPPDATA%\KairosSTT\models\
   ```
4. Look for the tray icon near the clock (hidden icons area). Wait for the **"Ready"** notification.

> **Note:** Windows SmartScreen may flag unsigned executables. Choose **More info → Run anyway** if you trust the source.

---

## 🚀 Usage

1. **Launch** `KairosSTT.exe` (or run from source — see below).
2. **Hold** `Ctrl` + `Alt` + `Space` and speak clearly.
3. **Release** any of the three keys to stop recording.
4. Transcribed text is copied to the clipboard and pasted at your cursor via `Ctrl+V`.

### Tray menu

Right-click the tray icon to:

- **Language** — switch between English and Hindi
- **Quit** — exit the application

### Logs & config

| Path | Purpose |
|------|---------|
| `%LOCALAPPDATA%\KairosSTT\config.json` | Saved language preference |
| `%LOCALAPPDATA%\KairosSTT\kairos_stt.log` | Application log |

---

## 💻 Development

### Run from source

```powershell
git clone https://github.com/ss10ss/KAIROS-STT.git
cd KAIROS-STT
pip install faster-whisper sounddevice keyboard pyperclip pyautogui pystray Pillow
python kairos_stt.py
```

### Build executable

```powershell
pip install pyinstaller
pyinstaller KairosSTT.spec
```

Output: `dist\KairosSTT.exe`

### Adding languages

Edit the `LANGUAGES` dictionary in `kairos_stt.py`:

```python
LANGUAGES: dict[str, str] = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",  # example
}
```

New entries appear automatically in the tray menu.

---

## ⚠️ Troubleshooting

| Issue | Suggestion |
|-------|------------|
| Hotkey not detected | Run as **Administrator** — global hooks require elevated privileges on some systems |
| No tray icon | Check the hidden icons overflow (^) next to the clock |
| Model download fails | Verify internet connectivity on first run; check `%LOCALAPPDATA%\KairosSTT\kairos_stt.log` |
| Empty transcription | Speak closer to the mic; hold the hotkey for at least ~0.25 seconds |
| Paste not working | Text is still copied to the clipboard — paste manually with `Ctrl+V` |

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/ss10ss">Shashank Srivastava</a>
</p>
