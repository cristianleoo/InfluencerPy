import pytest
from unittest.mock import MagicMock, patch, call
from influencerpy.platforms.x_platform import XProvider
from influencerpy.core.models import PostDraft

@pytest.fixture
def x_provider():
    provider = XProvider()
    provider.client = MagicMock()
    provider.api = MagicMock()
    # Force free tier for threading tests
    provider.account_tier = "free"
    provider.char_limit = 280
    return provider

def test_post_threading_balanced(x_provider):
    # Create content that is slightly over 280 chars with hashtags at the end
    # 275 chars of text + space + 36 chars of hashtags = 312 chars
    text_part = "This is a sentence that is repeated to fill space. " * 10 
    text_part = text_part[:275]
    hashtags = "#python #ai #coding #developer #tech"
    content = text_part + " " + hashtags
    
    # Mock create_tweet response
    mock_response = MagicMock()
    mock_response.data = {'id': '12345'}
    x_provider.client.create_tweet.return_value = mock_response
    
    x_provider.post(content)
    
    # Verify calls
    # We expect 2 tweets.
    # With balanced logic:
    # Total 312. Num tweets = 2. Target width ~ 156 + 40 = 196.
    # Tweet 1 should be around 196 chars.
    # Tweet 2 should be around 116 chars.
    
    assert x_provider.client.create_tweet.call_count == 2
    
    calls = x_provider.client.create_tweet.call_args_list
    tweet1_text = calls[0].kwargs['text']
    tweet2_text = calls[1].kwargs['text']
    
    print(f"Tweet 1 length: {len(tweet1_text)}")
    print(f"Tweet 2 length: {len(tweet2_text)}")
    
    # Assert that the second tweet is substantial (not just hashtags)
    # Hashtags length is 36. We want significantly more than that.
    assert len(tweet2_text) > 50 
    assert len(tweet1_text) < 280 # Should be well under the limit due to balancing

def test_post_threading_fallback(x_provider):
    # Test a case where balancing might fail or just normal long text
    # 600 chars
    content = "A" * 600
    
    mock_response = MagicMock()
    mock_response.data = {'id': '12345'}
    x_provider.client.create_tweet.return_value = mock_response
    
    x_provider.post(content)
    
    # 600 / 280 = 2.14 -> 3 tweets
    assert x_provider.client.create_tweet.call_count == 3

def test_post_short_no_threading(x_provider):
    content = "Short tweet"
    
    mock_response = MagicMock()
    mock_response.data = {'id': '12345'}
    x_provider.client.create_tweet.return_value = mock_response
    
    x_provider.post(content)
    
    x_provider.client.create_tweet.assert_called_once_with(text="Short tweet")
