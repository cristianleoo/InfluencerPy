import requests
from bs4 import BeautifulSoup
from strands import tool
from typing import Dict
import logging

logger = logging.getLogger(__name__)

@tool
def http_request(url: str, selector: str = None, extract_links: bool = False) -> Dict[str, str]:
    """
    Fetch and parse content from a web URL using Beautiful Soup.
    
    Use this tool to:
    - Read articles, blog posts, and web pages
    - Extract specific content using CSS selectors
    - Get links from a page
    - Analyze web content for social media posts
    
    Args:
        url: The URL to fetch and parse.
        selector: Optional CSS selector to extract specific elements (e.g., "article", ".content", "#main").
                  If not provided, extracts all text from the page.
        extract_links: If True, also returns all links found on the page.
        
    Returns:
        A dictionary containing:
        - url: The requested URL
        - title: Page title if available
        - content: The extracted text content
        - links: List of links (if extract_links=True)
        - error: Error message if request failed
        
    Examples:
        - http_request(url="https://example.com/article")
        - http_request(url="https://example.com", selector="article")
        - http_request(url="https://example.com", extract_links=True)
    """
    try:
        # Set a realistic user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the page with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No title"
        
        # Extract content
        if selector:
            # Use CSS selector to find specific elements
            elements = soup.select(selector)
            if not elements:
                content = f"No elements found matching selector '{selector}'"
            else:
                # Get text from all matching elements
                content = "\n\n".join(elem.get_text(strip=True, separator=' ') for elem in elements)
        else:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            content = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        content = ' '.join(content.split())
        
        # Limit content length to avoid overwhelming the model
        max_length = 10000
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n[Content truncated - original length: {len(content)} characters]"
        
        result = {
            "url": url,
            "title": title,
            "content": content
        }
        
        # Extract links if requested
        if extract_links:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text(strip=True)
                # Make relative URLs absolute
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                if href.startswith('http'):
                    links.append({"text": link_text, "url": href})
            
            result["links"] = links[:50]  # Limit to first 50 links
        
        return result
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching URL: {url}")
        return {
            "url": url,
            "error": "Request timed out after 10 seconds"
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return {
            "url": url,
            "error": f"Failed to fetch URL: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error parsing URL {url}: {e}")
        return {
            "url": url,
            "error": f"Error parsing content: {str(e)}"
        }
