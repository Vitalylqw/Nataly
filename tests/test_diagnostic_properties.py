"""Property-based tests for faster-whisper diagnostic script.

**Feature: faster-whisper-diagnostic, Property 1: Step status output**
For any step executed by the script (import, model loading, transcription),
the script should print at least one status message indicating the step is being performed.
**Validates: Requirements 1.2, 3.3**
"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Import the functions we're testing
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.diagnostic.test_faster_whisper_simple import (
    check_import,
    print_header,
)


@given(st.just(None))
@settings(max_examples=100)
def test_property_step_status_output_check_import(dummy):
    """**Feature: faster-whisper-diagnostic, Property 1: Step status output**
    
    Property: For any execution of check_import(), at least one status message
    should be printed indicating the step is being performed.
    **Validates: Requirements 1.2, 3.3**
    """
    # Capture stdout
    captured_output = StringIO()
    
    with patch("sys.stdout", captured_output):
        # Execute the step (may succeed or fail depending on environment)
        try:
            check_import()
        except Exception:
            # Even if it fails, we should have printed status
            pass
    
    output = captured_output.getvalue()
    
    # Property: At least one status message must be printed
    assert len(output) > 0, "No output was produced"
    assert "Step 1:" in output or "Checking" in output, \
        f"No step status message found in output: {output}"


@given(st.just(None))
@settings(max_examples=100)
def test_property_step_status_output_print_header(dummy):
    """**Feature: faster-whisper-diagnostic, Property 1: Step status output**
    
    Property: For any execution of print_header(), status output should be produced.
    **Validates: Requirements 1.2, 3.3**
    """
    # Capture stdout
    captured_output = StringIO()
    
    with patch("sys.stdout", captured_output):
        print_header()
    
    output = captured_output.getvalue()
    
    # Property: Header must produce output
    assert len(output) > 0, "No output was produced by print_header()"
    assert "DIAGNOSTIC" in output or "=" in output, \
        f"No diagnostic header found in output: {output}"


# Import additional functions for Property 2
from scripts.diagnostic.test_faster_whisper_simple import (
    load_model,
    run_transcription_test,
)


@given(
    st.sampled_from([
        Exception("Test error"),
        RuntimeError("Runtime test error"),
        ValueError("Value test error"),
        IOError("IO test error"),
        TypeError("Type test error"),
    ])
)
@settings(max_examples=100)
def test_property_error_traceback_display_load_model(exception):
    """**Feature: faster-whisper-diagnostic, Property 2: Error traceback display**
    
    Property: For any exception that occurs during load_model execution,
    the script should print both the error message and the full traceback.
    **Validates: Requirements 1.3, 4.5**
    """
    # Create a mock WhisperModel that raises the exception
    mock_whisper_model = MagicMock()
    mock_whisper_model.side_effect = exception
    
    # Capture stdout and stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    
    with patch("sys.stdout", captured_stdout), \
         patch("sys.stderr", captured_stderr):
        result = load_model(mock_whisper_model)
    
    stdout_output = captured_stdout.getvalue()
    stderr_output = captured_stderr.getvalue()
    combined_output = stdout_output + stderr_output
    
    # Property: Must return None on error
    assert result is None, "load_model should return None on exception"
    
    # Property: Error message must be displayed
    assert str(exception) in combined_output or "Failed to load model" in stdout_output, \
        f"Error message not found in output. Exception: {exception}, Output: {combined_output}"
    
    # Property: Traceback must be displayed
    assert "Traceback" in combined_output, \
        f"Traceback not found in output for exception: {exception}"


@given(
    st.sampled_from([
        Exception("Transcription test error"),
        RuntimeError("Transcription runtime error"),
        ValueError("Transcription value error"),
        IOError("Transcription IO error"),
        AttributeError("Transcription attribute error"),
    ])
)
@settings(max_examples=100)
def test_property_error_traceback_display_test_transcription(exception):
    """**Feature: faster-whisper-diagnostic, Property 2: Error traceback display**
    
    Property: For any exception that occurs during run_transcription_test execution,
    the script should print both the error message and the full traceback.
    **Validates: Requirements 1.3, 4.5**
    """
    # Create a mock model that raises the exception during transcribe
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = exception
    
    # Create a temporary test file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        # Capture stdout and stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        
        with patch("sys.stdout", captured_stdout), \
             patch("sys.stderr", captured_stderr):
            result = run_transcription_test(mock_model, tmp_path)
        
        stdout_output = captured_stdout.getvalue()
        stderr_output = captured_stderr.getvalue()
        combined_output = stdout_output + stderr_output
        
        # Property: Must return False on error
        assert result is False, "run_transcription_test should return False on exception"
        
        # Property: Error message must be displayed
        assert str(exception) in combined_output or "Transcription failed" in stdout_output, \
            f"Error message not found in output. Exception: {exception}, Output: {combined_output}"
        
        # Property: Traceback must be displayed
        assert "Traceback" in combined_output, \
            f"Traceback not found in output for exception: {exception}"
    finally:
        # Clean up temporary file
        tmp_path.unlink(missing_ok=True)
