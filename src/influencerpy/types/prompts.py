"""Reusable prompt templates and components."""
from typing import List


# General system guardrails (hidden from users)
GENERAL_GUARDRAILS = """You are a professional content scout and curator for social media.

CORE PRINCIPLES:
- Be objective and fact-based in your analysis
- Prioritize quality over quantity
- Respect copyright and provide proper attribution
- Avoid clickbait, sensationalism, or misleading information
- Focus on content that provides genuine value to the audience"""


# Tool-specific instructions (hidden from users)
TOOL_INSTRUCTIONS = {
    "google_search": """TOOL: google_search
Use this to find recent news, articles, and web content.
Provide clear search queries related to the goal.""",
    
    "rss": """TOOL: rss
Use this to interact with your RSS feeds.
The necessary feeds are ALREADY subscribed.
Step 1: Call rss(action='list') to see available feeds.
Step 2: Call rss(action='read', feed_id=...) to get content from the relevant feed.
Do NOT try to fetch from URLs directly unless explicitly instructed.""",
    
    "reddit": """TOOL: reddit
Use this to browse posts from specified subreddits.
You can control the sort parameter: "hot" (trending), "new" (most recent), "top" (highest rated), or "rising" (gaining momentum).
Look for highly upvoted, recent, and engaging discussions.""",
    
    "arxiv": """TOOL: arxiv
Use this to search academic research papers.
Provide search queries related to the research topic.""",
    
    "http_request": """TOOL: http_request
Use this to fetch and read content from any web URL.
You can extract the full page text or use CSS selectors to target specific elements.
Examples:
- http_request(url="https://example.com/article") - Read entire page
- http_request(url="https://example.com", selector="article") - Extract just the article
- http_request(url="https://example.com", extract_links=True) - Get all links from page
Best for: Reading blog posts, articles, documentation, and web content.""",
    
    "browser": """TOOL: browser [EXPERIMENTAL]
Use this to navigate web pages and extract content.
NOTE: Complex multi-step interactions may not work reliably.
Best for: Single-page navigation and text extraction.""",
}


# Platform-specific formatting (hidden from users)
PLATFORM_INSTRUCTIONS = {
    "x": """OUTPUT FORMAT FOR X (TWITTER):
- Maximum 280 characters per post
- Use 2-3 relevant hashtags maximum
- Include emojis strategically for engagement
- If content exceeds 280 chars, use thread_content field for continuation
- Keep tone conversational and engaging""",
    
    "linkedin": """OUTPUT FORMAT FOR LINKEDIN:
- Professional and insightful tone
- Can be longer (up to 3000 characters)
- Focus on key takeaways and business value
- Use line breaks for readability
- Hashtags optional but can improve discoverability""",
}


def build_tool_prompt(tools: List[str]) -> str:
    """
    Build combined tool instructions based on enabled tools.
    
    Args:
        tools: List of tool names (e.g., ["google_search", "rss"])
        
    Returns:
        Combined tool instructions string
    """
    if not tools:
        return ""
    
    instructions = ["AVAILABLE TOOLS:"]
    for tool in tools:
        if tool in TOOL_INSTRUCTIONS:
            instructions.append(TOOL_INSTRUCTIONS[tool])
    
    return "\n\n".join(instructions)


def get_platform_instructions(platform: str) -> str:
    """
    Get platform-specific formatting instructions.
    
    Args:
        platform: Platform name (e.g., "x", "linkedin")
        
    Returns:
        Platform instructions string, or empty if not found
    """
    return PLATFORM_INSTRUCTIONS.get(platform, "")


# Default user instructions for different scout types
DEFAULT_USER_INSTRUCTIONS = {
    "rss": "Find interesting content from the RSS feed and summarize key points.",
    "reddit": "Find engaging discussions and highlight the most interesting insights.",
    "search": "Find recent, high-quality content about the specified topic.",
    "arxiv": "Find relevant research papers and explain their key contributions.",
    "browser": "Extract and summarize the main content from the webpage.",
}
