import requests
from strands import tool
from typing import List, Dict, Union
from datetime import datetime

@tool
def reddit(subreddit: str, limit: int = 20, sort: str = "hot") -> Union[List[Dict], Dict]:
    """
    Fetch latest posts from a subreddit.
    
    Args:
        subreddit: The name of the subreddit (e.g., "arcteryx", "ArtificialInteligence").
        limit: Number of posts to fetch (default: 10).
        sort: Sort method ("hot", "new", "top", "rising"). Default is "hot".
        
    Returns:
        A list of dictionaries containing post details (title, url, content, score, comments).
    """
    if limit < 20:
        limit = 20
    elif limit > 100:
        limit = 100
        
    # Ensure subreddit name is clean
    subreddit = subreddit.strip()
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]
    elif subreddit.startswith("/r/"):
        subreddit = subreddit[3:]
        
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    
    # Reddit API requires a custom User-Agent
    headers = {
        "User-Agent": "InfluencerPy/1.0"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            return {"error": f"Subreddit 'r/{subreddit}' not found."}
        
        if response.status_code == 429:
            return {"error": "Rate limit exceeded for Reddit API."}
            
        if response.status_code != 200:
            return {"error": f"Error fetching subreddit: HTTP {response.status_code}"}
            
        data = response.json()
        posts = []
        
        if "data" in data and "children" in data["data"]:
            for child in data["data"]["children"]:
                post_data = child.get("data", {})
                
                # Handle content (selftext or url)
                content = post_data.get("selftext", "")
                if not content:
                    content = post_data.get("url", "")
                
                posts.append({
                    "title": post_data.get("title", "No Title"),
                    "url": f"https://www.reddit.com{post_data.get('permalink')}",
                    "content": content,
                    "score": post_data.get("score", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "author": post_data.get("author", "unknown"),
                    "created_utc": datetime.utcfromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                    "source": f"r/{subreddit}"
                })
                
        return posts
        
    except Exception as e:
        return {"error": f"Failed to fetch reddit posts: {str(e)}"}

