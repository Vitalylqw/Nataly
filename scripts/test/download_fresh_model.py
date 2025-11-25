"""Download a fresh model without moving it."""
import os
from pathlib import Path

model_dir = Path("var/models").resolve()
os.environ["HF_HOME"] = str(model_dir)

print(f"HF_HOME set to: {model_dir}")
print("\nDownloading tiny model for quick test...")

from huggingface_hub import snapshot_download

try:
    # Download tiny model (smallest, fastest to test)
    model_path = snapshot_download(
        repo_id="Systran/faster-whisper-tiny",
        cache_dir=str(model_dir),
        local_files_only=False
    )
    print(f"\n✓ Model downloaded to: {model_path}")
    
    # List files
    print("\nModel files:")
    for file in Path(model_path).iterdir():
        size_mb = file.stat().st_size / (1024**2)
        print(f"  - {file.name}: {size_mb:.2f} MB")
    
    # Now try to load it with faster-whisper
    print("\n" + "="*60)
    print("Testing model loading with faster-whisper...")
    print("="*60)
    
    from faster_whisper import WhisperModel
    
    print("\nCreating WhisperModel instance...")
    print("(This is where it usually hangs)")
    
    import sys
    sys.stdout.flush()
    
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    print("\n✓✓✓ SUCCESS! Model loaded!")
    print(f"Model: {model}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
