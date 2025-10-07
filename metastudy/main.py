#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdmodule voor het onderzoeken van papers over GitHub Copilot
"""

import arxiv

def search_copilot_papers():
    """Zoek papers over GitHub Copilot op arXiv"""
    print("Zoeken naar GitHub Copilot papers op arXiv...")
    
    # Gebruik de nieuwe Client API in plaats van de deprecated Search.results()
    client = arxiv.Client()
    search = arxiv.Search(
        query="GitHub Copilot OR Copilot programming OR AI code generation",
        max_results=10,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    papers = []
    for result in client.results(search):
        paper_info = {
            'title': result.title,
            'authors': [author.name for author in result.authors],
            'abstract': result.summary[:200] + "..." if len(result.summary) > 200 else result.summary,
            'published': result.published.strftime('%Y-%m-%d'),
            'url': result.entry_id
        }
        papers.append(paper_info)
        
        print(f"\nTitel: {paper_info['title']}")
        print(f"Auteurs: {', '.join(paper_info['authors'])}")
        print(f"Gepubliceerd: {paper_info['published']}")
        print(f"URL: {paper_info['url']}")
        print(f"Abstract: {paper_info['abstract']}")
        print("-" * 80)
    
    return papers

def main():
    """Hoofd functie van het metastudy programma"""
    print("GitHub Copilot Metastudy - Onderzoek naar AI-ondersteunde programmering")
    print("=" * 70)
    
    try:
        papers = search_copilot_papers()
        print(f"\nGevonden papers: {len(papers)}")
        
    except Exception as e:
        print(f"Fout bij het ophalen van papers: {e}")
        print("Zorg ervoor dat je internetverbinding hebt en probeer opnieuw.")

if __name__ == "__main__":
    main()
