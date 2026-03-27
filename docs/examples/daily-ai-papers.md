# Daily AI Paper Feed

This tutorial shows you how to create an RSS Scout that monitors the latest AI research papers from arXiv and automatically posts about them on your social media.

## What You'll Build

An automated system that:

1. ✅ Monitors arXiv's AI/ML RSS feeds daily
2. ✅ Uses AI to select the most interesting/relevant paper
3. ✅ Generates an engaging social media post with key insights
4. ✅ Posts automatically (or waits for your approval)

## Prerequisites

- InfluencerPy installed and configured ([Getting Started](../getting-started.md))
- An X (Twitter) account connected
- API keys set up (Gemini or Anthropic)

## Step 1: Find Your RSS Feeds

arXiv provides RSS feeds for all their categories. For AI/ML research, we recommend:

### arXiv AI Categories

| Category | RSS Feed URL | Focus Area |
|----------|-------------|------------|
| **cs.AI** | `http://export.arxiv.org/rss/cs.AI` | Artificial Intelligence (general) |
| **cs.LG** | `http://export.arxiv.org/rss/cs.LG` | Machine Learning |
| **cs.CL** | `http://export.arxiv.org/rss/cs.CL` | Computation & Language (NLP) |
| **cs.CV** | `http://export.arxiv.org/rss/cs.CV` | Computer Vision |
| **cs.NE** | `http://export.arxiv.org/rss/cs.NE` | Neural & Evolutionary Computing |

!!! tip "Combining Multiple Feeds"
    You can subscribe to multiple feeds in a single Scout. The AI will intelligently choose content from across all your subscribed feeds.

### Alternative Sources

Beyond arXiv, consider these RSS feeds for AI research and news:

**Academic & Research:**
- **arXiv Multi-Category Feed**: Combine multiple arXiv categories by subscribing to each separately
- **PMLR (Proceedings of ML Research)**: Check individual conference proceedings for RSS feeds
- **Semantic Scholar Alerts**: Set up email alerts and use an email-to-RSS service

**Industry Blogs & News (Verified RSS Feeds):**
- **MIT Technology Review AI**: `https://www.technologyreview.com/topic/artificial-intelligence/feed/`
- **The Batch (DeepLearning.AI)**: `https://www.deeplearning.ai/the-batch/feed/`
- **Ars Technica AI**: `https://feeds.arstechnica.com/arstechnica/technology-lab`
- **VentureBeat AI**: `https://venturebeat.com/category/ai/feed/`
- **TechCrunch AI**: `https://techcrunch.com/category/artificial-intelligence/feed/`

**Research Labs (check for RSS on their blogs):**
- **OpenAI Blog**: Visit `https://openai.com/blog/` and look for RSS icon
- **Google DeepMind**: Visit `https://deepmind.google/discover/blog/` and check for RSS
- **Meta AI Research**: Visit `https://ai.meta.com/blog/` and check for RSS

!!! tip "Finding RSS Feeds"
    Many sites hide their RSS feeds. Try adding `/feed`, `/rss`, or `/feed.xml` to the end of blog URLs. Or use browser extensions like "RSS Feed Finder" to discover feeds automatically.

## Step 2: Create the RSS Scout

Launch InfluencerPy and create your scout:

```bash
influencerpy
```

Then follow these steps in the CLI:

### 2.1 Select "Manage Scouts"

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ InfluencerPy Main Menu      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  Run Scout
> Manage Scouts
  Configure Settings
  View Analytics
  Exit
```

### 2.2 Select "Create New Scout"

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Scout Management            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
> Create New Scout
  View Scouts
  Delete Scout
  Calibrate Scout
  Back
```

### 2.3 Choose Scout Type: "RSS"

```
Scout Type:
  Search
> RSS
  Reddit
  Arxiv
  HTTP Request
  Meta-Scout
```

### 2.4 Configure Your Scout

You'll be prompted for:

#### Scout Name
```
Scout Name: DailyAIPapers
```

!!! note "Naming Convention"
    Choose a descriptive name. It will be used for logs and scheduling.

#### RSS Feed URL

```
RSS Feed URL: http://export.arxiv.org/rss/cs.AI
```

The system will validate the feed. Once validated, it will automatically **subscribe** to this feed in the database.

