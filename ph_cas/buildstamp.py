"""B77 (Sentire UAT Standard v1.0): the build stamp a tester checks against the UAT workbook's Cover.

The build is "<version>+<12 hex>", the hex being a SHA-1 over every file of the ph_cas package
(path and content, sorted by path; __pycache__, .pyc and BUILD left out). The image writes it to
ph_cas/BUILD at build time (Dockerfile); the developer works out the same value from the commit:

    python3 ph_cas/buildstamp.py            # from the files on disk
    python3 ph_cas/buildstamp.py --git REV  # from a commit, e.g. HEAD or origin/main

Docs, workflows and tests outside the package do not change it, so a docs-only commit keeps the
build. This module imports nothing from Frappe so the Dockerfile can run it before the bench starts.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"__pycache__", "node_modules"}


def _keep(rel: str) -> bool:
    parts = rel.split("/")
    return not (set(parts) & SKIP_DIRS) and not rel.endswith(".pyc") and rel != "BUILD"


def digest(items) -> str:
    h = hashlib.sha1()
    for rel, data in sorted(items):
        h.update(rel.encode() + b"\0" + data + b"\0")
    return h.hexdigest()[:12]


def from_disk(root: str = PKG) -> str:
    items = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            if _keep(rel):
                with open(os.path.join(d, f), "rb") as fh:
                    items.append((rel, fh.read()))
    return digest(items)


def from_git(rev: str, repo: str | None = None) -> str:
    repo = repo or os.path.dirname(PKG)
    names = [n for n in subprocess.check_output(["git", "-C", repo, "ls-tree", "-r", "-z", "--name-only", rev, "ph_cas"], text=True).split("\0") if n]
    items = []
    for n in names:
        rel = n[len("ph_cas/"):]
        if _keep(rel):
            items.append((rel, subprocess.check_output(["git", "-C", repo, "show", f"{rev}:{n}"])))
    return digest(items)


def version() -> str:
    with open(os.path.join(PKG, "__init__.py")) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("\"'")
    return "0"


def build() -> str:
    """The stamp written into the image, or worked out from the files when running from source."""
    path = os.path.join(PKG, "BUILD")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return f"{version()}+{from_disk()}"


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--git":
        print(f"{version()}+{from_git(sys.argv[2])}")
    else:
        print(f"{version()}+{from_disk()}")
