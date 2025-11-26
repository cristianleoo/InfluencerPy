# Scheduling

InfluencerPy includes a powerful **Schedule Builder** to help you plan when your Scouts should run.

## Configuration

When creating or updating a Scout, you can assign a schedule using the interactive wizard.

### The Schedule Builder

You don't need to know complex cron syntax. The CLI offers an easy-to-use menu:

1.  **Daily**: Select specific hours (e.g., `09:00`, `18:00`).
2.  **Weekly**: Select specific days and time (e.g., `Monday` and `Friday` at `10:00`).
3.  **Monthly**: Run on a specific day of the month.
4.  **Interval**: Run every X hours.
5.  **Advanced**: Manually enter a cron string (e.g., `0 12 * * 1`).

## Execution

Currently, the schedule configuration is stored as metadata attached to your Scout.

> **Note**: The background daemon that automatically executes Scouts based on this schedule is currently in development.

### Recommended Workflow (Current)

For now, we recommend running your Scouts manually via the CLI when you are ready to review content:

```bash
influencerpy
# Select "Manage Scouts" -> "Run Scout"
```

Or, for automation experts, you can use your system's `cron` or `launchd` to trigger the CLI command (feature coming soon: `influencerpy run scout-name`).
