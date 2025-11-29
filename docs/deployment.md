# Deployment Guide

InfluencerPy is designed to run continuously in the background to monitor feeds and manage your social media presence. This guide covers how to keep it running and where to host it for free.

## Running in the Background

Since InfluencerPy is a CLI application, closing your terminal will stop the bot. Here are two ways to keep it running.

### Langfuse Tracing (Optional)
To enable observability for your scouts via Langfuse:
1.  Sign up at [Langfuse](https://langfuse.com/).
2.  Get your API keys (Base URL, Public Key, Secret Key).
3.  **Easy Setup:** Run `influencerpy` and select **"Configure Credentials"** -> **"Langfuse (Tracing)"**.
4.  **Manual Setup:** Add them to your `.env` file:
    ```bash
    LANGFUSE_HOST="https://cloud.langfuse.com"
    LANGFUSE_PUBLIC_KEY="pk-lf-..."
    LANGFUSE_SECRET_KEY="sk-lf-..."
    ```
5.  When creating a scout, you can enable tracing. If keys are missing, the CLI will offer to help you set them up.

### Option 1: Using `tmux` (Recommended for Beginners)

`tmux` allows you to create a session that keeps running even after you disconnect from your server.

1.  **Install tmux**:
    ```bash
    # Ubuntu/Debian
    sudo apt install tmux
    
    # macOS
    brew install tmux
    ```

2.  **Start a new session**:
    ```bash
    tmux new -s influencerpy
    ```

3.  **Run the bot**:
    ```bash
    influencerpy bot
    ```

4.  **Detach**: Press `Ctrl+B` then `D`. You can now safely close your terminal.

5.  **Reattach**: To check on your bot later:
    ```bash
    tmux attach -s influencerpy
    ```

### Option 2: Using `systemd` (Recommended for Production)

For a more robust setup on Linux servers, use `systemd` to automatically restart the bot if it crashes or the server reboots.

1.  **Create a service file**:
    ```bash
    sudo nano /etc/systemd/system/influencerpy.service
    ```

2.  **Add the following configuration** (adjust paths and user):
    ```ini
    [Unit]
    Description=InfluencerPy Bot
    After=network.target

    [Service]
    Type=simple
    User=your_username
    WorkingDirectory=/home/your_username/InfluencerPy
    # Ensure the path to 'influencerpy' is correct (e.g., inside venv)
    ExecStart=/home/your_username/InfluencerPy/.venv/bin/influencerpy bot
    Restart=always
    RestartSec=10
    EnvironmentFile=/home/your_username/InfluencerPy/.env

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Enable and Start**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable influencerpy
    sudo systemctl start influencerpy
    ```

4.  **Check Logs**:
    ```bash
    sudo journalctl -u influencerpy -f
    ```

## Free Hosting Options

You don't need an expensive server to run InfluencerPy. Here are some excellent free options:

### 1. Oracle Cloud Free Tier (Best Performance)
Oracle offers "Always Free" ARM instances that are very powerful.
*   **Specs**: Up to 4 ARM Ampere CPUs and 24GB RAM.
*   **Pros**: extremely generous resources, fast network.
*   **Cons**: Sign-up can be picky about credit cards.

### 2. Google Cloud Platform (GCP) Free Tier
*   **Specs**: e2-micro instance (2 vCPUs, 1GB RAM).
*   **Pros**: Reliable, easy integration with other Google services.
*   **Cons**: Limited RAM (might need swap file).

### 3. AWS Free Tier
*   **Specs**: t2.micro or t3.micro (1 vCPU, 1GB RAM) for 12 months.
*   **Pros**: Industry standard.
*   **Cons**: Free trial expires after 1 year.

### 4. Fly.io (Containerized)
If you prefer Docker, Fly.io offers a free allowance.
*   **Pros**: Simple deployment if you have a Dockerfile.
*   **Cons**: Persistent storage (volumes) might cost extra after the free allowance.

## Tips for Cloud Deployment

*   **Environment Variables**: Ensure your `.env` file is securely copied to the server or variables are set in the deployment environment.
*   **Database**: By default, InfluencerPy uses SQLite (`database.db`). If you redeploy or destroy the instance, you will lose data unless you use a persistent volume or switch to a cloud database (PostgreSQL).
