#!/usr/bin/env python3
"""Simple diagnostic script for faster-whisper.

This script performs basic checks to verify faster-whisper functionality:
1. Import check - verifies the library is installed
2. Model loading - tests loading the tiny model on CPU
3. Transcription test - tests transcription on a sample audio file
"""

from pathlib import Path
import sys
import traceback


def print_header():
    """Print diagnostic header."""
    print("=" * 64)
    print("FASTER-WHISPER SIMPLE DIAGNOSTIC")
    print("=" * 64)
    print()


def check_import():
    """Step 1: Try to import faster_whisper."""
    print("Step 1: Checking faster-whisper import...")
    try:
        from faster_whisper import WhisperModel
        print("✓ faster-whisper imported successfully")
        return WhisperModel
    except ImportError as e:
        print(f"✗ Failed to import faster-whisper: {e}")
        print("  Install with: pip install faster-whisper")
        return None


def load_model(WhisperModel):
    """Step 2: Load tiny model on CPU."""
    print("\nStep 2: Loading model (tiny, cpu)...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("✓ Model loaded successfully")
        return model
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        traceback.print_exc()
        return None


def run_transcription_test(model, audio_path):
    """Step 3: Transcribe test audio file."""
    print(f"\nStep 3: Testing transcription on {audio_path}...")
    
    if not audio_path.exists():
        print(f"✗ Test file not found: {audio_path}")
        return False
    
    try:
        segments, info = model.transcribe(str(audio_path), beam_size=5)
        print("✓ Transcription successful")
        print(f"  Language: {info.language}")
        print("  Text:")
        
        for segment in segments:
            print(f"    {segment.text}")
        
        return True
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic steps."""
    pass


if __name__ == "__main__":
    main()
