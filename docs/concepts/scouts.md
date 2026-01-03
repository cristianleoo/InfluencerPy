# Scouts

**Scouts** are the autonomous agents at the heart of InfluencerPy. Think of them as tireless research assistants that constantly monitor the web for content that matches your specific interests and deliver curated reports or generate social media posts based on their **intent**.

## Scout Intents

Every scout has an **intent** that determines how it processes and delivers content:

### 🔍 Scouting Intent (Primary Use Case)

**Goal**: Find and list interesting content with summaries and links

**Perfect for**:
- Research and staying informed in your field
- Competitive intelligence
- Content curation for newsletters
- Discovery and learning

**Output**: A formatted report with:
- Content titles and summaries
- Links to original sources
- Delivered via Telegram for easy reading

**Example Report**:
```
# 📚 Daily AI Papers - Content Discovery

*Found 5 interesting items*

## 1. Large Language Models as Optimizers
Researchers propose using LLMs to optimize prompts automatically...
🔗 Source: https://arxiv.org/abs/2309.03409

## 2. Constitutional AI: Harmlessness from AI Feedback  
Anthropic introduces a method for training safer AI systems...
🔗 Source: https://arxiv.org/abs/2212.08073
```

### ✍️ Generation Intent (Optional)

**Goal**: Create social media posts from discovered content

**Perfect for**:
- Maintaining active social presence
- Content repurposing
- Automated Twitter accounts

**Output**: Draft social media posts ready to:
- Post automatically to X (Twitter)
- Review and edit in Telegram
- Copy/paste to other platforms

**Example Post**:
```
🤖 Breakthrough in AI optimization: 

New research shows LLMs can optimize their own prompts,
improving performance by up to 50% without human intervention.

This changes everything for prompt engineering.

📄 Read: https://arxiv.org/abs/2309.03409
```

---

## The Scout Lifecycle

The processing pipeline differs based on intent:

### For Scouting Intent:

1.  **Initialization**: Scout spins up an AI Agent with specific tools
2.  **Discovery**: Agent searches for content matching the goal
3.  **AI Selection**: Multiple items are analyzed and ranked
4.  **Formatting**: Best items are formatted as a curated list with summaries
5.  **Delivery**: Report sent to Telegram

### For Generation Intent:

1.  **Initialization**: Scout spins up an AI Agent with specific tools
2.  **Discovery**: Agent searches for content matching the goal
3.  **AI Selection**: Single best item is selected using relevance scoring
4.  **Drafting**: AI generates a social media post tailored to platform and tone
5.  **Action**: Post sent to Telegram for review or directly to platform

---

## Scout Types

InfluencerPy offers multiple specialized Scout types, each designed for different content sources.

### 1. Search Scout 🔍

**Best for:** Discovering new, trending, or broad information

*   **How it works:** Uses **Google Search** (via Gemini Grounding) to perform live web searches
*   **Configuration:**
    *   **Query**: Keywords or phrase to search for (e.g., "Latest AI breakthroughs")
*   **Example Use Cases:**
    *   **Scouting**: Get daily list of new AI regulation articles with summaries
    *   **Generation**: Create tweets about trending tech news

### 2. RSS Scout 📡

**Best for:** Monitoring specific, trusted sources like blogs and newsletters

*   **How it works:** Uses the **InfluencerPy RSS Tool** to subscribe to XML/Atom feeds
*   **Database Storage:** Feeds stored locally, preventing duplicate content
*   **Configuration:**
    *   **Feeds:** List of RSS Feed URLs (validated automatically)
*   **Intelligence:** Agent analyzes feed entries for relevance, not just newest item
*   **Example Use Cases:**
    *   **Scouting**: Weekly digest of TechCrunch articles with summaries
    *   **Generation**: Daily tweets about blog posts from favorite sources

### 3. Substack Scout 📰

**Best for:** Monitoring Substack newsletters and accessing paywalled content

*   **How it works:** Uses the **Substack API** to fetch posts
*   **Configuration:**
    *   **Newsletter URL**: Substack publication to monitor
    *   **Sorting**: "new" (most recent) or "top" (most popular)
*   **Authentication:** Optional cookies for paywalled content
*   **Example Use Cases:**
    *   **Scouting**: Track industry newsletters and get summaries with links
    *   **Generation**: Share insights from newsletters as Twitter threads
*   **Setup:** See [Substack Platform Guide](../platforms/substack.md)

### 4. Reddit Scout 👾

**Best for:** Community discussions, viral trends, and niche opinions

*   **How it works:** Fetches "Hot" posts from subreddits
*   **Configuration:**
    *   **Subreddits**: List of subreddit names (without `r/`)
*   **Example Use Cases:**
    *   **Scouting**: Daily list of trending discussions in r/MachineLearning
    *   **Generation**: Tweets about viral Reddit posts with community sentiment

### 5. Arxiv Scout 🎓

**Best for:** Academic papers and technical research

*   **How it works:** Searches Arxiv.org database
*   **Configuration:**
    *   **Query**: Search topic or Arxiv ID
    *   **Date Filter**: "Today", "This Week", or "This Month"
*   **Example Use Cases:**
    *   **Scouting**: Weekly roundup of new LLM papers with abstracts
    *   **Generation**: Thread explaining breakthrough research papers

### 6. HTTP Request Scout 🌐

**Best for:** Monitoring specific webpages or analyzing static resources

*   **How it works:** Fetches raw HTML/Text from URLs
*   **Configuration:**
    *   **URL**: Target website address
*   **Example Use Cases:**
    *   **Scouting**: Monitor company press release pages for updates
    *   **Generation**: Posts about new product announcements

### 7. Meta-Scout (Orchestrator) 🤖

**Best for:** Complex research combining multiple sources

*   **How it works:** Orchestrates multiple scouts or tools
*   **Configuration:**
    *   **Tools**: Enabled capabilities (Search, Arxiv, HTTP, etc.)
    *   **Goal**: High-level instruction for tool coordination
*   **Example Use Cases:**
    *   **Scouting**: Comprehensive reports combining news, papers, and discussions
    *   **Generation**: Multi-perspective posts synthesizing various sources

---

## Optimization & Calibration

Scouts improve over time through feedback:

### The Calibration Loop

1.  Run `influencerpy` → **Manage Scouts** → **Calibrate Scout**
2.  Scout generates output (list or post depending on intent)
3.  Provide **Feedback** (e.g., "Too technical" or "Include more context")
4.  **Meta-Prompting**: AI rewrites the Scout's system prompt automatically
5.  Future outputs reflect your preferences

### Feedback Recording

When reviewing scouts:
*   **Rejecting** content prompts for a reason
*   Feedback stored in database
*   Used to optimize selection logic and search queries

---

## Choosing the Right Intent

**Use Scouting Intent when you want to**:
- ✅ Stay informed without publishing
- ✅ Research and learn
- ✅ Curate content for others (newsletters, teams)
- ✅ Monitor competitors or trends
- ✅ Keep links to original sources

**Use Generation Intent when you want to**:
- ✅ Maintain active social media presence
- ✅ Automate content posting
- ✅ Repurpose content for different platforms
- ✅ Save time on social media management

**You can mix both!** Create scouting scouts for research and generation scouts for posting.
