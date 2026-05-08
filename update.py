#!/usr/bin/env python3
"""
Fuegt in allen Python-Dateien unterhalb des aktuellen Ordners
einen Copyright-Abschnitt am Dateikopf ein.

Ausgenommen sind Dateien in Ordnern mit dem Namen "migrations".

Autor: Edgar Butwilowski
Organisation / Copyright-Inhaber: Fachstelle Geoinformation
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


AUTHOR = "Edgar Butwilowski"
COPYRIGHT_HOLDER = "Fachstelle Geoinformation"

COPYRIGHT_MARKER = "Copyright"
ENCODING_RE = re.compile(r"^#.*coding[:=]\s*[-\w.]+")


def build_copyright_header(year: int) -> str:
    """
    Erstellt einen kompakten, ueblichen Copyright-Header fuer Python-Dateien.
    """
    return (
        f"# Copyright (c) {year} {COPYRIGHT_HOLDER}\n"
        f"# Author: {AUTHOR}\n"
        "# All rights reserved.\n"
        "#\n"
        "# This source code is the property of the copyright holder.\n"
        "# Unauthorized copying, modification, distribution, or use is prohibited\n"
        "# unless expressly permitted in writing.\n"
        "\n"
    )


def detect_insert_position(lines: list[str]) -> int:
    """
    Bestimmt die Einfuegeposition gemaess Python-Konventionen:

    1. Shebang bleibt in Zeile 1.
    2. Encoding-Deklaration bleibt direkt danach.
    3. Copyright-Header folgt anschliessend.
    """
    pos = 0

    if lines and lines[0].startswith("#!"):
        pos = 1

    if len(lines) > pos and ENCODING_RE.match(lines[pos]):
        pos += 1

    return pos


def already_has_copyright(text: str) -> bool:
    """
    Verhindert doppelte Copyright-Header.
    Es wird nur der Anfang der Datei geprueft.
    """
    head = text[:2000]
    return COPYRIGHT_MARKER in head and COPYRIGHT_HOLDER in head


def process_file(path: Path, header: str, dry_run: bool = False) -> bool:
    """
    Fuegt den Header in eine einzelne Datei ein.
    Gibt True zurueck, wenn die Datei geaendert wurde oder wuerde.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"Uebersprungen wegen unbekannter Kodierung: {path}")
        return False

    if already_has_copyright(text):
        return False

    lines = text.splitlines(keepends=True)
    insert_pos = detect_insert_position(lines)

    new_lines = lines[:insert_pos]

    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    new_lines.append(header)
    new_lines.extend(lines[insert_pos:])

    new_text = "".join(new_lines)

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")

    return True


def iter_python_files(root: Path) -> list[Path]:
    """
    Liefert alle Python-Dateien unterhalb von root,
    ohne typische virtuelle Umgebungen, Cache-Ordner und Migrationsordner.
    """
    ignored_dirs = {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        "migrations",
    }

    files: list[Path] = []

    for path in root.rglob("*.py"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        files.append(path)

    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fuegt rekursiv einen Copyright-Header in Python-Dateien ein."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Startordner. Standard: aktueller Ordner.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=dt.date.today().year,
        help="Copyright-Jahr. Standard: aktuelles Jahr.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Zeigt nur, welche Dateien geaendert wuerden.",
    )

    args = parser.parse_args()

    header = build_copyright_header(args.year)
    files = iter_python_files(args.root)

    changed: list[Path] = []

    for file_path in files:
        if process_file(file_path, header, dry_run=args.dry_run):
            changed.append(file_path)

    action = "Wuerde aendern" if args.dry_run else "Geaendert"

    for path in changed:
        print(f"{action}: {path}")

    print()
    print(f"Python-Dateien gefunden: {len(files)}")
    print(f"{action}: {len(changed)}")


if __name__ == "__main__":
    main()