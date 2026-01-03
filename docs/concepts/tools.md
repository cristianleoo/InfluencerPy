# Available Tools

InfluencerPy agents have access to several powerful tools for content discovery and analysis. Each tool serves a specific purpose and can be combined to create sophisticated content workflows.

## Core Tools

### 1. HTTP Request Tool 🌐

**Purpose:** Fetch and parse content from any web URL using Beautiful Soup.

**Best for:**
- Reading blog posts and articles
- Extracting specific content using CSS selectors
- Monitoring webpage content
- Getting links from pages

**Usage:**
```python
http_request(
    url="https://example.com/article",
    selector="article",  # Optional: CSS selector
    extract_links=True   # Optional: Extract all links
)
```

**Features:**
- Clean text extraction (removes scripts, styles)
- CSS selector support for targeting specific elements
- Link extraction with absolute URLs
- Automatic content truncation (10,000 char limit)
- 10-second timeout for reliability
- Graceful error handling

**Example Configuration:**
```python
scout = manager.create_scout(
    name="Blog Monitor",
    type="meta",
    config={
        "tools": ["http_request"],
        "orchestration_prompt": "Monitor tech blogs for interesting articles"
    }
)
```

**See:** [HTTP Request Tool Documentation](../tools/http-request.md)

---

### 2. Google Search Tool 🔍

**Purpose:** Perform real-time web searches using Gemini Grounding.

**Best for:**
- Finding recent news and updates
- Discovering trending topics
- General web research

**Usage:**
```python
google_search(query="machine learning breakthroughs 2026")
```

**Features:**
- Real-time search results
- Automatic source attribution
- Grounded responses with citations
- Detailed summaries (3-4 paragraphs)

**Example Configuration:**
```python
scout = manager.create_scout(
    name="News Scout",
    type="search",
    config={
        "tools": ["google_search"],
        "query": "AI regulation news"
    }
)
```

---

### 3. RSS Tool 📡

**Purpose:** Subscribe to and manage RSS/Atom feeds.

**Best for:**
- Monitoring specific blogs and news sites
- Following trusted content sources
- Tracking updates from known publishers

**Usage:**
```python
# List feeds
rss(action="list")

# Read feed
rss(action="read", feed_id="feed_123")

# Add feed
rss(action="add", url="https://blog.example.com/feed")
```

**Features:**
- Database-backed feed storage
- Automatic feed validation
- Duplicate detection
- Per-scout feed isolation

**Example Configuration:**
```python
scout = manager.create_scout(
    name="Tech Blog Scout",
    type="rss",
    config={
        "tools": ["rss"],
        "feeds": ["https://techcrunch.com/feed/"]
    }
)
```

---

### 4. Reddit Tool 👾

**Purpose:** Fetch posts from subreddits.

**Best for:**
- Community sentiment analysis
- Finding trending discussions
- Tapping into niche communities

**Usage:**
```python
reddit(
    subreddit="MachineLearning",
    limit=10,
    sort="hot"  # or "new", "top", "rising"
)
```

**Features:**
- Multiple sorting options (hot, new, top, rising)
- Configurable post limits
- Upvote and comment counts
- Rate limit compliance

**Example Configuration:**
```python
scout = manager.create_scout(
    name="AI Reddit Scout",
    type="reddit",
    config={
        "tools": ["reddit"],
        "subreddits": ["MachineLearning", "LocalLLaMA"],
        "reddit_sort": "hot"
    }
)
```

---

### 5. ArXiv Tool 🎓

**Purpose:** Search for academic papers and research.

**Best for:**
- Finding research papers
- Tracking scientific breakthroughs
- Academic content curation

**Usage:**
```python
arxiv_search(
    query="transformer models",
    days_back=7  # Optional: filter by recency
)
```

**Features:**
- Search by keywords or ArXiv ID
- Date filtering (days_back parameter)
- Full paper metadata (title, authors, abstract)
- Direct ArXiv links

**Example Configuration:**
```python
scout = manager.create_scout(
    name="AI Papers",
    type="meta",
    config={
        "tools": ["arxiv"],
        "query": "large language models",
        "date_filter": "week"
    }
)
```

