"""Optional offline audio input and Windows speech, with no import-time audio I/O."""
import importlib.util
import json
import re
import subprocess
import threading
import unicodedata
from pathlib import Path


def spoken_text(text):
    text = re.sub(r'```[\s\S]*?```', ' Code is shown in the chat. ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', ' website link ', text)
    text = re.sub(r'(?m)^\s*[#>*•-]+\s*', '', text)
    text = text.replace('**', '').replace('`', '').strip()
    if len(text) > 1800:
        text = text[:1800].rsplit(' ', 1)[0] + '. The full reply is in the chat.'
    return text


def resample_pcm(chunks, sample_rate):
    import numpy as np
    pcm = np.frombuffer(b''.join(chunks), dtype=np.int16)
    if sample_rate == 16000 or not pcm.size:
        return pcm.astype(np.float32) / 32768.0
    # Use the bundled FFmpeg resampler, including its anti-alias filter.
    import av
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format='s16', layout='mono')
    frame.sample_rate = sample_rate
    resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)
    frames = resampler.resample(frame) + resampler.resample(None)
    return np.concatenate([f.to_ndarray().reshape(-1) for f in frames]).astype(np.float32)


def choose_mixed_language(probabilities):
    """Never choose a third language for the English/Hindi profile."""
    probabilities = dict(probabilities)
    english, hindi = probabilities.get('en', 0), probabilities.get('hi', 0)
    return 'hi' if hindi >= .20 and hindi > english * 1.2 else 'en'


def expected_script(text):
    letters = [unicodedata.name(c, '') for c in text if c.isalpha()]
    return not letters or sum('LATIN' in n or 'DEVANAGARI' in n for n in letters) / len(letters) >= .8


