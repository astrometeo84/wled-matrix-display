#!/usr/bin/env python3
"""Prüft, ob die Version im Blueprint zum Git-Tag passt.

Aufruf:  python3 scripts/check_version.py 1.2.0
Der Blueprint trägt die Version als Kommentarzeile ``# Version: 1.2.0`` im Kopf,
weil das Blueprint-Schema von Home Assistant kein eigenes Versionsfeld kennt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BLUEPRINT = (
    Path(__file__).resolve().parent.parent
    / "blueprints"
    / "automation"
    / "wled_matrix"
    / "wled_matrix_display.yaml"
)
MUSTER = re.compile(r"^#\s*Version:\s*(\S+)\s*$", re.MULTILINE)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Aufruf: check_version.py <version-ohne-v>", file=sys.stderr)
        return 2

    erwartet = argv[1]
    treffer = MUSTER.search(BLUEPRINT.read_text(encoding="utf-8"))

    if not treffer:
        print(f"FEHLER: keine Zeile '# Version: ...' in {BLUEPRINT.name}", file=sys.stderr)
        return 1

    gefunden = treffer.group(1)
    if gefunden != erwartet:
        print(
            f"FEHLER: Tag sagt {erwartet}, Blueprint sagt {gefunden}.\n"
            f"        Die Zeile '# Version:' in {BLUEPRINT.name} anpassen "
            f"und den Tag neu setzen.",
            file=sys.stderr,
        )
        return 1

    print(f"Version {gefunden} passt zum Tag.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
