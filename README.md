# GitHub Copilot Metastudy

Een Python project voor het uitvoeren van een metastudie over GitHub Copilot.
Dit zijn de make targets in volgorde.

Initiele import:
import-metadata: importeer de metadata.
import-labels: importeer de labels.

Bereid het labelen voor (herhaalbaar):
list-questions: vraag de vragenlijst op en kies de vraag waarmee je wil labelen.
prepare-labeling: Geef de question.id mee, zet labeling jobs klaar in de queue.

voer de labeling uit:
run-labeling: Ga door de queue en voer de labeling uit.

...