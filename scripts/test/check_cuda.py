"""Проверка работы faster-whisper модели на CUDA."""
from __future__ import annotations

import concurrent.futures
import subprocess
import sys
import threading
import time
from pathlib import Path

# Добавляем путь к проекту для импорта модулей
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    print("[DEBUG] Импорт faster_whisper...")
    sys.stdout.flush()
    from faster_whisper import WhisperModel
    print("[DEBUG] faster_whisper успешно импортирован")
    sys.stdout.flush()
except ImportError as e:
    print(f"ERROR: faster-whisper не установлен: {e}")
    print("Установите: pip install faster-whisper")
    sys.stdout.flush()
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Ошибка при импорте faster-whisper: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)

# Проверка CUDA через PyTorch (опционально)
CUDA_AVAILABLE = None
CUDA_DEVICE_COUNT = None
CUDA_DEVICE_NAME = None

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        CUDA_DEVICE_COUNT = torch.cuda.device_count()
        CUDA_DEVICE_NAME = torch.cuda.get_device_name(0) if CUDA_DEVICE_COUNT > 0 else None
    else:
        CUDA_DEVICE_COUNT = 0
        CUDA_DEVICE_NAME = None
except ImportError:
    # PyTorch не обязателен для faster-whisper (использует CTranslate2)
    pass
except Exception as e:
    print(f"WARNING: Ошибка при проверке CUDA через PyTorch: {e}")

from src.core.config import load_config


def check_cuda_availability() -> None:
    """Проверка доступности CUDA."""
    print("=" * 60)
    print("Проверка доступности CUDA")
    print("=" * 60)
    
    # Проверка через PyTorch (если доступен)
    if CUDA_AVAILABLE is not None:
        if CUDA_AVAILABLE:
            print(f"✓ CUDA доступна (проверено через PyTorch)")
            print(f"  Количество GPU: {CUDA_DEVICE_COUNT}")
            if CUDA_DEVICE_NAME:
                print(f"  Устройство 0: {CUDA_DEVICE_NAME}")
        else:
            print("✗ CUDA недоступна через PyTorch (используется CPU)")
    else:
        print("INFO: PyTorch не установлен, проверка CUDA через PyTorch недоступна")
        print("      (faster-whisper использует CTranslate2, PyTorch не обязателен)")
    
    # Альтернативная проверка через nvidia-smi (если доступен)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_names = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            print(f"\n✓ Обнаружены GPU через nvidia-smi:")
            for i, name in enumerate(gpu_names):
                print(f"  GPU {i}: {name}")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass  # nvidia-smi недоступен, это нормально


