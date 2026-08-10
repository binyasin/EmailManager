# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup: camera names and locations, SSH hosts and aliases, preferred TTS voices, speaker/room names, device nicknames, anything environment-specific.

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Voice (sherpa-onnx-tts)

Local, offline TTS. Default to voice when the incoming message was itself a voice note (see "Voice input" below); for text conversations, only reply with voice when explicitly asked.

- Runtime: `C:/Users/DELL LATITUDE 5520/.openclaw/tools/sherpa-onnx-tts/runtime/bin`
- Env vars `SHERPA_ONNX_RUNTIME_DIR` / `SHERPA_ONNX_MODEL_DIR` are set in `openclaw.json` under `skills.entries.sherpa-onnx-tts.env` (point at the English voice only — for Urdu, use the full paths below instead of the env var).

**Voices installed — pick based on the language/script of the reply text:**

| Voice | Model dir | Use for |
|---|---|---|
| English | `models/vits-piper-en_US-lessac-high/en_US-lessac-high.onnx` | English text |
| ~~Urdu, Pakistani accent~~ **BROKEN, do not use** | `models/vits-piper-ur_PK-fasih-medium/ur_PK-fasih-medium.onnx` | Sounds like the right accent, but Arabic-script Urdu text passed to this exe over `exec` is unusable — see the CONFIRMED BUG note below. Was briefly documented as "default" earlier on 2026-07-28; that was wrong and is superseded by this row. |
| Urdu, Arabic script (old, MMS) | `models/mms-urd-arabic/model.onnx` | Same Arabic-script argv problem as the Piper voice above — also unusable over `exec` for the same reason. Kept only for reference. |
| **Urdu — actual default** (Roman/Latin script) | `models/mms-urd-latin/model.onnx` | Romanized Urdu text ("mera naam..."), plain ASCII — the only Urdu voice that reliably works over `exec` on this machine. No Pakistani-specific accent exists for romanized text, but this is the one to use. |

**No Pakistani-English voice exists in the public Piper/sherpa-onnx catalog** (checked 2026-07-28) — the English voice above is a standard American voice (`en_US-lessac-high`); if the user says it sounds "Indian," there isn't a ready offline swap for it. Don't try switching to a different `en_*` voice as a fix without asking the user first — none are Pakistani-accented, so a swap is a lateral guess, not a real fix.

Generate a voice note (PowerShell — this is the shell `exec` runs; use the `&` call operator and `$env:` prefix, NOT bash `$VAR` syntax, or the paths silently resolve empty/wrong):

```powershell
& "$env:SHERPA_ONNX_RUNTIME_DIR\bin\sherpa-onnx-offline-tts.exe" `
  --vits-model="$env:SHERPA_ONNX_MODEL_DIR\en_US-lessac-high.onnx" `
  --vits-tokens="$env:SHERPA_ONNX_MODEL_DIR\tokens.txt" `
  --vits-data-dir="$env:SHERPA_ONNX_MODEL_DIR\espeak-ng-data" `
  --output-filename=reply.wav `
  "Text to speak here."
