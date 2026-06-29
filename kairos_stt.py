"""
Kairos STT — system-wide offline speech-to-text for Windows 11.

Usage: python kairos_stt.py
PyInstaller: pyinstaller KairosSTT.spec
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
import keyboard
import numpy as np
import pyautogui
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw
from pystray import MenuItem as item

# ---------------------------------------------------------------------------
# Configuration — extend LANGUAGES to add more Whisper language codes later
# ---------------------------------------------------------------------------

APP_NAME = "KairosSTT"
MODEL_SIZE = "small"
SAMPLE_RATE = 16_000
CHANNELS = 1
MIN_RECORD_SECONDS = 0.25

LANGUAGES: dict[str, str] = {
    "English": "en",
    "Hindi": "hi",
}

CTRL_KEYS = frozenset({"ctrl", "left ctrl", "right ctrl"})
ALT_KEYS = frozenset({"alt", "left alt", "right alt"})
HOTKEY_LABEL = "Ctrl+Alt+Space"

# ---------------------------------------------------------------------------
# Paths (AppData — works for dev runs and PyInstaller builds)
# ---------------------------------------------------------------------------


def app_data_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return app_data_dir() / "config.json"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(app_data_dir() / "kairos_stt.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(APP_NAME)

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------


class State:
    LOADING = "loading"
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class KairosSTT:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = State.LOADING
        self._language = self._load_language()
        self._model = None
        self._icon: pystray.Icon | None = None

        self._ctrl_down = False
        self._alt_down = False
        self._space_down = False
        self._combo_held = False

        self._audio_chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._stop_event = threading.Event()

        self._idle_icon = self._make_icon((34, 197, 94))
        self._record_icon = self._make_icon((239, 68, 68))

    # ----- persistence -----------------------------------------------------

    def _load_language(self) -> str:
        default = LANGUAGES["English"]
        path = config_path()
        if not path.exists():
            return default
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            code = data.get("language", default)
            if code in LANGUAGES.values():
                return code
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            log.warning("Could not read config: %s", exc)
        return default

    def _save_language(self) -> None:
        try:
            config_path().write_text(
                json.dumps({"language": self._language}, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            log.error("Could not save config: %s", exc)

    # ----- tray UI ---------------------------------------------------------

    @staticmethod
    def _make_icon(rgb: tuple[int, int, int]) -> Image.Image:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, size - 8, size - 8), fill=(*rgb, 255))
        return img

    def _notify(self, title: str, message: str) -> None:
        log.info("%s: %s", title, message)
        if self._icon is not None:
            try:
                self._icon.notify(message, title)
            except Exception as exc:  # noqa: BLE001 — tray may be unavailable
                log.warning("Tray notification failed: %s", exc)

    def _set_icon_image(self, image: Image.Image) -> None:
        if self._icon is not None:
            self._icon.icon = image

    def _language_label(self, code: str) -> str:
        for label, lang_code in LANGUAGES.items():
            if lang_code == code:
                return label
        return code

    def _build_menu(self) -> pystray.Menu:
        language_items = [
            item(
                label,
                lambda _, c=code: self._select_language(c),
                checked=lambda _, c=code: self._language == c,
                radio=True,
            )
            for label, code in LANGUAGES.items()
        ]
        return pystray.Menu(
            item("Language", pystray.Menu(*language_items)),
            pystray.Menu.SEPARATOR,
            item("Quit", self._quit),
        )

    def _select_language(self, code: str) -> None:
        with self._lock:
            self._language = code
        self._save_language()
        label = self._language_label(code)
        self._notify(APP_NAME, f"Language set to {label}")

    def _quit(self, _icon: pystray.Icon | None = None, _item: item | None = None) -> None:
        log.info("Shutting down")
        self._stop_event.set()
        keyboard.unhook_all()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
        if self._icon is not None:
            self._icon.stop()

    # ----- model -------------------------------------------------------------

    def _load_model_thread(self) -> None:
        try:
            from faster_whisper import WhisperModel

            self._notify(APP_NAME, f"Downloading/loading '{MODEL_SIZE}' model (first run may take a while)…")
            model = WhisperModel(
                MODEL_SIZE,
                device="cpu",
                compute_type="int8",
                download_root=str(model_dir()),
            )
            with self._lock:
                self._model = model
                self._state = State.IDLE
            self._set_icon_image(self._idle_icon)
            self._notify(APP_NAME, f"Ready — hold {HOTKEY_LABEL} to dictate")
            log.info("Model loaded from %s", model_dir())
        except Exception as exc:
            log.exception("Model load failed")
            self._notify(APP_NAME, f"Model load failed: {exc}")

    # ----- audio -------------------------------------------------------------

    def _audio_callback(
        self,
        indata: np.ndarray,
        _frames: int,
        _time: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            log.warning("Audio status: %s", status)
        self._audio_chunks.append(indata.copy())

    def _start_recording(self) -> None:
        with self._lock:
            if self._state != State.IDLE or self._model is None:
                return
            self._state = State.RECORDING

        self._audio_chunks = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
            self._set_icon_image(self._record_icon)
            log.info("Recording started")
        except Exception as exc:
            log.exception("Could not start recording")
            with self._lock:
                self._state = State.IDLE
            self._set_icon_image(self._idle_icon)
            self._notify(APP_NAME, f"Microphone error: {exc}")

    def _stop_recording(self) -> np.ndarray | None:
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                log.warning("Error closing stream: %s", exc)

        if not self._audio_chunks:
            return None
        return np.concatenate(self._audio_chunks, axis=0).flatten()

    # ----- transcription & paste ---------------------------------------------

    def _transcribe_and_paste(self, audio: np.ndarray) -> None:
        with self._lock:
            model = self._model
            language = self._language
            if model is None:
                return
            self._state = State.TRANSCRIBING

        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_RECORD_SECONDS:
            with self._lock:
                self._state = State.IDLE
            self._set_icon_image(self._idle_icon)
            self._notify(APP_NAME, "Recording too short — try again")
            return

        try:
            segments, _info = model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
            )
            text = "".join(segment.text for segment in segments).strip()
        except Exception as exc:
            log.exception("Transcription failed")
            with self._lock:
                self._state = State.IDLE
            self._set_icon_image(self._idle_icon)
            self._notify(APP_NAME, f"Transcription failed: {exc}")
            return

        with self._lock:
            self._state = State.IDLE
        self._set_icon_image(self._idle_icon)

        if not text:
            self._notify(APP_NAME, "No speech detected")
            return

        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            log.info("Pasted: %r", text[:120])
        except Exception as exc:
            log.exception("Paste failed")
            self._notify(APP_NAME, f"Paste failed (text copied): {exc}")

    def _on_release(self, audio: np.ndarray | None) -> None:
        if audio is None:
            with self._lock:
                self._state = State.IDLE
            self._set_icon_image(self._idle_icon)
            self._notify(APP_NAME, "No audio captured")
            return
        threading.Thread(
            target=self._transcribe_and_paste,
            args=(audio,),
            daemon=True,
            name="transcribe",
        ).start()

    # ----- hotkey (Ctrl + Alt + Space hold) ----------------------------------

    def _on_key(self, event: keyboard.KeyboardEvent) -> None:
        if self._stop_event.is_set():
            return

        name = (event.name or "").lower()
        is_down = event.event_type == keyboard.KEY_DOWN

        if name in CTRL_KEYS:
            self._ctrl_down = is_down
        elif name in ALT_KEYS:
            self._alt_down = is_down
        elif name == "space":
            self._space_down = is_down
        else:
            return

        combo = self._ctrl_down and self._alt_down and self._space_down

        if combo and not self._combo_held:
            self._combo_held = True
            with self._lock:
                ready = self._state == State.IDLE and self._model is not None
                loading = self._state == State.LOADING
            if ready:
                self._start_recording()
            elif loading:
                self._notify(APP_NAME, "Still loading model — please wait")
            return

        if self._combo_held and not combo:
            self._combo_held = False
            with self._lock:
                recording = self._state == State.RECORDING
            if recording:
                audio = self._stop_recording()
                self._on_release(audio)

    def _keyboard_thread(self) -> None:
        keyboard.hook(self._on_key, suppress=False)
        while not self._stop_event.is_set():
            time.sleep(0.1)
        keyboard.unhook_all()

    # ----- main entry --------------------------------------------------------

    def run(self) -> None:
        pyautogui.FAILSAFE = False

        threading.Thread(
            target=self._load_model_thread,
            daemon=True,
            name="model-loader",
        ).start()
        threading.Thread(
            target=self._keyboard_thread,
            daemon=True,
            name="keyboard-hook",
        ).start()

        self._icon = pystray.Icon(
            APP_NAME,
            self._idle_icon,
            f"{APP_NAME} — hold {HOTKEY_LABEL} to dictate",
            menu=self._build_menu(),
        )
        self._icon.run()


def main() -> None:
    try:
        KairosSTT().run()
    except Exception as exc:
        log.exception("Fatal error")
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
                0,
                str(exc),
                f"{APP_NAME} — Fatal Error",
                0x10,
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
