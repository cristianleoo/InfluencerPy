import os
import asyncio
import logging
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlmodel import select
from influencerpy.database import get_session
from influencerpy.types.schema import PostModel, ScoutModel, ScoutFeedbackModel
import json
from influencerpy.platforms.x_platform import XProvider
from influencerpy.platforms.substack_platform import SubstackProvider
from influencerpy.channels.base import BaseChannel
from influencerpy.core.scouts import ScoutManager
from influencerpy.types.models import Platform, PostDraft

logger = logging.getLogger(__name__)

class TelegramChannel(BaseChannel):
    MAX_MESSAGE_LENGTH = 4096
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.application = None
        self.scout_manager = ScoutManager()
        self.waiting_for_feedback = {} # {user_id: post_id}
    
    @staticmethod
    def _escape_markdown(text: str) -> str:
        """
        Escape special characters for Telegram MarkdownV2.
        
        Args:
            text: The text to escape
            
        Returns:
            Escaped text safe for MarkdownV2
        """
        # Characters that need to be escaped in MarkdownV2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    def _split_message(self, text: str, max_length: int = None) -> list[str]:
        """Split a message into chunks that fit within Telegram's character limit.
        
        Args:
            text: The text to split
            max_length: Maximum length per chunk (defaults to MAX_MESSAGE_LENGTH)
        
        Returns:
            List of message chunks
        """
        if max_length is None:
            max_length = self.MAX_MESSAGE_LENGTH
        
        # If message fits, return as-is
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by lines to preserve formatting
        lines = text.split('\n')
        
        for line in lines:
            # If a single line is longer than max_length, we need to split it
            if len(line) > max_length:
                # First, add the current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                    current_chunk = ""
                
                # Split the long line into smaller pieces
                while len(line) > max_length:
                    chunks.append(line[:max_length])
                    line = line[max_length:]
                
                # Add remaining part of the line
                if line:
                    current_chunk = line + '\n'
            else:
                # Check if adding this line would exceed the limit
                if len(current_chunk) + len(line) + 1 > max_length:
                    # Save current chunk and start a new one
                    chunks.append(current_chunk.rstrip())
                    current_chunk = line + '\n'
                else:
                    # Add line to current chunk
                    current_chunk += line + '\n'
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(current_chunk.rstrip())
        
        return chunks
    
    async def _send_message_split(self, chat_id: str, text: str, **kwargs):
        """Send a message, splitting it into multiple messages if needed.
        
        Args:
            chat_id: The chat ID to send to
            text: The message text
            **kwargs: Additional arguments to pass to send_message (e.g., parse_mode, reply_markup)
        
        Returns:
            The last sent message object
        """
        chunks = self._split_message(text)
        
        # For the first N-1 chunks, send without reply_markup
        last_message = None
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            
            # Only add reply_markup to the last message
            msg_kwargs = kwargs.copy()
            if not is_last and 'reply_markup' in msg_kwargs:
                del msg_kwargs['reply_markup']
            
            # Add part indicator if message was split
            if len(chunks) > 1:
                part_text = f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"
            else:
                part_text = chunk
            
            last_message = await self.application.bot.send_message(
                chat_id=chat_id,
                text=part_text,
                **msg_kwargs
            )
        
        return last_message
    
    async def _reply_text_split(self, message, text: str, **kwargs):
        """Reply to a message, splitting it into multiple messages if needed.
        
        Args:
            message: The message object to reply to
            text: The message text
            **kwargs: Additional arguments to pass to reply_text (e.g., parse_mode, reply_markup)
        
        Returns:
            The last sent message object
        """
        chunks = self._split_message(text)
        
        # For the first N-1 chunks, send without reply_markup
        last_message = None
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            
            # Only add reply_markup to the last message
            msg_kwargs = kwargs.copy()
            if not is_last and 'reply_markup' in msg_kwargs:
                del msg_kwargs['reply_markup']
            
            # Add part indicator if message was split
            if len(chunks) > 1:
                part_text = f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"
            else:
                part_text = chunk
            
            last_message = await message.reply_text(part_text, **msg_kwargs)
        
        return last_message

    async def start(self):
        """Start the Telegram bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found.")
            print("Error: TELEGRAM_BOT_TOKEN not found.")
            return

        # Configure timeouts for better reliability on slower networks
        self.application = (
            Application.builder()
            .token(self.token)
            .read_timeout(180)  # Increase read timeout to 30 seconds
            .write_timeout(180)  # Increase write timeout to 30 seconds
            .build()
        )

        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("check", self._check_command))
        self.application.add_handler(CommandHandler("scouts", self._list_scouts_command))
        self.application.add_handler(CallbackQueryHandler(self._button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        # Job queue to check for posts every minute
        if self.application.job_queue:
            self.application.job_queue.run_repeating(self.check_pending_posts, interval=60, first=10)

        from telegram.error import Conflict

        await self.application.initialize()
        await self.application.start()
        try:
            await self.application.updater.start_polling()
        except Conflict:
            print("\n[red]Error: Another instance of the bot is already running.[/red]")
            print("Please stop the other instance first.")
            logger.error("Telegram Conflict: Another bot instance is running.")
            return

        print("🤖 Telegram Bot is running...")
        logger.info("Telegram Bot started polling.")
        
        # Keep running until cancelled
        stop_signal = asyncio.Event()
        try:
            await stop_signal.wait()
        except asyncio.CancelledError:
            pass
        finally:
            print("Stopping Telegram Bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def send_review_request(self, post: PostModel):
        """Send a post for review."""
        if not self.application or not self.chat_id:
            logger.warning("Cannot send review request: Bot not started or Chat ID missing.")
            return

        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{post.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post.id}"),
            ],
            [
                InlineKeyboardButton("💬 Feedback / Edit", callback_data=f"feedback_{post.id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message_split(
            chat_id=self.chat_id,
            text=f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}",
            reply_markup=reply_markup
        )

    async def notify_error(self, error_message: str):
        if self.application and self.chat_id:
            await self._send_message_split(
                chat_id=self.chat_id,
                text=f"❌ Error: {error_message}"
            )

    async def notify_success(self, message: str):
        if self.application and self.chat_id:
            await self._send_message_split(
                chat_id=self.chat_id,
                text=f"✅ {message}"
            )

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message."""
        await update.message.reply_text(
            "👋 Welcome to InfluencerPy Bot!\n\n"
            "I will notify you when new posts are ready for review.\n"
            "Commands:\n"
            "/help - Show available commands\n"
            "/check - Check for pending posts\n"
            "/scouts - List and run scouts"
        )

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available commands."""
        await update.message.reply_text(
            "📚 **InfluencerPy Bot Help**\n\n"
            "Here are the commands you can use:\n\n"
            "🔹 /start - Welcome message and status\n"
            "🔹 /check - Force check for pending reviews\n"
            "🔹 /scouts - List your scouts and run them manually\n"
            "🔹 /help - Show this help message\n\n"
            "You will also receive automatic notifications when a scout generates a new draft.",
            parse_mode="Markdown"
        )

    async def _check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force check for pending reviews and report status."""
        count = await self.check_pending_posts(context)
        if count == 0:
            await update.message.reply_text("✅ No pending reviews found at the moment.")
        else:
            # check_pending_posts already sent the cards
            pass

    async def _list_scouts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all scouts with Run buttons."""
        scouts = self.scout_manager.list_scouts()
        
        if not scouts:
            await update.message.reply_text("No scouts found. Create one using the CLI first.")
            return

        await update.message.reply_text("🕵️ **Your Scouts**:", parse_mode="Markdown")
        
        for scout in scouts:
            keyboard = [[InlineKeyboardButton("🚀 Run Scout", callback_data=f"run_scout_{scout.id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            info = f"**{scout.name}**\nType: {scout.type}"
            if scout.last_run:
                info += f"\nLast Run: {scout.last_run.strftime('%Y-%m-%d %H:%M')}"
            
            await self._reply_text_split(update.message, info, reply_markup=reply_markup, parse_mode="Markdown")

    async def check_pending_posts(self, context: ContextTypes.DEFAULT_TYPE):
        """Check DB for posts with status 'pending_review'."""
        # Note: This method is called by the job queue, so 'self' is available if bound correctly,
        # but context is passed by python-telegram-bot.
        
        # We need to access the bot instance from context if we are in a job
        bot = context.bot
        chat_id = self.chat_id

        if not chat_id:
             return

        with next(get_session()) as session:
            statement = select(PostModel).where(PostModel.status == "pending_review")
            posts = session.exec(statement).all()
            
            for post in posts:
                # Send to Telegram
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{post.id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post.id}"),
                    ],
                    [
                        InlineKeyboardButton("💬 Feedback / Edit", callback_data=f"feedback_{post.id}"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send using split method
                chunks = self._split_message(f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}")
                for i, chunk in enumerate(chunks):
                    is_last = (i == len(chunks) - 1)
                    
                    # Only add reply_markup to the last message
                    if len(chunks) > 1:
                        part_text = f"[Part {i+1}/{len(chunks)}]\n\n{chunk}"
                    else:
                        part_text = chunk
                    
                    await bot.send_message(
                        chat_id=chat_id,
                        text=part_text,
                        reply_markup=reply_markup if is_last else None
                    )
                
                # Update status to 'reviewing' to avoid re-sending
                post.status = "reviewing"
                session.add(post)
                session.commit()
            
            return len(posts)

    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        data = query.data
        
        if data.startswith("run_scout_"):
            scout_id = int(data.split("_")[-1])
            await self._handle_run_scout(query, scout_id)
            return

        action, post_id = data.split("_")
        post_id = int(post_id)
        
        with next(get_session()) as session:
            post = session.get(PostModel, post_id)
            if not post:
                await query.edit_message_text("❌ Post not found (might have been deleted).")
                return

            if action == "confirm":
                if post.platform == "telegram":
                    # Telegram-only posts are just acknowledged (for manual copy/paste elsewhere)
                    post.status = "posted"
                    post.posted_at = datetime.utcnow()
                    session.add(post)
                    session.commit()
                    await query.edit_message_text(
                        "✅ Draft confirmed!\n\n"
                        "📋 You can now copy and manually post this content to your target platform."
                    )
                elif post.platform == "x":
                    provider = XProvider()
                    if provider.authenticate():
                        try:
                            tweet_id = provider.post(post.content)
                            post.status = "posted"
                            post.external_id = tweet_id
                            post.posted_at = datetime.utcnow()
                            session.add(post)
                            session.commit()
                            await query.edit_message_text(f"✅ Posted to X! (ID: {tweet_id})")
                        except Exception as e:
                            await query.edit_message_text(f"❌ Error posting to X: {e}")
                    else:
                        await query.edit_message_text("❌ Authentication failed for X.")
                elif post.platform == "substack":
                    provider = SubstackProvider()
                    if provider.authenticate():
                        try:
                            draft_id = provider.post(post.content)
                            post.status = "posted"
                            post.external_id = draft_id
                            post.posted_at = datetime.utcnow()
                            session.add(post)
                            session.commit()
                            # Construct the draft edit URL
                            subdomain = os.getenv("SUBSTACK_SUBDOMAIN")
                            edit_url = f"https://{subdomain}.substack.com/publish/post/{draft_id}"
                            await query.edit_message_text(
                                f"✅ Substack draft created!\n\n"
                                f"📝 Edit and publish at:\n{edit_url}"
                            )
                        except Exception as e:
                            await query.edit_message_text(f"❌ Error creating Substack draft: {e}")
                    else:
                        await query.edit_message_text("❌ Authentication failed for Substack. Check your SUBSTACK_SUBDOMAIN, SUBSTACK_SID, and SUBSTACK_LLI environment variables.")
                else:
                    await query.edit_message_text(f"❌ Platform '{post.platform}' not supported via bot yet.")
                    
            elif action == "reject":
                post.status = "rejected"
                session.add(post)
                session.commit()
                await query.edit_message_text("🚫 Post rejected.")

            elif action == "feedback":
                user_id = query.from_user.id
                self.waiting_for_feedback[user_id] = post.id
                await self._reply_text_split(
                    query.message,
                    "Please reply to this message with your feedback or instructions to improve the post.\n"
                    "Example: 'Make it shorter', 'Add hashtags', 'Change tone to professional'"
                )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for feedback loop)."""
        user_id = update.effective_user.id
        
        if user_id in self.waiting_for_feedback:
            post_id = self.waiting_for_feedback.pop(user_id)
            feedback = update.message.text
            
            await update.message.reply_text("🔄 Regenerating draft based on your feedback... Please wait.")
            
            with next(get_session()) as session:
                post = session.get(PostModel, post_id)
                if not post:
                    await update.message.reply_text("❌ Post not found (might have been deleted).")
                    return
                
                # Save feedback if linked to a scout
                if post.scout_id:
                    try:
                        fb = ScoutFeedbackModel(
                            scout_id=post.scout_id,
                            content_url=f"draft:{post.id}", # Placeholder since we track draft refinement
                            action="refinement",
                            feedback_text=feedback,
                            created_at=datetime.utcnow()
                        )
                        session.add(fb)
                        # Commit later with post update
                    except Exception as e:
                        logger.error(f"Failed to save feedback: {e}")

                # Run regeneration in thread
                try:
                    def regenerate_logic():
                        manager = ScoutManager() # New instance for thread safety
                        return manager.regenerate_draft_from_feedback(post.content, feedback, post.platform)
                    
                    new_content = await asyncio.to_thread(regenerate_logic)
                    
                    # Update Post
                    post.content = new_content
                    # Status remains 'reviewing' or 'pending_review'
                    session.add(post)
                    session.commit()
                    
                    # Re-send review card
                    await self.send_review_request(post)
                    
                except Exception as e:
                    logger.error(f"Error regenerating post: {e}", exc_info=True)
                    await self._reply_text_split(update.message, f"❌ Error regenerating post: {e}")
                    
    async def _handle_run_scout(self, query, scout_id: int):
        """Handle the run scout action."""
        # Get scout
        scout = self.scout_manager.session.get(ScoutModel, scout_id) # Access session directly or add get_scout_by_id to manager
        # Manager has get_scout(name), let's use session for ID or add method. 
        # Actually, let's just use the session from manager if available, or create new.
        # ScoutManager creates a session in __init__.
        
        # Re-fetch to be safe with session state
        with next(get_session()) as session:
            scout = session.get(ScoutModel, scout_id)
            if not scout:
                await query.edit_message_text("❌ Scout not found.")
                return
            
            await query.edit_message_text(f"🚀 Running scout '{scout.name}'... This may take a minute.")
            
            try:
                # Run in thread to avoid blocking
                # We need to create a new manager instance or ensure thread safety if sharing session.
                # Best to create new manager/session for the thread.
                
                def run_logic():
                    # New session for thread
                    manager = ScoutManager()
                    # Re-fetch scout in this session
                    local_scout = manager.session.get(ScoutModel, scout_id)
                    
                    items = manager.run_scout(local_scout)
                    if not items:
                        return None, local_scout.intent
                    
                    # Handle based on intent
                    if local_scout.intent == "scouting":
                        # Format as curated list
                        formatted_output = manager.format_scouting_output(local_scout, items)
                        return formatted_output, "scouting"
                    else:
                        # Generate social post
                        item = manager.select_best_content(items, local_scout)
                        if not item:
                            return None, "generation"
                        draft_content = manager.generate_draft(local_scout, item)
                        return draft_content, "generation"

                result = await asyncio.to_thread(run_logic)
                draft_content, intent = result if result else (None, "generation")
                
                if not draft_content:
                    await self._send_message_split(
                        chat_id=self.chat_id,
                        text=f"⚠️ Scout '{scout.name}' finished but found no suitable content."
                    )
                    return

                # Save draft to DB
                with next(get_session()) as session:
                    # Check platforms
                    platforms = json.loads(scout.platforms) if scout.platforms else []
                    
                    # For scouting intent, always use telegram
                    if intent == "scouting":
                        primary_platform = "telegram"
                    else:
                        primary_platform = platforms[0] if platforms else "x"
                    
                    db_post = PostModel(
                        content=draft_content,
                        platform=primary_platform,
                        status="pending_review",
                        created_at=datetime.utcnow(),
                        scout_id=scout.id
                    )
                    session.add(db_post)
                    session.commit()
                    
                message_type = "report" if intent == "scouting" else "draft"
                await self._send_message_split(
                    chat_id=self.chat_id,
                    text=f"✅ Scout '{scout.name}' finished! {message_type.capitalize()} created."
                )
                
                # Trigger check immediately to show the review card
                # We can't pass context easily, but we can call the logic
                # Actually, check_pending_posts uses self.chat_id and self.application.bot, 
                # but it expects 'context' for context.bot.
                # Let's just call the logic manually or wait for the job.
                # Calling manually is better.
                await self._show_pending_posts()

            except Exception as e:
                logger.error(f"Error running scout: {e}", exc_info=True)
                await self._send_message_split(
                    chat_id=self.chat_id,
                    text=f"❌ Error running scout '{scout.name}': {e}"
                )

    async def _show_pending_posts(self):
        """Helper to show pending posts immediately."""
        if not self.chat_id: return
        
        with next(get_session()) as session:
            posts = session.exec(select(PostModel).where(PostModel.status == "pending_review")).all()
            for post in posts:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{post.id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{post.id}"),
                    ],
                    [
                        InlineKeyboardButton("💬 Feedback / Edit", callback_data=f"feedback_{post.id}"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self._send_message_split(
                    chat_id=self.chat_id,
                    text=f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}",
                    reply_markup=reply_markup
                )
                post.status = "reviewing"
                session.add(post)
                session.commit()
