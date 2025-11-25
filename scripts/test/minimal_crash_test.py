import sys
import os
from pathlib import Path

print("1. Start import")
sys.stdout.flush()

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("ERROR: faster_whisper module not found. Check requirements.")
    sys.exit(1)

print("2. Import success. Checking model path...")
sys.stdout.flush()

# Path to the local model as configured in the project
project_root = Path(__file__).parent.parent.parent
model_path = project_root / "var" / "models" / "faster-whisper-large-v3"

if not model_path.exists():
    print(f"ERROR: Model path not found: {model_path}")
    # Fallback to checking if 'models' dir exists at all
    print(f"Listing {model_path.parent}:")
    if model_path.parent.exists():
        for p in model_path.parent.iterdir():
            print(f" - {p.name}")
    sys.exit(1)

print(f"3. Init model from: {model_path}")
sys.stdout.flush()

try:
    # Using CPU and int8 to minimize resource usage for this crash test, 
    # but using the actual large-v3 model files to ensure they load.
    # Import numpy to check version
    import numpy
    import ctranslate2
    print(f"   Numpy version: {numpy.__version__}")
    print(f"   CTranslate2 version: {ctranslate2.__version__}")

    model = WhisperModel(
        str(model_path), 
        device="cpu", 
        compute_type="int8", 
        local_files_only=True
    )
    print("4. Model initialized successfully!")
except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

sys.stdout.flush()
