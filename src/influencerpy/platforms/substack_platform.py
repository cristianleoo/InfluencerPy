import os
import json
from typing import Optional
from influencerpy.core.interfaces import SocialProvider
from influencerpy.types.models import Platform, PostDraft
from influencerpy.platforms.substack.auth import SubstackAuth


class SubstackProvider(SocialProvider):
    """Provider for posting to Substack as drafts."""
    
    def __init__(self):
        self.auth: Optional[SubstackAuth] = None
        self.publication_id: Optional[int] = None
        self.subdomain: Optional[str] = None
        
    @property
    def platform(self) -> Platform:
        return Platform.SUBSTACK
    
    def authenticate(self) -> bool:
        """Authenticate with Substack using cookies from environment."""
        subdomain = os.getenv("SUBSTACK_SUBDOMAIN")
        sid = os.getenv("SUBSTACK_SID")
        lli = os.getenv("SUBSTACK_LLI")
        
        if not subdomain or not sid or not lli:
            return False
        
        try:
            # Use cookies dict instead of file path
            cookies_dict = {
                'sid': sid,
                'lli': lli
            }
            self.auth = SubstackAuth(cookies_dict=cookies_dict)
            self.subdomain = subdomain
            
            # Verify authentication by trying to get publication info
            url = f"https://{subdomain}.substack.com/api/v1/publication"
            response = self.auth.get(url, timeout=30)
            response.raise_for_status()
            
            pub_data = response.json()
            # The publication endpoint doesn't return 'id' directly
            # But if we get a 200 response with publication data, auth is working
            # We can try to get the ID from posts endpoint later if needed
            self.publication_id = pub_data.get("id") or subdomain  # Use subdomain as fallback
            
            # If we got a 200 status with publication data, auth is valid
            return self.auth.authenticated and response.status_code == 200
            
        except Exception as e:
            print(f"Substack authentication error: {e}")
            return False
    
    def post(self, draft) -> str:
        """
        Create a draft post on Substack.
        
        Note: Substack API doesn't allow direct publishing via API for security.
        This creates a draft that the user must manually publish from their dashboard.
        
        Parameters
        ----------
        draft : PostDraft or str
            The content to post
            
        Returns
        -------
        str
            The draft ID
        """
        if not self.auth or not self.auth.authenticated:
            if not self.authenticate():
                raise RuntimeError("Substack Provider not authenticated")
        
        # Handle both string and PostDraft types
        content = draft.content if hasattr(draft, 'content') else draft
        
        # Create a draft post via Substack API
        # Note: Title is required for Substack posts
        # We'll extract the first line as title and rest as body
        lines = content.split('\n', 1)
        title = lines[0][:80] if lines[0] else "Untitled Post"
        body_html = f"<p>{content.replace(chr(10), '</p><p>')}</p>"
        
        try:
            url = f"https://{self.subdomain}.substack.com/api/v1/posts"
            
            payload = {
                "title": title,
                "subtitle": "",
                "draft_body": body_html,
                "type": "newsletter",
                "audience": "everyone",  # or "only_paid" for paid subscribers
                "post_date": None,  # Draft, not scheduled
                "draft_byline": None,
                "draft_section_id": None,
            }
            
            response = self.auth.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            draft_id = str(result.get("id", "unknown"))
            
            # Construct the draft edit URL for user reference
            edit_url = f"https://{self.subdomain}.substack.com/publish/post/{draft_id}"
            print(f"Draft created! Edit and publish at: {edit_url}")
            
            return draft_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to create Substack draft: {e}")
