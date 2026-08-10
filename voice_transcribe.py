"""
voice_transcribe.py - Speech-to-text for incoming WhatsApp voice notes.

Usage:
    python voice_transcribe.py <path-to-audio-file>

Prints the transcript to stdout. Accepts .ogg (WhatsApp voice notes), .wav,
or anything else PyAV can decode - audio is resampled to 16kHz mono before
being fed to the local sherpa-onnx Whisper model (offline, no API key, no cost).
"""

import sys
import os
import subprocess
import tempfile
import wave

import av
import numpy as np

TOOLS_DIR = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts"
BIN_DIR = os.path.join(TOOLS_DIR, "runtime", "bin")
MODELS_DIR = os.path.join(TOOLS_DIR, "models")

ASR_EXE = os.path.join(BIN_DIR, "sherpa-onnx-vad-with-offline-asr.exe")
VAD_MODEL = os.path.join(MODELS_DIR, "silero_vad.onnx")
WHISPER_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-whisper-medium")
WHISPER_ENCODER = os.path.join(WHISPER_DIR, "medium-encoder.int8.onnx")
WHISPER_DECODER = os.path.join(WHISPER_DIR, "medium-decoder.int8.onnx")
WHISPER_TOKENS = os.path.join(WHISPER_DIR, "medium-tokens.txt")


def decode_to_wav(src_path, dst_wav_path, target_rate=16000):
    """Decode any audio format (ogg/opus, mp3, m4a, ...) to 16kHz mono PCM WAV."""
    container = av.open(src_path)
    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=target_rate)

    chunks = []
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):
            chunks.append(rframe.to_ndarray())
    container.close()

    if not chunks:
        raise ValueError(f"No audio data decoded from {src_path}")

    pcm = np.concatenate(chunks, axis=1).astype("int16").tobytes()

    with wave.open(dst_wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(target_rate)
        wf.writeframes(pcm)


# Whisper's automatic language detection is unreliable on short WhatsApp voice
# notes - it has been observed misidentifying clear English audio as Urdu/Hindi
# and producing fluent-looking but wrong-language gibberish. Since this account
# only needs English and Urdu, we run both forced languages and let the caller
# (the agent, reading the text) pick whichever transcript is actually coherent -
# that's far more reliable than trusting the model's own language guess.
CANDIDATE_LANGUAGES = ["en", "ur"]


# How long a pause the VAD must see before it treats a speech segment as
# finished and passes it to Whisper (sherpa-onnx default is 0.5s, which cuts
# off short WhatsApp pauses mid-sentence). Raised to 1.8s per the caller's
# spec (1.5-2s range) so a normal breath/pause doesn't get sent as a partial
# chunk.
VAD_MIN_SILENCE_DURATION = 1.8


def _run_asr(wav_path, language):
    cmd = [
        ASR_EXE,
        f"--silero-vad-model={VAD_MODEL}",
        f"--silero-vad-min-silence-duration={VAD_MIN_SILENCE_DURATION}",
        f"--whisper-encoder={WHISPER_ENCODER}",
        f"--whisper-decoder={WHISPER_DECODER}",
        f"--tokens={WHISPER_TOKENS}",
        f"--whisper-language={language}",
        "--whisper-task=transcribe",
        "--num-threads=2",
        wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"ASR process failed (language={language}): {result.stderr}")

    # Each recognized segment is printed as "start -- end:  text"
    lines = []
    for line in result.stdout.splitlines():
        if "--" in line and ":" in line:
            lines.append(line.split(":", 1)[1].strip())
    return " ".join(lines).strip()


def transcribe(audio_path):
    """
    Transcribe an audio file. Returns a dict {language: transcript} with one
    entry per candidate language (currently English and Urdu).
    """
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "audio_16k_mono.wav")
        decode_to_wav(audio_path, wav_path)
        return {lang: _run_asr(wav_path, lang) for lang in CANDIDATE_LANGUAGES}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python voice_transcribe.py <path-to-audio-file>", file=sys.stderr)
        sys.exit(1)

    # Force UTF-8 for multilingual output (Urdu, etc.)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    results = transcribe(sys.argv[1])
    for lang, text in results.items():
        label = {"en": "English", "ur": "Urdu"}.get(lang, lang)
        print(f"[{label}]: {text}")
