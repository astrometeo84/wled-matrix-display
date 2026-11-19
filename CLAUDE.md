# Hinweise für Claude

Home-Assistant-Blueprint, der eine WLED-Matrix (64×8) zur Info-Anzeige im Stil
von Awtrix macht. Läuft produktiv an echter Hardware.

## Vor jeder Änderung lesen

`README.md`, `CONTRIBUTING.md` und `docs/entwicklung.md`. Dort und in den
Kommentaren im Blueprint steht, warum bestimmte Dinge so sind, wie sie sind.
Was dort begründet ist, nicht „aufräumen“. Beispiele: `default: []` statt `""`
bei Entitäten in Triggern, `version = "0"` in der `pyproject.toml`, feste
Effekt-ID statt Erkennung über `effect_list`, ASCII-Zeichen statt Gradzeichen
oder Pfeilen.

## Arbeitsweise

- `main` ist geschützt, alles läuft über einen Branch und einen PR.
- Commits nach Conventional Commits, auf Deutsch, so formuliert, dass sie im
  CHANGELOG verständlich sind. Bricht eine Änderung bestehende Automationen
  (Eingabe umbenannt oder entfernt): `feat!:` plus `BREAKING CHANGE:` im Rumpf.
- release-please erzeugt Version, CHANGELOG und Release-PR. Keine Version von
  Hand anheben, keinen Tag setzen, `CHANGELOG.md` nicht anfassen.
- Der Nutzer testet am echten Home Assistant, bevor er committet. Nicht
  ungefragt committen oder pushen; Änderungen im Arbeitsverzeichnis lassen.

## Prüfen

```bash
uv run pytest               # rund 270 Tests
uv run yamllint --strict .
```

- Die Tests lesen die Jinja-Vorlagen direkt aus der Blueprint-Datei. In den
  Tests keine Kopien davon anlegen; Standardwerte über `input_default()` lesen.
- Neue Logik: erst den Test, dann prüfen, ob er ohne die Funktion wirklich
  fehlschlägt (Blueprint absichtlich kaputt machen). Erkannte Fehler in die
  Tabelle in `docs/entwicklung.md` eintragen.

## Skills in diesem Repo

- `neue-app`: alle Stellen, die eine neue App im Blueprint berührt.
- `ha-testen`: Blueprint vor dem Commit ins echte Home Assistant spielen.
