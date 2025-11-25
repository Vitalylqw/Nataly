# Design Document

## Overview

Простой диагностический скрипт для faster-whisper представляет собой автономный Python-скрипт (~100 строк), который выполняет три базовые проверки:
1. Импорт библиотеки faster-whisper
2. Загрузка модели (tiny, CPU)
3. Транскрибация тестового файла scripts/test/voce.mp3

Скрипт полностью независим от основного проекта и использует только стандартную библиотеку Python плюс faster-whisper.

## Architecture

Скрипт имеет линейную структуру без классов:

```
┌─────────────────────────────────────┐
│         Main Script                 │
│                                     │
│  1. Print header                    │
│  2. Try import faster_whisper       │
│  3. Try load model (tiny, cpu)      │
│  4. Try transcribe voce.mp3         │
│  5. Print results                   │
│                                     │
└─────────────────────────────────────┘
```

## Components and Interfaces

Скрипт не использует классы или сложные структуры данных. Все реализовано как последовательность простых функций:

### Step 1: Import Check

```python
def check_import():
    """Try to import faster_whisper."""
    print("Step 1: Checking faster-whisper import...")
    try:
        from faster_whisper import WhisperModel
        print("✓ faster-whisper imported successfully")
        return WhisperModel
    except ImportError as e:
        print(f"✗ Failed to import faster-whisper: {e}")
        print("  Install with: pip install faster-whisper")
        return None
```

### Step 2: Model Loading

```python
def load_model(WhisperModel):
    """Load tiny model on CPU."""
    print("\nStep 2: Loading model (tiny, cpu)...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("✓ Model loaded successfully")
        return model
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return None
```

### Step 3: Transcription Test

```python
def test_transcription(model, audio_path):
    """Transcribe test audio file."""
    print(f"\nStep 3: Testing transcription on {audio_path}...")
    
    if not audio_path.exists():
        print(f"✗ Test file not found: {audio_path}")
        return False
    
    try:
        segments, info = model.transcribe(str(audio_path), beam_size=5)
        print(f"✓ Transcription successful")
        print(f"  Language: {info.language}")
        print(f"  Text:")
        
        for segment in segments:
            print(f"    {segment.text}")
        
        return True
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return False
```

## Data Models

Скрипт не использует специальные модели данных. Все данные передаются как простые типы Python (str, Path, bool).

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, several properties can be consolidated to eliminate redundancy:

- Error handling properties (1.4, 2.3, 3.4, 4.4) all describe capturing errors with context - consolidated into Property 1
- Success output properties (2.2, 3.3, 4.3) all describe displaying details after success - consolidated into Property 2
- CLI argument properties (6.1-6.4) all describe accepting command-line arguments - consolidated into Property 3
- Recommendation properties (5.2, 5.4, 5.5) all describe providing recommendations for failures - consolidated into Property 4

### Correctness Properties

Property 1: Universal error capture
*For any* diagnostic check that encounters an error, the system should capture the full exception with traceback and include it in the diagnostic result
**Validates: Requirements 1.4, 2.3, 3.4, 4.4**

Property 2: Success details display
*For any* diagnostic check that succeeds, the system should include relevant details (version info, configuration, output) in the result
**Validates: Requirements 2.2, 3.3, 4.3**

Property 3: CLI argument acceptance
*For any* valid command-line argument (model, device, compute_type, cache_dir), the system should parse and apply it to the diagnostic configuration
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

Property 4: Failure recommendations
*For any* failed diagnostic check, the system should generate at least one specific recommendation for resolving the issue
**Validates: Requirements 5.2, 5.4, 5.5**

Property 5: Logging completeness
*For any* diagnostic check executed, the system should output at least one log message describing the check being performed
**Validates: Requirements 1.2**

Property 6: Summary completeness
*For any* completed diagnostic run, the summary report should include the status (passed/failed) of every check that was executed
**Validates: Requirements 1.3, 5.1**

Property 7: Custom cache directory usage
*For any* custom cache directory specified via configuration, the system should set HF_HOME environment variable to that directory before model operations
**Validates: Requirements 3.5**

Property 8: Compute type flexibility
*For any* valid compute type specified (int8, float16, float32, etc.), the system should attempt to use that compute type when loading the model
**Validates: Requirements 4.5**

