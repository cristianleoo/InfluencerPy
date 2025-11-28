# Image Generation

InfluencerPy integrates with **Stability AI** to automatically generate high-quality images for your social media posts.

## Features

*   **Context-Aware**: The AI analyzes the content found by your Scout and generates a relevant image prompt.
*   **High Quality**: Uses Stability AI's latest models (e.g., Stable Image Core) for professional results.
*   **Automated**: Images are generated and attached to your draft posts automatically.

## Setup

1.  **Get an API Key**: Sign up at [Stability AI Platform](https://platform.stability.ai/) and generate an API Key.
2.  **Configure InfluencerPy**:
    ```bash
    influencerpy configure
    ```
    Select "Stability AI" and paste your key.

## Usage

When creating a new Scout, you will be asked:
> Enable Image Generation (requires Stability AI)?

Select **Yes**.

Now, whenever this Scout runs:
1.  It finds interesting content (e.g., a news article).
2.  It generates a text draft.
3.  It calls Stability AI to generate an image representing that content.
4.  The image is saved locally and referenced in your draft.

## Cost

Image generation uses credits from your Stability AI account. Please refer to their pricing page for current rates.
