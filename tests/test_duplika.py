import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duplika


def _setup(tmp_path):
    (tmp_path / "a.txt").write_text("hello!!")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("hello!!")
    (tmp_path / "c.txt").write_text("differ!")  # same size, different content
    os.utime(tmp_path / "a.txt", (1, 1))  # a is the oldest: must be kept


def test_finds_and_moves(tmp_path):
    _setup(tmp_path)
    groups = duplika.find_duplicates(tmp_path)
    assert len(groups) == 1
    size, g = groups[0]
    assert size == 7 and [p.name for p in g] == ["a.txt", "b.txt"]
    q = tmp_path.parent / (tmp_path.name + "_q")
    assert duplika.quarantine(groups, tmp_path, q) == 1
    assert (tmp_path / "a.txt").exists() and not (tmp_path / "sub" / "b.txt").exists()
    assert (q / "sub" / "b.txt").read_text() == "hello!!"  # moved, not deleted


def test_quarantine_inside_root_is_not_rescanned(tmp_path):
    _setup(tmp_path)
    q = tmp_path / "quarantine"
    duplika.quarantine(duplika.find_duplicates(tmp_path, exclude=q), tmp_path, q)
    assert duplika.find_duplicates(tmp_path, exclude=q) == []


def test_existing_target_is_not_overwritten(tmp_path):
    _setup(tmp_path)
    q = tmp_path.parent / (tmp_path.name + "_q2")
    (q / "sub").mkdir(parents=True)
    (q / "sub" / "b.txt").write_text("old")
    assert duplika.quarantine(duplika.find_duplicates(tmp_path), tmp_path, q) == 1
    assert (q / "sub" / "b.txt").read_text() == "old"
    assert (q / "sub" / "b (2).txt").read_text() == "hello!!"


def test_empty_files_skipped_by_default(tmp_path):
    (tmp_path / "x").write_bytes(b"")
    (tmp_path / "y").write_bytes(b"")
    assert duplika.find_duplicates(tmp_path) == []
    assert len(duplika.find_duplicates(tmp_path, min_size=0)) == 1


def test_env_folders_skipped(tmp_path):
    for d in (".venv", "env2", ".git"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "lib.py").write_text("same")
    (tmp_path / "env2" / "pyvenv.cfg").write_text("home = x")
    (tmp_path / "lib.py").write_text("same")
    assert duplika.find_duplicates(tmp_path) == []
    assert len(duplika.find_duplicates(tmp_path, include_all=True)[0][1]) == 4


def test_free_name_keeps_parentheses(tmp_path):
    (tmp_path / "photo (copy).jpg").touch()
    assert duplika._free_name(tmp_path / "photo (copy).jpg").name == "photo (copy) (2).jpg"
    (tmp_path / "photo (copy) (2).jpg").touch()
    assert duplika._free_name(tmp_path / "photo (copy).jpg").name == "photo (copy) (3).jpg"
