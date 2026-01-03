# HTTP Request Tool - Technical Overview

## Architecture

The HTTP Request tool integrates seamlessly with InfluencerPy's agent system:

```
┌─────────────────────────────────────────────────────────────┐
│                         User/CLI                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scout Manager                            │
│  - Orchestrates scout execution                             │
│  - Manages tool configuration                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      AI Agent                               │
│  - Powered by Gemini/Anthropic                              │
│  - Equipped with selected tools                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Google    │ │   HTTP      │ │   Reddit    │ │   ArXiv     │
│   Search    │ │   Request   │ │    Tool     │ │    Tool     │
└─────────────┘ └──────┬──────┘ └─────────────┘ └─────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │   Beautiful Soup     │
            │   - HTML Parsing     │
            │   - CSS Selectors    │
            │   - Text Extraction  │
            └──────────────────────┘
```

## Data Flow

### 1. Tool Invocation
```python
# Agent calls the tool
result = http_request(
    url="https://example.com/article",
    selector="article"
)
```

### 2. Request Processing
```
Request → Headers → HTTP GET → Response → Parse HTML → Extract Text → Clean → Return
```

### 3. Response Handling
```python
# Agent receives structured data
{
    "url": "https://example.com/article",
    "title": "Article Title",
    "content": "Clean extracted text...",
    "links": [...]  # If requested
}
```

## Integration Points

### 1. Tool Registration
Located in: `src/influencerpy/core/scouts.py`

```python
# Import the tool
from influencerpy.tools.http_tool import http_request

# Add to agent tools list
if "http_request" in tools_config:
    agent_tools.append(http_request)
```

### 2. Prompt Configuration
Located in: `src/influencerpy/types/prompts.py`

```python
TOOL_INSTRUCTIONS = {
    "http_request": """TOOL: http_request
Use this to fetch and read content from any web URL.
..."""
}
```

### 3. Scout Configuration
User-facing configuration:

```python
config = {
    "tools": ["http_request"],  # Enable the tool
    "orchestration_prompt": "..."
}
```

## Technical Implementation

### Core Function Signature
```python
@tool
def http_request(
    url: str, 
    selector: str = None, 
    extract_links: bool = False
) -> Dict[str, str]:
    """Fetch and parse web content."""
```

### Key Features

#### 1. User Agent Spoofing
```python
headers = {
    'User-Agent': 'Mozilla/5.0 ...'
}
```
Prevents blocking by websites that reject bot requests.

#### 2. Timeout Protection
```python
response = requests.get(url, timeout=10)
```
Prevents hanging on slow/unresponsive servers.

#### 3. Content Cleaning
```python
# Remove scripts and styles
for script in soup(["script", "style"]):
    script.decompose()

# Extract clean text
content = soup.get_text(separator=' ', strip=True)
```

#### 4. Content Truncation
```python
max_length = 10000
if len(content) > max_length:
    content = content[:max_length] + "..."
```
Prevents overwhelming the AI model with too much text.

#### 5. CSS Selector Support
```python
if selector:
    elements = soup.select(selector)
    content = "\n\n".join(elem.get_text() for elem in elements)
```

#### 6. Link Extraction
```python
if extract_links:
    for link in soup.find_all('a', href=True):
        href = urljoin(url, link['href'])  # Make absolute
        links.append({"text": link_text, "url": href})
```

### Error Handling Strategy

```python
try:
    # Request logic
except requests.exceptions.Timeout:
    return {"url": url, "error": "Timeout"}
except requests.exceptions.RequestException as e:
    return {"url": url, "error": str(e)}
except Exception as e:
    return {"url": url, "error": f"Parsing error: {e}"}
```

## Performance Characteristics

### Typical Response Times
- **Simple page**: 0.5-2 seconds
- **Complex page**: 2-5 seconds
- **Timeout**: 10 seconds (then error)

### Resource Usage
- **Memory**: ~10-50 MB per request
- **CPU**: Low (parsing is fast)
- **Network**: Depends on page size

### Limitations
| Aspect | Limit | Reason |
|--------|-------|--------|
| Content length | 10,000 chars | Prevent model overload |
| Links | 50 links | Prevent excessive data |
| Timeout | 10 seconds | Prevent hanging |
| JavaScript | Not supported | Use browser tool instead |

## Testing Strategy

### Unit Tests
```python
# Mock HTTP responses
with patch("requests.get", return_value=mock_response):
    result = http_request(url="...")
    assert result["content"] == expected
```

### Integration Tests
```python
# Verify Strands compatibility
assert hasattr(http_request, 'tool_spec')
assert http_request.tool_spec['name'] == 'http_request'
```

### Manual Testing
```bash
# Run the demo
python examples/http_tool_demo.py
```

## Security Considerations

### 1. URL Validation
The tool trusts the AI agent to provide valid URLs. In production:
- Consider URL whitelist/blacklist
- Validate URL schemes (http/https only)
- Block internal IPs/localhost

### 2. Content Safety
- The tool extracts text only (no script execution)
- XSS is not a concern (no rendering)
- Content is sanitized by text extraction

### 3. Rate Limiting
Consider adding:
- Per-domain rate limits
- Request caching
- Backoff on errors

## Future Enhancements

### Phase 1: Stability
- [x] Basic implementation
- [x] Error handling
- [x] Unit tests
- [ ] Rate limiting per domain
- [ ] Request caching

### Phase 2: Features
- [ ] Custom headers support
- [ ] Cookie/session handling
- [ ] Retry logic with backoff
- [ ] Robots.txt checking

### Phase 3: Advanced
- [ ] JavaScript rendering (Playwright)
- [ ] Screenshot capture
- [ ] PDF extraction
- [ ] Form submission

## Comparison with Browser Tool

### When to Use HTTP Request
✅ Static content only  
✅ Speed is important  
✅ Simple extraction  
✅ Reliable execution needed  

### When to Use Browser Tool
✅ JavaScript required  
✅ Complex interactions  
✅ Form submissions  
✅ Screenshot needed  

## Dependencies

### Required Packages
```toml
[project]
dependencies = [
    "beautifulsoup4",  # HTML parsing
    "requests",        # HTTP client
    "strands-agents",  # Tool decoration
]
```

All dependencies are already in the project - no new installations needed!

## Code Quality

### Type Hints
```python
def http_request(url: str, selector: str = None, extract_links: bool = False) -> Dict[str, str]:
```

### Documentation
- ✅ Comprehensive docstrings
- ✅ Inline comments
- ✅ Usage examples
- ✅ User guide

### Testing
- ✅ Unit tests with mocking
- ✅ Integration tests
- ✅ Demo script
- ✅ Error case coverage

## Summary

The HTTP Request tool is:
- **Fast**: No browser overhead
- **Reliable**: Comprehensive error handling
- **Flexible**: CSS selectors for precise extraction
- **Well-tested**: Unit and integration tests
- **Well-documented**: Multiple documentation files
- **Easy to use**: Simple API, clear examples

Perfect for most web scraping needs in InfluencerPy! 🎯