class VoiceController:
    def __init__(self, events, base, data):
        self.events, self.base, self.data = events, Path(base), Path(data)
        small = self.data / 'voice-model-small'
        required = ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt')
        use_small = all((small / name).is_file() for name in required)
        self.model_path = small if use_small else self.data / 'voice-model'
        self.model_name = 'Small' if use_small else 'Base'
        self.model = None
        self.input_busy = False
        self.recording = False
        self.stop_recording = threading.Event()
        self.speech_lock = threading.Lock()
        self.speech_process = None
        self.speech_generation = 0
        self.closed = False

    def ready(self):
        return (importlib.util.find_spec('sounddevice') is not None and
                importlib.util.find_spec('faster_whisper') is not None and
                (self.model_path / 'model.bin').is_file())

    def helper(self, mode):
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                str(self.base / 'windows-voice.ps1'), '-Mode', mode]

    def installed_voices(self):
        result = subprocess.run(self.helper('list'), capture_output=True, encoding='utf-8', errors='replace',
                                timeout=20, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('Windows voices could not be loaded. ' + result.stderr[-350:])
        voices = json.loads(result.stdout.lstrip('\ufeff') or '[]')
        return voices if isinstance(voices, list) else [voices]

    def input_devices(self):
        import sounddevice as sd
        devices = sd.query_devices()
        return [{'id': i, 'name': d['name']} for i, d in enumerate(devices) if d['max_input_channels'] > 0]

    def start_recording(self, device=None, language='en'):
        if self.input_busy:
            return False
        if not self.ready():
            raise RuntimeError('Voice setup is not complete. Close ASUNA and run Setup Voice.bat, then reopen it.')
        self.stop_speaking()
        self.input_busy = True
        self.stop_recording.clear()
        threading.Thread(target=self.capture, args=(device, language), daemon=True).start()
        return True

    def capture(self, device, language):
        try:
            import sounddevice as sd
            import numpy as np
            info = sd.query_devices(device, 'input')
            rate = int(info['default_samplerate'])
            sd.check_input_settings(device=device, channels=1, dtype='int16', samplerate=rate)
            chunks, errors = [], []
            frames = 0

            def callback(data, count, timing, status):
                nonlocal frames
                if status:
                    errors.append(str(status))
                remaining = max(0, 30 * rate - frames)
                chunks.append(bytes(data)[:remaining * 2])
                frames += min(remaining, count)
                if frames >= 30 * rate:
                    self.stop_recording.set()

            with sd.RawInputStream(device=device, channels=1, dtype='int16', samplerate=rate, callback=callback):
                self.recording = True
                self.events.put(('voice_recording', None))
                self.stop_recording.wait(31)
            self.recording = False
            if self.closed:
                return
            if errors:
                raise RuntimeError('Microphone audio was interrupted. Please try again or choose another input device.')
            audio = resample_pcm(chunks, rate)
            if len(audio) < 1600 or not audio.size or float(np.max(np.abs(audio))) < .005:
                raise RuntimeError('No clear speech was recorded. Speak closer to the microphone and try again.')
            self.events.put(('voice_status', 'Transcribing locally…'))
            text = self.transcribe(audio, language)
            if not text:
                raise RuntimeError('No speech was recognized. Try again; nothing was sent.')
            if not self.closed:
                self.events.put(('voice_transcript', text))
        except Exception as exc:
            if not self.closed:
                self.events.put(('voice_error', str(exc)))
        finally:
            self.recording = False
            self.input_busy = False

    def transcribe(self, audio, language='en'):
        if self.model is None:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(str(self.model_path), device='cpu', compute_type='int8',
                                      cpu_threads=4, local_files_only=True)
        profile = language
        if language == 'mixed':
            if isinstance(audio, (str, Path)):
                from faster_whisper.audio import decode_audio
                audio = decode_audio(str(audio), sampling_rate=16000)
            _, _, probabilities = self.model.detect_language(audio=audio, vad_filter=True)
            language = choose_mixed_language(probabilities)
        segments, _ = self.model.transcribe(audio, language=language, task='transcribe', vad_filter=True,
                                            beam_size=5, temperature=0.0,
                                            hotwords='ASUNA, Ollama, YouTube',
                                            condition_on_previous_text=False)
        text = ' '.join(s.text.strip() for s in segments if s.text.strip()).strip()
        if profile in ('en', 'hi', 'mixed') and not expected_script(text):
            raise RuntimeError('Recognition produced an unexpected language/script. Nothing was sent. Try again or select English/Hindi explicitly.')
        return text

    def speak(self, text, voice=''):
        text = spoken_text(text)
        if not text or self.input_busy or self.closed:
            return
        self.stop_speaking()
        with self.speech_lock:
            generation = self.speech_generation
        threading.Thread(target=self.speech_worker, args=(text, voice, generation), daemon=True).start()

    def speech_worker(self, text, voice, generation):
        proc = None
        try:
            with self.speech_lock:
                if self.closed or generation != self.speech_generation:
                    return
                proc = subprocess.Popen(self.helper('speak'), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self.speech_process = proc
            self.events.put(('speech_status', (generation, 'Speaking…')))
            _, error = proc.communicate(json.dumps({'text': text, 'voice': voice}, ensure_ascii=False).encode('utf-8'), timeout=240)
            with self.speech_lock:
                cancelled = generation != self.speech_generation or self.closed
            if proc.returncode and not cancelled:
                raise RuntimeError('Speech playback failed. ' + error.decode('utf-8', errors='replace')[-350:])
            if not cancelled:
                self.events.put(('speech_status', (generation, 'Voice ready')))
        except Exception as exc:
            with self.speech_lock:
                cancelled = generation != self.speech_generation or self.closed
            if proc and proc.poll() is None:
                proc.kill()
                proc.communicate()
            if not cancelled:
                self.events.put(('voice_error', str(exc)))
        finally:
            with self.speech_lock:
                if self.speech_process is proc:
                    self.speech_process = None

    def stop_speaking(self):
        with self.speech_lock:
            self.speech_generation += 1
            if self.speech_process and self.speech_process.poll() is None:
                self.speech_process.terminate()

    def close(self):
        self.closed = True
        self.stop_recording.set()
        self.stop_speaking()
