"""Copy faster-whisper model from system cache to project directory."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def main() -> int:
	"""Copy faster-whisper model from system cache to project var/models."""
	# Ensure project root is importable
	try:
		project_root = Path(__file__).resolve().parents[2]
		if str(project_root) not in sys.path:
			sys.path.insert(0, str(project_root))
	except Exception:
		pass

	try:
		from src.core.config import load_config
	except Exception as e:
		print(f"[!] Failed to import project config: {e}")
		return 1

	cfg = load_config()
	model_name = cfg.local.model

	# Source: system cache
	userprofile = os.getenv("USERPROFILE", "")
	system_cache = Path(userprofile) / ".cache" / "huggingface"
	source_model_dir = system_cache / "hub" / f"models--Systran--faster-whisper-{model_name}"

	# Destination: project cache
	project_model_dir = Path(cfg.paths.model_dir).resolve()
	project_model_dir.mkdir(parents=True, exist_ok=True)

	print(f"[i] Copying model from system cache to project:")
	print(f"    Source: {source_model_dir}")
	print(f"    Destination: {project_model_dir}")

	if not source_model_dir.exists():
		print(f"[!] Model not found in system cache: {source_model_dir}")
		print(f"[i] Model will be downloaded on first use to: {project_model_dir}")
		return 0

	# Copy the entire model directory
	try:
		# Check if already exists
		dest_hub = project_model_dir / "hub" / f"models--Systran--faster-whisper-{model_name}"
		if dest_hub.exists():
			print(f"[i] Model already exists in project cache: {dest_hub}")
			print(f"[i] Skipping copy. Delete {dest_hub} to force re-copy.")
			return 0

		# Create hub structure
		hub_dir = project_model_dir / "hub"
		hub_dir.mkdir(parents=True, exist_ok=True)

		# Copy model directory
		print(f"[i] Copying model files (this may take a while, ~3GB)...")
		shutil.copytree(source_model_dir, dest_hub)
		print(f"[OK] Model copied successfully to: {dest_hub}")

		# Calculate size
		total_size = sum(f.stat().st_size for f in dest_hub.rglob("*") if f.is_file())
		print(f"[OK] Total size: {total_size / (1024**3):.2f} GB")

		return 0
	except Exception as e:
		print(f"[!] Failed to copy model: {e}")
		return 1


if __name__ == "__main__":
	sys.exit(main())



