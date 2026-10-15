"""Duplika: klasördeki yinelenen dosyaları bulur; istenirse karantinaya taşır (silmez)."""
import argparse
import hashlib
import os
import shutil
import stat
import sys
from collections import defaultdict
from pathlib import Path

# OneDrive "yalnızca bulutta" dosyaları: okumak indirmeyi tetikler, atlıyoruz
CLOUD_ATTRS = getattr(stat, "FILE_ATTRIBUTE_OFFLINE", 0x1000) | 0x400000 | 0x40000
# içindeki "kopyalar" taşınırsa araç/ortam bozulur; --hepsi ile dahil edilir
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__"}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def _inside(path, parent):
    return parent is not None and (path == parent or parent in path.parents)


def _skip_dir(d):
    return d.name in SKIP_DIRS or (d / "pyvenv.cfg").is_file()  # adı farklı sanal ortamlar


def find_duplicates(root, min_size=1, exclude=None, include_cloud=False, include_all=False):
    """Aynı içerikli dosya gruplarını döndürür: [(boyut, [Path, ...]), ...]; her grubun ilki saklanacak olandır."""
    root = Path(root).resolve()
    exclude = Path(exclude).resolve() if exclude else None
    by_size = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        dirnames[:] = [n for n in dirnames if not _inside(d / n, exclude) and (include_all or not _skip_dir(d / n))]
        for name in filenames:
            p = d / name
            try:
                st = p.lstat()
            except OSError:
                continue  # erişilemeyen dosya taramayı durdurmasın
            if not stat.S_ISREG(st.st_mode) or st.st_size < min_size:
                continue  # sembolik bağlantı, aygıt vb.
            if not include_cloud and getattr(st, "st_file_attributes", 0) & CLOUD_ATTRS:
                continue
            by_size[st.st_size].append((st.st_mtime, p))
    groups = []
    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue
        by_hash = defaultdict(list)
        for mtime, p in same_size:
            try:
                by_hash[sha256(p)].append((mtime, p))
            except OSError:
                continue
        for g in by_hash.values():
            if len(g) > 1:
                # saklanacak olan: en eski, eşitse en kısa yol
                g.sort(key=lambda t: (t[0], len(str(t[1])), str(t[1])))
                groups.append((size, [p for _, p in g]))
    groups.sort(key=lambda t: -t[0] * (len(t[1]) - 1))  # en çok yer kazandıran önce
    return groups


def _free_name(target):
    """Hedef doluysa 'ad (2).uzantı' gibi boş bir ad bulur."""
    n = 2
    while target.exists():
        target = target.with_name(f"{target.stem.rsplit(' (', 1)[0]} ({n}){target.suffix}")
        n += 1
    return target


def quarantine(groups, root, dest):
    """Her grubun ilkini bırakır, kalanları dest altına (göreli yolu koruyarak) taşır. Taşınan sayısını döndürür."""
    root, dest = Path(root).resolve(), Path(dest).resolve()
    moved = 0
    for _, g in groups:
        for p in g[1:]:
            try:
                target = _free_name(dest / p.relative_to(root))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(target))
                moved += 1
            except OSError as e:
                print(f"  ! taşınamadı: {p} ({e})", file=sys.stderr)
    return moved


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(errors="replace")  # garip dosya adları çıktıyı çökertmesin
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("klasor")
    ap.add_argument("--min-boyut", type=int, default=1, help="bayt; bundan küçük dosyaları atla (varsayılan 1)")
    ap.add_argument("--tasi", metavar="KARANTINA", help="kopyaları bu klasöre taşı (verilmezse sadece rapor)")
    ap.add_argument("--hepsi", action="store_true", help=".git, .venv, node_modules gibi klasörleri de tara")
    ap.add_argument("--bulut-dahil", action="store_true", help="OneDrive'da yalnızca bulutta olan dosyaları da tara (indirir)")
    a = ap.parse_args(argv)
    root = Path(a.klasor)
    if not root.is_dir():
        sys.exit(f"Klasör yok: {root}")
    groups = find_duplicates(root, a.min_boyut, exclude=a.tasi, include_cloud=a.bulut_dahil, include_all=a.hepsi)
    waste = sum(size * (len(g) - 1) for size, g in groups)
    for _, g in groups:
        print(f"[sakla] {g[0]}")
        for p in g[1:]:
            print(f"  kopya {p}")
    print(f"\n{len(groups)} grup, {waste / 1e6:.2f} MB geri kazanılabilir.")
    if a.tasi and groups:
        print(f"{quarantine(groups, root, a.tasi)} dosya {a.tasi} klasörüne taşındı.")
    elif groups:
        print("Taşımak için: --tasi KARANTINA_KLASORU")


if __name__ == "__main__":
    main()
