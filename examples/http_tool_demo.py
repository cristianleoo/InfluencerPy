#!/usr/bin/env python3
"""
Demo script for the HTTP Request tool.
This demonstrates how to use the http_request tool to fetch and parse web content.
"""

from influencerpy.tools.http_tool import http_request

def demo_basic_fetch():
    """Demonstrate basic URL fetching."""
    print("=" * 80)
    print("Demo 1: Basic URL Fetch")
    print("=" * 80)
    
    result = http_request(url="https://example.com")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Title: {result['title']}")
        print(f"✅ Content length: {len(result['content'])} characters")
        print(f"\nFirst 200 characters:\n{result['content'][:200]}...")
    
    print("\n")

def demo_with_selector():
    """Demonstrate fetching with CSS selector."""
    print("=" * 80)
    print("Demo 2: Fetch with CSS Selector")
    print("=" * 80)
    
    # Try to fetch just the main content from Wikipedia
    result = http_request(
        url="https://en.wikipedia.org/wiki/Web_scraping",
        selector="#mw-content-text"
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Title: {result['title']}")
        print(f"✅ Content length: {len(result['content'])} characters")
        print(f"\nFirst 300 characters:\n{result['content'][:300]}...")
    
    print("\n")

def demo_with_links():
    """Demonstrate link extraction."""
    print("=" * 80)
    print("Demo 3: Extract Links")
    print("=" * 80)
    
    result = http_request(
        url="https://news.ycombinator.com",
        extract_links=True
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Title: {result['title']}")
        print(f"✅ Found {len(result.get('links', []))} links")
        
        print("\nFirst 5 links:")
        for i, link in enumerate(result.get("links", [])[:5], 1):
            print(f"{i}. {link['text'][:50]}: {link['url']}")
    
    print("\n")

def demo_error_handling():
    """Demonstrate error handling."""
    print("=" * 80)
    print("Demo 4: Error Handling")
    print("=" * 80)
    
    # Try an invalid URL
    result = http_request(url="https://this-domain-definitely-does-not-exist-12345.com")
    
    if "error" in result:
        print(f"✅ Error handled gracefully: {result['error']}")
    else:
        print(f"❌ Expected an error but got: {result}")
    
    print("\n")

def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "HTTP Request Tool Demo" + " " * 36 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    demos = [
        ("Basic Fetch", demo_basic_fetch),
        ("CSS Selector", demo_with_selector),
        ("Link Extraction", demo_with_links),
        ("Error Handling", demo_error_handling),
    ]
    
    print("This demo will showcase different features of the http_request tool.\n")
    
    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"❌ Demo '{name}' failed with exception: {e}\n")
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print("\nThe http_request tool is now available to all your agents.")
    print("Add 'http_request' to the tools config when creating scouts.\n")

if __name__ == "__main__":
    main()
