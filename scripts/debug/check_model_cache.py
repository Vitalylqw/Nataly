"""Check where faster-whisper models are cached."""
import os
from pathlib import Path


def check_cache():
    """Check all possible cache locations."""
    print("=== Checking faster-whisper model cache locations ===\n")
    
    # Hugging Face cache
    userprofile = os.getenv("USERPROFILE", "")
    hf_cache = Path(userprofile) / ".cache" / "huggingface"
    print(f"1. Hugging Face cache: {hf_cache}")
    print(f"   Exists: {hf_cache.exists()}")
    
    if hf_cache.exists():
        model_dir = hf_cache / "hub" / "models--Systran--faster-whisper-large-v3"
        if model_dir.exists():
            print(f"   [OK] Model found: faster-whisper-large-v3")
            snapshot = model_dir / "snapshots" / "edaa852ec7e145841d8ffdb056a99866b5f0a478"
            if snapshot.exists():
                model_bin = snapshot / "model.bin"
                if model_bin.exists():
                    size_gb = model_bin.stat().st_size / (1024**3)
                    print(f"   Model size: {size_gb:.2f} GB")
                    print(f"   Full path: {snapshot}")
        else:
            print("   [NOT FOUND] Model not found")
    
    print()
    
    # CTranslate2 cache locations
    localappdata = os.getenv("LOCALAPPDATA", "")
    ct2_cache1 = Path(userprofile) / ".cache" / "ctranslate2"
    ct2_cache2 = Path(localappdata) / "ctranslate2"
    
    print(f"2. CTranslate2 cache (UserProfile): {ct2_cache1}")
    print(f"   Exists: {ct2_cache1.exists()}")
    if ct2_cache1.exists():
        items = list(ct2_cache1.iterdir())
        print(f"   Items: {len(items)}")
        for item in sorted(items)[:5]:
            if item.is_dir():
                print(f"     - {item.name}/")
    
    print()
    print(f"3. CTranslate2 cache (LocalAppData): {ct2_cache2}")
    print(f"   Exists: {ct2_cache2.exists()}")
    if ct2_cache2.exists():
        items = list(ct2_cache2.iterdir())
        print(f"   Items: {len(items)}")
        for item in sorted(items)[:5]:
            if item.is_dir():
                print(f"     - {item.name}/")
    
    print()
    print("=== Summary ===")
    if hf_cache.exists() and (hf_cache / "hub" / "models--Systran--faster-whisper-large-v3").exists():
        print("[OK] Model faster-whisper-large-v3 is cached in Hugging Face cache")
        print(f"  Location: {hf_cache / 'hub' / 'models--Systran--faster-whisper-large-v3'}")
    else:
        print("[NOT FOUND] Model not found in standard cache locations")


if __name__ == "__main__":
    check_cache()

