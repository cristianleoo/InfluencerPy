# Scout Scheduler

The Scout Scheduler is the heartbeat of InfluencerPy's automation. It ensures your scouts run automatically at their configured times, fetching content and generating drafts even when you're away.

## How it Works

The scheduler is built on top of `APScheduler` and runs alongside the Telegram bot when you execute:

```bash
influencerpy bot
```

It loads all your Scouts from the database and schedules them based on their Cron expressions.

## Configuration

When creating or updating a Scout, you can choose from several scheduling options:

*   **Daily**: Runs every day at a specific time (e.g., 09:00 AM).
*   **Hourly**: Runs at the top of every hour.
*   **Weekly**: Runs on specific days of the week.
*   **Interval**: Runs every X hours.
*   **Custom Cron**: For advanced users, you can provide a standard Cron expression (e.g., `0 12 * * 1-5` for weekdays at noon).

## Monitoring

You can monitor the scheduler's activity using the logs command:

```bash
influencerpy logs -f
```

You will see messages like:
```
INFO - Scheduled scout 'Daily AI' with cron: 0 9 * * *
INFO - Executing scheduled run for scout: Daily AI
INFO - Generated and saved draft for Daily AI: Top 10 AI Trends
```

## Review Workflow

When a scheduled scout finds content:
1.  It generates a draft post using your configured AI model.
2.  It saves the draft to the database with a status of `pending_review`.
3.  The Telegram Bot detects the new draft and sends you a notification with "Approve" and "Reject" buttons.