Property 9: Recommendation prioritization
*For any* set of multiple failed checks, the recommendations should be ordered with environment/dependency issues before model/transcription issues
**Validates: Requirements 5.3**

Property 10: Transcription result validation
*For any* successful transcription, the result should contain non-empty text and a detected language code
**Validates: Requirements 4.2**

## Error Handling

### Error Categories

1. **Import Errors**: Missing dependencies, incompatible versions
2. **Model Loading Errors**: Download failures, corrupted files, timeout
3. **Transcription Errors**: Invalid audio, processing failures
4. **Configuration Errors**: Invalid arguments, missing directories

### Error Handling Strategy

- All errors are caught and wrapped in DiagnosticResult objects
- Full tracebacks are preserved for debugging
- User-friendly error messages are generated
- Specific recommendations are provided for each error type
- Script continues to next check even if one fails (fail-safe)

### Timeout Handling

Model loading can hang indefinitely on some systems. We implement timeout protection:

```python
def load_model_with_timeout(model_name: str, device: str, compute_type: str, timeout: int) -> tuple[Any | None, Exception | None]:
    """Load model with timeout protection."""
    result = [None, None]  # [model, error]
    
    def load():
        try:
            from faster_whisper import WhisperModel
            result[0] = WhisperModel(model_name, device=device, compute_type=compute_type)
        except Exception as e:
            result[1] = e
    
    thread = threading.Thread(target=load, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        return None, TimeoutError(f"Model loading exceeded {timeout}s timeout")
    
    return result[0], result[1]
```

## Testing Strategy

### Unit Testing

Unit tests will cover:

- DiagnosticResult creation and serialization
- CLI argument parsing with various input combinations
- Report generation with different result sets
- Recommendation generation for specific error types
- Configuration validation

Example unit tests:
- Test that invalid model names are rejected
- Test that default configuration is applied when no args provided
- Test that summary includes all executed checks
- Test that recommendations are generated for known error patterns

### Property-Based Testing

Property-based tests will verify universal properties using the Hypothesis library for Python. Each test will run a minimum of 100 iterations with randomly generated inputs.

Property tests will cover:

- **Property 1 (Universal error capture)**: Generate random exceptions, verify all are captured with tracebacks
- **Property 3 (CLI argument acceptance)**: Generate random valid CLI arguments, verify all are parsed correctly
- **Property 4 (Failure recommendations)**: Generate random failure scenarios, verify recommendations are always provided
- **Property 5 (Logging completeness)**: Generate random diagnostic checks, verify logging occurs
- **Property 6 (Summary completeness)**: Generate random sets of results, verify summary includes all
- **Property 9 (Recommendation prioritization)**: Generate random sets of failures, verify ordering

Each property-based test will be tagged with a comment explicitly referencing the correctness property from this design document using the format: **Feature: faster-whisper-diagnostic, Property {number}: {property_text}**

### Integration Testing

Integration tests will verify the full diagnostic flow:

- Run diagnostic with real faster-whisper installation
- Run diagnostic with missing dependencies (mocked)
- Run diagnostic with various CLI argument combinations
- Verify exit codes match diagnostic results

### Manual Testing

Manual testing scenarios:

- Run on system with working faster-whisper
- Run on system without faster-whisper installed
- Run with various model sizes (tiny, base, small)
- Run with different compute types (cpu, cuda if available)
- Run with custom cache directory
- Verify recommendations are actionable

## Implementation Notes

### Audio Generation

For test audio generation, we'll use numpy to create a simple sine wave:

```python
import numpy as np
import wave

def generate_test_audio(output_path: Path, duration: float = 1.0, sample_rate: int = 16000) -> Path:
    """Generate a simple sine wave test audio file."""
    frequency = 440.0  # A4 note
    samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(sample_rate * duration)))
    samples = (samples * 32767).astype(np.int16)
    
    with wave.open(str(output_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    return output_path
```

### Dependency Detection

We'll check for dependencies in order of importance:

1. faster_whisper (critical)
2. ctranslate2 (critical - backend for faster_whisper)
3. numpy (required for audio generation)
4. av (optional - for audio decoding)
5. torch (optional - only needed for CUDA)

### Recommendation Database

Common issues and their recommendations:

