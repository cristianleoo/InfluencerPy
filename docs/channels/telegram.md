# Telegram Integration

InfluencerPy includes a powerful Telegram integration that allows you to monitor your scouts, review drafts, and trigger runs remotely.

## Setup

To use the Telegram features, you need to create a Telegram Bot and configure InfluencerPy with your credentials.

### 1. Create a Telegram Bot
1.  Open Telegram and search for **@BotFather**.
2.  Send the command `/newbot`.
3.  Follow the prompts to name your bot (e.g., "MyInfluencerBot").
4.  **Copy the HTTP API Token** provided by BotFather.

### 2. Get Your Chat ID
1.  Search for **@userinfobot** on Telegram.
2.  Start the chat.
3.  **Copy the "Id"** (a number) it sends you.

### 3. Configure InfluencerPy
Run the configuration wizard:
```bash
influencerpy configure
```
Select **Telegram** and enter your **Bot Token** and **Chat ID**.

---

## Running the Bot

To start the Telegram listener, run:

```bash
influencerpy bot
```

Keep this command running (e.g., in a background terminal or on a server). The bot will poll for updates and handle notifications.

---

## Features

### 🔔 Review Notifications
When a Scout generates a draft (and `telegram_review` is enabled), the bot will send you a message with the draft content and inline buttons:

*   **✅ Confirm**: Immediately posts the content to the configured platform (e.g., X/Twitter).
*   **❌ Reject**: Discards the draft.

### 🕵️ Manage Scouts (`/scouts`)
You can list and run your configured scouts directly from Telegram.

1.  Send the command `/scouts`.
2.  The bot will list your available scouts.
3.  Click **🚀 Run Scout** next to any scout to trigger it immediately.
    *   The scout will run in the background.
    *   Once finished, the bot will send you the generated draft for review.

### 🔄 Manual Check (`/check`)
If you think you missed a notification or want to force a check for pending drafts in the database:

1.  Send the command `/check`.
2.  The bot will query the database for any posts with `pending_review` status and send them to you.
