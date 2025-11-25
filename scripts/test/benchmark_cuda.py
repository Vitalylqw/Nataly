"""Benchmark transcription speed on CUDA."""
import sys
import time
import logging
from pathlib import Path
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.config import load_config
from src.transcription.router import TranscriptionRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # 1. Setup paths
    test_audio = Path(r"scripts\test\voce.mp3").resolve()
    if not test_audio.exists():
        print(f"Error: File {test_audio} not found")
        return

    print(f"Target file: {test_audio}")
    
    # 2. Force Config to use CUDA and Local provider
    print("\n--- Loading Config ---")
    config = load_config()
    
    # Override settings for benchmark
    # We want to test the local provider specifically
    print(f"Original Device: {config.local.device}")
    
    if config.local.device != "cuda":
        print("WARNING: Config is not set to 'cuda'. Attempting to continue, but results may be CPU-based if fallback happens or if config is respected strictly.")
        # Note: We can't easily change the immutable config object in place if it's frozen, 
        # but we can check what the router does.
    
    # 3. Initialize Router (Measure Load Time)
    print("\n--- Initializing Router & Model ---")
    start_load = time.perf_counter()
    
    # Mock Storage to bypass cache
    from src.core.storage import Storage
    original_get_transcript = Storage.get_transcript
    
    # Define mock that always returns None (cache miss)
    def mock_get_transcript(*args, **kwargs):
        return None
        
    # Patch the class method
    Storage.get_transcript = mock_get_transcript
    
    router = TranscriptionRouter(config=config)
    
    # Pre-warm / Load model by accessing it? 
    # The router loads lazily on first transcribe usually, unless we force it.
    # Let's run a dummy transcription or just rely on the first run timing which includes load.
    # Actually, to separate load time, we might want to peek into the provider.
    # But the user cares about "transcription speed", usually end-to-end or processing time.
    # Let's do one warm-up run (to load model) and one measured run?
    # Or just measure the first run (cold start) vs second run (warm start).
    
    print("Performing Warm-up run (Loading model into VRAM)...")
    try:
        # Warmup
        router.transcribe(test_audio)
    except Exception as e:
        print(f"Warmup failed: {e}")
        return
        
    load_time = time.perf_counter() - start_load
    print(f"Warm-up (includes model load) took: {load_time:.2f} seconds")

    # 4. Measure Inference Speed (Warm)
    print("\n--- Measuring Inference Speed (Warm) ---")
    start_transcribe = time.perf_counter()
    
    # We still need cache bypass for the second run as well
    result = router.transcribe(test_audio)
    
    end_transcribe = time.perf_counter()
    
    # Restore original method (good practice, though script ends anyway)
    Storage.get_transcript = original_get_transcript
    duration = end_transcribe - start_transcribe
    
    # 5. Stats
    print("\n" + "="*40)
    print("BENCHMARK RESULTS (CUDA)")
    print("="*40)
    print(f"Audio File:      {test_audio.name}")
    print(f"Inference Time:  {duration:.4f} seconds")
    
    # Estimate audio duration (we can get it from the result if we look at segments or just assume)
    # The router result text doesn't have total audio duration metadata directly exposed easily 
    # unless we look at the last segment end time.
    audio_duration_approx = 0.0
    if result.segments:
        audio_duration_approx = result.segments[-1].end
        print(f"Audio Duration:  ~{audio_duration_approx:.2f} seconds")
        if duration > 0:
            rtf = duration / audio_duration_approx
            print(f"Real-Time Factor: {rtf:.4f} (lower is better)")
            print(f"Speedup:          {1/rtf:.2f}x real-time")
    
    print(f"Provider Used:   {result.provider}")
    print("="*40)

if __name__ == "__main__":
    main()

