# Duplika

Finds byte-identical files in a folder by content (SHA-256). By default it **only reports**;
with `--move` it moves duplicates to a quarantine folder instead of deleting them. It never deletes anything.

## Usage

Python 3.8+, no dependencies.

```
python duplika.py C:\Users\me\Desktop
python duplika.py C:\Users\me\Desktop --move C:\quarantine
python duplika.py D:\Photos --min-size 100000 --move D:\quarantine
```

| Option | Description |
|---|---|
| `--move FOLDER` | Moves duplicates into this folder, preserving their relative paths. Report only if omitted. |
| `--min-size N` | Skips files smaller than N bytes (default 1, so empty files are skipped). |
| `--all` | Also scans folders like `.git`, `.venv`, `node_modules` (skipped by default). |
| `--include-cloud` | Also scans OneDrive online-only files; this downloads them. |

## How it decides

- Filters by size first, then hashes only files that share a size.
- In each group the **oldest** file is kept (on a tie, the shortest path).
- If the quarantine folder is inside the scanned folder, it is excluded from the scan, so re-running is safe.
- If a file with the same name already exists in quarantine, it is not overwritten; the file is moved as `name (2).ext`.
- Virtual environments and version-control folders are skipped by default, because moving "duplicates" out of them breaks them.

## Limits

- Only finds exact duplicates, not similar photos or the same song encoded differently.
- Symbolic links are skipped.

## Development

```
pip install pytest
python -m pytest tests
```

License: MIT
