"""Substack tool for fetching newsletter content."""

from typing import List, Dict, Any
from strands.tools.tools import PythonAgentTool


def substack_fetch(newsletter_url: str, limit: int = 10, sorting: str = "new") -> List[Dict[str, Any]]:
    """
    Fetch posts from a Substack newsletter.
    
    Parameters
    ----------
    newsletter_url : str
        URL of the Substack newsletter (e.g., 'https://newsletter.substack.com')
    limit : int
        Maximum number of posts to fetch (default: 10)
    sorting : str
        Sort order: 'new' (most recent) or 'top' (most popular)
    
    Returns
    -------
    List[Dict[str, Any]]
        List of posts with title, url, and summary
    """
    try:
        from influencerpy.platforms.substack import Newsletter
        
        newsletter = Newsletter(newsletter_url)
        posts = newsletter.get_posts(sorting=sorting, limit=limit)
        
        results = []
        for post in posts:
            try:
                metadata = post.get_metadata()
                results.append({
                    "title": metadata.get("title", "Untitled"),
                    "url": post.url,
                    "summary": metadata.get("description", ""),
                    "author": metadata.get("publishedBylines", [{}])[0].get("name", "Unknown"),
                    "published_at": metadata.get("post_date", ""),
                })
            except Exception as e:
                # Skip posts that fail to fetch
                continue
        
        return results
        
    except Exception as e:
        return [{"error": f"Failed to fetch from Substack: {str(e)}"}]


# Tool specification for Strands
SUBSTACK_TOOL_SPEC = {
    "name": "substack",
    "description": "Fetch posts from a Substack newsletter. Use this to discover content from specific newsletters.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "newsletter_url": {
                    "type": "string",
                    "description": "URL of the Substack newsletter (e.g., 'https://newsletter.substack.com' or 'newsletter.substack.com')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of posts to fetch (default: 10)",
                    "default": 10
                },
                "sorting": {
                    "type": "string",
                    "description": "Sort order: 'new' (most recent) or 'top' (most popular)",
                    "enum": ["new", "top"],
                    "default": "new"
                }
            },
            "required": ["newsletter_url"]
        }
    }
}

# Create the tool
substack_tool = PythonAgentTool(
    tool_name=SUBSTACK_TOOL_SPEC["name"],
    tool_spec=SUBSTACK_TOOL_SPEC,
    tool_func=substack_fetch
)