---

### 6. Browser Tool (Experimental) 🌐

**Purpose:** Navigate web pages with JavaScript support.

**Best for:**
- Complex web interactions
- JavaScript-heavy sites
- Multi-step navigation

**Usage:**
```python
browser(
    url="https://example.com",
    action="navigate"
)
```

**Features:**
- Full browser automation
- JavaScript execution
- Multi-step interactions
- Screenshot capabilities

**Limitations:**
- Slower than http_request
- More resource-intensive
- Experimental stability

**Example Configuration:**
```python
scout = manager.create_scout(
    name="Complex Site Monitor",
    type="meta",
    config={
        "tools": ["browser"],
        "orchestration_prompt": "Navigate to site and extract data"
    }
)
```

---

## Tool Comparison

### HTTP Request vs Browser

| Feature | http_request | browser |
|---------|--------------|---------|
| Speed | ⚡ Fast | 🐌 Slower |
| JavaScript | ❌ No | ✅ Yes |
| CSS Selectors | ✅ Yes | ✅ Yes |
| Stability | ✅ Stable | ⚠️ Experimental |
| Resource Use | ⬇️ Low | ⬆️ High |
| Best For | Static content | Dynamic sites |

**Recommendation:** Use `http_request` for most web scraping tasks. Only use `browser` when you specifically need JavaScript execution.

---

## Combining Tools

The power of InfluencerPy comes from combining multiple tools in a Meta-Scout:

### Example: Complete Research Workflow

```python
scout = manager.create_scout(
    name="Complete Research Agent",
    type="meta",
    config={
        "tools": ["google_search", "http_request", "arxiv"],
        "orchestration_prompt": """
            1. Use google_search to find trending AI topics
            2. Use http_request to read full articles
            3. Use arxiv to find related research papers
            4. Synthesize findings into a comprehensive post
        """
    }
)
```

### Example: News + Community Sentiment

```python
scout = manager.create_scout(
    name="News with Sentiment",
    type="meta",
    config={
        "tools": ["rss", "reddit", "http_request"],
        "orchestration_prompt": """
            1. Check RSS feeds for latest tech news
            2. Use http_request to read full articles
            3. Check Reddit for community reactions
            4. Create a post combining news and sentiment
        """
    }
)
```

---

## Adding Tools to Scouts

When creating a scout, specify tools in the `tools` array:

```python
from influencerpy.core.scouts import ScoutManager

manager = ScoutManager()

scout = manager.create_scout(
    name="My Scout",
    type="meta",
    config={
        "tools": [
            "http_request",    # Web scraping
            "google_search",   # Search
            "arxiv",          # Research papers
            "reddit"          # Community discussions
        ],
        "orchestration_prompt": "Your orchestration instructions here"
    }
)
```

---

## Best Practices

1. **Start Simple:** Begin with one tool and add more as needed
2. **Choose the Right Tool:** Use the comparison tables above
3. **Combine Strategically:** Think about the workflow (search → fetch → analyze)
4. **Handle Errors:** Tools return error information in responses
5. **Respect Rate Limits:** Don't hammer endpoints repeatedly
6. **Use Selectors:** When scraping, use CSS selectors for cleaner content

---

## Tool Return Formats

All tools return structured data that the AI can understand:

### http_request
```python
{
    "url": str,
    "title": str,
    "content": str,
    "links": [{"text": str, "url": str}],  # Optional
    "error": str  # If failed
}
```

### google_search
```python
str  # Formatted text with sources
```

### arxiv_search
```python
str  # Paper details formatted as text
```

### reddit
```python
str  # Posts formatted as text with metadata
```

---

## Next Steps

- **Try the Demo:** Run `python examples/http_tool_demo.py` to see the HTTP tool in action
- **Create a Scout:** Use the CLI to create a scout with your desired tools
- **Experiment:** Try different tool combinations to find what works best

For detailed API documentation of each tool, see the individual tool documentation files in the `docs/tools/` directory.
