import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from influencerpy.bot import check_pending_posts, button_callback
from influencerpy.database import PostModel

@pytest.mark.asyncio
async def test_check_pending_posts():
    with patch("influencerpy.bot.get_session") as mock_get_session, \
         patch("influencerpy.bot.os.getenv") as mock_getenv, \
         patch("influencerpy.bot.select") as mock_select:
        
        mock_getenv.return_value = "12345"
        
        # Setup session mock
        mock_session = MagicMock(name="mock_session")
        mock_session.__enter__.return_value = mock_session
        mock_get_session.return_value = iter([mock_session])
        
        # Setup post mock
        mock_post = MagicMock(spec=PostModel)
        mock_post.id = 1
        mock_post.content = "Test Post"
        mock_post.platform = "x"
        mock_post.status = "pending_review"
        
        # Setup exec result
        mock_result = MagicMock(name="exec_result")
        mock_result.all.return_value = [mock_post]
        mock_session.exec.return_value = mock_result
        
        # Mock context
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        await check_pending_posts(context)
        
        # Verify
        if not mock_session.exec.called:
            pytest.fail("Session exec not called")
            
        mock_session.exec.assert_called()
        context.bot.send_message.assert_called_once()
        assert "Test Post" in context.bot.send_message.call_args[1]["text"]
        assert mock_post.status == "reviewing"
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_button_callback_confirm():
    with patch("influencerpy.bot.get_session") as mock_get_session, \
         patch("influencerpy.bot.XProvider") as mock_x_provider:
        
        mock_session = MagicMock(name="mock_session")
        mock_session.__enter__.return_value = mock_session
        mock_get_session.return_value = iter([mock_session])
        
        mock_post = MagicMock(spec=PostModel)
        mock_post.id = 1
        mock_post.content = "Test Post"
        mock_post.platform = "x"
        mock_post.status = "reviewing"
        
        mock_session.get.return_value = mock_post
        
        mock_provider = MagicMock()
        mock_x_provider.return_value = mock_provider
        mock_provider.authenticate.return_value = True
        mock_provider.post.return_value = "tweet_123"
        
        update = MagicMock()
        update.callback_query.data = "confirm_1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        context = MagicMock()
        
        await button_callback(update, context)
        
        mock_provider.post.assert_called_with("Test Post")
        assert mock_post.status == "posted"
        assert mock_post.external_id == "tweet_123"
        mock_session.commit.assert_called()
        update.callback_query.edit_message_text.assert_called_with("✅ Posted to X! (ID: tweet_123)")

@pytest.mark.asyncio
async def test_button_callback_reject():
    with patch("influencerpy.bot.get_session") as mock_get_session:
        mock_session = MagicMock(name="mock_session")
        mock_session.__enter__.return_value = mock_session
        mock_get_session.return_value = iter([mock_session])
        
        mock_post = MagicMock(spec=PostModel)
        mock_post.id = 1
        mock_post.status = "reviewing"
        
        mock_session.get.return_value = mock_post
        
        update = MagicMock()
        update.callback_query.data = "reject_1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        context = MagicMock()
        
        await button_callback(update, context)
        
        assert mock_post.status == "rejected"
        mock_session.commit.assert_called()
        update.callback_query.edit_message_text.assert_called_with("🚫 Post rejected.")
