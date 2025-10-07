# GitHub Copilot Metastudy

Een Python project voor het uitvoeren van een metastudie over GitHub Copilot.

## Beschrijving

Dit is een basis Python project template met een proper virtual environment configuratie. Het project bevat alle benodigde bestanden om direct te kunnen beginnen met ontwikkelen.

## Vereisten

- Python 3.7 of hoger
- pip

## Installatie

1. Clone of download dit project
2. Navigeer naar de project directory:
   ```bash
   cd github-copilot-metastudy
   ```

3. Maak een virtual environment aan (als nog niet gedaan):
   ```bash
   python3 -m venv venv
   ```

4. Activeer het virtual environment:
   ```bash
   source venv/bin/activate
   ```

5. Installeer de dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Gebruik

### Basis Gebruik

```bash
# Activeer virtual environment
source venv/bin/activate

# Draai volledige pipeline
cd metastudy && python main.py
```

### Configuratie Aanpassen

Het systeem is volledig configureerbaar via `metastudy/config.py`. Je kunt aanpassen:

#### 🔍 **Zoekparameters**
```python
SEARCH_CONFIG = {
    "queries": [
        "GitHub Copilot",
        "AI code generation", 
        # Voeg je eigen termen toe...
    ],
    "max_results_per_query": 20,
    "total_max_papers": 200,
}
```

#### ⚙️ **Processing Instellingen**
- **Rate limiting**: API en download timeouts (min 3s voor arXiv compliance)
- **Retry logic**: Maximum pogingen en delays  
- **Conversie opties**: Pandoc vs pdfplumber preferences

#### 📁 **Storage Configuratie**
- **Directories**: PDF en Markdown opslag locaties
- **Bestandsgroottes**: Min/max limieten voor validatie

Zie [`CONFIGURATION_GUIDE.md`](CONFIGURATION_GUIDE.md) voor volledige documentatie.

## Project Structuur

```
github-copilot-metastudy/
├── data/                    # Data opslag (NIET in git)
│   ├── papers.db           # SQLite database met papers
│   ├── pdf/                # Gedownloade PDFs
│   └── md/                 # Geconverteerde Markdown bestanden
├── src/                    # Hoofd package directory
│   ├── arxiv/              # ArXiv API module
│   ├── pdf/                # PDF processing module  
│   ├── database/           # Database module
│   ├── tests/              # Unit tests
│   ├── config.py           # Configuratie
│   └── main.py             # Package workflow
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── .gitignore             # Git ignore bestand
└── README.md              # Dit bestand
```

## Development

### Virtual Environment

Om het virtual environment te activeren:
```bash
source venv/bin/activate
```

Om het virtual environment te deactiveren:
```bash
deactivate
```

### Dependencies toevoegen

Voeg nieuwe dependencies toe aan `metastudy/requirements.txt` en installeer ze:
```bash
pip install -r metastudy/requirements.txt
```

### Code formatting en linting

Het project bevat development tools voor code kwaliteit:
- `black` - Code formatting
- `flake8` - Linting
- `pytest` - Testing

## Bijdragen

1. Fork het project
2. Maak een feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit je wijzigingen (`git commit -m 'Add some AmazingFeature'`)
4. Push naar de branch (`git push origin feature/AmazingFeature`)
5. Open een Pull Request

## Licentie

Dit project is open source en beschikbaar onder de [MIT License](https://opensource.org/licenses/MIT).
