"""Duplika: finds duplicate files in a folder and optionally moves them to a quarantine folder (never deletes)."""
import argparse
import hashlib
import os
import shutil
import stat
import sys
from collections import defaultdict
from pathlib import Path

# OneDrive "online-only" files: reading them triggers a download, so they are skipped
CLOUD_ATTRS = getattr(stat, "FILE_ATTRIBUTE_OFFLINE", 0x1000) | 0x400000 | 0x40000
# moving "duplicates" out of these breaks the tool/environment; included with --all
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
    return d.name in SKIP_DIRS or (d / "pyvenv.cfg").is_file()  # virtualenvs with custom names


def find_duplicates(root, min_size=1, exclude=None, include_cloud=False, include_all=False):
    """Returns groups of identical files: [(size, [Path, ...]), ...]; the first path in each group is the one to keep."""
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
                continue  # an unreadable file must not stop the scan
            if not stat.S_ISREG(st.st_mode) or st.st_size < min_size:
                continue  # symlinks, devices, etc.
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
                # keep the oldest; on a tie, the shortest path
                g.sort(key=lambda t: (t[0], len(str(t[1])), str(t[1])))
                groups.append((size, [p for _, p in g]))
    groups.sort(key=lambda t: -t[0] * (len(t[1]) - 1))  # biggest savings first
    return groups


def _free_name(target):
    """If the target exists, finds a free name like 'name (2).ext'."""
    n = 2
    while target.exists():
        target = target.with_name(f"{target.stem.rsplit(' (', 1)[0]} ({n}){target.suffix}")
        n += 1
    return target


def quarantine(groups, root, dest):
    """Keeps the first file of each group and moves the rest under dest, preserving relative paths. Returns the count moved."""
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
                print(f"  ! could not move: {p} ({e})", file=sys.stderr)
    return moved


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(errors="replace")  # odd file names must not crash the output
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder")
    ap.add_argument("--min-size", type=int, default=1, help="bytes; skip smaller files (default 1)")
    ap.add_argument("--move", metavar="QUARANTINE", help="move duplicates to this folder (report only if omitted)")
    ap.add_argument("--all", action="store_true", help="also scan folders like .git, .venv, node_modules")
    ap.add_argument("--include-cloud", action="store_true", help="also scan OneDrive online-only files (downloads them)")
    a = ap.parse_args(argv)
    root = Path(a.folder)
    if not root.is_dir():
        sys.exit(f"Folder not found: {root}")
    groups = find_duplicates(root, a.min_size, exclude=a.move, include_cloud=a.include_cloud, include_all=a.all)
    waste = sum(size * (len(g) - 1) for size, g in groups)
    for _, g in groups:
        print(f"[keep] {g[0]}")
        for p in g[1:]:
            print(f"  dupe {p}")
    print(f"\n{len(groups)} group(s), {waste / 1e6:.2f} MB reclaimable.")
    if a.move and groups:
        print(f"{quarantine(groups, root, a.move)} file(s) moved to {a.move}.")
    elif groups:
        print("To move them: --move QUARANTINE_FOLDER")


if __name__ == "__main__":
    main()
