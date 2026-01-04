"""
Example: RSS Entry Tracking - Preventing Duplicate Content

This example demonstrates how the RSS tracking system prevents
the LLM from seeing the same content repeatedly.
"""

from influencerpy.tools.rss import rss


def example_basic_workflow():
    """Basic workflow: read, process, mark, read again."""
    print("=" * 60)
    print("Example 1: Basic Workflow")
    print("=" * 60)
    
    # Step 1: Read unprocessed entries (first time)
    print("\n1. First read - getting all unprocessed entries...")
    results = rss(action="read_all", max_entries=5)
    
    if not results:
        print("No unprocessed entries found.")
        return
    
    print(f"Found {len(results)} feed(s) with unprocessed entries")
    
    # Collect entry IDs
    entry_ids = []
    for feed_result in results:
        print(f"\nFeed: {feed_result['feed_title']}")
        print(f"  Unprocessed entries: {feed_result['entry_count']}")
        
        for entry in feed_result['entries']:
            print(f"    - {entry['title'][:60]}...")
            entry_ids.append(entry['id'])
    
    # Step 2: Simulate LLM processing
    print(f"\n2. Processing {len(entry_ids)} entries with LLM...")
    # ... your LLM processing code here ...
    print("   (LLM processing complete)")
    
    # Step 3: Mark entries as processed
    print("\n3. Marking entries as processed...")
    result = rss(action="mark_processed", entry_ids=entry_ids)
    print(f"   {result['content'][0]['text']}")
    
    # Step 4: Read again - should get no entries (or only new ones)
    print("\n4. Reading again - should only get NEW entries...")
    results2 = rss(action="read_all", max_entries=5)
    
    if not results2:
        print("   ✓ No unprocessed entries - all have been processed!")
    else:
        print(f"   Found {len(results2)} feed(s) with new entries")
        for feed_result in results2:
            print(f"   - {feed_result['feed_title']}: {feed_result['entry_count']} new")


def example_incremental_processing():
    """Process entries incrementally, marking as you go."""
    print("\n" + "=" * 60)
    print("Example 2: Incremental Processing")
    print("=" * 60)
    
    print("\n1. Reading unprocessed entries...")
    results = rss(action="read_all", max_entries=10)
    
    if not results:
        print("No unprocessed entries found.")
        return
    
    # Process and mark entries one at a time
    print("\n2. Processing entries incrementally...")
    for feed_result in results:
        print(f"\nProcessing feed: {feed_result['feed_title']}")
        
        for entry in feed_result['entries']:
            print(f"  Processing: {entry['title'][:50]}...")
            
            # Process with LLM
            # ... your processing code ...
            
            # Mark this single entry as processed
            rss(action="mark_processed", entry_ids=[entry['id']])
            print(f"    ✓ Marked as processed")


def example_reset_for_testing():
    """Reset processed status for testing or re-processing."""
    print("\n" + "=" * 60)
    print("Example 3: Reset for Testing")
    print("=" * 60)
    
    # List feeds
    print("\n1. Listing feeds...")
    feeds = rss(action="list")
    
    if not feeds:
        print("No feeds found.")
        return
    
    print(f"Found {len(feeds)} feed(s)")
    for feed in feeds:
        print(f"  - {feed['title']}")
    
    # Reset first feed
    if feeds:
        feed_id = feeds[0]['feed_id']
        print(f"\n2. Resetting processed status for feed {feed_id}...")
        result = rss(action="reset_processed", feed_id=feed_id)
        print(f"   {result['content'][0]['text']}")
        
        # Now read will return all entries again
        print("\n3. Reading after reset...")
        result = rss(action="read", feed_id=feed_id, max_entries=5)
        print(f"   Entries available: {len(result['entries'])}")


def example_override_filter():
    """Override the filter to see all entries including processed."""
    print("\n" + "=" * 60)
    print("Example 4: Override Filter to See All Entries")
    print("=" * 60)
    
    # List feeds
    feeds = rss(action="list")
    if not feeds:
        print("No feeds found.")
        return
    
    feed_id = feeds[0]['feed_id']
    
    # Read only unprocessed (default)
    print(f"\n1. Reading unprocessed entries from feed {feed_id}...")
    result1 = rss(action="read", feed_id=feed_id, max_entries=10, only_unprocessed=True)
    print(f"   Unprocessed entries: {len(result1['entries'])}")
    
    # Read all entries (including processed)
    print(f"\n2. Reading ALL entries (including processed)...")
    result2 = rss(action="read", feed_id=feed_id, max_entries=10, only_unprocessed=False)
    print(f"   Total entries: {len(result2['entries'])}")
    
    print(f"\n   Processed entries: {len(result2['entries']) - len(result1['entries'])}")


def example_scout_integration():
    """Example of how a scout would use this system."""
    print("\n" + "=" * 60)
    print("Example 5: Scout Integration Pattern")
    print("=" * 60)
    
    print("\nScout workflow:")
    print("1. Scout runs on schedule (e.g., daily)")
    print("2. Reads unprocessed entries from subscribed feeds")
    print("3. LLM analyzes and curates content")
    print("4. Marks entries as processed")
    print("5. Sends report to Telegram")
    print("6. Next run only sees NEW entries")
    
    # Simulate scout run
    print("\n--- Scout Run #1 ---")
    results = rss(action="read_all", max_entries=5)
    
    if results:
        entry_ids = []
        for feed_result in results:
            print(f"Feed: {feed_result['feed_title']} - {feed_result['entry_count']} new entries")
            for entry in feed_result['entries']:
                entry_ids.append(entry['id'])
        
        # Mark as processed
        rss(action="mark_processed", entry_ids=entry_ids)
        print(f"\nProcessed {len(entry_ids)} entries")
    
    print("\n--- Scout Run #2 (next day) ---")
    results = rss(action="read_all", max_entries=5)
    
    if not results:
        print("No new entries since last run")
    else:
        print(f"Found {len(results)} feed(s) with new entries")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RSS Entry Tracking Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_workflow()
        example_incremental_processing()
        example_reset_for_testing()
        example_override_filter()
        example_scout_integration()
        
        print("\n" + "=" * 60)
        print("Examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have:")
        print("1. Initialized the database: influencerpy init")
        print("2. Subscribed to some RSS feeds")
        print("3. Run update to fetch entries: rss(action='update')")
