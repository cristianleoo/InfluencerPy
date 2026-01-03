# Multi-Feed RSS Enhancement - Technical Summary

## Problem Statement

When multiple RSS feeds were added to a scout, the AI agent was not consistently exploring ALL feeds. It might pick just one feed to read from, resulting in incomplete coverage and missing content from other subscribed sources.

## Root Causes

1. **Vague instructions**: The tool prompt said "list available feeds and read them" but didn't emphasize reading from ALL feeds
2. **Manual iteration**: The agent had to call `list`, then call `read` for each feed individually (inefficient and error-prone)
3. **Unclear goal**: The scout goal didn't explicitly say to gather content from ALL sources

## Solution Implemented

### 1. Enhanced Tool Instructions (`src/influencerpy/types/prompts.py`)

**Before:**
```python
"rss": """TOOL: rss
Use this to interact with your RSS feeds.
Step 1: Call rss(action='list') to see available feeds.
Step 2: Call rss(action='read', feed_id=...) to get content from the relevant feed.
"""
```

**After:**
```python
"rss": """TOOL: rss
Use this to interact with your RSS feeds.

RECOMMENDED APPROACH (for multiple feeds):
- Call rss(action='read_all') to get entries from ALL subscribed feeds at once

ALTERNATIVE APPROACH (for selective reading):
- Step 1: Call rss(action='list') to see ALL available feeds
- Step 2: Call rss(action='read', feed_id=...) to get content from each feed you want

IMPORTANT: You should gather content from ALL feeds (not just one) to provide comprehensive coverage.
"""
```

### 2. New `read_all` Action (`src/influencerpy/tools/rss.py`)

Added a new convenience method that reads from ALL subscribed feeds in one call:

```python
def read_all_feeds(
    self,
    scout_id: Optional[int] = None,
    max_entries_per_feed: int = 5,
    include_content: bool = False,
) -> List[Dict]:
    """
    Read entries from ALL subscribed feeds (optionally filtered by scout_id).
    Returns a list of feed results, each containing entries from that feed.
    """
    # Implementation reads all feeds for the scout and returns structured results
```

**Benefits:**
- ✅ Single tool call instead of N+1 calls (list + N reads)
- ✅ Automatic scout isolation (only reads feeds for current scout)
- ✅ Returns structured data with feed attribution
- ✅ Efficient database queries

### 3. Explicit Scout Goals (`src/influencerpy/core/scouts.py`)

**Before:**
```python
goal = "Find interesting content from your subscribed RSS feeds. Use the 'rss' tool to list available feeds and read them."
```

**After:**
```python
goal = "Find interesting content from ALL your subscribed RSS feeds. Use the 'rss' tool to list available feeds, then read entries from EACH feed to gather diverse content across all sources."
```

### 4. Updated Default Instructions (`src/influencerpy/types/prompts.py`)

**Before:**
```python
"rss": "Find interesting content from the RSS feed and summarize key points."
```

**After:**
```python
"rss": "Find interesting content from ALL subscribed RSS feeds and summarize key points from each source."
```

## API Changes

### New Action: `read_all`

```python
# Old approach (requires multiple calls)
feeds = rss(action='list')  # Call 1
for feed in feeds:
    entries = rss(action='read', feed_id=feed['feed_id'])  # Call 2, 3, 4, 5...

# New approach (single call)
all_content = rss(action='read_all', max_entries=5)
# Returns:
# [
#   {
#     "feed_id": "1",
#     "feed_title": "Berkeley AI Research",
#     "feed_url": "https://bair.berkeley.edu/blog/feed.xml",
#     "entry_count": 5,
#     "entries": [...]
#   },
#   {
#     "feed_id": "2",
#     "feed_title": "Google Research",
#     ...
#   },
#   ...
# ]
```

## Expected Behavior Changes

### Before
1. Agent calls `rss(action='list')`
2. Agent **might** only read from one feed
3. Limited content diversity
4. Inconsistent multi-feed exploration

### After
1. Agent calls `rss(action='read_all')` (recommended)
   - OR calls `list` then reads from EACH feed
2. Agent gathers entries from **ALL** feeds
3. Rich content diversity from multiple sources
4. Consistent, comprehensive coverage

## Documentation Updates

Updated the following files to reflect multi-feed behavior:
- `docs/concepts/scouts.md` - Added note about multi-feed exploration
- `docs/getting-started.md` - Enhanced example to emphasize ALL feeds explored
- `examples/multi_rss_scout_example.md` - Added technical note about `read_all`
- `examples/multi_rss_visual_guide.md` - Updated key features

## Testing Recommendations

To verify this works:

1. Create a scout with 3-5 RSS feeds
2. Run the scout manually
3. Check the agent's tool calls in logs/telemetry
4. Verify it calls `read_all` OR calls `read` multiple times (once per feed)
5. Check the output includes content from ALL feeds (not just one)

## Backward Compatibility

✅ **Fully backward compatible**
- The `read` action still works for single-feed reading
- The `list` action is unchanged
- Old scouts will continue working
- The agent can choose either approach (`read_all` or `list + read`)

## Performance Impact

⚡ **Improved performance**
- Fewer database queries (1 query instead of N+1)
- Fewer tool calls (1 instead of N+1)
- Faster agent execution
- Lower API costs (fewer LLM calls for tool selection)

## Example Use Case

**Scout Configuration:**
- Name: AI Research Digest
- Feeds: 5 sources (Berkeley, Google, MIT, Microsoft, Takara)
- Intent: Content Discovery (Scouting)
- Schedule: Daily at 9 AM

**Agent Behavior:**
1. Calls `rss(action='read_all', max_entries=5)`
2. Receives entries from all 5 feeds (25 total entries, 5 per feed)
3. Analyzes all entries using AI
4. Selects 6-8 best articles across all sources
5. Generates report with source attribution

**Output:**
```
📚 AI Research Digest - Content Discovery

Found 8 interesting items from 5 sources

1. [Berkeley] Scaling Multimodal Models...
2. [Google] Gemini 2.0 Announcement...
3. [MIT] New Quantum Computing Breakthrough...
4. [Takara] Top Papers This Week...
5. [Microsoft] Azure AI Updates...
...
```

## Files Changed

- ✅ `src/influencerpy/tools/rss.py` - Added `read_all_feeds()` method and action
- ✅ `src/influencerpy/types/prompts.py` - Updated tool instructions and defaults
- ✅ `src/influencerpy/core/scouts.py` - Enhanced goal to emphasize ALL feeds
- ✅ `docs/concepts/scouts.md` - Added multi-feed exploration note
- ✅ `docs/getting-started.md` - Enhanced example
- ✅ `examples/multi_rss_scout_example.md` - Added technical details
- ✅ `examples/multi_rss_visual_guide.md` - Updated features list
