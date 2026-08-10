"""Call sherpa-onnx TTS with proper Unicode support via CreateProcessW."""
import ctypes
from ctypes import wintypes
import os

text_file = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\urdu_text.txt"
out_file = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\urdu_test4.wav"

tts_exe = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\runtime\bin\sherpa-onnx-offline-tts.exe"
model = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\ur_PK-fasih-medium.onnx"
tokens = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\tokens.txt"
data_dir = r"C:\Users\DELL LATITUDE 5520\.openclaw\tools\sherpa-onnx-tts\models\vits-piper-ur_PK-fasih-medium\espeak-ng-data"

with open(text_file, 'r', encoding='utf-8') as f:
    text = f.read().strip()

cmd = f'"{tts_exe}" --vits-model="{model}" --vits-tokens="{tokens}" --vits-data-dir="{data_dir}" --output-filename="{out_file}" "{text}"'

# Use CreateProcessW for proper Unicode command line
kernel32 = ctypes.windll.kernel32

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

si = STARTUPINFOW()
si.cb = ctypes.sizeof(STARTUPINFOW)
pi = PROCESS_INFORMATION()

success = kernel32.CreateProcessW(
    None,
    cmd,
    None, None, False,
    0, None, None,
    ctypes.byref(si),
    ctypes.byref(pi)
)

if not success:
    print(f"CreateProcessW failed: {kernel32.GetLastError()}")
else:
    kernel32.WaitForSingleObject(pi.hProcess, 30000)
    exit_code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
    print(f"Exit code: {exit_code.value}")
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)
