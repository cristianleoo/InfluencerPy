# HTTP Request Tool

The HTTP Request tool allows all agents to fetch and parse web content using Beautiful Soup. This tool is perfect for reading articles, blog posts, documentation, and any web content to create social media posts.

## Features

- **Fetch any web page**: Read the full content from any URL
- **CSS selectors**: Target specific elements using CSS selectors
- **Link extraction**: Optionally extract all links from a page
- **Clean text extraction**: Automatically removes scripts, styles, and excess whitespace
- **Smart truncation**: Limits content to prevent overwhelming the AI model

## Usage

### Basic URL Fetch

Fetch and read the entire content of a web page:

```python
from influencerpy.tools.http_tool import http_request

result = http_request(url="https://example.com/article")
print(result["content"])  # Full page text
print(result["title"])    # Page title
```

### Using CSS Selectors

Extract specific content using CSS selectors:

```python
# Extract just the article content
result = http_request(
    url="https://example.com/blog/post", 
    selector="article"
)

# Extract specific class
result = http_request(
    url="https://example.com/page", 
    selector=".main-content"
)

# Extract by ID
result = http_request(
    url="https://example.com/docs", 
    selector="#documentation"
)
```

### Extracting Links

Get all links from a page:

```python
result = http_request(
    url="https://example.com", 
    extract_links=True
)

for link in result["links"]:
    print(f"{link['text']}: {link['url']}")
```

## Integration with Scouts

The HTTP Request tool is available to all agents through the tools configuration. To enable it for a scout:

### When Creating a Scout

```python
from influencerpy.core.scouts import ScoutManager

manager = ScoutManager()

scout = manager.create_scout(
    name="Tech Blog Monitor",
    type="meta",
    config={
        "tools": ["http_request"],  # Enable the tool
        "orchestration_prompt": "Monitor tech blogs and find interesting articles"
    },
    platforms=["x"]
)
```

### Example: Blog Post Scout

Create a scout that monitors specific blog posts:

```python
scout = manager.create_scout(
    name="ML Blog Watcher",
    type="meta",
    config={
        "tools": ["http_request"],
        "orchestration_prompt": """
            Read the latest posts from machine learning blogs.
            Use http_request to fetch article content and summarize key insights.
        """
    },
    prompt_template="Summarize technical articles with key takeaways and practical applications.",
    platforms=["x", "linkedin"]
)
```

### Example: Link Aggregator Scout

Create a scout that finds and analyzes links:

```python
scout = manager.create_scout(
    name="Resource Curator",
    type="meta",
    config={
        "tools": ["http_request"],
        "orchestration_prompt": """
            Find useful resources from curated lists.
            Use http_request with extract_links=True to find related content.
        """
    }
)
```

## Return Format

The tool returns a dictionary with the following structure:

```python
{
    "url": str,        # The requested URL
    "title": str,      # Page title (if available)
    "content": str,    # Extracted text content
    "links": [         # List of links (if extract_links=True)
        {
            "text": str,  # Link text
            "url": str    # Link URL (absolute)
        }
    ],
    "error": str       # Error message (if failed)
}
```

## Error Handling

The tool gracefully handles errors and returns them in the response:

```python
result = http_request(url="https://invalid-url.example")
if "error" in result:
    print(f"Failed: {result['error']}")
```

Common errors:
- Request timeout (10 seconds)
- Network connection issues
- Invalid URLs
- Parsing errors

## Best Practices

1. **Use CSS selectors** when you know the page structure to get cleaner content
2. **Check for errors** in the response before processing content
3. **Combine with other tools** like `google_search` to find URLs first
4. **Respect rate limits** - don't hammer the same domain repeatedly
5. **Content length** - The tool automatically truncates content over 10,000 characters

## Example Workflow

A typical workflow combining multiple tools:

1. Use `google_search` to find interesting articles
2. Use `http_request` to read the full content
3. Use the LLM to generate a social media post based on the content

```python
# This is what the agent does internally:
# 1. Search for content
search_results = google_search("machine learning breakthroughs 2026")

# 2. Extract URL from results
url = extract_first_url(search_results)

# 3. Fetch full content
article = http_request(url=url, selector="article")

# 4. Generate post (done by the agent automatically)
```

## Limitations

- **Timeout**: Requests timeout after 10 seconds
- **Content length**: Truncated at 10,000 characters
- **Link limit**: Maximum 50 links when extract_links=True
- **JavaScript**: Cannot execute JavaScript (use browser tool for that)
- **Authentication**: Cannot handle login/authenticated pages

## Comparison with Browser Tool

| Feature | http_request | browser |
|---------|-------------|---------|
| Speed | Fast | Slower |
| JavaScript | No | Yes |
| CSS Selectors | Yes | Yes |
| Multiple steps | No | Yes |
| Stability | Stable | Experimental |

Use `http_request` for simple content fetching and the `browser` tool for complex interactions requiring JavaScript.
