"""
LLM Checker voor GitHub Copilot Metastudy
Gebruikt Ollama voor kwaliteitscontrole en verbetering van Markdown bestanden
"""

import requests
import json
import logging
from typing import Optional, Tuple
from pathlib import Path

# Import configuratie
from src.config import LLM_CONFIG


class LLMChecker:
    def __init__(self, ollama_url: str = None, model_name: str = None):
        self.config = LLM_CONFIG
        self.ollama_url = ollama_url or self.config.get('ollama_api_base_url', 'http://localhost:11434')
        self.model_name = model_name or self.config.get('model_name', 'llama3.2')
        self.logger = logging.getLogger(__name__)
        
        # Check if LLM is enabled
        if not self.config.get('enabled', False):
            self.logger.info("LLM checker is disabled in configuration")
        else:
            self.logger.info(f"LLM Checker initialized: {self.ollama_url} with model {self.model_name}")
    
    def is_enabled(self) -> bool:
        """Check if LLM functionality is enabled"""
        return self.config.get('enabled', False)
    
    def check_ollama_availability(self) -> bool:
        """Check if Ollama server is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name', '') for model in models]
                
                if any(self.model_name in name for name in model_names):
                    self.logger.info(f"Ollama server available with model {self.model_name}")
                    return True
                else:
                    self.logger.warning(f"Model {self.model_name} not found. Available models: {model_names}")
                    return False
            else:
                self.logger.error(f"Ollama server responded with status {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Cannot connect to Ollama server: {e}")
            return False
    
    def check_and_fix_markdown(self, md_content: str, arxiv_id: str) -> Tuple[str, str]:
        """
        Check en verbeter Markdown met lokale LLM
        Returns: (improved_content, status)
        Status can be: 'CLEAN', 'FIXED', 'FAILED'
        """
        if not self.is_enabled():
            self.logger.info(f"LLM checker disabled, marking {arxiv_id} as CLEAN")
            return md_content, 'CLEAN'
        
        if not self.check_ollama_availability():
            self.logger.error(f"Ollama not available, marking {arxiv_id} as FAILED")
            return md_content, 'FAILED'
        
        # Prepare prompt based on configuration
        prompt_template = self.config.get('prompt_template', self._get_default_prompt())
        
        # Truncate content if too long to avoid token limits
        max_tokens = self.config.get('max_tokens', 4000)
        if len(md_content) > max_tokens * 3:  # Rough estimate: 1 token ≈ 3 chars
            self.logger.warning(f"Content too long for {arxiv_id}, truncating...")
            md_content = md_content[:max_tokens * 3]
        
        full_prompt = f"{prompt_template}\n\nTEKST:\n{md_content}"
        
        try:
            self.logger.info(f"Sending {arxiv_id} to LLM for quality check...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.get('temperature', 0.1),
                        "num_predict": max_tokens
                    }
                },
                timeout=self.config.get('timeout_seconds', 120)
            )
            
            if response.status_code == 200:
                result = response.json()
                improved_content = result.get('response', '').strip()
                
                # Sanity checks
                if not improved_content:
                    self.logger.warning(f"Empty LLM response for {arxiv_id}")
                    return md_content, 'FAILED'
                
                # Check if response is reasonable (not too short or too different)
                original_length = len(md_content)
                improved_length = len(improved_content)
                
                if improved_length < original_length * 0.5:
                    self.logger.warning(f"LLM response too short for {arxiv_id} ({improved_length} vs {original_length} chars)")
                    return md_content, 'CLEAN'
                
                if improved_length > original_length * 2:
                    self.logger.warning(f"LLM response too long for {arxiv_id} ({improved_length} vs {original_length} chars)")
                    return md_content, 'CLEAN'
                
                # Check if content was actually improved
                if improved_content.strip() == md_content.strip():
                    self.logger.info(f"No improvements needed for {arxiv_id}")
                    return md_content, 'CLEAN'
                else:
                    self.logger.info(f"Successfully improved {arxiv_id} ({original_length} → {improved_length} chars)")
                    return improved_content, 'FIXED'
                    
            else:
                self.logger.error(f"LLM API error for {arxiv_id}: HTTP {response.status_code}")
                return md_content, 'FAILED'
                
        except requests.exceptions.Timeout:
            self.logger.error(f"LLM request timeout for {arxiv_id}")
            return md_content, 'FAILED'
        except Exception as e:
            self.logger.error(f"LLM check failed for {arxiv_id}: {e}")
            return md_content, 'FAILED'
    
    def _get_default_prompt(self) -> str:
        """Get default prompt for markdown improvement"""
        return """Je bent een expert in het controleren van academische papers die zijn geconverteerd van PDF naar Markdown.

Controleer de volgende Markdown tekst op:
1. Verkeerde koppen (# ## ###) - zorg dat ze logisch genest zijn
2. Gebroken tabellen - herstel tabel formatting
3. Foute lijstopmaak - corrigeer genummerde en bullet lists
4. Referentie formatting - zorg voor correcte [1], [2] notatie
5. Figuur/tabel captions - herstel "Figure 1:", "Table 2:" formatting
6. Paragraaf structuur - voeg ontbrekende line breaks toe
7. Code blocks - zorg voor correcte ``` formatting
8. Mathematical formulas - behoud LaTeX notatie waar mogelijk

BELANGRIJKE REGELS:
- Behoud ALLE originele inhoud en betekenis
- Verander GEEN wetenschappelijke termen of concepten
- Voeg GEEN nieuwe informatie toe
- Focus alleen op Markdown opmaak verbetering
- Als de tekst al goed geformatteerd is, verander dan niets

Antwoord ALLEEN met de gecorrigeerde Markdown, geen extra uitleg of commentaar."""
    
    def process_batch(self, papers_data: list) -> dict:
        """
        Process multiple papers in batch
        Returns: {'processed': int, 'fixed': int, 'failed': int, 'clean': int}
        """
        stats = {'processed': 0, 'fixed': 0, 'failed': 0, 'clean': 0}
        
        if not self.is_enabled():
            self.logger.info("LLM checker disabled, skipping batch processing")
            return stats
        
        for paper_data in papers_data:
            arxiv_id = paper_data.get('arxiv_id')
            md_path = paper_data.get('md_path')
            
            if not md_path or not Path(md_path).exists():
                self.logger.warning(f"No markdown file found for {arxiv_id}")
                continue
            
            try:
                # Read markdown content
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Process with LLM
                improved_content, status = self.check_and_fix_markdown(md_content, arxiv_id)
                
                # Save improved version if fixed
                if status == 'FIXED':
                    # Create backup first
                    backup_path = Path(md_path).with_suffix('.md.backup')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    
                    # Save improved version
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(improved_content)
                    
                    self.logger.info(f"Saved improved version for {arxiv_id} (backup: {backup_path})")
                
                # Update stats
                stats['processed'] += 1
                stats[status.lower()] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {arxiv_id}: {e}")
                stats['failed'] += 1
        
        self.logger.info(f"Batch processing complete: {stats}")
        return stats
