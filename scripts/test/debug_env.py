import sys
import os

print("="*50)
print("ДИАГНОСТИКА ОКРУЖЕНИЯ")
print("="*50)

print(f"Python: {sys.version}")
print(f"Path: {sys.executable}")

print("\n1. Проверка импорта ctranslate2...")
try:
    import ctranslate2
    print(f"SUCCESS: ctranslate2 импортирован. Версия: {ctranslate2.__version__}")
    print(f"CUDA доступна (по мнению ctranslate2): {ctranslate2.get_cuda_device_count() > 0}")
    print(f"Поддерживаемые compute types: {ctranslate2.get_supported_compute_types('cpu')}")
except ImportError as e:
    print(f"ERROR: Не удалось импортировать ctranslate2: {e}")
except Exception as e:
    print(f"CRITICAL: Ошибка при работе с ctranslate2: {e}")

print("\n2. Проверка импорта faster_whisper...")
try:
    import faster_whisper
    print(f"SUCCESS: faster_whisper импортирован.")
except ImportError as e:
    print(f"ERROR: Не удалось импортировать faster_whisper: {e}")
except Exception as e:
    print(f"CRITICAL: Ошибка при импорте faster_whisper: {e}")

print("\n3. Проверка зависимостей (pip)...")
try:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "freeze"])
except Exception as e:
    print(f"Не удалось выполнить pip freeze: {e}")

print("\n="*50)
print("КОНЕЦ ДИАГНОСТИКИ")
print("="*50)

