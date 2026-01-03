# Multi-Feed RSS Scout Example

This example demonstrates how to create a content discovery scout that monitors multiple RSS feeds simultaneously.

## Use Case: AI Research Digest

Monitor multiple AI research sources and receive a daily curated digest of the most interesting articles **from ALL sources**.

**Key Feature**: When you add multiple RSS feeds, the scout automatically explores **ALL of them** (not just one), gathering entries from each feed to provide comprehensive, multi-source coverage.

## Setup

1. Start InfluencerPy:
```bash
influencerpy
```

2. Navigate to: **Scouts** → **Create Scout**

3. Configure the scout:

| Setting | Value |
|---------|-------|
| **Scout Name** | AI Research Digest |
| **Intent** | 🔍 Content Discovery (Scouting) |
| **Scout Type** | 📡 RSS |
| **RSS Feed URLs** | See below ⬇️ |
| **Schedule** | Daily at 9:00 AM |

### RSS Feed URLs

When prompted for "RSS Feed URL (or multiple URLs separated by comma):", paste this:

```
https://tldr.takara.ai/api/papers, https://bair.berkeley.edu/blog/feed.xml, https://research.google/blog/rss/, https://news.mit.edu/rss/topic/artificial-intelligence2, https://news.microsoft.com/source/topics/ai/feed/
```

This monitors:
- **Takara AI TLDR** - Summarized research papers
- **Berkeley AI Research (BAIR)** - Academic blog posts
- **Google Research** - Industry research updates
- **MIT AI News** - Academic news and breakthroughs
- **Microsoft AI** - Industry applications and research

**Technical Note**: The agent uses the `rss(action='read_all')` tool action to efficiently read entries from ALL 5 feeds in one call, ensuring comprehensive coverage across all sources.

## Expected Behavior

### During Setup
The system will validate each feed individually:

```
✓ Feed validated: https://tldr.takara.ai/api/papers
✓ Feed validated: https://bair.berkeley.edu/blog/feed.xml
✓ Feed validated: https://research.google/blog/rss/
✓ Feed validated: https://news.mit.edu/rss/topic/artificial-intelligence2
✓ Feed validated: https://news.microsoft.com/source/topics/ai/feed/

Successfully validated 5 feed(s)
```

### Daily Reports

You'll receive a Telegram message every morning at 9 AM with content like:

```
📚 AI Research Digest - Content Discovery

Found 6 interesting items from 5 sources

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Scaling Multimodal Models with Better Data

Summary: Berkeley researchers demonstrate that data quality 
matters more than quantity for vision-language models, achieving 
SOTA results with 10x less training data.

Key insights:
- Curated datasets outperform web-scraped data
- New filtering techniques reduce compute costs
- Open-sourcing the dataset and methodology

🔗 Source: https://bair.berkeley.edu/blog/2025/...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. Gemini 2.0: Multimodal Reasoning at Scale

Summary: Google introduces next-generation model with improved 
reasoning capabilities across text, images, and code...

🔗 Source: https://research.google/blog/...

[... more articles ...]
```

## Advantages of Multi-Feed Scouting

1. **Comprehensive Coverage**: The agent explores ALL feeds, not just one - ensuring you don't miss content from any source
2. **AI-Powered Selection**: The AI analyzes articles from ALL feeds and picks only the best ones
3. **Diverse Perspectives**: Get content from academia (Berkeley, MIT), industry (Google, Microsoft), and aggregators (Takara)
4. **Single Digest**: One consolidated report instead of notification overload
5. **Time Efficient**: Set up once, get curated insights forever
6. **Source Attribution**: See which feed each article came from for context
7. **Comparative Analysis**: See how different organizations approach similar topics

## Customization Ideas

### Focus on Specific Topics

Add a more specific system prompt during calibration:

```
"Focus on papers and articles about large language models, 
especially those related to reasoning, planning, and tool use. 
Ignore general AI news."
```

### Adjust Frequency

Change the schedule based on your needs:
- **Hourly**: For breaking news and real-time monitoring
- **Daily**: For morning briefings (recommended)
- **Weekly**: For weekend deep reads
- **Manual**: Run on-demand when you need insights

### Mix with Other Tools

Create a "Meta-Scout" that combines RSS feeds with other sources:

| Setting | Value |
|---------|-------|
| **Scout Type** | 🤖 Meta-Scout (Orchestrator) |
| **Tools** | RSS, Google Search, Arxiv |
| **Goal** | "Find the latest breakthroughs in AI research from blogs, papers, and news" |

This allows the AI to cross-reference sources and provide richer context.

## Testing Your Scout

Before scheduling, test it manually:

1. Go to **Scouts** → **Manage Scouts**
2. Select your "AI Research Digest" scout
3. Choose **"Run Scout"**
4. Check Telegram for the output
5. Provide feedback if needed to calibrate results

## Troubleshooting

### "Invalid or empty feed" Error

If one feed fails validation:
- Check if the URL is accessible in your browser
- Some feeds may have rate limiting or geo-restrictions
- Remove problematic feeds and continue with working ones

### Too Many Results

If you're getting too many articles:
1. Use **Calibrate Scout** to add constraints
2. Reduce the number of feeds
3. Adjust schedule to less frequent runs

### Too Few Results

If you're not getting enough content:
1. Check feed activity (some feeds update infrequently)
2. Add more feeds to increase content pool
3. Adjust AI temperature for broader selection
4. Calibrate the scout to be less strict

## Related Examples

- [HTTP Tool Demo](http_tool_demo.py) - Scraping web content
- [Creating Custom Scouts](../docs/concepts/scouts.md)
- [Scheduling Guide](../docs/concepts/scheduling.md)

## Next Steps

1. ✅ Create the scout following this example
2. 🔄 Run it manually to test
3. 🎯 Calibrate based on initial results
4. ⏰ Let it run automatically and enjoy your daily digest!
