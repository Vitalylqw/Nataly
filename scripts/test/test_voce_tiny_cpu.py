"""Test with tiny model on CPU."""
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import load_config
from src.transcription.router import TranscriptionRouter

test_audio = Path(r"D:\work_d\Projects\Nataly\scripts\test\voce.mp3")

print(f"Testing: {test_audio}")
print(f"Exists: {test_audio.exists()}")

config = load_config()
config.local.model = "tiny"
config.local.device = "cpu"
config.local.compute_type = "int8"

print(f"Config: model={config.local.model}, device={config.local.device}, compute={config.local.compute_type}")

router = TranscriptionRouter(config=config)
print("Starting transcription...")

try:
    result = router.transcribe(test_audio)
    print("\n" + "="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"Provider: {result.provider}")
    print(f"Language: {result.language}")
    print(f"Text: {result.text}")
    print("="*60)
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
