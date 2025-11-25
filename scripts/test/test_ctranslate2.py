"""Test ctranslate2 import."""
print("Testing ctranslate2...")

try:
    import ctranslate2
    print(f"✓ ctranslate2 version: {ctranslate2.__version__}")
    print(f"✓ Supported compute types: {ctranslate2.get_supported_compute_types('cpu')}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
