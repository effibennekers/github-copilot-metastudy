# Project Rules - GitHub Copilot Metastudy

## ArXiv API Usage Rules

### Rate Limiting (VERPLICHT)

**Alle code die de arXiv API gebruikt MOET zich houden aan de volgende rate limits:**

- **Maximum 1 request per 3 seconden**
- **Gebruik slechts 1 verbinding tegelijk**
- **Geen circumvention van rate limits toegestaan**

Bron: [arXiv API Terms of Use](https://info.arxiv.org/help/api/tou.html)

### Implementatie Vereisten

1. **Elke API call moet een delay van minimaal 3 seconden** hebben tussen opeenvolgende requests
2. **Gebruik `time.sleep(3)` of vergelijkbare mechanismen** tussen API calls
3. **Geen parallelle requests** naar de arXiv API
4. **Monitor en log API usage** om compliance te waarborgen

### Voorbeeld Implementatie

```python
import time
import arxiv

def safe_arxiv_search(query, max_results=10):
    """
    Zoek papers op arXiv met rate limiting compliance
    """
    # Rate limiting: wacht 3 seconden voor de request
    time.sleep(3)
    
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results)
    
    return list(client.results(search))
```

### Consequenties van Overtreding

- **IP ban** door arXiv mogelijk
- **Verstoring van service** voor andere gebruikers
- **Schending van Terms of Use** kan leiden tot permanente blokkering

### Copyright en Gebruik

- **Metadata** mag worden opgeslagen en gedeeld (CC0 1.0 Public Domain)
- **E-print content** mag NIET worden opgeslagen/gediend zonder toestemming copyright houder
- **Verwijs altijd naar arXiv.org** voor volledige papers
- **Link naar abstract pages** in plaats van directe PDF links

## Code Style Rules

### Python Code Standards

- Gebruik **Nederlandse commentaren** voor documentatie
- Volg **PEP 8** styling guidelines
- Gebruik **type hints** waar mogelijk
- Schrijf **docstrings** voor alle functies

### Git Commit Standards

- Gebruik **Nederlandse commit messages**
- Begin commits met werkwoord (bijv. "Voeg toe", "Fix", "Update")
- Verwijs naar issue numbers waar relevant

## Dependencies

### Versie Management

- **Pin exacte versies** in requirements.txt
- Test nieuwe versies voordat je update
- Documenteer breaking changes in commit messages

### Toegestane Libraries

- **arxiv==2.2.0** (verplicht voor arXiv API access)
- **Standard library modules** (time, json, etc.)
- **Testing libraries** (pytest, etc.)
- **Code quality tools** (black, flake8, etc.)

---

**Belangrijk**: Deze regels zijn niet optioneel. Overtreding kan leiden tot blokkering van de arXiv API toegang voor het hele project.

Laatste update: Oktober 2025