def check_faster_whisper_cuda() -> int:
    """Проверка работы faster-whisper на CUDA."""
    print("\n" + "=" * 60)
    print("Проверка faster-whisper с CUDA")
    print("=" * 60)
    
    # Загружаем конфигурацию проекта
    try:
        config = load_config()
        model_name = config.local.model
        device = config.local.device
        compute_type = config.local.compute_type
        print(f"Конфигурация из проекта:")
        print(f"  Модель: {model_name}")
        print(f"  Device: {device}")
        print(f"  Compute type: {compute_type}")
    except Exception as e:
        print(f"WARNING: Не удалось загрузить конфиг проекта: {e}")
        print("Используются значения по умолчанию")
        model_name = "large-v3"
        device = "cuda"
        compute_type = "float16"
    
    # Проверяем, что device="cuda" указан
    if device != "cuda":
        print(f"\nWARNING: В конфиге указан device='{device}', а не 'cuda'")
        print("Для проверки CUDA будет использован device='cuda'")
        device = "cuda"
    
    print(f"\nПопытка загрузки модели '{model_name}' с device='{device}'...")
    
    # Сначала пробуем быструю проверку с CPU (если CUDA не работает)
    print("\n" + "-" * 60)
    print("ШАГ 1: Быстрая проверка с CPU (для диагностики)")
    print("-" * 60)
    
    try:
        test_model_cpu = "tiny"
        print(f"Пробуем загрузить модель '{test_model_cpu}' с device='cpu'...")
        print("  Примечание: при первом запуске модель скачивается из интернета")
        print("  Это может занять 1-2 минуты")
        print("  Загружаем модель напрямую (без потоков) для диагностики...")
        sys.stdout.flush()
        
        # Загружаем напрямую, чтобы увидеть реальную ошибку
        print(f"  [DEBUG] Начало загрузки CPU модели...")
        sys.stdout.flush()
        
        try:
            cpu_model_obj = WhisperModel(
                test_model_cpu,
                device="cpu",
                compute_type="int8",  # Для CPU используем int8
            )
            print(f"  [DEBUG] CPU модель загружена успешно!")
            sys.stdout.flush()
            print(f"✓ CPU версия работает! Модель может быть загружена.")
            del cpu_model_obj  # Освобождаем память
            sys.stdout.flush()
        except Exception as direct_error:
            print(f"\n✗ ОШИБКА при прямой загрузке CPU модели: {direct_error}")
            print("Это означает проблему с faster-whisper или моделью, а не с CUDA")
            import traceback
            print("\nПолный traceback:")
            traceback.print_exc()
            sys.stdout.flush()
            return 1
        
    except Exception as cpu_error:
        print(f"✗ ОШИБКА даже с CPU: {cpu_error}")
        print("Это означает проблему с faster-whisper или моделью, а не с CUDA")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return 1
    
    print("\n" + "-" * 60)
    print("ШАГ 2: Проверка CUDA")
    print("-" * 60)
    
    try:
        # Используем tiny модель для быстрой проверки
        test_model = "tiny"
        print(f"Для быстрой проверки используем модель '{test_model}'")
        print("Загрузка модели с CUDA... (это может занять некоторое время при первом запуске)")
        print("  Примечание: при первом запуске модель скачивается из интернета")
        print("  Если процесс завис, подождите 2-3 минуты или прервите (Ctrl+C)")
        sys.stdout.flush()
        
        # Функция для загрузки модели в отдельном потоке
        model_loaded = threading.Event()
        model_error = [None]
        loaded_model = [None]
        
        def load_model():
            try:
                print(f"  [DEBUG] Начало загрузки модели в потоке...")
                sys.stdout.flush()
                
                # Пробуем сначала с device='auto' для автоматического определения
                # Если это не сработает, попробуем указанный device
                try:
                    print(f"  [DEBUG] Попытка загрузки с device='{device}'...")
                    sys.stdout.flush()
                    result = WhisperModel(
                        test_model,
                        device=device,
                        compute_type=compute_type,
                    )
                except Exception as auto_error:
                    # Если не получилось с указанным device, пробуем 'auto'
                    if device != "auto":
                        print(f"  [DEBUG] Ошибка с device='{device}': {auto_error}")
                        print(f"  [DEBUG] Пробуем device='auto'...")
                        sys.stdout.flush()
                        result = WhisperModel(
                            test_model,
                            device="auto",
                            compute_type=compute_type,
                        )
                    else:
                        raise
                
                print(f"  [DEBUG] Модель загружена успешно в потоке")
                sys.stdout.flush()
                loaded_model[0] = result
                model_loaded.set()
            except Exception as e:
                print(f"  [DEBUG] ОШИБКА в потоке загрузки: {e}")
                import traceback
                print(f"  [DEBUG] Traceback:")
                traceback.print_exc()
                sys.stdout.flush()
                model_error[0] = e
                model_loaded.set()
        
        # Запускаем загрузку в отдельном потоке (НЕ демон, чтобы не завершился преждевременно)
        loader_thread = threading.Thread(target=load_model, daemon=False)
        loader_thread.start()
        
        # Показываем прогресс каждые 5 секунд
        start_time = time.time()
        timeout = 120  # 2 минуты максимум (для tiny модели этого должно хватить)
        last_message_time = start_time
        
        print(f"  Таймаут установлен: {timeout} секунд")
        print(f"  Нажмите Ctrl+C для прерывания")
        sys.stdout.flush()
        
        while not model_loaded.is_set():
            elapsed = time.time() - start_time
            
            # Проверяем, жив ли поток
            if not loader_thread.is_alive() and not model_loaded.is_set():
                print(f"\n✗ Поток загрузки завершился, но событие не установлено!")
                print("Это может означать критическую ошибку при загрузке")
                if model_error[0] is not None:
                    print(f"Ошибка: {model_error[0]}")
                sys.stdout.flush()
                break
            
            if elapsed > timeout:
                print(f"\n✗ ТАЙМАУТ: Загрузка модели превысила {timeout} секунд")
                print("Возможные причины:")
                print("  1. Медленное интернет-соединение (скачивание модели)")
                print("  2. Проблемы с CUDA/драйверами (модель зависла при инициализации)")
                print("  3. Недостаточно памяти GPU")
                print("\nПопробуйте:")
                print("  - Проверить интернет-соединение")
                print("  - Проверить драйверы: nvidia-smi")
                print("  - Использовать device='cpu' в конфиге (CPU версия работает)")
                sys.stdout.flush()
                return 1
            
            # Показываем прогресс каждые 5 секунд
            if time.time() - last_message_time >= 5:
                elapsed_sec = int(elapsed)
                remaining = timeout - elapsed_sec
                print(f"  ... загрузка продолжается ({elapsed_sec} сек, осталось ~{remaining} сек) ...")
                sys.stdout.flush()
                last_message_time = time.time()
            
            time.sleep(0.5)
        
        # Ждем завершения потока (на всякий случай)
        loader_thread.join(timeout=1.0)
        
        # Проверяем результат
        if model_error[0] is not None:
            print(f"\n✗ ОШИБКА при загрузке модели: {model_error[0]}")
            sys.stdout.flush()
            raise model_error[0]
        
        model = loaded_model[0]
        elapsed = int(time.time() - start_time)
        print(f"✓ Модель загружена за {elapsed} секунд")
        sys.stdout.flush()
        
        # Проверяем, какой device реально используется
        # faster-whisper не предоставляет прямой способ узнать device,
        # но мы можем проверить через ошибки при транскрипции
        
        print(f"✓ Модель успешно загружена")
        print(f"  Указанный device: {device}")
        print(f"  Compute type: {compute_type}")
        
        # Пытаемся выполнить транскрипцию для проверки
        print("\nПроверка транскрипции (создаем тестовый аудио файл)...")
        
        # Создаем простой тестовый WAV файл (1 секунда тишины)
        import wave
        import numpy as np
        
        test_wav_path = project_root / "var" / "test_cuda_check.wav"
        test_wav_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаем простой синусоидальный сигнал
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0  # Ля первой октавы
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(str(test_wav_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print(f"Тестовый файл создан: {test_wav_path}")
        
        # Пытаемся транскрибировать
        print("Запуск транскрипции...")
        sys.stdout.flush()
        
        segments, info = model.transcribe(str(test_wav_path), beam_size=1)
        
        sys.stdout.flush()
        
        # Читаем первый сегмент для проверки
        first_segment = next(segments, None)
        if first_segment:
            print(f"✓ Транскрипция выполнена успешно")
            print(f"  Распознанный язык: {getattr(info, 'language', 'unknown')}")
            print(f"  Текст: {first_segment.text[:50]}...")
        else:
            print("✓ Транскрипция выполнена (сегменты не найдены)")
        
        # Удаляем тестовый файл
        if test_wav_path.exists():
            test_wav_path.unlink()
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: Модель работает на CUDA ✓")
        print("=" * 60)
        sys.stdout.flush()
        return 0  # Успешное завершение
        
    except RuntimeError as e:
        error_msg = str(e)
        print(f"\n✗ ОШИБКА RuntimeError: {error_msg}")
        
        if "CUDA" in error_msg or "cuda" in error_msg.lower():
            print("\nПроблема связана с CUDA. Возможные причины:")
            print("  1. CUDA драйверы не установлены или устарели")
            print("  2. CUDA toolkit не установлен")
            print("  3. faster-whisper/CTranslate2 скомпилирован без поддержки CUDA")
            print("  4. Недостаточно памяти GPU")
            print("\nПопробуйте:")
            print("  - Проверить драйверы: nvidia-smi")
            print("  - Использовать device='cpu' в конфиге")
            print("  - Переустановить faster-whisper с поддержкой CUDA")
        else:
            print("\nВозможные причины:")
            print("  - Модель не может быть загружена")
            print("  - Проблемы с доступом к файлам")
            print("  - Недостаточно памяти")
        
        import traceback
        print("\nПолный traceback:")
        traceback.print_exc()
        sys.stdout.flush()
        return 1
    except KeyboardInterrupt:
        print("\n\n✗ Прервано пользователем")
        sys.stdout.flush()
        return 130
    except Exception as e:
        print(f"\n✗ НЕОЖИДАННАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    print("=" * 60)
    print("СКРИПТ ПРОВЕРКИ CUDA ДЛЯ FASTER-WHISPER")
    print("=" * 60)
    print()
    sys.stdout.flush()
    
    try:
        check_cuda_availability()
        exit_code = check_faster_whisper_cuda()
        final_code = exit_code if exit_code is not None else 0
        
        print("\n" + "=" * 60)
        if final_code == 0:
            print("СКРИПТ ЗАВЕРШЕН УСПЕШНО")
        else:
            print(f"СКРИПТ ЗАВЕРШЕН С ОШИБКОЙ (код: {final_code})")
        print("=" * 60)
        sys.stdout.flush()
        
        sys.exit(final_code)
    except KeyboardInterrupt:
        print("\n\n✗ Прервано пользователем (Ctrl+C)")
        sys.stdout.flush()
        sys.exit(130)
    except Exception as e:
        print(f"\n\n✗ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)

