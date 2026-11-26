"""Create a source-only ZIP; excludes credentials, caches and runtime state."""

import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
out = root / ".local" / "mai-team-source.zip"
out.parent.mkdir(exist_ok=True)
exclude = {
    ".git",
    "node_modules",
    ".next",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".local",
    "dist",
    "test-results",
}
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude]
        for name in sorted(files):
            p = Path(directory) / name
            if (name.startswith(".env") and name != ".env.example") or p.suffix in {
                ".db",
                ".pyc",
                ".log",
                ".zip",
            }:
                continue
            if not p.resolve().is_relative_to(root.resolve()):
                continue
            archive.write(p, Path(root.name) / p.relative_to(root))
print(out)
