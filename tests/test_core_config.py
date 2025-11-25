from pathlib import Path

from src.core.config import load_config


def _p(path: Path) -> str:
	return path.as_posix()


def test_load_config_env_overrides_and_dirs(tmp_path, monkeypatch):
	base_dir = tmp_path / "runtime"
	settings_path = tmp_path / "settings.yaml"
	settings_path.write_text(
		"\n".join(
			[
				"paths:",
				f'  base_dir: "{_p(base_dir)}"',
				f'  inbox_dir: "{_p(base_dir / "inbox")}"',
				f'  cache_dir: "{_p(base_dir / "cache")}"',
				f'  out_dir: "{_p(base_dir / "out")}"',
				f'  db_path: "{_p(base_dir / "db" / "app.db")}"',
				"provider:",
				'  default: "cloud"',
				'  fallback: "none"',
				"chunk:",
				"  max_sec: 45",
			]
		),
		encoding="utf-8",
	)

	monkeypatch.setenv("SETTINGS_FILE", str(settings_path))
	monkeypatch.setenv("TELEGRAM_TOKEN", "env-token")
	monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
	monkeypatch.setenv("ENV", "test")
	monkeypatch.setenv("PROVIDER_DEFAULT", "local")
	monkeypatch.setenv("PROVIDER_FALLBACK", "cloud")

	cfg = load_config()

	assert cfg.telegram_token == "env-token"
	assert cfg.openai_api_key == "env-openai"
	assert cfg.env == "test"
	assert cfg.provider.default == "local"
	assert cfg.provider.fallback == "cloud"
	assert cfg.chunk.max_sec == 45

	assert Path(cfg.paths.base_dir).exists()
	assert Path(cfg.paths.inbox_dir).exists()
	assert Path(cfg.paths.cache_dir).exists()
	assert Path(cfg.paths.out_dir).exists()
	assert Path(cfg.paths.db_path).parent.exists()

