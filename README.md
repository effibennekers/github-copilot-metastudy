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

3. Voer de setup uit:
   ```bash
   make setup
   ```

   Of handmatig:
   ```bash
   # Maak een virtual environment aan
   python3 -m venv venv
   
   # Activeer het virtual environment
   source venv/bin/activate
   
   # Installeer dependencies
   pip install -r requirements.txt
   ```

## Gebruik

### Snelle Start

```bash
# Eenmalige setup
make setup

# Check status
make status

# Volledige pipeline
make pipeline
```

### Afzonderlijke Stappen

```bash
# Stap 1: Zoek nieuwe papers
make search

# Stap 2: Download PDFs  
make download

# Stap 3: Converteer naar Markdown
make convert

# Stap 4: LLM kwaliteitscontrole (optioneel)
make llm
```

### LLM Kwaliteitscontrole (Optioneel)

Voor automatische Markdown verbetering met Ollama:

1. **Installeer Ollama**:
   ```bash
   make install-ollama
   ```

2. **Setup model**:
   ```bash
   make setup-ollama
   ```

3. **Schakel LLM in** in `src/config.py`:
   ```python
   LLM_CONFIG = {
       "enabled": True,  # Zet op True
       "model_name": "llama3.2",
       # ... andere instellingen
   }
   ```

4. **Run LLM stap**:
   ```bash
   make llm
   ```

### Alle Beschikbare Commando's

```bash
# Setup en cleanup
make setup          # Installeer dependencies en setup virtual environment
make clean          # Verwijder virtual environment en cache bestanden

# Pipeline stappen
make status          # Toon database statistieken
make search          # Zoek en indexeer papers van arXiv
make download        # Download PDFs voor geïndexeerde papers
make convert         # Converteer PDFs naar Markdown
make llm             # Voer LLM kwaliteitscontrole uit
make pipeline        # Voer volledige pipeline uit (alle stappen)

# Development
make test            # Voer unit tests uit
make lint            # Voer code linting uit
make format          # Formatteer code met black

# Ollama setup
make install-ollama  # Installeer Ollama
make setup-ollama    # Download en setup llama3.2 model
make check-ollama    # Check Ollama status

# Utilities
make logs            # Toon recente logs
make data-info       # Toon data directory informatie

# Combinaties
make search-download # Zoek en download in één keer
make download-convert # Download en converteer in één keer
make convert-llm     # Converteer en LLM check in één keer
```

### Configuratie Aanpassen

Het systeem is volledig configureerbaar via `src/config.py`. Je kunt aanpassen:

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
- **PDF conversie**: Gebruikt pdfplumber voor betrouwbare tekstextractie

#### 🤖 **LLM Kwaliteitscontrole** (Optioneel)
- **Ollama integratie**: Lokale LLM voor Markdown verbetering
- **Automatische formatting**: Herstelt koppen, tabellen, lijsten en referenties
- **Batch processing**: Efficiënte verwerking van meerdere papers
- **Backup systeem**: Bewaart originele bestanden voor rollback

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
│   ├── arxiv_client/       # 📡 ArXiv API client
│   ├── pdf/                # 📄 PDF processing module  
│   ├── database/           # 🗄️ Database module
│   ├── llm/                # 🤖 LLM quality control
│   ├── tests/              # 🧪 Unit tests
│   ├── config.py           # ⚙️ Centralized configuratie
│   └── main.py             # 🚀 Hoofd workflow
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