```
✓ Successfully subscribed to cs.AI updates on arXiv.org
```

!!! tip "Adding More Feeds"
    You can add multiple feeds by repeating the creation process or by manually managing feeds (see [Advanced Configuration](#advanced-configuration)).

#### Goal/Instructions

This is where you define what the Scout should look for. Example:

```
Goal/Instructions: 
Find the most interesting and impactful AI research paper from today's 
arXiv submissions. Focus on papers related to large language models, 
agents, or novel architectures. Prioritize papers with practical 
applications or surprising results.
```

#### User Post Instructions

Tell the AI how to write your posts:

```
User Post Instructions:
Write an engaging tweet about the paper. Include:
- A catchy hook that highlights why the research matters
- The core contribution in simple terms
- One surprising finding or implication
- The arXiv link
- Keep it under 280 characters or thread if needed
- Use a conversational but informative tone
- No hashtags unless highly relevant
```

### 2.5 Set Posting Mode

```
Posting Mode:
> manual  (Review before posting)
  auto    (Post immediately)
```

For your first runs, choose **manual** to see what the Scout produces.

## Step 3: Test Your Scout

Run your newly created Scout:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ InfluencerPy Main Menu      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
> Run Scout
```

Select your `DailyAIPapers` scout from the list.

### What Happens During Execution

1. **Agent Initialization**: The Scout spins up an AI agent with the RSS tool
2. **Feed Discovery**: Agent lists subscribed feeds
3. **Content Retrieval**: Agent reads the latest entries from arXiv
4. **Intelligent Selection**: AI analyzes all papers and selects the best one based on your goal
5. **Draft Generation**: AI writes a social media post following your instructions
6. **Review** (manual mode): You see the draft and can Accept/Redraft/Reject

### Example Output

```
╭────────────────────────────────────────────────╮
│ Scout: DailyAIPapers                           │
│ Found: 15 papers                               │
│ Selected: "Constitutional AI: Harmlessness..." │
╰────────────────────────────────────────────────╯

📝 Generated Post:

🧠 New paper challenges how we align AI systems

Constitutional AI trains models to be helpful AND harmless 
without human feedback on every output. Key insight: AI can 
critique its own responses using simple "rules" (a constitution).

Result: 2x improvement in harmlessness with no loss in helpfulness

Read: https://arxiv.org/abs/2212.08073

Thread: 1/1

────────────────────────────────────────────────
Actions:
  [A] Accept & Post
  [R] Redraft
  [X] Reject
  [E] Edit Manually
```

## Step 4: Schedule Daily Runs

Once you're happy with the output, automate it!

### 4.1 Open Scheduler

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ InfluencerPy Main Menu      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  Run Scout
  Manage Scouts
> Configure Settings
  View Analytics
```

Then select **"Manage Schedules"**

### 4.2 Create Schedule

```
> Add New Schedule
```

Select your `DailyAIPapers` scout and configure:

#### Run Frequency

```
When should this scout run?
> Daily at specific time
  Every X hours
  Weekly
  Custom cron expression
```

#### Time

```
What time? (24-hour format): 09:00
```

!!! tip "Best Time to Post"
    arXiv publishes new papers around 00:00 UTC (Sunday-Thursday). 
    Schedule your scout for morning hours in your timezone to catch fresh papers.

#### Auto-Post Configuration

```
Enable auto-posting for this schedule?
> Yes (Scout will post automatically)
  No  (Scout will save drafts for manual review)
```

If you choose **Yes**, the Scout will run and post without your intervention.

### 4.3 Verify Schedule

The system will display your cron schedule:

```
✓ Schedule created successfully!

Scout: DailyAIPapers
Runs: Every day at 09:00
Auto-post: Enabled
Next run: Tomorrow at 09:00:00
```

## Step 5: Monitor & Improve

### Check Logs

Logs are saved in `.influencerpy/logs/scouts/DailyAIPapers/`

```bash
tail -f .influencerpy/logs/scouts/DailyAIPapers/$(ls -t .influencerpy/logs/scouts/DailyAIPapers/ | head -1)
```

### Calibrate Your Scout

If the posts aren't quite right, use the **Calibrate Scout** feature:

1. Go to **Manage Scouts** > **Calibrate Scout**
2. Select `DailyAIPapers`
3. Provide feedback on a generated draft
4. The system uses an "Expert Prompt Engineer" AI to automatically rewrite your Scout's system prompt based on your feedback

Example feedback:
```
Feedback: 
The posts are too technical. Use simpler language and focus more 
on the "why this matters" angle rather than methodology details.
```

The Scout will permanently improve based on this feedback.

### View Analytics

Check your performance:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ InfluencerPy Main Menu      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
> View Analytics
```

See metrics like:
- Total posts created
- Acceptance rate
- Top performing content
- Feedback trends

## Advanced Configuration

### Multiple Feed Sources

To subscribe to multiple feeds for one scout, you can manually add feeds using the RSS tool in a Python shell:



Your Scout will now pull from all subscribed feeds.

### Custom Update Intervals

By default, feeds update every 60 minutes. To change this:



### Filtering by Category/Tag

Some RSS feeds include categories. You can filter in your Goal instructions:

```
Goal: Find AI safety papers from today's arXiv submissions. 
Only consider papers with tags related to alignment, safety, 
or interpretability.
```

### Using Meta-Scouts for Cross-Referencing

For advanced workflows, create a **Meta-Scout** that:

1. Uses the RSS tool to find a paper
2. Uses the Reddit tool to check community discussions
3. Combines insights from both sources

Example Goal:
```
Use the RSS tool to find today's top AI paper. Then use the Reddit 
tool to check r/MachineLearning for any discussions about it. 
Summarize both the paper's contribution and community reaction.
```

## Troubleshooting

### Feed Not Updating

**Issue**: Scout isn't finding new papers.

**Solution**: Manually trigger an update:



### Posts Too Similar

**Issue**: Every post has the same structure.

**Solution**: Add variety instructions:

```
User Post Instructions:
...
Vary your approach: sometimes lead with the result, sometimes 
with the problem, sometimes with a surprising stat. Keep it fresh!
```

### Agent Not Selecting Good Papers

**Issue**: The AI picks boring or irrelevant papers.

**Solution**: Improve your Goal with specific criteria:

```
Goal: Find papers that:
1. Have novel architectures or surprising results
2. Show significant performance improvements (>10%)
3. Have practical applications
4. Are NOT incremental improvements on existing work
5. Introduce new concepts or challenge existing assumptions

Prioritize papers with clear real-world impact over purely theoretical work.
```

### Rate Limiting / API Errors

**Issue**: Hitting API limits.

**Solution**: 
- Reduce RSS update frequency
- Use fewer feeds
- Space out scheduled runs
- Consider upgrading your AI provider tier

## Next Steps

- **Add Images**: Check out [Image Generation](../concepts/image-generation.md) to auto-generate graphics for your papers
- **Telegram Control**: Set up [Telegram Integration](../channels/telegram.md) to control your scouts remotely
- **Deploy**: Learn about [Deployment](../deployment.md) to run InfluencerPy 24/7 on a server

## Real-World Example

Here's a real Scout configuration that has been successfully running:

```yaml
name: "ML_Papers_Daily"
type: "rss"
goal: |
  Find the most impactful machine learning paper published today. 
  Prioritize papers about:
  - Large language models and transformers
  - Novel training techniques
  - Efficient inference methods
  - Real-world applications with measurable impact
  
  Skip papers that are:
  - Purely theoretical with no experiments
  - Incremental improvements (<5% gains)
  - Surveys or literature reviews (unless groundbreaking)
  
posting_instructions: |
  Write a 2-3 tweet thread:
  
  Tweet 1: Hook - Why should people care? What problem does this solve?
  Tweet 2: The method - Explain the key innovation in simple terms
  Tweet 3 (if needed): Impact - What does this enable? Include link.
  
  Style: Conversational, informative, not overly hyped.
  Avoid: Buzzwords, hashtags, emoji overuse.
  
feeds:
  - "http://export.arxiv.org/rss/cs.LG"
  
schedule: "0 10 * * *"  # Daily at 10 AM
auto_post: true
```

---

**Questions or issues?** Open a discussion on [GitHub](https://github.com/cristianleoo/InfluencerPy/discussions) or check the [API Reference](../reference.md).
