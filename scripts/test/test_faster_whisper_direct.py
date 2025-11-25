"""Direct test of faster-whisper library."""
import os
from pathlib import Path

# Set model directory
model_dir = Path("var/models").resolve()
os.environ["HF_HOME"] = str(model_dir)

print(f"HF_HOME: {os.environ['HF_HOME']}")
print("Importing faster_whisper...")

try:
    from faster_whisper import WhisperModel
    print("✓ Import successful")
    
    print("\nLoading model 'base' on CPU...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("✓ Model loaded successfully")
    
    # Test transcription
    test_file = Path("var/cache/voce_16k_mono.wav")
    if test_file.exists():
        print(f"\nTranscribing: {test_file}")
        segments, info = model.transcribe(str(test_file), beam_size=5)
        
        print(f"Language: {info.language}")
        print("\nSegments:")
        for segment in segments:
            print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
    else:
        print(f"\n⚠️  Test file not found: {test_file}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
