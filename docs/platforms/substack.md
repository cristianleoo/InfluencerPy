# Substack Platform Integration

InfluencerPy provides integration with Substack as a content source, allowing you to monitor newsletters and use them as inspiration for your own content.

## Features

### As a Content Source (Scout)
- Monitor any public Substack newsletter
- Filter by sorting (new/top posts)
- Access paywalled content from newsletters you subscribe to
- Automatic content extraction and summarization
- Generate content inspired by Substack posts

## Setup for Reading Substack Content

### Optional: Authentication for Paywalled Content

If you want to read paywalled content from newsletters you subscribe to, you'll need to provide authentication:

1. Log into your Substack account in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies
4. Find and copy these cookies:
   - `substack.sid`
   - `substack.lli`
5. Add them to your `.influencerpy/.env` file:

```bash
SUBSTACK_SUBDOMAIN=your-subdomain
SUBSTACK_SID=your_sid_value_here
SUBSTACK_LLI=your_lli_value_here
```

**Note**: These cookies may expire and need to be refreshed periodically.

## Using Substack as a Scout

Create a Substack Scout to monitor newsletters:

```bash
influencerpy scouts
# Select "Create Scout"
# Choose "📰 Substack (Follow newsletters)"
```

## Workflow for Substack-Inspired Content

1. **Create a scout** that monitors Substack newsletters
2. **Set platform to "Telegram"** when configuring output channels
3. **Scout runs** and generates drafts based on Substack content
4. **Review drafts in Telegram** - edit if needed
5. **Click ✅ Confirm** to mark as ready
6. **Manually copy/paste** the content to your Substack publication and publish

### Why Manual Publishing?

Substack's API doesn't support automated draft creation for security reasons. This manual workflow ensures you have full control over what gets published while still benefiting from automated content discovery and draft generation.

## Example Scout Configuration

```yaml
Scout Name: Weekly AI Substack
Type: Substack
URL: https://example.substack.com
Platforms: ["telegram"]
Schedule: Weekly (every Monday)
```

When this scout runs:
1. It monitors the specified Substack newsletter
2. Generates a draft based on recent posts
3. Sends the draft to your Telegram for review
4. You copy/paste the approved draft to your own Substack

## Additional Resources

- [Scout Concepts](../concepts/scouts.md) - Understanding scouts
- [Telegram Channel](../channels/telegram.md) - Setting up Telegram bot
- [Scheduling](../concepts/scheduling.md) - Automating scouts
