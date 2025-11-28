import feedparser
from typing import List, Dict, Union, Any

def rss(action: str = "fetch", url: str = None, max_entries: int = 5) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Read an RSS feed.
    
    Args:
        action: The action to perform. Currently only "fetch" is supported.
        url: The URL of the RSS feed.
        max_entries: The maximum number of entries to return.
        
    Returns:
        A list of dictionaries containing feed entries, or an error dict.
    """
    if action != "fetch":
        return {"error": f"Unknown action: {action}"}
    
    if not url:
        return {"error": "URL is required"}
        
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo:
            # feedparser sets bozo to 1 if there's an error, but often still parses content.
            # We'll log it but proceed if entries exist.
            pass
            
        entries = []
        for entry in feed.entries[:max_entries]:
            item = {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "published": entry.get("published", entry.get("updated", "")),
                "summary": entry.get("summary", entry.get("description", "")),
                "id": entry.get("id", "")
            }
            entries.append(item)
            
        return entries
        
    except Exception as e:
        return {"error": str(e)}

# Tool metadata for Strands/Agent
rss.tool_name = "rss"
rss.tool_description = "Read an RSS feed to find latest articles."
rss.args_schema = {
    "action": {"type": "string", "description": "Action to perform (must be 'fetch')"},
    "url": {"type": "string", "description": "The URL of the RSS feed"},
    "max_entries": {"type": "integer", "description": "Maximum number of entries to return (default 5)"}
}
