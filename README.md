# InfluencerPy

<div align="center">

![InfluencerPy](https://img.shields.io/badge/Influencer-Py-7B1FA2?style=for-the-badge&logo=robot&logoColor=white)
[![Python](https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge)](https://github.com/psf/black)

**Intelligent Content Discovery & Curation, Powered by AI**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation)

</div>

---

**InfluencerPy** is an AI-powered content discovery tool that helps you find, monitor, and curate the best content from across the web. Using intelligent **AI Scouts**, it continuously discovers relevant content, summarizes key insights, and optionally generates social media posts.

Never miss important content in your field again.

## ✨ Features

### 🔍 Smart Content Discovery

Create AI scouts that continuously monitor sources and find relevant content:

- **RSS Scouts**: Monitor blogs, newsletters, and news feeds
- **Reddit Scouts**: Track trending discussions and viral posts
- **Substack Scouts**: Follow newsletter publications
- **Search Scouts**: Discover trending topics via Google
- **Arxiv Scouts**: Stay updated on research papers
- **HTTP Tool**: Extract content from any webpage
- **Browser Scouts** ⚠️ *[Experimental]*: Navigate dynamic web pages

### 🧠 Two Modes of Operation

**🔍 Scouting Mode (Primary)**: Find and list interesting content
- Curated lists with summaries
- Links to original sources
- Delivered via Telegram
- Perfect for research, competitive intelligence, and staying informed

**✍️ Generation Mode (Optional)**: Create social media posts
- Automatically generate posts from discovered content
- Post directly to X (Twitter)
- Review and edit before publishing
- Maintain your authentic voice

### 💎 Premium Experience

- **Beautiful CLI**: Rich, interactive terminal interface with dashboards and wizards
- **AI-Powered**: Uses Gemini or Anthropic for smart content selection and generation
- **Self-Improving**: Calibration feature learns from your feedback
- **Smart Scheduling**: Set it and forget it - scouts run automatically
- **Telegram Integration**: Review discoveries and approve posts from your phone

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

---

## ⚙️ Setup

### Telegram Setup (Required)

Scouts deliver discoveries via Telegram:

1. Message `@BotFather` on Telegram to create a new bot and get the **Bot Token**.
2. Message `@userinfobot` to get your **Chat ID**.
3. Run `influencerpy configure` and enter these credentials.
4. Run `influencerpy bot` to start receiving scout reports.

### Substack Setup (Optional)

To monitor paywalled Substack newsletters:

1. See the detailed [Substack Platform Guide](docs/platforms/substack.md)
2. Run `influencerpy configure` and select "Substack"
3. Enter your cookies and subdomain when prompted

## 🎮 Usage

Start the interactive dashboard:

```bash
influencerpy
```

### First Run Setup

On your first launch, the **Setup Wizard** will guide you through:

1. **Credentials**: Securely save your API Keys (Gemini/Anthropic for AI, X/Twitter if posting)
2. **AI Configuration**: Select your preferred model and temperature

### Quick Start: Content Scouting

1. **Create a Scout**: Choose sources to monitor (e.g., RSS feeds, Reddit, Arxiv)
2. **Select "Scouting" Intent**: Get curated lists with links
3. **Set Schedule**: Daily, weekly, or custom timing
4. **Run**: Scouts find content and send reports to Telegram
5. **Review**: Get organized lists of relevant content with summaries

### Optional: Social Media Generation

1. **Create a Scout**: Same as above
2. **Select "Generation" Intent**: Create social posts
3. **Choose Platform**: X (Twitter) or manual copy/paste
4. **Review in Telegram**: Edit and approve before posting

---

## 📚 Documentation

Full documentation is available at **[https://cristianleoo.github.io/InfluencerPy/](https://cristianleoo.github.io/InfluencerPy/)**.

- [Getting Started Guide](docs/getting-started.md)
- [Understanding Scouts](docs/concepts/scouts.md)
- [Scouting vs Generation Intents](docs/concepts/scouts.md#scout-intents)
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
