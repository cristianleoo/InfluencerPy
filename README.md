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

---



---

**InfluencerPy** is an intelligent CLI agent that autonomously discovers, curates, and publishes content to social media. Unlike basic scheduling tools, it uses **AI Scouts** to research topics, learn from your feedback, and draft high-quality posts that sound like you.

## ✨ Features

### 🕵️ Autonomous Scouts

Create configurable agents that patrol the web for you:

- **RSS Scouts**: Monitor your favorite blogs and newsletters.
- **Reddit Scouts**: Surface viral discussions from specific subreddits.
- **Search Scouts**: Discover trending news via Google Search.
- **Arxiv Scouts**: Monitor new research papers on Arxiv.
- **Browser Scouts** ⚠️ *[Experimental]*: Navigate web pages and extract content dynamically.
- **Telegram Integration**: Review and approve posts via a Telegram bot before they are published.

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

Ensure you have Python 3.11 or higher.

### 🚀 Option 1: uv (Blazing Fast)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver.

```bash
# Install directly from GitHub
uv tool install git+https://github.com/cristianleoo/influencerpy.git

# Run it
influencerpy
```

### 📦 Option 2: pipx (Recommended for Users)

If you just want to use the tool anywhere on your system without worrying about dependencies, use [pipx](https://pypa.github.io/pipx/):

```bash
# Install directly from GitHub
pipx install git+https://github.com/cristianleoo/influencerpy.git

# Run it from anywhere
influencerpy
```

### 🐍 Option 3: pip (Standard)

Standard installation in a virtual environment:

```bash
git clone https://github.com/cristianleoo/influencerpy.git
cd influencerpy

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install
pip install .
```

### 🛠️ Option 4: Development (Editable)

If you want to modify the code:

```bash
git clone https://github.com/cristianleoo/influencerpy.git
cd influencerpy
pip install -e .
```

### 🐳 Option 5: Docker

You can also run InfluencerPy using Docker. This is recommended for long-running bots.

1. **Clone the repository:**

   ```bash
   git clone https://github.com/cristianleoo/influencerpy.git
   cd influencerpy
   ```

2. **Build the image:**

   ```bash
   docker build -t influencerpy .
   ```

3. **Run interactively (for configuration):**

   We simply mount the `.influencerpy` directory to persist configuration.

   ```bash
   docker run -it --rm \
     -v $(pwd)/.influencerpy:/app/.influencerpy \
     influencerpy
   ```

4. **Run the bot (detached):**

   ```bash
   docker run -d \
     --name influencerpy-bot \
     --restart unless-stopped \
     -v $(pwd)/.influencerpy:/app/.influencerpy \
     influencerpy bot
   ```

---

### Telegram Setup

1. Message `@BotFather` on Telegram to create a new bot and get the **Bot Token**.
2. Message `@userinfobot` to get your **Chat ID**.
3. Run `influencerpy configure` and enter these credentials.
4. Run `influencerpy bot` to start the notification service.

## 🎮 Usage

Start the interactive dashboard:

```bash
influencerpy
```

### First Run Setup

On your first launch, the **Setup Wizard** will guide you through:

1. **Credentials**: securely saving your API Keys (X/Twitter, Gemini/Anthropic).
2. **AI Configuration**: Selecting your preferred model and temperature.

### Workflow

1. **Create a Scout**: Tell it what to look for (e.g., "AI News" via RSS).
2. **Run Scout**: Let it find content and draft a post.
3. **Review**: Accept, Edit, or Reject the draft.
4. **Post**: Publish immediately or schedule for later.

---

## 📚 Documentation

Full documentation is available at **[https://cristianleoo.github.io/InfluencerPy/](https://cristianleoo.github.io/InfluencerPy/)**.

- [Getting Started Guide](docs/getting-started.md)
- [Understanding Scouts](docs/concepts/scouts.md)
- [Scheduling Concepts](docs/concepts/scheduling.md)

---

## 🛠️ Development

We welcome contributions!

1. Clone the repo.
2. Install dependencies with hatch or pip.
3. Run tests:

    ```bash
    pytest
    ```

## 📄 License

This project is licensed under the [MIT License](LICENSE).
