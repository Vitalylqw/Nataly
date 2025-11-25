"""Test transcription with cloud provider (OpenAI)."""
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import load_config
from src.transcription.router import TranscriptionRouter

# Test file
test_audio = Path(r"D:\work_d\Projects\Nataly\scripts\test\voce.mp3")

print(f"Testing: {test_audio}")
print(f"Exists: {test_audio.exists()}")

config = load_config()
# Force cloud provider
config.provider.default = "cloud"
config.provider.fallback = "none"

print(f"Config loaded. Provider: {config.provider.default}")
print(f"OpenAI API Key: {'SET' if config.openai_api_key and config.openai_api_key != 'YOUR_OPENAI_API_KEY_HERE' else 'NOT SET'}")

if not config.openai_api_key or config.openai_api_key == 'YOUR_OPENAI_API_KEY_HERE':
    print("\n⚠️  WARNING: OpenAI API key is not set!")
    print("Please set OPENAI_API_KEY in .env file")
    sys.exit(1)

router = TranscriptionRouter(config=config)
print("Router created. Starting transcription...")

try:
    result = router.transcribe(test_audio)
    print("\n" + "="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"Provider: {result.provider}")
    print(f"Language: {result.language}")
    print(f"Text length: {len(result.text)} chars")
    print("\nTranscribed text:")
    print(result.text)
    print("="*60)
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
