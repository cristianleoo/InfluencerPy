# Multi-Feed RSS Scout - Quick Visual Guide

## Step-by-Step Screenshots (Text Format)

### Step 1: Start InfluencerPy
```
$ influencerpy

╔══════════════════════════════════════════════════════════════╗
║                      InfluencerPy                           ║
║          Intelligent Content Discovery & Curation           ║
╚══════════════════════════════════════════════════════════════╝

Main Menu:
> Scouts
  Configure AI Settings
  Exit
```

### Step 2: Navigate to Create Scout
```
Scouts Menu:
> Create Scout
  Manage Scouts
  Back to Main Menu
```

### Step 3: Choose Intent
```
? Select Intent:
> 🔍 Content Discovery (Scouting)
  ✍️  Post Generation
  
[Scouting finds and lists content with summaries and links]
```

### Step 4: Choose Scout Type
```
? Select Scout Type:
  🔍 Search (Google)
> 📡 RSS (Follow specific feed URLs)
  📰 Substack
  👾 Reddit
  🎓 Arxiv
  🌐 HTTP Request
  🤖 Meta-Scout (Orchestrator)
```

### Step 5: Enter Multiple RSS Feeds
```
? RSS Feed URL (or multiple URLs separated by comma): 
https://tldr.takara.ai/api/papers, https://bair.berkeley.edu/blog/feed.xml, https://research.google/blog/rss/, https://news.mit.edu/rss/topic/artificial-intelligence2, https://news.microsoft.com/source/topics/ai/feed/

⠋ Validating feed: https://tldr.takara.ai/api/papers...
✓ Feed validated: https://tldr.takara.ai/api/papers

⠋ Validating feed: https://bair.berkeley.edu/blog/feed.xml...
✓ Feed validated: https://bair.berkeley.edu/blog/feed.xml

⠋ Validating feed: https://research.google/blog/rss/...
✓ Feed validated: https://research.google/blog/rss/

⠋ Validating feed: https://news.mit.edu/rss/topic/artificial-intelligence2...
✓ Feed validated: https://news.mit.edu/rss/topic/artificial-intelligence2

⠋ Validating feed: https://news.microsoft.com/source/topics/ai/feed/...
✓ Feed validated: https://news.microsoft.com/source/topics/ai/feed/

✓ Successfully validated 5 feed(s)
```

### Step 6: Configure Scout Details
```
? Scout Name: AI Research Digest
? Description (optional): Daily digest of AI research from top sources
```

### Step 7: Set Schedule
```
? Select Schedule:
> Daily
  Weekly
  Custom
  Manual only

? What time should this run daily?
> 09:00
```

### Step 8: Success!
```
✓ Scout "AI Research Digest" created successfully!

Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name:        AI Research Digest
Intent:      🔍 Content Discovery
Type:        📡 RSS Scout
Feeds:       5 subscribed feeds
             - Takara AI Papers
             - Berkeley AI Research
             - Google Research
             - MIT AI News
             - Microsoft AI
Schedule:    Daily at 09:00
Status:      Active ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Would you like to:
> Run scout now (test it)
  Configure schedule
  Back to menu
```

### Step 9: Test Run (Optional)
```
? Run scout now (test it)

🚀 Running scout: AI Research Digest...
⠋ Fetching feeds...
⠋ Analyzing content with AI...
⠋ Generating report...

✓ Scout completed successfully!
✓ Report sent to Telegram

Found 8 interesting articles across 5 sources
Check your Telegram for the full report!
```

### Step 10: Telegram Report Received
```
📚 AI Research Digest - Content Discovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Found 8 interesting items from 5 sources

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Scaling Vision-Language Models

📝 Berkeley researchers demonstrate that careful 
data curation outperforms raw scale in multimodal 
learning, achieving SOTA with 10x less compute.

Key points:
• Quality over quantity in training data
• New filtering techniques for web data
• Open-sourced datasets and code

🔗 https://bair.berkeley.edu/blog/2025/01/...
📡 Source: Berkeley AI Research

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ Gemini 2.0: Next-Gen Multimodal AI

📝 Google unveils Gemini 2.0 with breakthrough 
reasoning capabilities across text, images, audio, 
and video modalities...

🔗 https://research.google/blog/...
📡 Source: Google Research

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[... 6 more articles ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ Next run: Tomorrow at 09:00
🔄 Want to adjust settings? Send /scouts
```

## Key Features Shown

✓ **Multiple feeds in one input** - Comma-separated URLs
✓ **Individual validation** - Each feed tested separately
✓ **Visual feedback** - Checkmarks and status messages
✓ **Summary count** - Know how many feeds succeeded
✓ **ALL feeds explored** - Agent reads from every subscribed feed
✓ **Multiple entries per feed** - Diverse content from each source
✓ **Consolidated report** - Single digest from all sources
✓ **Source attribution** - See which feed each article came from
✓ **Automatic scheduling** - Set it and forget it

## Tips for Best Results

1. **Start with 3-5 feeds** - Too many can be overwhelming
2. **Test before scheduling** - Run manually first to see output
3. **Mix source types** - Combine academic, industry, and news
4. **Calibrate based on feedback** - Tell the scout what you like
5. **Adjust frequency** - Daily might be too much for some feeds

## Common Patterns

### Research Digest (shown above)
5 AI research feeds → Daily morning digest

### News Aggregator
```
Tech news feeds: TechCrunch, Verge, Ars Technica
Schedule: Every 6 hours
Intent: Scouting
```

### Industry Monitor
```
Company blogs: OpenAI, Anthropic, DeepMind, Google AI
Schedule: Weekly summary
Intent: Scouting
```

### Content Pipeline
```
Inspiration feeds: Your favorite creators
Schedule: Daily
Intent: Generation (creates posts)
```
