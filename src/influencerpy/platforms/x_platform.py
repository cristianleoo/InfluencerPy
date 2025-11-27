import os
import tweepy
import textwrap
import math
from typing import Optional
from influencerpy.core.interfaces import SocialProvider
from influencerpy.core.models import Platform, PostDraft

class XProvider(SocialProvider):
    def __init__(self):
        self.client: Optional[tweepy.Client] = None
        self.api: Optional[tweepy.API] = None
        self.account_tier = "free" # 'free', 'premium'
        self.char_limit = 280
        self.daily_post_limit = 50 # Approx for free tier

    @property
    def platform(self) -> Platform:
        return Platform.X

    def authenticate(self) -> bool:
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")



        if not all([api_key, api_secret, access_token, access_token_secret]):
            return False

        try:
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            # v1.1 API for media upload if needed
            auth = tweepy.OAuth1UserHandler(
                api_key, api_secret, access_token, access_token_secret
            )
            self.api = tweepy.API(auth)
            
            # Auto-detect account tier
            self._detect_tier()
            return True
        except Exception:
            return False

    def _detect_tier(self):
        """Detect if account is Premium/Business to adjust limits."""
        try:
            response = self.client.get_me(user_fields=["verified_type"])
            user = response.data
            # verified_type: 'blue', 'business', 'government' -> Premium features
            # None -> Free/Standard
            if user.verified_type in ['blue', 'business', 'government']:
                self.account_tier = "premium"
                self.char_limit = 25000 # 25k chars for long posts
                self.daily_post_limit = 2400 # Much higher limit
            else:
                self.account_tier = "free"
                self.char_limit = 280
                self.daily_post_limit = 50 # ~1500/month
        except Exception:
            # Fallback to free limits on error
            self.account_tier = "free"
            self.char_limit = 280
            self.daily_post_limit = 50

    def post(self, draft) -> str:
        """
        Post content to X. 
        - If Premium: Posts as single long tweet (up to 25k chars).
        - If Free: Auto-threads if longer than 280 chars.
        - Handles 429 Rate Limits gracefully.
        """
        if not self.client:
            if not self.authenticate():
                raise RuntimeError("X Provider not authenticated")
        
        # Handle both string and PostDraft types
        content = draft.content if hasattr(draft, 'content') else draft
        
        try:
            # Logic:
            # If content < 280: Post normally (works for all)
            # If content > 280 AND Premium: Post long tweet
            # If content > 280 AND Free: Thread it
            
            if len(content) <= 280 or self.account_tier == "premium":
                # Post single tweet (short or long)
                try:
                    response = self.client.create_tweet(text=content)
                    return str(response.data['id'])
                except tweepy.errors.Forbidden as e:
                    # Fallback: sometimes Premium detection might be stale or specific endpoint issue
                    # If it fails and length > 280, try threading as backup?
                    # But 'Forbidden' usually means length issue if 403.
                    if len(content) > 280 and "too long" in str(e).lower():
                         # Fallback to threading logic below
                         pass
                    else:
                        raise e

            # Threading Logic (for Free tier or Fallback)
            # Calculate ideal number of tweets
            num_tweets = math.ceil(len(content) / 280)
            
            # Calculate target width to balance tweets
            # We add a buffer because textwrap breaks on whitespace, so lines are often shorter than width
            target_width = math.ceil(len(content) / num_tweets) + 40 
            target_width = min(target_width, 280)
            
            tweets = textwrap.wrap(content, width=target_width, break_long_words=True, break_on_hyphens=False)
            
            # If balancing resulted in more tweets than necessary, fallback to max width
            if len(tweets) > num_tweets:
                tweets = textwrap.wrap(content, width=280, break_long_words=True, break_on_hyphens=False)
            
            first_id = None
            previous_id = None
            
            for i, tweet_text in enumerate(tweets):
                if previous_id:
                    response = self.client.create_tweet(text=tweet_text, in_reply_to_tweet_id=previous_id)
                else:
                    response = self.client.create_tweet(text=tweet_text)
                
                current_id = str(response.data['id'])
                previous_id = current_id
                
                if i == 0:
                    first_id = current_id
                    
            return first_id
            
        except tweepy.errors.TooManyRequests:
            raise RuntimeError(
                f"Rate Limit Exceeded (429). Your account ({self.account_tier}) "
                f"has likely hit the daily limit (approx {self.daily_post_limit} posts/24h)."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to post to X: {e}")
