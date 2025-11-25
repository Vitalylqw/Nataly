from pathlib import Path

from src.utils.hashing import sha256_of_file


def test_sha256_of_file(tmp_path: Path) -> None:
	p = tmp_path / "file.txt"
	p.write_bytes(b"abc")
	assert sha256_of_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


