from abc import ABC, abstractmethod
from typing import Any

class BaseChannel(ABC):
    """
    Abstract base class for management channels (e.g., Telegram, WhatsApp, Slack).
    These channels are used to review posts, receive notifications, and control the bot.
    """

    @abstractmethod
    async def start(self):
        """
        Start the channel listener (e.g., start polling or listening for webhooks).
        This method should be blocking or run indefinitely until stopped.
        """
        pass

    @abstractmethod
    async def send_review_request(self, post: Any):
        """
        Send a post draft to the channel for user review.
        
        Args:
            post: The post object (PostModel) containing content and metadata.
        """
        pass

    @abstractmethod
    async def notify_error(self, error_message: str):
        """
        Send an error notification to the user.
        """
        pass

    @abstractmethod
    async def notify_success(self, message: str):
        """
        Send a success notification to the user.
        """
        pass
