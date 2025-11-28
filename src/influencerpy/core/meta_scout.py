from strands import tool
from typing import Any, Callable
import json

def create_scout_tool(scout_model: Any, scout_manager: Any) -> Callable:
    """
    Creates a Strands tool from a ScoutModel.
    
    The returned tool function will execute the scout when called by an agent.
    """
    
    config = json.loads(scout_model.config_json)
    scout_name = scout_model.name
    scout_type = scout_model.type
    
    # Build a description of what this scout does
    description = f"Runs the '{scout_name}' scout."
    
    if scout_type == "search":
        query = config.get("query", "unknown topic")
        description += f" Useful for finding information about: {query}."
    elif scout_type == "rss":
        feeds = config.get("feeds", [])
        description += f" Useful for fetching latest news from {len(feeds)} configured RSS feeds."
    elif scout_type == "reddit":
        subs = config.get("subreddits", [])
        description += f" Useful for finding discussions from subreddits: {', '.join(subs)}."
    elif scout_type == "arxiv":
        query = config.get("query", "research")
        description += f" Useful for finding research papers about: {query}."
    elif scout_type == "http_request":
        url = config.get("url", "")
        description += f" Useful for analyzing content from: {url}."
        
    # Define the tool function based on type to expose relevant arguments
    if scout_type == "http_request":
        def dynamic_scout_tool(query: str = None, url: str = None) -> str:
            """
            Executes the scout.
            """
            try:
                override_config = {}
                if url:
                    override_config["url"] = url
                
                # Run the scout with the provided query override if any
                items = scout_manager.run_scout(scout_model, limit=5, override_query=query, override_config=override_config)
                
                if not items:
                    return f"Scout '{scout_name}' found no items."
                    
                # Format items as string
                result = f"Results from {scout_name}:\n\n"
                for item in items:
                    result += f"- Title: {item.title}\n"
                    result += f"  URL: {item.url}\n"
                    result += f"  Summary: {item.summary}\n"
                    result += "---\n"
                    
                return result
            except Exception as e:
                return f"Error running scout '{scout_name}': {str(e)}"
                
        dynamic_scout_tool.__doc__ = f"""
        {description}
        
        Args:
            query: Optional. Specific query or instruction for this scout.
            url: Optional. Override the target URL for this request.
            
        Returns:
            A string containing summaries of the content found by the scout.
        """

    elif scout_type == "arxiv":
        def dynamic_scout_tool(query: str = None, date_filter: str = None) -> str:
            """
            Executes the scout.
            """
            try:
                override_config = {}
                if date_filter:
                    override_config["date_filter"] = date_filter
                
                # Run the scout with the provided query override if any
                items = scout_manager.run_scout(scout_model, limit=5, override_query=query, override_config=override_config)
                
                if not items:
                    return f"Scout '{scout_name}' found no items."
                    
                # Format items as string
                result = f"Results from {scout_name}:\n\n"
                for item in items:
                    result += f"- Title: {item.title}\n"
                    result += f"  URL: {item.url}\n"
                    result += f"  Summary: {item.summary}\n"
                    result += "---\n"
                    
                return result
            except Exception as e:
                return f"Error running scout '{scout_name}': {str(e)}"

        dynamic_scout_tool.__doc__ = f"""
        {description}
        
        Args:
            query: Optional. Specific query or instruction for this scout.
            date_filter: Optional. Filter papers by date. Options: 'today', 'week', 'month', 'none'.
            
        Returns:
            A string containing summaries of the content found by the scout.
        """

    else:
        # Default generic tool signature
        def dynamic_scout_tool(query: str = None) -> str:
            """
            Executes the scout.
            """
            try:
                # Run the scout with the provided query override if any
                items = scout_manager.run_scout(scout_model, limit=5, override_query=query)
                
                if not items:
                    return f"Scout '{scout_name}' found no items."
                    
                # Format items as string
                result = f"Results from {scout_name}:\n\n"
                for item in items:
                    result += f"- Title: {item.title}\n"
                    result += f"  URL: {item.url}\n"
                    result += f"  Summary: {item.summary}\n"
                    result += "---\n"
                    
                return result
            except Exception as e:
                return f"Error running scout '{scout_name}': {str(e)}"

        dynamic_scout_tool.__doc__ = f"""
        {description}
        
        Args:
            query: Optional. Specific query or instruction for this scout. If provided, it overrides the scout's default query.
            
        Returns:
            A string containing summaries of the content found by the scout.
        """
    
    # Set metadata for the tool
    # We sanitize the name to be a valid python identifier
    safe_name = "".join(c if c.isalnum() else "_" for c in scout_name).lower()
    dynamic_scout_tool.__name__ = f"scout_{safe_name}"
    
    # Apply the Strands tool decorator
    return tool(dynamic_scout_tool)