```

Verified working one-liners (full paths, no env vars needed — use whichever voice matches the reply language):

English:
```powershell
& "C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe" --vits-model="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-en_US-lessac-high\en_US-lessac-high.onnx" --vits-tokens="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-en_US-lessac-high\tokens.txt" --vits-data-dir="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-en_US-lessac-high\espeak-ng-data" --output-filename=reply.wav "Text to speak here."
```

~~Urdu, Pakistani accent~~ — **do not use, see CONFIRMED BUG below.** (Kept here only so you recognize the broken pattern if you see it in old logs — do not copy it.)
```powershell
& "C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe" --vits-model="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\ur_PK-fasih-medium.onnx" --vits-tokens="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\tokens.txt" --vits-data-dir="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\espeak-ng-data" --output-filename=reply.wav "میرا نام سراج الدین بن یاسین ہے"
```

~~Urdu, Arabic script — old MMS voice~~ — **also broken, same reason, do not use:**
```powershell
& "C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe" --vits-model="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\mms-urd-arabic\model.onnx" --vits-tokens="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\mms-urd-arabic\tokens.txt" --output-filename=reply.wav "میرا نام سراج الدین بن یاسین ہے"
```

**⚠️ CONFIRMED BUG (2026-07-28): Urdu/Arabic script text is ALWAYS mangled to `????` when passed to the sherpa-onnx CLI exe via PowerShell `exec`.** This is a hard C++ `char* argv[]` encoding limitation in the exe — no workaround (chcp 65001, CreateProcessW, Python subprocess, encoding tricks) fixes it. The Python sherpa-onnx package (`pip install sherpa-onnx`) is blocked by Windows Application Control.

**Working Urdu voice output: only Roman Urdu ✅.** Use the `mms-urd-latin` model with ASCII-safe Roman script ("aap ki baat samajh gaya"). For English, use `en_US-lessac-high` ✅.

**Skip the Piper ur_PK voice (and the old MMS Arabic-script voice) entirely** — both need real Arabic-script Urdu text, which is a broken path on this Windows host. Default Urdu replies to Roman script + the MMS Latin model.

**⚠️ SECOND CONFIRMED BUG (2026-07-28, found live via WhatsApp testing): a "write text to a temp .txt file, then pass the file's path" workaround does NOT dodge the argv encoding bug — it produces a different, worse failure.** `sherpa-onnx-offline-tts.exe`'s last positional argument is always the *literal text to speak* — there is no flag to make it read text from a file (`--help` confirms no such option exists). If you write Urdu text to `tempfile.NamedTemporaryFile(...)` and pass that file's *path* as the last CLI argument (instead of the text itself), the exe happily synthesizes speech **for the path string**, e.g. it will literally speak out "backslash... users... dell... app data... local... temp... tmp... dot txt" — which is exactly what a stale/broken `reply.wav` sounds like if you transcribe it back with `voice_transcribe.py`. This is a real bug that reached the live WhatsApp agent, not just a theoretical risk. **Fix: never pass a file path as the text argument.** Always pass the actual text as a literal (quoted) CLI argument — English or Roman-Urdu text is plain ASCII, so it can go directly on the command line with no file/encoding workaround needed at all. If a voice reply ever comes back sounding like it's reading a Windows path instead of the intended sentence, this is the bug to check first — inspect the actual `exec` command that generated it for a `tempfile`/`txt_path`-as-last-arg pattern.

Urdu, Roman/Latin script:
```powershell
& "C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe" --vits-model="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\mms-urd-latin\model.onnx" --vits-tokens="C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\mms-urd-latin\tokens.txt" --output-filename=reply.wav "mera naam siraj uddin binyasin hai"
```

Common mistakes that fail silently or with a parser error (do not use):
- Bash-style `$SHERPA_ONNX_RUNTIME_DIR` (not `$env:...`) — expands to empty in PowerShell, producing a bogus relative path like `/bin/sherpa-onnx-offline-tts.exe`.
- Calling the quoted `.exe` path directly without a leading `&` — PowerShell parses `--vits-model=...` as the subtraction operator and throws "Unexpected token".
- An unquoted path — breaks on the space in `DELL LATITUDE 5520`.
- Wrapping the whole thing in `cmd /c "..."` with nested quotes — the outer quotes get mangled and the path is truncated at the first space.
- Using the English voice for Urdu text (or vice versa) — it'll still produce audio but mispronounce everything. Match the voice to the script.
- Writing text to a temp file and passing the file's *path* as the last argument — the exe speaks the path literally (see the SECOND CONFIRMED BUG above). Always pass the literal text itself.

Send the resulting `.wav` as a voice note/attachment on the reply channel (WhatsApp, etc.).

**Applies to skill output too, not just free-form chat:** the smart-email skill's `SKILL.md` gives its own text-formatting instructions (bulleted list of sender/subject/summary) and says nothing about voice — that's a formatting suggestion for the *text*, not an override of the voice-matching rule above. If the incoming request that triggered a `check`/`digest`/`read` call was a voice note, still generate the reply as a voice note (summarize the CLI's JSON output into speakable sentences, then TTS it) instead of defaulting to text just because the skill doc only shows a text example. Same rule applies to any other skill's output.

## Voice input (speech-to-text) — set up 2026-07-28, updated 2026-07-28

Local, offline STT via the same sherpa-onnx runtime as TTS above (no API key, no per-use cost).

- VAD model: `.../models/silero_vad.onnx`, tuned with `--silero-vad-min-silence-duration=1.8` (up from the sherpa-onnx default of 0.5s) so a normal mid-sentence breath/pause in a WhatsApp voice note isn't treated as the end of speech and cut off before the full note is processed. Only whole, VAD-closed segments are ever handed to Whisper — there's no partial-chunk/streaming path here to worry about.
- ASR model: `.../models/sherpa-onnx-whisper-medium/` (int8 quantized Whisper medium multilingual — `medium-encoder.int8.onnx`, `medium-decoder.int8.onnx`, `medium-tokens.txt`). ~900MB, slower than tiny/small but noticeably more accurate.
- Binary: `sherpa-onnx-vad-with-offline-asr.exe` in the same `runtime/bin` as the TTS exe
- Requires the Python `av` package (`pip install av`) to decode WhatsApp's `.ogg`/Opus voice notes to 16kHz mono WAV before ASR — already installed.

**Use the wrapper script, don't call the exe directly:**

```powershell
python "C:\Users\DELL LATITUDE 5520\.openclaw\workspace\voice_transcribe.py" "<path-to-voice-note.ogg>"
```

**Important: Whisper's automatic language detection is unreliable on short WhatsApp voice notes** — testing during setup showed it misidentifying clear English speech as Urdu/Hindi and producing fluent-looking but wrong-language gibberish. So the script does NOT trust auto-detection: it transcribes the same audio twice, once forced to English and once forced to Urdu, and prints both:

```
[English]: Hello, please give me details of your 5 emails.
[Urdu]: ہلو مجھے اپنے پانچ ایمیلز کا ٹی
```

Read both lines and use whichever one is actually coherent (usually only one makes grammatical sense — the other will be garbled). Don't try to guess from the label alone; read the text.

Full two-way voice chat loop: transcribe incoming voice notes with the above, pick the coherent transcript, respond to it, and **reply with a voice note by default when the incoming message was a voice note** (use the matching-language TTS voice from the table above). For text-only conversations, keep defaulting to text unless the user explicitly asks for voice.

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)
