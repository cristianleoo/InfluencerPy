# RSS Entry Processing Tracking

## Problem

Previously, the RSS tool would return all entries every time it was called, causing the LLM to see the same content repeatedly. This resulted in:

- Duplicate content being presented to the LLM
- Inefficient processing of already-seen entries
- Potential confusion in scout reports
- Wasted API calls and processing time

## Solution

We've implemented a **processing tracking system** that marks RSS entries as "processed" after they've been presented to the LLM. This ensures that only new, unseen entries are returned in subsequent calls.

### Key Features

1. **Automatic Filtering**: By default, `read` and `read_all` actions only return unprocessed entries
2. **Manual Marking**: Entries can be marked as processed using the `mark_processed` action
3. **Flexible Control**: You can override the filtering to see all entries if needed
4. **Reset Capability**: For testing or re-processing, you can reset the processed status

## Database Schema Changes

Two new fields were added to the `RSSEntryModel`:

```python
is_processed: bool = Field(default=False, index=True)
processed_at: Optional[datetime] = None
```

- `is_processed`: Boolean flag indicating if the entry has been presented to the LLM
- `processed_at`: Timestamp of when the entry was marked as processed

## Usage

### Reading Unprocessed Entries (Default Behavior)

```python
from influencerpy.tools.rss import rss

# Read only unprocessed entries from a specific feed
result = rss(
    action="read",
    feed_id="1",
    max_entries=10,
    only_unprocessed=True  # This is the default
)

# Read unprocessed entries from all feeds
results = rss(
    action="read_all",
    max_entries=5,  # Per feed
    only_unprocessed=True  # This is the default
)
```

### Marking Entries as Processed

After the LLM processes entries, mark them to prevent re-processing:

```python
# Get entry IDs from the read results
entry_ids = [entry["id"] for entry in result["entries"]]

# Mark them as processed
rss(
    action="mark_processed",
    entry_ids=entry_ids
)
```

### Reading All Entries (Including Processed)

If you need to see all entries regardless of processing status:

```python
result = rss(
    action="read",
    feed_id="1",
    max_entries=10,
    only_unprocessed=False  # Override default
)
```

### Resetting Processed Status

For testing or re-processing:

```python
# Reset specific feed
rss(
    action="reset_processed",
    feed_id="1"
)

# Reset all feeds
rss(
    action="reset_processed"
)
```

## Complete Workflow Example

Here's a typical workflow for a scout:

```python
from influencerpy.tools.rss import rss

# 1. Read unprocessed entries
results = rss(
    action="read_all",
    max_entries=10,
    include_content=True,
    only_unprocessed=True
)

# 2. Process entries with LLM
processed_entry_ids = []
for feed_result in results:
    for entry in feed_result["entries"]:
        # LLM processes the entry
        process_with_llm(entry)
        processed_entry_ids.append(entry["id"])

# 3. Mark entries as processed
if processed_entry_ids:
    rss(
        action="mark_processed",
        entry_ids=processed_entry_ids
    )

# 4. Next time you call read_all, these entries won't appear
```

## Migration

The database migration runs automatically when you start InfluencerPy. For existing databases:

1. The migration adds the new fields to the `rss_entries` table
2. Existing entries are marked as `is_processed=False` by default
3. An index is created on `is_processed` for query performance

### Manual Migration

If you need to run the migration manually:

```python
from influencerpy.migrations import run_all_migrations

run_all_migrations()
```

## API Reference

### New RSS Tool Actions

#### `mark_processed`

Mark entries as processed to prevent them from appearing in future reads.

**Parameters:**
- `entry_ids` (List[int], required): List of entry IDs to mark

**Returns:**
```python
{
    "status": "success",
    "content": [{"text": "Marked N entries as processed"}],
    "marked_count": N
}
```

#### `reset_processed`

Reset processed status for entries (useful for testing).

**Parameters:**
- `feed_id` (str, optional): Feed ID to reset, or omit to reset all feeds

**Returns:**
```python
{
    "status": "success",
    "content": [{"text": "Reset N entries"}],
    "reset_count": N
}
```

### Modified Actions

#### `read` and `read_all`

**New Parameter:**
- `only_unprocessed` (bool, default=True): If True, only return unprocessed entries

**Entry Response Changes:**
- Each entry now includes an `id` field for use with `mark_processed`

## Performance Considerations

1. **Indexed Field**: The `is_processed` field is indexed for fast filtering
2. **Efficient Queries**: Only unprocessed entries are fetched from the database
3. **Batch Marking**: Multiple entries can be marked in a single operation

## Testing

Comprehensive tests are available in `tests/test_rss_processing.py`:

```bash
# Run RSS processing tests
uv run pytest tests/test_rss_processing.py -v

# Run all RSS tests
uv run pytest tests/test_rss*.py -v
```

## Backward Compatibility

- Existing code continues to work without changes
- The default behavior now filters unprocessed entries (more useful)
- To get the old behavior, set `only_unprocessed=False`
- Existing entries in the database are treated as unprocessed by default

## Future Enhancements

Potential improvements for the future:

1. **Automatic Marking**: Automatically mark entries as processed after LLM processing
2. **Expiration**: Auto-reset processed status after a certain time period
3. **Per-Scout Tracking**: Track processing status per scout (if multiple scouts use the same feed)
4. **Processing Metadata**: Store additional metadata about how entries were processed
