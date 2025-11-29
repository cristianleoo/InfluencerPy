# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# git: for installing dependencies from git repositories
# curl: for healthchecks or downloading tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the application
RUN pip install --no-cache-dir -e .

# Create configuration directory
RUN mkdir -p .influencerpy

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default entrypoint
ENTRYPOINT ["influencerpy"]
