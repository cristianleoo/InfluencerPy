# Browser Tool (Experimental)

⚠️ **Status**: The Browser tool integration is currently **EXPERIMENTAL**. 

## Overview

The Browser tool uses Playwright-based browser automation via `strands_tools` to enable scouts to navigate web pages and extract content dynamically. This is more powerful than simple HTTP requests for JavaScript-heavy sites.

## Current Limitations

### 🔴 Multi-Step Workflows Not Reliable

The AI agent currently struggles with **complex, multi-step browser interactions**:

- ❌ **Click Actions**: The agent often doesn't click on links even when instructed
- ❌ **Form Filling**: Multi-field forms are not reliably completed
- ❌ **Navigation Sequences**: "Navigate → Find Element → Click → Read Content" workflows often fail
- ❌ **JavaScript Evaluation**: The agent rarely uses the `evaluate` action even when prompted

**Why?**: The underlying model (gemini-2.5-flash by default) tends to take the shortest path and only uses basic actions like `navigate` and `get_text`.

### ✅ What Works

- ✅ **Single Page Navigation**: Navigate to a URL and read its content
- ✅ **Text Extraction**: Extract visible text from a page
- ✅ **Simple Content Scraping**: Get HTML from static pages
- ✅ **Basic Screenshots**: Capture page screenshots

## Recommended Use Cases

### ✅ Good Use Cases
- Extracting content from a known, stable URL
- Reading blog posts or article pages
- Monitoring specific web pages for text changes
- Simple content aggregation from listings

### ❌ Not Recommended (Yet)
- Complex multi-page workflows
- Dynamic content requiring clicking through UI
- Sites requiring form interactions
- Workflows needing JavaScript inspection

## Example: What Works

```python
# ✅ This works well
scout = {
    "name": "TechCrunchDaily",
    "type": "web",
    "url": "https://techcrunch.com",
    "tools": ["browser"],
    "goal": "Extract the titles and summaries of the top 3 articles"
}
```

## Example: What Doesn't Work Reliably

```python
# ❌ This often fails
scout = {
    "name": "HuggingFaceTop",
    "type": "web",
    "url": "https://huggingface.co/papers",
    "tools": ["browser"],
    "goal": "Find paper with most upvotes, click it, and read the abstract"
}
# Problem: Agent won't click on the paper link
```

## Workarounds

If you need complex browser automation:

1. **Use Direct URLs**: If you know the exact URL of the content, navigate directly to it
2. **Pre-scraping**: Use a separate script to find links, then feed URLs to scouts
3. **Simplify Goals**: Break complex workflows into multiple simpler scouts
4. **Alternative Tools**: Use RSS, Reddit, or Arxiv scouts when applicable

## Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Agent ignores `click` instructions | Open | Navigate directly to target URL |
| Agent ignores `evaluate` for JS inspection | Open | Use simpler selectors |
| Agent doesn't follow multi-step prompts | Open | Use single-action goals |

## Future Improvements

We're actively working on:
- [ ] Better prompt engineering for multi-step workflows
- [ ] Testing with more capable models (GPT-4, Claude)
- [ ] Custom high-level browser actions (e.g., `click_most_upvoted_paper()`)
- [ ] Example-based few-shot prompting

## Reporting Issues

If you encounter issues with the Browser tool:

1. Check the scout logs: `.influencerpy/logs/scouts/[ScoutName]/`
2. Look for which browser actions were actually called
3. Note if `evaluate` or `click` actions are missing
4. Report to: [GitHub Issues](https://github.com/cristianleoo/influencerpy/issues)

## Contributing

Help us improve the Browser tool! We especially need:
- Test cases for working multi-step workflows
- Prompt templates that successfully trigger clicking
- Model comparisons (which models follow instructions better?)
