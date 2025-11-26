# Scouts

**Scouts** are the autonomous agents at the heart of InfluencerPy. Think of them as tireless research assistants that constantly monitor the web for content that matches your specific interests, filter it for quality, and draft social media posts for you.

## The Scout Lifecycle

Every time a Scout runs, it follows a sophisticated 5-step process:

1.  **Initialization**: The Scout spins up an AI Agent (powered by Gemini or Anthropic) and equips it with specific **Tools** based on its type (e.g., Search Tool, RSS Reader, Reddit Fetcher).
2.  **Discovery (The Hunt)**: The Agent actively searches the web. Unlike simple automation that just grabs the "latest" item, the Scout uses its AI reasoning to find content that matches its goal.
3.  **AI Selection (The Filter)**:
    *   The Scout Manager collects all candidates found by the Agent.
    *   It runs a **second AI pass** to analyze these options.
    *   It scores them based on **Relevance**, **Engagement Potential**, and **Quality** to pick the single best piece of content.
4.  **Drafting (The Creative)**:
    *   The selected content is fed into a Generative AI model.
    *   The AI writes a social media post using your configured **System Prompt** (Tone, Style, constraints).
    *   *Note:* For X (Twitter), posts longer than 280 characters are automatically threaded.
5.  **Action**:
    *   **Manual Mode**: The draft is presented to you in the CLI for review (Accept/Redraft/Reject).
    *   **Auto-Post Mode**: If configured, the draft is immediately posted to your connected platforms.

---

## Scout Types

InfluencerPy offers four specialized Scout types, each designed for a different kind of content discovery.

### 1. Search Scout 🔍

**Best for:** Discovering new, trending, or broad information where you don't have a specific source.

*   **How it works:** Uses **Google Search** (via Gemini Grounding) to perform live web searches.
*   **Configuration:**
    *   **Query**: The keyword or phrase to search for (e.g., "Latest breakthroughs in fusion energy", "New Python libraries").
*   **Example Use Case:**
    *   *Query:* "Artificial Intelligence regulation updates"
    *   *Result:* The Scout finds a new EU AI Act article from a major news outlet, summarizes it, and drafts a tweet about compliance.

### 2. RSS Scout 📡

**Best for:** Monitoring specific, trusted sources like blogs, newsletters, or news sites.

*   **How it works:** Uses the **Strands RSS Tool** to fetch and parse XML/Atom feeds.
*   **Configuration:**
    *   **Feeds**: A list of valid RSS Feed URLs.
*   **Intelligence:** The Agent doesn't just blindly pick the newest item. It reads the feed entries and selects the one most relevant to the prompt "Find interesting content".
*   **Finding Feeds:** Most news sites have an RSS feed at `/rss`, `/feed`, or `/feeds`.
    *   *TechCrunch:* `https://techcrunch.com/feed/`
    *   *The Verge:* `https://www.theverge.com/rss/index.xml`

### 3. Reddit Scout 👾

**Best for:** Tapping into community discussions, viral trends, and niche opinions.

*   **How it works:** Uses the custom **Reddit Tool** to fetch "Hot" posts from a subreddit's JSON endpoint.
*   **Configuration:**
    *   **Subreddits**: A list of subreddit names (without `r/`).
*   **Example Use Case:**
    *   *Subreddit:* `LocalLLaMA`
    *   *Result:* The Scout finds a highly upvoted post about a new open-source model release, captures the community sentiment, and drafts a post sharing the news.
*   **Note:** This tool respects Reddit's rate limits.

### 4. HTTP Request Scout 🌐

**Best for:** Monitoring a specific webpage for changes or analyzing a specific static resource.

*   **How it works:** Fetches the raw HTML/Text from a target URL.
*   **Configuration:**
    *   **URL**: The target website address.
*   **Use Case:** Summarizing a specific company's press release page or a daily updated status report.

---

## Optimization & Calibration

One of InfluencerPy's most powerful features is that **Scouts get smarter the more you use them.**

### The Calibration Loop

You can manually "train" a Scout to understand your voice and preferences.

1.  Run `influencerpy` and select **Manage Scouts** -> **Calibrate Scout**.
2.  The Scout will fetch an item and generate a draft.
3.  You provide **Feedback** (e.g., "Too formal, make it punchier," or "Don't use hashtags").
4.  **Meta-Prompting**: The system uses an "Expert Prompt Engineer" AI to analyze your feedback and **rewrite the Scout's System Prompt** automatically.
5.  This permanently improves the Scout's future output.

### Feedback Recording

When running a Scout in **Manual Mode**:
*   **Rejecting** a draft prompts you for a reason.
*   This feedback is stored in the database.
*   (Future Feature) The **Optimize Scout** command uses this historical data to perform batch optimization of the Scout's search queries and selection logic using DSPy.
