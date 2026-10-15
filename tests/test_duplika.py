import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duplika


def _kur(tmp_path):
    (tmp_path / "a.txt").write_text("merhaba")
    (tmp_path / "alt").mkdir()
    (tmp_path / "alt" / "b.txt").write_text("merhaba")
    (tmp_path / "c.txt").write_text("farkli!")  # aynı boyut, farklı içerik
    os.utime(tmp_path / "a.txt", (1, 1))  # a en eski: saklanmalı


def test_bulur_ve_tasir(tmp_path):
    _kur(tmp_path)
    groups = duplika.find_duplicates(tmp_path)
    assert len(groups) == 1
    size, g = groups[0]
    assert size == 7 and [p.name for p in g] == ["a.txt", "b.txt"]
    q = tmp_path.parent / (tmp_path.name + "_q")
    assert duplika.quarantine(groups, tmp_path, q) == 1
    assert (tmp_path / "a.txt").exists() and not (tmp_path / "alt" / "b.txt").exists()
    assert (q / "alt" / "b.txt").read_text() == "merhaba"  # taşındı, silinmedi


def test_karantina_icerdeyse_tekrar_taramaz(tmp_path):
    _kur(tmp_path)
    q = tmp_path / "karantina"
    duplika.quarantine(duplika.find_duplicates(tmp_path, exclude=q), tmp_path, q)
    assert duplika.find_duplicates(tmp_path, exclude=q) == []


def test_hedef_doluysa_ezmez(tmp_path):
    _kur(tmp_path)
    q = tmp_path.parent / (tmp_path.name + "_q2")
    (q / "alt").mkdir(parents=True)
    (q / "alt" / "b.txt").write_text("eski")
    assert duplika.quarantine(duplika.find_duplicates(tmp_path), tmp_path, q) == 1
    assert (q / "alt" / "b.txt").read_text() == "eski"
    assert (q / "alt" / "b (2).txt").read_text() == "merhaba"


def test_bos_dosyalar_varsayilan_atlanir(tmp_path):
    (tmp_path / "x").write_bytes(b"")
    (tmp_path / "y").write_bytes(b"")
    assert duplika.find_duplicates(tmp_path) == []
    assert len(duplika.find_duplicates(tmp_path, min_size=0)) == 1


def test_ortam_klasorleri_atlanir(tmp_path):
    for d in (".venv", "env2", ".git"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "lib.py").write_text("ayni")
    (tmp_path / "env2" / "pyvenv.cfg").write_text("home = x")
    (tmp_path / "lib.py").write_text("ayni")
    assert duplika.find_duplicates(tmp_path) == []
    assert len(duplika.find_duplicates(tmp_path, include_all=True)[0][1]) == 4