```python
RECOMMENDATIONS = {
    "import_error_faster_whisper": [
        "Install faster-whisper: pip install faster-whisper",
        "Verify Python version is >= 3.8",
        "Check for conflicting packages in environment"
    ],
    "import_error_ctranslate2": [
        "Reinstall faster-whisper: pip install --force-reinstall faster-whisper",
        "Install ctranslate2 directly: pip install ctranslate2",
        "Check system architecture compatibility (x86_64 required)"
    ],
    "model_loading_timeout": [
        "Try smaller model: use 'tiny' instead of 'large'",
        "Check antivirus software (may block model loading)",
        "Verify model files are not corrupted",
        "Try CPU compute type: --compute-type int8"
    ],
    "cuda_not_available": [
        "Install PyTorch with CUDA support",
        "Verify NVIDIA drivers are installed",
        "Use CPU device instead: --device cpu"
    ],
    "transcription_failed": [
        "Verify audio file format (WAV 16kHz mono recommended)",
        "Check model is fully loaded",
        "Try with generated test audio first"
    ]
}
```

### Output Format

The script will produce structured output:

```
================================================================
FASTER-WHISPER DIAGNOSTIC TOOL
================================================================

Configuration:
  Model: tiny
  Device: cpu
  Compute Type: int8
  Cache Directory: /path/to/cache

[1/7] Checking Python environment...
  ✓ Python 3.11.0
  ✓ Platform: Windows

[2/7] Checking dependencies...
  ✓ faster_whisper: 1.2.1
  ✓ ctranslate2: 4.0.0
  ✓ numpy: 1.24.0
  ⚠ torch: not installed (optional)

[3/7] Checking compute devices...
  ✓ CPU available
  ✗ CUDA not available

[4/7] Checking model cache...
  ✓ Cache directory exists: /path/to/cache
  ⚠ Model 'tiny' not in cache (will download)

[5/7] Loading model...
  ⏳ Downloading model... 100%
  ✓ Model loaded successfully
  ℹ Model info: tiny.en, 39M parameters

[6/7] Generating test audio...
  ✓ Test audio created: /tmp/test_audio.wav

[7/7] Testing transcription...
  ✓ Transcription successful
  ℹ Language: en
  ℹ Text: "Test audio signal"

================================================================
DIAGNOSTIC SUMMARY
================================================================

Passed: 6/7 checks
Failed: 1/7 checks

Issues Found:
  • CUDA not available

Recommendations:
  1. Install PyTorch with CUDA support for GPU acceleration
  2. Or continue using CPU (slower but functional)

Exit Code: 0 (SUCCESS - core functionality works)
================================================================
```

## Dependencies

The diagnostic script itself requires minimal dependencies:

- Python >= 3.8 (standard library only for basic checks)
- faster-whisper (the library being tested)
- numpy (for test audio generation)

Optional dependencies:
- torch (for CUDA detection)
- hypothesis (for property-based testing during development)

## File Structure

```
scripts/
  diagnostic/
    faster_whisper_diagnostic.py  # Main script
    README.md                      # Usage instructions
```

The script should be completely self-contained in a single file for easy distribution and use.


### Property Reflection

After analyzing all acceptance criteria, most are specific examples rather than universal properties. For a simple diagnostic script, this is appropriate. Only two universal properties emerge:

- Property 1: Status messages for all steps (1.2, 3.3)
- Property 2: Error display with traceback (1.3, 4.5)

All other criteria are specific behaviors that should be tested as examples.

### Correctness Properties

Property 1: Step status output
*For any* step executed by the script (import, model loading, transcription), the script should print at least one status message indicating the step is being performed
**Validates: Requirements 1.2, 3.3**

Property 2: Error traceback display
*For any* exception that occurs during script execution, the script should print both the error message and the full traceback
**Validates: Requirements 1.3, 4.5**

## Error Handling

### Error Handling Strategy

Скрипт использует простую стратегию обработки ошибок:

1. Каждый шаг обернут в try-except блок
2. При ошибке выводится сообщение и traceback
3. Скрипт завершается с кодом 1 при любой ошибке
4. Скрипт завершается с кодом 0 только если все шаги успешны

