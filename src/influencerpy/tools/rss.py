import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import feedparser
import html2text
import requests
from sqlmodel import select
from strands import tool

from influencerpy.database import get_session
from influencerpy.types.rss import RSSEntryModel, RSSFeedModel
from influencerpy.core.embeddings import EmbeddingManager

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
    """Manage RSS feed subscriptions, updates, and content retrieval via Database.
    
    Includes embedding-based duplicate detection to prevent returning the same content."""

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
            result["categories"] = [
                tag.get("term", "") for tag in entry.tags if "term" in tag
            ]
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

    def fetch_feed(
        self, url: str, auth: Optional[Dict] = None, headers: Optional[Dict] = None
    ) -> Dict:
        # Initialize headers dictionary if not provided
        if headers is None:
            headers = {}
        # Handle case where headers might be a string
        elif isinstance(headers, str):
            headers = {"User-Agent": headers}

        # If using basic auth
        if auth and auth.get("type") == "basic":
            response = requests.get(
                url,
                headers=headers,
                auth=(auth.get("username", ""), auth.get("password", "")),
            )
            return feedparser.parse(response.content)

        # For non-auth requests
        user_agent = headers.get("User-Agent")
        return feedparser.parse(url, agent=user_agent)

    def subscribe(
        self,
        url: str,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        auth: Dict = None,
        headers: Dict = None,
        scout_id: Optional[int] = None,
    ) -> Dict:
        with next(get_session()) as session:
            # Check if feed already exists (by URL alone, since URL has UNIQUE constraint)
            existing = session.exec(
                select(RSSFeedModel).where(RSSFeedModel.url == url)
            ).first()
            
            if existing:
                # Use the existing feed instead of creating a new one
                scout_info = f" for scout {existing.scout_id}" if existing.scout_id else ""
                return {
                    "status": "success",
                    "content": [
                        {
                            "text": f"Using existing feed: {existing.title} (ID: {existing.id}){scout_info}"
                        }
                    ],
                }

            # Fetch first to validate and get title
            try:
                feed_data = self.fetch_feed(url, auth, headers)
                if not hasattr(feed_data, "entries"):
                    return {
                        "status": "error",
                        "content": [{"text": f"Could not parse feed from {url}"}],
                    }

                title = getattr(feed_data.feed, "title", url)
            except Exception as e:
                return {
                    "status": "error",
                    "content": [{"text": f"Error fetching feed: {e}"}],
                }

            new_feed = RSSFeedModel(
                url=url,
                title=title,
                scout_id=scout_id,  # Link to scout
                update_interval=update_interval,
                auth_json=json.dumps(auth) if auth else None,
                headers_json=json.dumps(headers) if headers else None,
                added_at=datetime.utcnow(),
            )
            session.add(new_feed)
            session.commit()
            session.refresh(new_feed)

            # Initial update
            self.update_feed(new_feed.id)

            scout_info = f" for scout {scout_id}" if scout_id else ""
            return {
                "status": "success",
                "content": [{"text": f"Subscribed to: {title} with ID: {new_feed.id}{scout_info}"}],
            }

    def unsubscribe(self, feed_id: int) -> Dict:
        with next(get_session()) as session:
            feed = session.get(RSSFeedModel, feed_id)
            if not feed:
                return {
                    "status": "error",
                    "content": [{"text": f"Feed {feed_id} not found"}],
                }

            # Delete entries first (though cascade should handle it if configured, explicit is safer without cascade setup)
            entries = session.exec(
                select(RSSEntryModel).where(RSSEntryModel.feed_id == feed_id)
            ).all()
            for entry in entries:
                session.delete(entry)

            session.delete(feed)
            session.commit()

            return {
                "status": "success",
                "content": [{"text": f"Unsubscribed from: {feed.title}"}],
            }

    def list_feeds(self, scout_id: Optional[int] = None) -> List[Dict]:
        """List RSS feeds, optionally filtered by scout_id."""
        with next(get_session()) as session:
            query = select(RSSFeedModel)
            if scout_id is not None:
                # Only show feeds for this specific scout
                query = query.where(RSSFeedModel.scout_id == scout_id)
            feeds = session.exec(query).all()
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
                return {
                    "status": "error",
                    "content": [{"text": f"Feed {feed_id} not found"}],
                }

            try:
                auth = json.loads(feed.auth_json) if feed.auth_json else None
                headers = json.loads(feed.headers_json) if feed.headers_json else None

                fetched = self.fetch_feed(feed.url, auth, headers)
                if not hasattr(fetched, "entries"):
                    return {
                        "status": "error",
                        "content": [{"text": f"Could not parse feed"}],
                    }

                # Update feed metadata
                feed.title = getattr(fetched.feed, "title", feed.url)
                feed.last_updated = datetime.utcnow()
                session.add(feed)

                # Process entries
                new_entries_list = []
                total_count = 0

                # Get existing entry IDs to avoid duplicates
                existing_ids = session.exec(
                    select(RSSEntryModel.entry_id).where(
                        RSSEntryModel.feed_id == feed_id
                    )
                ).all()
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
                            author=formatted["author"],
                            summary=entry.get("summary", ""),
                            content=formatted.get("content", ""),
                            categories_json=json.dumps(formatted.get("categories", [])),
                            created_at=datetime.utcnow(),
                        )

                        # Handle date parsing
                        try:
                            if (
                                hasattr(entry, "published_parsed")
                                and entry.published_parsed
                            ):
                                new_entry.published = datetime(
                                    *entry.published_parsed[:6]
                                )
                            else:
                                new_entry.published = datetime.utcnow()
                        except:
                            new_entry.published = datetime.utcnow()

                        session.add(new_entry)
                        
                        # Add to return list
                        entry_dict = {
                            "id": entry_id, # return the feed's ID for the entry
                            "title": formatted["title"],
                            "link": formatted["link"],
                            "published": str(new_entry.published),
                            "author": formatted["author"],
                            "summary": new_entry.summary,
                            "categories": formatted.get("categories", []),
                            "content": new_entry.content
                        }
                        new_entries_list.append(entry_dict)

                    total_count += 1

                session.commit()

                return {
                    "feed_id": str(feed_id),
                    "title": feed.title,
                    "new_entries_count": len(new_entries_list),
                    "total_entries": total_count,
                    "entries": new_entries_list
                }

            except Exception as e:
                logger.error(f"Error updating feed {feed_id}: {e}")
                return {
                    "status": "error",
                    "content": [{"text": f"Error updating feed: {e}"}],
                }

    def read_feed(
        self,
        feed_id: int,
        max_entries: int = 10,
        category: str = None,
        include_content: bool = False,
        only_unprocessed: bool = True,
    ) -> Dict:
        with next(get_session()) as session:
            feed = session.get(RSSFeedModel, feed_id)
            if not feed:
                return {
                    "status": "error",
                    "content": [{"text": f"Feed {feed_id} not found"}],
                }

            query = (
                select(RSSEntryModel)
                .where(RSSEntryModel.feed_id == feed_id)
            )
            
            # Filter for unprocessed entries by default
            if only_unprocessed:
                query = query.where(RSSEntryModel.is_processed == False)
            
            query = query.order_by(RSSEntryModel.published.desc())
            entries = session.exec(query).all()

            # Initialize embedding manager for duplicate detection
            embedding_manager = EmbeddingManager()

            # Filter by category and check embeddings in python
            filtered_entries = []
            for entry in entries:
                if category:
                    cats = (
                        json.loads(entry.categories_json)
                        if entry.categories_json
                        else []
                    )
                    if not any(category.lower() == c.lower() for c in cats):
                        continue

                # Check for duplicates using embeddings (on content side)
                content_text = f"{entry.title} {entry.summary or ''}"
                if embedding_manager.is_similar(content_text):
                    logger.debug(f"Skipping duplicate RSS entry: {entry.title}")
                    continue

                entry_dict = {
                    "id": entry.id,  # Include entry ID for marking as processed
                    "title": entry.title,
                    "link": entry.link,
                    "published": str(entry.published),
                    "author": entry.author,
                    "summary": entry.summary,
                    "categories": (
                        json.loads(entry.categories_json)
                        if entry.categories_json
                        else []
                    ),
                }
                if include_content:
                    entry_dict["content"] = entry.content

                # Index the content to prevent future duplicates
                embedding_manager.add_item(content_text, source_type="retrieved")

                filtered_entries.append(entry_dict)
                if len(filtered_entries) >= max_entries:
                    break

            return {
                "feed_id": str(feed_id),
                "title": feed.title,
                "entries": filtered_entries,
            }

    def read_all_feeds(
        self,
        scout_id: Optional[int] = None,
        max_entries_per_feed: int = 5,
        include_content: bool = False,
        only_unprocessed: bool = True,
    ) -> List[Dict]:
        """
        Fetch updates from ALL subscribed feeds and return the NEW entries.
        
        Args:
            scout_id: Optional scout ID to filter feeds
            max_entries_per_feed: Ignored for now as we return all NEW entries from the update
            include_content: Whether to include full content (default True in update_feed but checked here)
            only_unprocessed: Ignored, as we fundamentally return "new" entries which are naturally unprocessed
            
        Returns:
            List of dicts, each with feed info and its NEW entries
        """
        # Initialize embedding manager for duplicate detection on the result
        embedding_manager = EmbeddingManager()
        
        with next(get_session()) as session:
            query = select(RSSFeedModel)
            if scout_id is not None:
                query = query.where(RSSFeedModel.scout_id == scout_id)
            
            feeds = session.exec(query).all()
            results = []
            
            for feed in feeds:
                # Update the feed and get new entries
                update_result = self.update_feed(feed.id)
                
                if "entries" in update_result and update_result["entries"]:
                    new_entries = update_result["entries"]
                    
                    # Filter/Format entries
                    formatted_entries = []
                    for entry in new_entries:
                        # Check for duplicates using embeddings (on content side)
                        # Even though they are "new" to the DB, they might be semantically similar to others
                        content_text = f"{entry['title']} {entry['summary'] or ''}"
                        if embedding_manager.is_similar(content_text):
                            logger.debug(f"Skipping duplicate newly fetched RSS entry: {entry['title']}")
                            continue
                        
                        # Apply include_content filter
                        if not include_content:
                            entry.pop("content", None)
                        
                        # Index the content 
                        embedding_manager.add_item(content_text, source_type="retrieved")
                        
                        formatted_entries.append(entry)
                    
                    if formatted_entries:
                        results.append({
                            "feed_id": str(feed.id),
                            "feed_title": feed.title,
                            "feed_url": feed.url,
                            "entry_count": len(formatted_entries),
                            "entries": formatted_entries,
                        })
            
            return results

    def search(
        self, query_text: str, max_entries: int = 10, include_content: bool = False
    ) -> List[Dict]:
        # Simple search implementation (sqlite LIKE)
        with next(get_session()) as session:
            # This is a basic search. Full text search would be better.
            statement = (
                select(RSSEntryModel)
                .where(
                    (RSSEntryModel.title.contains(query_text))
                    | (RSSEntryModel.content.contains(query_text))
                )
                .limit(max_entries)
            )

            entries = session.exec(statement).all()
            results = []
            for entry in entries:
                res = {
                    "feed_id": str(entry.feed_id),
                    "title": entry.title,
                    "link": entry.link,
                }
                if include_content:
                    res["content"] = entry.content
                results.append(res)

            return (
                results
                if results
                else {
                    "status": "error",
                    "content": [{"text": f"No entries found for '{query_text}'"}],
                }
            )

    def mark_processed(self, entry_ids: List[int]) -> Dict:
        """
        Mark RSS entries as processed/seen by the LLM.
        This prevents them from being returned in future read operations.
        
        Args:
            entry_ids: List of entry IDs to mark as processed
            
        Returns:
            Dict with status and count of marked entries
        """
        with next(get_session()) as session:
            marked_count = 0
            for entry_id in entry_ids:
                entry = session.get(RSSEntryModel, entry_id)
                if entry:
                    entry.is_processed = True
                    entry.processed_at = datetime.utcnow()
                    session.add(entry)
                    marked_count += 1
            
            session.commit()
            
            return {
                "status": "success",
                "content": [{"text": f"Marked {marked_count} entries as processed"}],
                "marked_count": marked_count,
            }
    
    def reset_processed_status(self, feed_id: Optional[int] = None) -> Dict:
        """
        Reset processed status for entries (useful for testing or re-processing).
        
        Args:
            feed_id: Optional feed ID to reset only that feed's entries
            
        Returns:
            Dict with status and count of reset entries
        """
        with next(get_session()) as session:
            query = select(RSSEntryModel).where(RSSEntryModel.is_processed == True)
            
            if feed_id:
                query = query.where(RSSEntryModel.feed_id == feed_id)
            
            entries = session.exec(query).all()
            reset_count = 0
            
            for entry in entries:
                entry.is_processed = False
                entry.processed_at = None
                session.add(entry)
                reset_count += 1
            
            session.commit()
            
            return {
                "status": "success",
                "content": [{"text": f"Reset {reset_count} entries"}],
                "reset_count": reset_count,
            }


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
    entry_ids: Optional[List[int]] = None,
    only_unprocessed: bool = True,
) -> Union[List[Dict], Dict]:
    """
    Interact with RSS feeds - fetch, subscribe, search, and manage feeds via Database.

    Actions:
    - fetch: Get feed content from URL without subscribing
    - subscribe: Add a feed to your subscription list
    - unsubscribe: Remove a feed subscription
    - list: List all subscribed feeds (filtered by scout context if available)
    - read: Read entries from a single subscribed feed (by default only unprocessed)
    - read_all: Read entries from ALL subscribed feeds (by default only unprocessed)
    - update: Update feeds with new content
    - search: Find entries matching a query
    - mark_processed: Mark entries as processed/seen (requires entry_ids)
    - reset_processed: Reset processed status for testing (optional feed_id)

    Args:
        action: Action to perform
        url: URL of the RSS feed
        feed_id: ID of a subscribed feed
        max_entries: Maximum number of entries to return (for read_all, this is per feed)
        include_content: Whether to include full content
        query: Search query
        category: Filter entries by category
        entry_ids: List of entry IDs (for mark_processed action)
        only_unprocessed: If True, read/read_all only returns unprocessed entries (default: True)
    """
    
    # Get scout_id from environment variable (set by ScoutManager)
    scout_id_str = os.environ.get("INFLUENCERPY_SCOUT_ID")
    scout_id = int(scout_id_str) if scout_id_str else None
    
    try:
        if action == "fetch":
            if not url:
                return {
                    "status": "error",
                    "content": [{"text": "URL is required for fetch action"}],
                }

            feed = rss_manager.fetch_feed(url, headers=headers)
            if not hasattr(feed, "entries"):
                return {
                    "status": "error",
                    "content": [{"text": "Could not parse feed"}],
                }

            # Initialize embedding manager for duplicate detection
            embedding_manager = EmbeddingManager()
            
            # Filter entries using embeddings
            entries = []
            for entry in feed.entries[:max_entries]:
                formatted = rss_manager.format_entry(entry, include_content)
                
                # Check for duplicates using embeddings (on content side)
                content_text = f"{formatted.get('title', '')} {formatted.get('summary', '')}"
                if content_text.strip() and embedding_manager.is_similar(content_text):
                    logger.debug(f"Skipping duplicate RSS entry: {formatted.get('title', 'Unknown')}")
                    continue
                
                # Index the content to prevent future duplicates
                if content_text.strip():
                    embedding_manager.add_item(content_text, source_type="retrieved")
                
                entries.append(formatted)
            
            return entries

        elif action == "subscribe":
            if not url:
                return {
                    "status": "error",
                    "content": [{"text": "URL is required for subscribe"}],
                }

            auth = None
            if auth_username and auth_password:
                auth = {
                    "type": "basic",
                    "username": auth_username,
                    "password": auth_password,
                }

            return rss_manager.subscribe(
                url, update_interval or DEFAULT_UPDATE_INTERVAL, auth, headers, scout_id
            )

        elif action == "unsubscribe":
            if not feed_id:
                return {"status": "error", "content": [{"text": "feed_id is required"}]}
            return rss_manager.unsubscribe(int(feed_id))

        elif action == "list":
            return rss_manager.list_feeds(scout_id)

        elif action == "read":
            if not feed_id:
                return {"status": "error", "content": [{"text": "feed_id is required"}]}
            return rss_manager.read_feed(
                int(feed_id), max_entries, category, include_content, only_unprocessed
            )
        
        elif action == "read_all":
            # Read from all subscribed feeds (filtered by scout_id if available)
            return rss_manager.read_all_feeds(
                scout_id=scout_id,
                max_entries_per_feed=max_entries,
                include_content=include_content,
                only_unprocessed=only_unprocessed
            )

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
        
        elif action == "mark_processed":
            if not entry_ids:
                return {"status": "error", "content": [{"text": "entry_ids is required"}]}
            return rss_manager.mark_processed(entry_ids)
        
        elif action == "reset_processed":
            # Optional feed_id to reset only specific feed
            return rss_manager.reset_processed_status(int(feed_id) if feed_id else None)

        else:
            return {
                "status": "error",
                "content": [{"text": f"Unknown action: {action}"}],
            }

    except Exception as e:
        logger.error(f"RSS tool error: {e}")
        return {"status": "error", "content": [{"text": str(e)}]}
