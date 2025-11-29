import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import feedparser
import html2text
import requests
from strands import tool
from sqlmodel import select

from influencerpy.database import get_session
from influencerpy.types.rss import RSSFeedModel, RSSEntryModel

# Configure logging
logger = logging.getLogger(__name__)

# Defaults
DEFAULT_MAX_ENTRIES = 100
DEFAULT_UPDATE_INTERVAL = 60  # minutes

# Create HTML to text converter
html_converter = html2text.HTML2Text()
html_converter.ignore_links = False
html_converter.ignore_images = True
html_converter.body_width = 0

class RSSManager:
    """Manage RSS feed subscriptions, updates, and content retrieval via Database."""

    def __init__(self):
        pass

    def clean_html(self, html_content: str) -> str:
        return "" if not html_content else html_converter.handle(html_content)

    def format_entry(self, entry: Dict, include_content: bool = False) -> Dict:
        result = {
            "title": entry.get("title", "Untitled"),
            "link": entry.get("link", ""),
            "published": entry.get("published", entry.get("updated", "Unknown date")),
            "author": entry.get("author", "Unknown author"),
        }

        # Add categories
        if "tags" in entry:
            result["categories"] = [tag.get("term", "") for tag in entry.tags if "term" in tag]
        elif "categories" in entry:
            result["categories"] = entry.get("categories", [])

        # Add content if requested
        if include_content:
            content = ""
            # Handle content as both attribute and dictionary key
            if "content" in entry:
                # Handle dictionary access
                if isinstance(entry["content"], list):
                    for item in entry["content"]:
                        if isinstance(item, dict) and "value" in item:
                            content = self.clean_html(item["value"])
                            break
                # Handle string content directly
                elif isinstance(entry["content"], str):
                    content = self.clean_html(entry["content"])
            # Handle summary and description fields
            if not content and "summary" in entry:
                content = self.clean_html(entry["summary"])
            if not content and "description" in entry:
                content = self.clean_html(entry["description"])
            result["content"] = content or "No content available"

        return result

    def fetch_feed(self, url: str, auth: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        # Initialize headers dictionary if not provided
        if headers is None:
            headers = {}
        # Handle case where headers might be a string
        elif isinstance(headers, str):
            headers = {"User-Agent": headers}

        # If using basic auth
        if auth and auth.get("type") == "basic":
            response = requests.get(url, headers=headers, auth=(auth.get("username", ""), auth.get("password", "")))
            return feedparser.parse(response.content)

        # For non-auth requests
        user_agent = headers.get("User-Agent")
        return feedparser.parse(url, agent=user_agent)

    def subscribe(self, url: str, update_interval: int = DEFAULT_UPDATE_INTERVAL, auth: Dict = None, headers: Dict = None) -> Dict:
        with next(get_session()) as session:
            # Check if already exists
            existing = session.exec(select(RSSFeedModel).where(RSSFeedModel.url == url)).first()
            if existing:
                 return {"status": "error", "content": [{"text": f"Already subscribed to feed: {url} (ID: {existing.id})"}]}

            # Fetch first to validate and get title
            try:
                feed_data = self.fetch_feed(url, auth, headers)
                if not hasattr(feed_data, "entries"):
                     return {"status": "error", "content": [{"text": f"Could not parse feed from {url}"}]}
                
                title = getattr(feed_data.feed, "title", url)
            except Exception as e:
                return {"status": "error", "content": [{"text": f"Error fetching feed: {e}"}]}

            new_feed = RSSFeedModel(
                url=url,
                title=title,
                update_interval=update_interval,
                auth_json=json.dumps(auth) if auth else None,
                headers_json=json.dumps(headers) if headers else None,
                added_at=datetime.utcnow()
            )
            session.add(new_feed)
            session.commit()
            session.refresh(new_feed)
            
            # Initial update
            self.update_feed(new_feed.id)

            return {
                "status": "success",
                "content": [{"text": f"Subscribed to: {title} with ID: {new_feed.id}"}],
            }

    def unsubscribe(self, feed_id: int) -> Dict:
        with next(get_session()) as session:
            feed = session.get(RSSFeedModel, feed_id)
            if not feed:
                return {"status": "error", "content": [{"text": f"Feed {feed_id} not found"}]}
            
            # Delete entries first (though cascade should handle it if configured, explicit is safer without cascade setup)
            entries = session.exec(select(RSSEntryModel).where(RSSEntryModel.feed_id == feed_id)).all()
            for entry in entries:
                session.delete(entry)
                
            session.delete(feed)
            session.commit()
            
            return {
                "status": "success",
                "content": [{"text": f"Unsubscribed from: {feed.title}"}],
            }

    def list_feeds(self) -> List[Dict]:
        with next(get_session()) as session:
            feeds = session.exec(select(RSSFeedModel)).all()
            return [
                {
                    "feed_id": str(f.id),
                    "title": f.title,
                    "url": f.url,
                    "last_updated": str(f.last_updated) if f.last_updated else "Never",
                    "update_interval": f.update_interval,
                }
                for f in feeds
            ]

    def update_feed(self, feed_id: int) -> Dict:
        with next(get_session()) as session:
            feed = session.get(RSSFeedModel, feed_id)
            if not feed:
                return {"status": "error", "content": [{"text": f"Feed {feed_id} not found"}]}
            
            try:
                auth = json.loads(feed.auth_json) if feed.auth_json else None
                headers = json.loads(feed.headers_json) if feed.headers_json else None
                
                fetched = self.fetch_feed(feed.url, auth, headers)
                if not hasattr(fetched, "entries"):
                     return {"status": "error", "content": [{"text": f"Could not parse feed"}]}

                # Update feed metadata
                feed.title = getattr(fetched.feed, "title", feed.url)
                feed.last_updated = datetime.utcnow()
                session.add(feed)

                # Process entries
                new_count = 0
                total_count = 0
                
                # Get existing entry IDs to avoid duplicates
                existing_ids = session.exec(select(RSSEntryModel.entry_id).where(RSSEntryModel.feed_id == feed_id)).all()
                existing_set = set(existing_ids)

                for entry in fetched.entries:
                    entry_id = entry.get("id", entry.get("link"))
                    if entry_id and entry_id not in existing_set:
                        formatted = self.format_entry(entry, include_content=True)
                        
                        new_entry = RSSEntryModel(
                            feed_id=feed_id,
                            entry_id=entry_id,
                            title=formatted["title"],
                            link=formatted["link"],
                            # published logic... feedparser parses dates to structs, we might need conversion
                            # simplified for now using string or raw if compatible, otherwise datetime conversion needed
                            # format_entry returns string for published.
                            # Let's assume format_entry returns something we can use or adapt.
                            # format_entry returns "Unknown date" if missing.
                            # Models expect datetime. We should try to parse or use current time if fail.
                            author=formatted["author"],
                            summary=entry.get("summary", ""),
                            content=formatted.get("content", ""),
                            categories_json=json.dumps(formatted.get("categories", [])),
                            created_at=datetime.utcnow()
                        )
                        
                        # Handle date parsing if needed
                        try:
                            # feedparser often gives struct_time in 'published_parsed'
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                new_entry.published = datetime(*entry.published_parsed[:6])
                            else:
                                new_entry.published = datetime.utcnow() 
                        except:
                            new_entry.published = datetime.utcnow()

                        session.add(new_entry)
                        new_count += 1
                    
                    total_count += 1

                session.commit()
                
                return {
                    "feed_id": str(feed_id),
                    "title": feed.title,
                    "new_entries": new_count,
                    "total_entries": total_count,
                }

            except Exception as e:
                logger.error(f"Error updating feed {feed_id}: {e}")
                return {"status": "error", "content": [{"text": f"Error updating feed: {e}"}]}

    def read_feed(self, feed_id: int, max_entries: int = 10, category: str = None, include_content: bool = False) -> Dict:
        with next(get_session()) as session:
            feed = session.get(RSSFeedModel, feed_id)
            if not feed:
                return {"status": "error", "content": [{"text": f"Feed {feed_id} not found"}]}
            
            query = select(RSSEntryModel).where(RSSEntryModel.feed_id == feed_id).order_by(RSSEntryModel.published.desc())
            entries = session.exec(query).all()
            
            # Filter by category in python (JSON storage)
            filtered_entries = []
            for entry in entries:
                if category:
                    cats = json.loads(entry.categories_json) if entry.categories_json else []
                    if not any(category.lower() == c.lower() for c in cats):
                        continue
                
                entry_dict = {
                    "title": entry.title,
                    "link": entry.link,
                    "published": str(entry.published),
                    "author": entry.author,
                    "summary": entry.summary,
                    "categories": json.loads(entry.categories_json) if entry.categories_json else []
                }
                if include_content:
                    entry_dict["content"] = entry.content
                
                filtered_entries.append(entry_dict)
                if len(filtered_entries) >= max_entries:
                    break
            
            return {
                "feed_id": str(feed_id),
                "title": feed.title,
                "entries": filtered_entries,
            }

    def search(self, query_text: str, max_entries: int = 10, include_content: bool = False) -> List[Dict]:
        # Simple search implementation (sqlite LIKE)
        with next(get_session()) as session:
            # This is a basic search. Full text search would be better.
            statement = select(RSSEntryModel).where(
                (RSSEntryModel.title.contains(query_text)) | 
                (RSSEntryModel.content.contains(query_text))
            ).limit(max_entries)
            
            entries = session.exec(statement).all()
            results = []
            for entry in entries:
                res = {
                    "feed_id": str(entry.feed_id),
                    "title": entry.title,
                    "link": entry.link
                }
                if include_content:
                    res["content"] = entry.content
                results.append(res)
                
            return results if results else {"status": "error", "content": [{"text": f"No entries found for '{query_text}'"}]}


# Initialize RSS manager
rss_manager = RSSManager()


@tool
def rss(
    action: str,
    url: Optional[str] = None,
    feed_id: Optional[str] = None,
    max_entries: int = 10,
    include_content: bool = False,
    query: Optional[str] = None,
    category: Optional[str] = None,
    update_interval: Optional[int] = None,
    auth_username: Optional[str] = None,
    auth_password: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Union[List[Dict], Dict]:
    """
    Interact with RSS feeds - fetch, subscribe, search, and manage feeds via Database.

    Actions:
    - fetch: Get feed content from URL without subscribing
    - subscribe: Add a feed to your subscription list
    - unsubscribe: Remove a feed subscription
    - list: List all subscribed feeds
    - read: Read entries from a subscribed feed
    - update: Update feeds with new content
    - search: Find entries matching a query
    # - categories: List all categories/tags (Not implemented in DB version yet)

    Args:
        action: Action to perform
        url: URL of the RSS feed
        feed_id: ID of a subscribed feed
        max_entries: Maximum number of entries to return
        include_content: Whether to include full content
        query: Search query
        category: Filter entries by category
    """
    try:
        if action == "fetch":
            if not url:
                return {"status": "error", "content": [{"text": "URL is required for fetch action"}]}
            
            feed = rss_manager.fetch_feed(url, headers=headers)
            if not hasattr(feed, "entries"):
                 return {"status": "error", "content": [{"text": "Could not parse feed"}]}
            
            entries = [rss_manager.format_entry(entry, include_content) for entry in feed.entries[:max_entries]]
            return entries

        elif action == "subscribe":
            if not url:
                return {"status": "error", "content": [{"text": "URL is required for subscribe"}]}
            
            auth = None
            if auth_username and auth_password:
                auth = {"type": "basic", "username": auth_username, "password": auth_password}
            
            return rss_manager.subscribe(url, update_interval or DEFAULT_UPDATE_INTERVAL, auth, headers)

        elif action == "unsubscribe":
            if not feed_id:
                 return {"status": "error", "content": [{"text": "feed_id is required"}]}
            return rss_manager.unsubscribe(int(feed_id))

        elif action == "list":
            return rss_manager.list_feeds()

        elif action == "read":
            if not feed_id:
                 return {"status": "error", "content": [{"text": "feed_id is required"}]}
            return rss_manager.read_feed(int(feed_id), max_entries, category, include_content)

        elif action == "update":
            if feed_id:
                return rss_manager.update_feed(int(feed_id))
            else:
                # Update all
                with next(get_session()) as session:
                    ids = session.exec(select(RSSFeedModel.id)).all()
                    return [rss_manager.update_feed(fid) for fid in ids]

        elif action == "search":
            if not query:
                 return {"status": "error", "content": [{"text": "query is required"}]}
            return rss_manager.search(query, max_entries, include_content)

        else:
            return {"status": "error", "content": [{"text": f"Unknown action: {action}"}]}

    except Exception as e:
        logger.error(f"RSS tool error: {e}")
        return {"status": "error", "content": [{"text": str(e)}]}