```python
import sys
import traceback

def main():
    # Step 1: Import
    WhisperModel = check_import()
    if WhisperModel is None:
        sys.exit(1)
    
    # Step 2: Load model
    model = load_model(WhisperModel)
    if model is None:
        sys.exit(1)
    
    # Step 3: Transcribe
    success = test_transcription(model, Path("scripts/test/voce.mp3"))
    if not success:
        sys.exit(1)
    
    print("\n✓ All checks passed!")
    sys.exit(0)
```

## Testing Strategy

### Unit Testing

Для такого простого скрипта unit-тесты будут минимальными:

- Тест что скрипт не импортирует из src/
- Тест что используется правильный путь к файлу
- Тест что используются правильные параметры модели (tiny, cpu, int8)

### Property-Based Testing

Property-based тесты будут использовать Hypothesis:

- **Property 1 (Step status output)**: Мокируем выполнение шагов, проверяем что для каждого есть вывод
- **Property 2 (Error traceback display)**: Генерируем случайные исключения, проверяем что traceback выводится

Каждый property-based тест будет помечен комментарием: **Feature: faster-whisper-diagnostic, Property {number}: {property_text}**

### Manual Testing

Основное тестирование будет ручным:

1. Запуск на системе с установленным faster-whisper
2. Запуск на системе без faster-whisper
3. Запуск с отсутствующим файлом voce.mp3
4. Запуск с поврежденным файлом voce.mp3
5. Проверка что вывод понятен и информативен

## Implementation Notes

### File Location

Скрипт будет размещен в:
```
scripts/diagnostic/test_faster_whisper_simple.py
```

### Dependencies

Скрипт требует только:
- Python >= 3.8 (стандартная библиотека)
- faster-whisper (тестируемая библиотека)

Никаких других зависимостей не требуется.

### Expected Output

Пример успешного выполнения:

```
================================================================
FASTER-WHISPER SIMPLE DIAGNOSTIC
================================================================

Step 1: Checking faster-whisper import...
✓ faster-whisper imported successfully

Step 2: Loading model (tiny, cpu)...
✓ Model loaded successfully

Step 3: Testing transcription on scripts\test\voce.mp3...
✓ Transcription successful
  Language: ru
  Text:
    Привет, это тестовое аудио сообщение

✓ All checks passed!
================================================================
```

Пример с ошибкой:

```
================================================================
FASTER-WHISPER SIMPLE DIAGNOSTIC
================================================================

Step 1: Checking faster-whisper import...
✗ Failed to import faster-whisper: No module named 'faster_whisper'
  Install with: pip install faster-whisper
================================================================
```

### Script Structure

Полная структура скрипта:

```python
#!/usr/bin/env python3
"""Simple diagnostic script for faster-whisper."""

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
    # Implementation here
    pass


def load_model(WhisperModel):
    """Step 2: Load tiny model on CPU."""
    # Implementation here
    pass


def test_transcription(model, audio_path):
    """Step 3: Transcribe test audio file."""
    # Implementation here
    pass


def main():
    """Run all diagnostic steps."""
    print_header()
    
    # Step 1
    WhisperModel = check_import()
    if WhisperModel is None:
        sys.exit(1)
    
    # Step 2
    model = load_model(WhisperModel)
    if model is None:
        sys.exit(1)
    
    # Step 3
    audio_path = Path("scripts/test/voce.mp3")
    success = test_transcription(model, audio_path)
    if not success:
        sys.exit(1)
    
    print("\n✓ All checks passed!")
    print("=" * 64)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

## Design Decisions

### Why No Command-Line Arguments?

Для максимальной простоты скрипт не принимает аргументы. Все параметры жестко заданы:
- Модель: tiny (самая быстрая)
- Устройство: cpu (максимальная совместимость)
- Compute type: int8 (минимальные требования)
- Файл: scripts/test/voce.mp3 (фиксированный тестовый файл)

Если нужно тестировать другие конфигурации, можно просто отредактировать скрипт.

### Why No Classes?

Для скрипта из ~100 строк классы добавляют ненужную сложность. Простые функции более читаемы и понятны.

### Why No Logging Module?

Простые print() statements достаточны для диагностического скрипта. Они проще и не требуют настройки.

### Why No Configuration File?

Скрипт предназначен для быстрой проверки с фиксированными параметрами. Конфигурационный файл добавил бы ненужную сложность.
