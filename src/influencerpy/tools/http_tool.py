import requests
from bs4 import BeautifulSoup
from typing import Dict, Union

def http_request(url: str) -> Dict[str, str]:
    """
    Fetch the content of a URL.
    
    Args:
        url: The URL to fetch.
        
    Returns:
        A dictionary containing the text content of the page.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return {
            "url": url,
            "content": text[:10000] # Limit content length
        }
        
    except Exception as e:
        return {"error": str(e)}

# Tool metadata for Strands/Agent
http_request.tool_name = "http_request"
http_request.tool_description = "Fetch the text content of a webpage."
http_request.args_schema = {
    "url": {"type": "string", "description": "The URL to fetch"}
}
