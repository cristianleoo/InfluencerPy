from abc import ABC, abstractmethod
from typing import List, Optional
from influencerpy.core.models import ContentItem, PostDraft, Platform

class SocialProvider(ABC):
    """Abstract base class for social media platforms."""
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform."""
        pass

    @abstractmethod
    def post(self, draft: PostDraft) -> str:
        """Post content to the platform. Returns the ID of the created post."""
        pass

class ContentSource(ABC):
    """Interface for content sources (RSS, Search, etc)."""
    
    @abstractmethod
    def fetch_latest(self, limit: int = 5) -> List[ContentItem]:
        """Fetch latest content items."""
        pass

class AgentProvider(ABC):
    """Interface for AI Agent providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        pass
