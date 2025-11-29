# System Prompts Architecture

## Overview

InfluencerPy uses a **structured system prompt architecture** that separates concerns into four distinct components. This ensures users can customize their scout's behavior without accidentally breaking system guardrails or platform formatting rules.

## Prompt Components

### 1. General Instructions (Hidden)

**Purpose**: Core system guardrails and professional behavioral guidelines.

**Content**:
- Be objective and fact-based
- Prioritize quality over quantity
- Respect copyright and attribution
- Avoid clickbait or sensationalism

**Visibility**: Hidden from users, automatically included in all scouts.

### 2. Tool Instructions (Hidden)

**Purpose**: Auto-generated guidance for using enabled tools.

**Content**: Varies based on scout type and tools:
- **google_search**: How to formulate search queries
- **rss**: How to parse feed items
- **reddit**: How to browse subreddit discussions
- **arxiv**: How to search academic papers
- **browser** [EXPERIMENTAL]: How to navigate and extract content

**Visibility**: Hidden from users, automatically generated based on configured tools.

### 3. Platform Instructions (Hidden)

**Purpose**: Platform-specific formatting and constraints.

**Supported Platforms**:

**X (Twitter)**:
- Maximum 280 characters per post
- 2-3 hashtags maximum
- Emojis for engagement
- Threading for longer content

**LinkedIn**:
- Professional tone
- Up to 3000 characters
- Focus on insights and takeaways
- Strategic use of line breaks

**Visibility**: Hidden from users, automatically applied based on target platform.

### 4. User Instructions (Visible & Editable)

**Purpose**: Your custom scout goal.

**Examples**:
- "Find breaking AI safety research"
- "Summarize this content for a technical audience"
- "Find controversial blockchain discussions"

**Visibility**: **This is the ONLY component users see and edit in the UI.**

**Label in UI**: "User Instructions (Your Scout Goal)"

## How It Works

### Prompt Construction

When a scout runs, the system builds the final prompt using the `SystemPrompt` dataclass:

```python
from influencerpy.core.prompts import SystemPrompt
from influencerpy.core.prompt_templates import (
    GENERAL_GUARDRAILS,
    build_tool_prompt,
    get_platform_instructions
)

system_prompt = SystemPrompt(
    general_instructions=GENERAL_GUARDRAILS,
    tool_instructions=build_tool_prompt(["rss", "google_search"]),
    platform_instructions=get_platform_instructions("x"),
    user_instructions="Find trending AI news"
)

final_prompt = system_prompt.build(
    date="2025-11-28",
    limit=10
)
```

### Example Output

The final prompt sent to the AI looks like:

```
You are a professional content scout and curator for social media.

CORE PRINCIPLES:
- Be objective and fact-based in your analysis
- Prioritize quality over quantity
- Respect copyright and provide proper attribution
- Avoid clickbait or sensationalism

AVAILABLE TOOLS:

TOOL: rss
Use this to fetch feed items from the configured RSS source.

TOOL: google_search
Use this to find recent news, articles, and web content.

YOUR GOAL: Find trending AI news

OUTPUT FORMAT FOR X (TWITTER):
- Maximum 280 characters per post
- Use 2-3 relevant hashtags maximum
- Include emojis strategically for engagement

CONTEXT:
date: 2025-11-28
limit: 10
```

## Benefits

### For Users

✅ **Simple UX**: Only edit your custom goal, not system internals  
✅ **Protected**: Can't accidentally break guardrails or formatting  
✅ **Platform-Aware**: Posts automatically formatted correctly  
✅ **Tool-Aware**: Instructions auto-update when tools change

### For Developers

✅ **Maintainable**: All prompt logic centralized  
✅ **Testable**: Each component independently verifiable  
✅ **Extensible**: Easy to add new platforms or tools  
✅ **Type-Safe**: Dataclass ensures valid composition

## Customization

### Editing User Instructions

1. In the CLI, select **Update Scout**
2. Choose **User Instructions**
3. Enter your custom goal

Your instruction will be combined with system guardrails, tool guidance, and platform formatting automatically.

### Adding New Platforms

To add a new platform (e.g., Instagram):

1. Edit `src/influencerpy/core/prompt_templates.py`
2. Add to `PLATFORM_INSTRUCTIONS` dictionary:
   ```python
   "instagram": """OUTPUT FORMAT FOR INSTAGRAM:
   - Visually-driven content
   - Up to 2200 characters
   - Use emojis liberally
   - Hashtags at the end (up to 30)"""
   ```

3. No other code changes needed!

## Migration

Existing scouts are **fully backward compatible**. The `prompt_template` field is now interpreted as "User Instructions" and combined with system components automatically.
