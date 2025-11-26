# InfluencerPy

<div align="center">

![InfluencerPy](https://img.shields.io/badge/Influencer-Py-7B1FA2?style=for-the-badge&logo=robot&logoColor=white)
[![Python](https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge)](https://github.com/psf/black)

**The Premium Social Media Automation Agent.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation)

</div>

---

**InfluencerPy** is an intelligent CLI agent that autonomously discovers, curates, and publishes content to social media. Unlike basic scheduling tools, it uses **AI Scouts** to research topics, learn from your feedback, and draft high-quality posts that sound like you.

## ✨ Features

### 🕵️ Autonomous Scouts
Create configurable agents that patrol the web for you:
- **RSS Scouts**: Monitor your favorite blogs and newsletters.
- **Reddit Scouts**: Surface viral discussions from specific subreddits.
- **Search Scouts**: Discover trending news via Google Search.
- **HTTP Scouts**: Watch specific webpages for updates.

### 🧠 AI-Powered Core
- **Smart Selection**: Uses a two-step AI process to pick only the *best* content, not just the newest.
- **Contextual Drafting**: Generates posts using Gemini or Anthropic, tailored to your specific tone and style.
- **Self-Improving**: The "Calibration" feature rewrites its own system prompts based on your feedback.

### 💎 Premium Experience
- **Beautiful CLI**: A rich, interactive terminal interface with dashboards, wizards, and progress bars.
- **Multi-Platform**: First-class support for **X (Twitter)**, including auto-threading for long posts.
- **Smart Scheduling**: Interactive schedule builder (Daily, Weekly, Interval) – no cron syntax required.

---

## 🚀 Installation

Ensure you have Python 3.9 or higher.

```bash
pip install influencerpy
```

Or for the latest development version:

```bash
git clone https://github.com/yourusername/influencerpy.git
cd influencerpy
pip install -e .
```

---

## 🎮 Usage

Start the interactive dashboard:

```bash
influencerpy
```

### First Run Setup
On your first launch, the **Setup Wizard** will guide you through:
1.  **Credentials**: securely saving your API Keys (X/Twitter, Gemini/Anthropic).
2.  **AI Configuration**: Selecting your preferred model and temperature.

### Workflow
1.  **Create a Scout**: Tell it what to look for (e.g., "AI News" via RSS).
2.  **Run Scout**: Let it find content and draft a post.
3.  **Review**: Accept, Edit, or Reject the draft.
4.  **Post**: Publish immediately or schedule for later.

---

## 📚 Documentation

Full documentation is available at **[https://your-username.github.io/InfluencerPy](https://your-username.github.io/InfluencerPy)**.

- [Getting Started Guide](docs/getting-started.md)
- [Understanding Scouts](docs/concepts/scouts.md)
- [Scheduling Concepts](docs/concepts/scheduling.md)

---

## 🛠️ Development

We welcome contributions!

1.  Clone the repo.
2.  Install dependencies with hatch or pip.
3.  Run tests:
    ```bash
    pytest
    ```

## 📄 License

This project is licensed under the [MIT License](LICENSE).
