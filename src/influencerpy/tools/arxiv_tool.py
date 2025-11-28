import requests
from bs4 import BeautifulSoup
import arxiv
from strands import tool

def get_top_paper_url(exclude_urls: set | None = None):
    """
    Fetches the URL of the top paper from the Hugging Face papers page.
    """
    url = "https://huggingface.co/papers"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # This selector might need adjustment based on HF's actual structure
        # Based on x-ai example: soup.find("article").find("a")
        article = soup.find("article")
        if article:
            link = article.find("a")
            if link and link.has_attr('href'):
                full_url = f"https://huggingface.co{link['href']}"
                if exclude_urls and full_url in exclude_urls:
                    return None
                return full_url
    except Exception as e:
        print(f"Error fetching top paper: {e}")
        return None
    return None

def get_arxiv_id_from_url(url: str) -> str:
    """
    Extracts the ArXiv ID from a Hugging Face paper URL or Arxiv URL.
    """
    # Simple extraction logic, assumes ID is the last part
    # e.g. https://huggingface.co/papers/2310.12345 -> 2310.12345
    # e.g. https://arxiv.org/abs/2310.12345 -> 2310.12345
    return url.split("/")[-1]

@tool
def arxiv_search(query: str, days_back: int = None) -> str:
    """
    Search for papers on Arxiv.
    
    Use this tool to find academic papers, research, and technical documents.
    
    Args:
        query: The search query string (e.g., "LLM agents", "2310.12345").
        days_back: Optional. Filter for papers published within the last N days.
        
    Returns:
        A summary of the top search result.
    """
    try:
        from datetime import datetime, timedelta
        import pytz

        # Check if query is likely an ID or a search term
        # If it looks like an ID (digits.digits), treat as ID search
        # Otherwise search by query
        
        # If filtering by date, we need to fetch more results to find a match
        max_results = 20 if days_back else 1
        sort_by = arxiv.SortCriterion.SubmittedDate if days_back else arxiv.SortCriterion.Relevance
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )
        
        results = list(search.results())
        if not results:
            return "No results found on Arxiv."
            
        selected_paper = None
        
        if days_back:
            cutoff_date = datetime.now(pytz.utc) - timedelta(days=days_back)
            for paper in results:
                # Arxiv published date is timezone aware (UTC)
                if paper.published >= cutoff_date:
                    selected_paper = paper
                    break
            
            if not selected_paper:
                return f"No papers found matching '{query}' published within the last {days_back} days."
        else:
            selected_paper = results[0]
        
        paper = selected_paper
        
        summary = f"**Title:** {paper.title}\n"
        summary += f"**Authors:** {', '.join(a.name for a in paper.authors)}\n"
        summary += f"**Published:** {paper.published.strftime('%Y-%m-%d')}\n"
        summary += f"**Arxiv ID:** {paper.entry_id.split('/')[-1]}\n"
        summary += f"**URL:** {paper.entry_id}\n\n"
        summary += f"**Abstract:**\n{paper.summary}\n"
        
        return summary
        
    except Exception as e:
        return f"Error searching Arxiv: {e}"
