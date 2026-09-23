#!/usr/bin/env bash
#
# Richtet das Repo ein: Platzhalter ersetzen, Git vorbereiten, optional hochladen.
#
#   ./scripts/setup.sh <github-benutzer> [repo-name]
#
# Beispiel:
#   ./scripts/setup.sh maxmuster wled-matrix-display
#
set -euo pipefail

BENUTZER="${1:-}"
REPO="${2:-wled-matrix-display}"

if [ -z "$BENUTZER" ]; then
  echo "Aufruf: $0 <github-benutzer> [repo-name]" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

if grep -rq "BENUTZER/REPO\|BENUTZER%2FREPO" . --include='*.md' --include='*.yml' --include='*.yaml' 2>/dev/null; then
  echo "» Platzhalter ersetzen: BENUTZER/REPO -> $BENUTZER/$REPO"
  # Normale Vorkommen und die URL-kodierte Form im Import-Knopf
  grep -rl "BENUTZER/REPO\|BENUTZER%2FREPO" . \
    --include='*.md' --include='*.yml' --include='*.yaml' 2>/dev/null \
    | while read -r datei; do
        sed -i.bak \
          -e "s|BENUTZER/REPO|$BENUTZER/$REPO|g" \
          -e "s|BENUTZER%2FREPO|$BENUTZER%2F$REPO|g" \
          "$datei"
        rm -f "$datei.bak"
        echo "   $datei"
      done
else
  echo "» Keine Platzhalter mehr vorhanden, übersprungen."
fi

echo "» Tests"
# Alles über denselben Interpreter, sonst findet ein global installiertes
# pytest die Pakete nicht, die in der virtuellen Umgebung liegen.
PY="${PYTHON:-python3}"
if ! "$PY" -c "import pytest, yaml, jinja2" >/dev/null 2>&1; then
  # Fehlende Werkzeuge sind kein Grund abzubrechen – die Einrichtung geht weiter.
  echo "   Übersprungen: pytest, PyYAML oder Jinja2 fehlen für $PY."
  echo "   Nachholen mit: $PY -m pip install -r requirements-dev.txt && $PY -m pytest"
else
  # Ein echter Testfehler bricht dagegen ab: nichts Kaputtes veröffentlichen.
  "$PY" -m pytest -q
fi

if [ ! -d .git ]; then
  echo "» Git-Repository anlegen"
  git init -b main >/dev/null
  git add -A
  git commit -q -m "WLED Matrix Display Blueprint"
else
  echo "» Git-Repository besteht bereits, nichts geändert."
fi

echo
echo "Fertig. Nächster Schritt:"
echo
if command -v gh >/dev/null 2>&1; then
  echo "  gh repo create $REPO --public --source=. --push"
else
  echo "  Repo auf github.com anlegen (Name: $REPO), dann:"
  echo "  git remote add origin git@github.com:$BENUTZER/$REPO.git"
  echo "  git push -u origin main"
fi
echo
echo "Danach das erste Release:"
echo "  git tag v1.0.0 && git push origin --tags"
