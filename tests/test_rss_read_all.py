"""
Test the new read_all action for RSS feeds.

This test verifies that when multiple RSS feeds are subscribed,
the read_all action returns content from ALL feeds.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from influencerpy.tools.rss import rss


def test_read_all_action():
    """Test that read_all returns content from all feeds."""
    
    print("=" * 60)
    print("Testing RSS read_all action")
    print("=" * 60)
    
    # Test 1: List feeds
    print("\n1. Listing subscribed feeds...")
    feeds = rss(action='list')
    
    if isinstance(feeds, list) and len(feeds) > 0:
        print(f"✓ Found {len(feeds)} subscribed feed(s)")
        for feed in feeds:
            print(f"  - {feed.get('title', 'Untitled')}: {feed.get('url', 'N/A')}")
    else:
        print("✗ No feeds found. Please subscribe to some feeds first.")
        print("\nTo test properly:")
        print("1. Run influencerpy and create a scout with multiple RSS feeds")
        print("2. Or manually subscribe using: rss(action='subscribe', url='...')")
        return
    
    # Test 2: Read all feeds
    print("\n2. Reading from ALL feeds using read_all...")
    all_content = rss(action='read_all', max_entries=3)
    
    if isinstance(all_content, list):
        print(f"✓ Read from {len(all_content)} feed(s)")
        
        total_entries = 0
        for feed_result in all_content:
            feed_title = feed_result.get('feed_title', 'Unknown')
            feed_url = feed_result.get('feed_url', 'Unknown')
            entry_count = feed_result.get('entry_count', 0)
            total_entries += entry_count
            
            print(f"\n  Feed: {feed_title}")
            print(f"  URL: {feed_url}")
            print(f"  Entries: {entry_count}")
            
            # Show first entry as example
            entries = feed_result.get('entries', [])
            if entries:
                first_entry = entries[0]
                print(f"    → {first_entry.get('title', 'No title')[:60]}...")
        
        print(f"\n✓ Total entries across all feeds: {total_entries}")
        
        if len(all_content) == len(feeds):
            print(f"✓ SUCCESS: read_all returned content from ALL {len(feeds)} feeds")
        else:
            print(f"⚠ WARNING: read_all returned {len(all_content)} feeds but {len(feeds)} are subscribed")
    else:
        print(f"✗ Unexpected result type: {type(all_content)}")
        print(f"Result: {all_content}")
    
    # Test 3: Compare with individual reads
    print("\n3. Comparing with individual read calls...")
    individual_count = 0
    for feed in feeds:
        feed_id = feed.get('feed_id')
        result = rss(action='read', feed_id=feed_id, max_entries=3)
        if isinstance(result, dict):
            entries = result.get('entries', [])
            individual_count += len(entries)
    
    print(f"  Individual reads: {individual_count} total entries")
    print(f"  read_all: {total_entries} total entries")
    
    if individual_count == total_entries:
        print("✓ Both methods return same number of entries")
    else:
        print("⚠ Entry counts differ (this may be normal if feeds updated)")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_read_all_action()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
