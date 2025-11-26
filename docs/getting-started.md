# Getting Started

## Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.9 or higher**: Check with `python --version`.
2.  **API Keys**: You will need API keys for the services you intend to use:
    *   **Google Gemini API Key** (Required for AI features): Get it from [Google AI Studio](https://aistudio.google.com/).
    *   **X (Twitter) API Keys** (Required for posting): You need a Developer Account with "Read and Write" permissions. Get them from the [X Developer Portal](https://developer.twitter.com/en/portal/dashboard).

## Installation

### Option 1: Install via PIP (Recommended)

InfluencerPy is available as a Python package.

```bash
pip install influencerpy
```

### Option 2: Install from Source

If you want the latest features or want to contribute:

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/influencerpy.git
    cd influencerpy
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

1.  The wizard will ask for your **X API Key**, **API Secret**, **Access Token**, and **Access Token Secret**.
2.  It will also ask for your **Gemini API Key**.
3.  These are saved securely in a `.env` file in your project root.

### 3. Configure AI Settings

By default, InfluencerPy uses **Gemini Pro** (via Strands). You can customize this:

1.  Select **Configure AI Settings** from the main menu.
2.  Choose your provider: **Gemini** or **Anthropic**.
3.  Set a specific Model ID (e.g., `gemini-2.5-flash` for speed, or `gemini-1.5-pro` for reasoning).
4.  Adjust the Temperature (default `0.7`). Higher values make posts more creative; lower values make them more factual.

## Next Steps

Once installed and configured, you are ready to create your first Scout!

*   👉 [Learn about Scouts](concepts/scouts.md) to start automating content.
*   👉 [Explore Scheduling](concepts/scheduling.md) to run scouts automatically.
