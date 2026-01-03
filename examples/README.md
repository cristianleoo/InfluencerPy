# InfluencerPy Examples

This directory contains example scripts and demonstrations for InfluencerPy features.

## Available Examples

### HTTP Tool Demo (`http_tool_demo.py`)

Demonstrates the HTTP Request tool for web scraping and content extraction.

**Run it:**
```bash
cd /home/cristian/workplace/InfluencerPy
python examples/http_tool_demo.py
```

or

```bash
uv run examples/http_tool_demo.py
```

**What it does:**
- Fetches and parses web pages
- Demonstrates CSS selector usage
- Shows link extraction
- Handles errors gracefully

**Features demonstrated:**
1. **Basic URL Fetch**: Retrieve full page content
2. **CSS Selectors**: Target specific page elements
3. **Link Extraction**: Get all links from a page
4. **Error Handling**: Graceful failure handling

## Creating Your Own Examples

Feel free to add more examples following this pattern:

1. Create a new Python file in this directory
2. Import the necessary InfluencerPy modules
3. Add clear comments and print statements
4. Make it executable with `chmod +x filename.py`
5. Add a shebang line: `#!/usr/bin/env python3`
6. Update this README with your example

## Running Examples

### Option 1: Direct Python
```bash
python examples/your_example.py
```

### Option 2: Using uv
```bash
uv run examples/your_example.py
```

### Option 3: Make it executable
```bash
chmod +x examples/your_example.py
./examples/your_example.py
```

## Example Ideas

Here are some ideas for additional examples:

- **Multi-tool Scout**: Demonstrate combining multiple tools (search + http + arxiv)
- **RSS Monitor**: Show how to set up an RSS-based scout
- **Reddit Sentiment**: Analyze Reddit posts for sentiment
- **Automated Workflow**: Complete end-to-end content creation workflow
- **Custom Tool**: Show how to create a custom tool
- **Scheduling**: Demonstrate scout scheduling configuration

Feel free to contribute!
