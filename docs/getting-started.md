# Getting Started

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.9 or higher**: Check with `python --version`.
2.  **Telegram Bot** (Required): Used to receive scout reports and review drafts.
    - Message `@BotFather` to create a bot and get your **Bot Token**
    - Message `@userinfobot` to get your **Chat ID**
3.  **API Keys**: You will need API keys depending on your use case:
    *   **Google Gemini API Key** (Required for AI features): Get it from [Google AI Studio](https://aistudio.google.com/).
    *   **X (Twitter) API Keys** (Optional, only for posting): You need a Developer Account with "Read and Write" permissions. Get them from the [X Developer Portal](https://developer.twitter.com/en/portal/dashboard).
    *   **Substack Cookies** (Optional, only for paywalled content): See the [Substack Setup Guide](platforms/substack.md) for details.

## Installation

### Installation

InfluencerPy is currently available via source installation.

1.  Clone the repository:
    ```bash
    git clone https://github.com/cristianleoo/InfluencerPy.git
    cd InfluencerPy
    ```

2.  Install dependencies:
    ```bash
    pip install -e .
    ```

## Initial Configuration

InfluencerPy uses a configuration wizard to make setup easy. You don't need to manually edit config files unless you want to.

### 1. Run the CLI

Start the application:

```bash
influencerpy
```

### 2. Setup Credentials

On your first run, you will see the **Credential Setup Guide**.

1.  The wizard will ask for your **Gemini API Key** (required for AI features).
2.  It will ask for your **Telegram Bot Token** and **Chat ID** (required for receiving reports).
3.  Optionally, add **X API credentials** if you plan to post to Twitter.
4.  These are saved securely in a `.env` file in your project root.

### 3. Configure AI Settings

By default, InfluencerPy uses **Gemini Flash** for fast processing. You can customize this:

1.  Select **Configure AI Settings** from the main menu.
2.  Choose your provider: **Gemini** or **Anthropic**.
3.  Set a specific Model ID (e.g., `gemini-2.5-flash` for speed, or `claude-sonnet-4` for quality).
4.  Adjust the Temperature (default `0.7`). Higher values make output more creative; lower values make it more factual.

### 4. Optional: Telemetry (Langfuse)

To trace and debug your Scout's AI reasoning, you can enable [Langfuse](https://langfuse.com/) integration.

1.  Select **Configure AI Settings** -> **Langfuse (Tracing)** from the menu.
2.  Enter your **Host**, **Public Key**, and **Secret Key**.
3.  This setting is **global**: once enabled, all Scouts will report traces to your Langfuse project.

## Creating Your First Scout

Let's create a content discovery scout:

1. Run `influencerpy` and select **"Scouts"** → **"Create Scout"**
2. **Choose Intent**: Select **"🔍 Content Discovery"** (this finds and lists content)
3. **Scout Type**: Choose a source (RSS, Reddit, Arxiv, etc.)
4. **Configure Source**: Enter feed URLs, subreddits, or search queries
   - **Tip**: For RSS feeds, you can add multiple feeds separated by commas (e.g., `https://feed1.com/rss, https://feed2.com/rss`)
5. **Schedule**: Set when it should run (Daily, Weekly, or Manual)
6. **Done!**: Your scout is ready

### Running Your Scout

**Manual Run**:
- From CLI: Select the scout and choose "Run Scout"
- From Telegram: Send `/scouts` and click "🚀 Run Scout"

**Scheduled Run**:
- The bot will automatically run scouts based on their schedule
- Reports are sent to Telegram

### What You'll Receive

For **Scouting Intent** scouts, you'll receive:
- A curated list of content items
- Summary of each item
- Links to original sources
- Delivered via Telegram for easy reading

For **Generation Intent** scouts (optional), you'll receive:
- Draft social media posts
- Ready to post to X (Twitter) or copy/paste elsewhere

## Example: Multi-Feed AI Research Scout

Here's a complete example of creating a content discovery scout that monitors multiple AI research sources:

### Configuration

```
Scout Name: AI Research Digest
Intent: 🔍 Content Discovery (Scouting)
Scout Type: 📡 RSS
RSS Feed URLs: https://tldr.takara.ai/api/papers, https://bair.berkeley.edu/blog/feed.xml, https://research.google/blog/rss/, https://news.mit.edu/rss/topic/artificial-intelligence2, https://news.microsoft.com/source/topics/ai/feed/
Schedule: Daily at 9:00 AM
```

### What This Does

This scout will:

1. **Monitor 5 AI research sources simultaneously**:
   - Takara AI TLDR Papers
   - Berkeley AI Research (BAIR) Blog
   - Google Research Blog
   - MIT AI News
   - Microsoft AI News

2. **Explore ALL feeds comprehensively**: The AI automatically reads entries from ALL 5 feeds (not just one), gathering diverse content across all sources

3. **Analyze and select the best content**: The AI reviews articles from all feeds and selects the most relevant and interesting ones

4. **Deliver a curated report** to Telegram with:
   - Article titles and summaries
   - Key insights from each piece
   - Links to original sources
   - Source attribution (showing which feed each article came from)
   - Delivered every morning at 9 AM

### Sample Output

```
# 📚 AI Research Digest - Content Discovery
*Found 6 interesting items from 5 sources*

## 1. New Advances in Multimodal Learning
Summary: Researchers at Berkeley demonstrate significant improvements in vision-language models...
🔗 Source: https://bair.berkeley.edu/blog/2025/...

## 2. Scaling Language Models: Latest Insights
Summary: Google Research shares findings on training efficiency...
🔗 Source: https://research.google/blog/...

[... more items ...]
```

### Why Multiple Feeds?

- **Broader coverage**: Get diverse perspectives from academia and industry
- **All feeds explored**: The agent automatically reads from ALL feeds, not just one
- **Better selection**: More content from multiple sources means the AI can pick truly standout articles
- **Single digest**: One consolidated report instead of multiple notifications
- **Source attribution**: See which feed each article came from
- **Efficient**: Set up once, runs automatically every day

## Next Steps

*   👉 [Learn about Scouts](concepts/scouts.md) to understand scouting vs generation
*   👉 [Explore Scheduling](concepts/scheduling.md) to automate your scouts
*   👉 [Telegram Integration](channels/telegram.md) for remote management
