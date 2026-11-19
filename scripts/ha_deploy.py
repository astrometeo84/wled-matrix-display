#!/usr/bin/env python3
"""Blueprint aus dem Arbeitsverzeichnis in ein laufendes Home Assistant spielen.

Gedacht zum Ausprobieren vor dem Commit: Die Datei wird so kopiert, wie sie
gerade auf der Platte liegt, auch mit ungespeicherten oder nur gestagten
Änderungen. Danach lässt Home Assistant die Konfiguration prüfen und lädt die
Automationen neu. Dabei liest es auch die Blueprints neu ein, ein Neustart ist
nicht nötig.

Aufruf:
    uv run scripts/ha_deploy.py            # kopieren, prüfen, neu laden
    uv run scripts/ha_deploy.py --trocken  # nur anzeigen, was passieren würde

Einstellungen kommen aus Umgebungsvariablen oder aus der Datei ``.ha.env``
im Wurzelverzeichnis (steht in .gitignore, der Token gehört nicht ins Repo):

    HA_BLUEPRINT_ZIEL  Wohin die Datei kopiert wird. Entweder ein Ordner, etwa
                       die Samba-Freigabe von Home Assistant:
                         \\\\homeassistant.local\\config\\blueprints\\automation\\wled_matrix
                         /Volumes/config/blueprints/automation/wled_matrix
                       oder ein scp-Ziel über das SSH-Add-on:
                         root@homeassistant.local:/config/blueprints/automation/wled_matrix/
    HA_URL             optional, z. B. http://homeassistant.local:8123
    HA_TOKEN           optional, langlebiger Zugriffstoken (Profil → Sicherheit)

Ohne HA_URL und HA_TOKEN wird nur kopiert. Dann in Home Assistant unter
Entwicklerwerkzeuge → YAML die Automationen von Hand neu laden.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
BLUEPRINT = WURZEL / "blueprints" / "automation" / "wled_matrix" / "wled_matrix_display.yaml"
ENV_DATEI = WURZEL / ".ha.env"

# benutzer@host:pfad – aber kein Windows-Laufwerk wie C:\...
SCP_MUSTER = re.compile(r"^[^\\/:@\s]+@[^\\/:\s]+:")


def lies_env_datei(pfad: Path) -> dict[str, str]:
    """KEY=VALUE-Zeilen lesen. Leerzeilen, Kommentare und Anführungszeichen erlaubt."""
    werte: dict[str, str] = {}
    if not pfad.is_file():
        return werte
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, wert = zeile.split("=", 1)
        werte[schluessel.strip()] = wert.strip().strip('"').strip("'")
    return werte


def einstellungen(env: dict[str, str] | None = None) -> dict[str, str]:
    """Umgebungsvariablen haben Vorrang vor der Datei."""
    werte = lies_env_datei(ENV_DATEI)
    quelle = os.environ if env is None else env
    for schluessel in ("HA_BLUEPRINT_ZIEL", "HA_URL", "HA_TOKEN"):
        if quelle.get(schluessel):
            werte[schluessel] = quelle[schluessel]
    return werte


def ist_scp_ziel(ziel: str) -> bool:
    return bool(SCP_MUSTER.match(ziel))


def kopieren(ziel: str, trocken: bool) -> None:
    if ist_scp_ziel(ziel):
        befehl = ["scp", "-q", str(BLUEPRINT), ziel]
        print("scp  ->", ziel)
        if not trocken:
            subprocess.run(befehl, check=True)
        return
    ordner = Path(ziel)
    print("copy ->", ordner / BLUEPRINT.name)
    if trocken:
        return
    if not ordner.is_dir():
        raise SystemExit(f"Zielordner nicht gefunden: {ordner}\n"
                         "Ist die Samba-Freigabe verbunden und der Ordner angelegt?")
    shutil.copy2(BLUEPRINT, ordner / BLUEPRINT.name)


def ha_aufruf(url: str, token: str, pfad: str) -> object:
    anfrage = urllib.request.Request(
        url.rstrip("/") + pfad,
        data=b"{}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(anfrage, timeout=120) as antwort:
        text = antwort.read().decode("utf-8") or "null"
    return json.loads(text)


def pruefen_und_neu_laden(url: str, token: str, trocken: bool) -> int:
    print("prüfe Konfiguration und lade Automationen neu:", url)
    if trocken:
        return 0
    try:
        ergebnis = ha_aufruf(url, token, "/api/config/core/check_config")
        if isinstance(ergebnis, dict) and ergebnis.get("result") != "valid":
            print("Home Assistant meldet Fehler, Automationen NICHT neu geladen:")
            print(ergebnis.get("errors") or ergebnis)
            return 1
        ha_aufruf(url, token, "/api/services/automation/reload")
    except urllib.error.HTTPError as fehler:
        hinweis = " (Token falsch oder abgelaufen?)" if fehler.code == 401 else ""
        print(f"Home Assistant antwortet mit {fehler.code}{hinweis}")
        return 1
    except urllib.error.URLError as fehler:
        print(f"Home Assistant nicht erreichbar: {fehler.reason}")
        return 1
    print("fertig – Automation öffnen, neue Felder ausfüllen, Traces ansehen.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--trocken", action="store_true", help="nichts ändern, nur anzeigen")
    args = parser.parse_args(argv)

    cfg = einstellungen()
    ziel = cfg.get("HA_BLUEPRINT_ZIEL")
    if not ziel:
        print("HA_BLUEPRINT_ZIEL fehlt – siehe Kopf von scripts/ha_deploy.py", file=sys.stderr)
        return 2

    kopieren(ziel, args.trocken)

    if cfg.get("HA_URL") and cfg.get("HA_TOKEN"):
        return pruefen_und_neu_laden(cfg["HA_URL"], cfg["HA_TOKEN"], args.trocken)
    print("Kein HA_URL/HA_TOKEN: Automationen in Home Assistant von Hand neu laden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
