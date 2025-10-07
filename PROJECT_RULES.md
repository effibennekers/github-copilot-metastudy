# Project Rules - GitHub Copilot Metastudy

## ArXiv API Usage Rules

**BELANGRIJK**: Alle arXiv API gerelateerde regels staan nu in de Cursor Rules: `.cursor/rules/arxiv-terms-of-use.mdc`

Deze regels worden automatisch toegepast door Cursor en bevatten:
- **Rate limiting vereisten**: 1 request per 3 seconden
- **Copyright compliance** 
- **Implementatie voorbeelden**
- **Consequenties van overtreding**

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
