# Urdu TTS wrapper - reads text from file to avoid Windows encoding issues
import subprocess, sys

tts_exe = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe"
model = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\ur_PK-fasih-medium.onnx"
tokens = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\tokens.txt"
data_dir = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\espeak-ng-data"

text_file = sys.argv[1]
out_file = sys.argv[2]

with open(text_file, 'r', encoding='utf-8') as f:
    text = f.read().strip()

cmd = [
    tts_exe,
    f'--vits-model={model}',
    f'--vits-tokens={tokens}',
    f'--vits-data-dir={data_dir}',
    f'--output-filename={out_file}',
    text
]

subprocess.run(cmd, check=True)
