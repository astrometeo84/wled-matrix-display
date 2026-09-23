# Mitwirken

## Ablauf

`main` ist geschützt. Änderungen laufen immer über einen Pull Request.

```bash
git switch -c feat/fenster-mit-namen
# ... arbeiten ...
uv run pytest
uv run yamllint --strict .

git add -A
git commit -m "feat: Fenster-App zeigt Raumnamen statt Anzahl"
git push -u origin feat/fenster-mit-namen
gh pr create --fill
```

Im Pull Request laufen die Prüfungen automatisch. Sind alle grün, kann gemergt werden.

## Commit-Nachrichten

Das Projekt benutzt [Conventional Commits](https://www.conventionalcommits.org/de/). Aus dem Präfix leitet release-please die nächste Versionsnummer ab und baut daraus den CHANGELOG. Deshalb lohnt es sich, kurz zu überlegen, welches passt.

| Präfix | Bedeutung | Version |
|---|---|---|
| `feat:` | neue Funktion | 1.0.0 → 1.**1**.0 |
| `fix:` | Fehlerbehebung | 1.0.0 → 1.0.**1** |
| `docs:` | nur Dokumentation | keine |
| `test:` | nur Tests | keine |
| `refactor:` | Umbau ohne sichtbare Änderung | keine |
| `ci:` / `chore:` | Werkzeuge, Wartung | keine |

**Bricht eine Änderung bestehende Automationen**, etwa weil eine Eingabe umbenannt oder entfernt wurde, gehört ein `!` hinter das Präfix und eine Erklärung in den Rumpf:

```
feat!: Eingabe hp_color in hp_color_low umbenannt

BREAKING CHANGE: Wer die Wärmepumpen-App nutzt, muss die
Automation einmal öffnen und neu speichern.
```

Das hebt die **Hauptversion** an, aus 1.4.2 wird 2.0.0.

Schreib die Beschreibung so, dass sie im CHANGELOG verständlich ist — dort landet sie wörtlich. Also lieber „Fenster-App zeigt Raumnamen statt Anzahl" als „Fenster angepasst".

## Wie ein Release entsteht

Du musst **keine Version von Hand anheben und keinen Tag setzen**. Das übernimmt release-please:

1. Du mergst einen PR nach `main`.
2. Der Bot legt einen Pull Request namens **`chore(main): release X.Y.Z`** an oder aktualisiert ihn. Darin: der ergänzte CHANGELOG und die angehobene Version im Blueprint und in der `pyproject.toml`.
3. Weitere Merges sammeln sich in demselben Release-PR.
4. Wenn du veröffentlichen willst, **mergst du den Release-PR**. Daraufhin entstehen Tag und GitHub-Release, und die Blueprint-Datei wird angehängt.

Der Release-PR ist eine Vorschau: Du siehst vor dem Veröffentlichen genau, welche Version herauskommt und was im CHANGELOG stehen wird. Passt etwas nicht, korrigierst du es vorher im Branch des Release-PR.

## Einstellungen auf GitHub

Einmalig einzurichten, unter **Settings → Rules → Rulesets → New branch ruleset**:

| Einstellung | Wert |
|---|---|
| Target branches | `main` |
| Restrict deletions | an |
| Block force pushes | an |
| Require a pull request before merging | an |
| Required approvals | 0, wenn du allein arbeitest |
| Require status checks to pass | an |

Als erforderliche Prüfungen auswählen:

- `YAML-Stil`
- `Tests (Python 3.11)`, `Tests (Python 3.12)`, `Tests (Python 3.13)`
- `Home Assistant lädt den Blueprint`

Die Namen tauchen in der Auswahlliste erst auf, nachdem sie mindestens einmal gelaufen sind.

> **Wichtig, wenn du allein arbeitest:** Setze „Required approvals" auf 0. Sonst kannst du deine eigenen Pull Requests nicht mergen, auch den Release-PR nicht.

Unter **Settings → Actions → General** muss außerdem **„Allow GitHub Actions to create and approve pull requests"** aktiv sein — sonst darf der Bot den Release-PR nicht anlegen.

## Warum kein Release bei jedem Merge

Das wäre technisch möglich, erfordert aber eine Ausnahme vom Branch-Schutz: Der Bot müsste die Versionsanhebung direkt nach `main` pushen. Der Weg über den Release-PR kommt ohne solche Ausnahme aus und hat den Nebeneffekt, dass mehrere kleine Änderungen zu einer Version zusammengefasst werden, statt für jeden Tippfehler eine neue Veröffentlichung zu erzeugen.
