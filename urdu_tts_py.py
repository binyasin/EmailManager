"""Test Urdu TTS using sherpa-onnx Python package (native Unicode)."""
import sherpa_onnx

model_path = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\ur_PK-fasih-medium.onnx"
tokens_path = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\tokens.txt"
data_dir = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\espeak-ng-data"

config = sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
            model=model_path,
            tokens=tokens_path,
            data_dir=data_dir,
        ),
        num_threads=1,
    ),
)

tts = sherpa_onnx.OfflineTts(config)
text = "آپ کی بات سمجھ گیا۔ کیا یہ آواز اب ٹھیک ہے؟"
audio = tts.generate(text, sid=0, speed=1.0)

out_path = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\urdu_py_test.wav"
with open(out_path, "wb") as f:
    f.write(audio.samples)
print(f"Saved {audio.sample_rate}Hz, {len(audio.samples)} bytes to {out_path}")
print(f"Duration: {audio.samples.shape[0] / float(audio.sample_rate):.2f}s")
print(f"Text: {text}")
