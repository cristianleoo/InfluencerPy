# Substack Platform Integration

InfluencerPy provides comprehensive integration with Substack, allowing you to both monitor newsletters and publish content to your own Substack publication.

## Features

### As a Content Source (Scout)
- Monitor any public Substack newsletter
- Filter by sorting (new/top posts)
- Access paywalled content from newsletters you subscribe to
- Automatic content extraction and summarization

### As a Posting Platform
- Create draft posts directly from CLI
- Automatic title extraction from content
- HTML formatting support
- Secure cookie-based authentication

## Setup

For detailed setup instructions, see the [Substack Setup Guide](../../SUBSTACK_SETUP.md).

## Using Substack as a Scout

Create a Substack Scout to monitor newsletters:

```bash
influencerpy scouts
# Select "Create Scout"
# Choose "📰 Substack (Follow newsletters)"
```

## Using Substack as a Posting Platform

Select "Substack" when choosing posting platforms for your scouts.

**Note**: Substack posts are created as drafts for manual review and publishing.

## Additional Resources

- [Substack Setup Guide](../../SUBSTACK_SETUP.md) - Detailed authentication
- [Scout Concepts](../concepts/scouts.md) - Understanding scouts
- [Scheduling](../concepts/scheduling.md) - Automating scouts
