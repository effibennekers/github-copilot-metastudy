# GitHub Copilot Metastudy

Een Python project voor het uitvoeren van een metastudie over GitHub Copilot.
Dit zijn de make targets in volgorde.
Notitie: clear dure tabellen niet, zoals voor labeling.

Initiele import:
import-metadata: importeer de metadata.
import-labels: importeer de labels.

Bereid het labelen voor (herhaalbaar):
list-questions: vraag de vragenlijst op en kies de vraag waarmee je wil labelen.
prepare-labeling: Geef de question.id mee, zet labeling jobs klaar in de queue.

Voer de labeling uit:
run-labeling: Ga door de queue en voer de labeling uit.

Download de papers:
aan de hand van gewenste labels, ga door metadata_labels voor de metadata ids.
maak daar een paper id van
...

CLI (click) via entrypoint:

```bash
python -m src.main stats
python -m src.main list-questions
python -m src.main import-labels
python -m src.main import-metadata --max-records 1000 --batch-size 500
python -m src.main prepare-labeling 42 --date-after 2025-09-01
python -m src.main label --jobs 10
python -m src.main prepare-paper --batch-size 1000 --limit 5000
python -m src.main prepare-download 3
```