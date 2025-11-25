from __future__ import annotations

import argparse
import sys


def main() -> int:
	"""Download a faster-whisper model to the local cache by instantiation.

	By default, reads the model name from project settings (src/config/settings.yaml),
	but allows overriding via CLI. Uses CPU to avoid requiring CUDA on the host.
	"""
	parser = argparse.ArgumentParser(description="Download faster-whisper model to local cache")
	parser.add_argument("--model", type=str, default=None, help="Model name or local path (e.g. large-v3)")
	parser.add_argument(
		"--device",
		type=str,
		default="cuda",
		choices=["cpu", "cuda", "auto"],
		help="Device to use for initialization (cpu recommended for download)",
	)
	parser.add_argument(
		"--compute-type",
		type=str,
		default="float16",
		choices=["float32", "float16", "int8_float16"],
		help="Precision for initialization (float32 recommended on CPU)",
	)
	args = parser.parse_args()

	# Ensure project root is importable so 'src' package can be resolved when run as a script
	try:
		from pathlib import Path
		project_root = Path(__file__).resolve().parents[2]
		if str(project_root) not in sys.path:
			sys.path.insert(0, str(project_root))
	except Exception:
		pass

	try:
		# Lazy import to avoid dependency at parse-time
		from src.core.config import load_config
		import os
		from pathlib import Path
	except Exception as e:  # pragma: no cover - utility script
		print(f"[!] Failed to import project config: {e}")
		return 1

	try:
		from faster_whisper import WhisperModel  # type: ignore
	except Exception as e:  # pragma: no cover - utility script
		print(
			"[!] faster-whisper is not installed. "
			"Install it in your venv: pip install faster-whisper\n"
			f"Details: {e}"
		)
		return 1

	cfg = load_config()
	model_name = args.model or cfg.local.model
	device = args.device or "cpu"
	# Prefer safe default for CPU-only hosts if not provided
	compute_type = args.compute_type or ("float32" if device == "cpu" else cfg.local.compute_type)

	# Set HF_HOME to project model directory
	model_dir = Path(cfg.paths.model_dir).resolve()
	model_dir.mkdir(parents=True, exist_ok=True)
	original_hf_home = os.environ.get("HF_HOME")
	os.environ["HF_HOME"] = str(model_dir)

	print(f"[i] Ensuring faster-whisper model is present:")
	print(f"    model       : {model_name}")
	print(f"    device      : {device}")
	print(f"    compute_type: {compute_type}")
	print(f"    cache dir   : {model_dir}")

	# Instantiation triggers download to cache if missing
	try:
		_ = WhisperModel(model_name, device=device, compute_type=compute_type)  # noqa: F841
	except Exception as e:
		# Restore original HF_HOME on error
		if original_hf_home is not None:
			os.environ["HF_HOME"] = original_hf_home
		elif "HF_HOME" in os.environ:
			os.environ.pop("HF_HOME")
		print(f"[!] Failed to initialize/download model '{model_name}': {e}")
		return 1

	# Restore original HF_HOME
	if original_hf_home is not None:
		os.environ["HF_HOME"] = original_hf_home
	elif "HF_HOME" in os.environ:
		os.environ.pop("HF_HOME")

	print(f"[OK] Model is available in project cache: {model_dir}")
	return 0


if __name__ == "__main__":
	sys.exit(main())


