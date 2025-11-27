import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlmodel import select
from influencerpy.database import get_session, PostModel, ScoutModel
import json
from influencerpy.platforms.x_platform import XProvider
from influencerpy.channels.base import BaseChannel
from influencerpy.core.scouts import ScoutManager
from influencerpy.core.models import Platform, PostDraft

logger = logging.getLogger(__name__)

class TelegramChannel(BaseChannel):
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.application = None
        self.scout_manager = ScoutManager()

    async def start(self):
        """Start the Telegram bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not found.")
            print("Error: TELEGRAM_BOT_TOKEN not found.")
            return

        self.application = Application.builder().token(self.token).build()

        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("check", lambda u, c: self.check_pending_posts(c)))
        self.application.add_handler(CommandHandler("scouts", self._list_scouts_command))
        self.application.add_handler(CallbackQueryHandler(self._button_callback))

        # Job queue to check for posts every minute
        if self.application.job_queue:
            self.application.job_queue.run_repeating(self.check_pending_posts, interval=60, first=10)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

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
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.application.bot.send_message(
            chat_id=self.chat_id,
            text=f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def notify_error(self, error_message: str):
        if self.application and self.chat_id:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=f"❌ Error: {error_message}"
            )

    async def notify_success(self, message: str):
        if self.application and self.chat_id:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=f"✅ {message}"
            )

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message."""
        await update.message.reply_text(
            "👋 Welcome to InfluencerPy Bot!\n\n"
            "I will notify you when new posts are ready for review.\n"
            "Commands:\n"
            "/check - Check for pending posts\n"
            "/scouts - List and run scouts"
        )

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
            
            await update.message.reply_text(info, reply_markup=reply_markup, parse_mode="Markdown")

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
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
                # Update status to 'reviewing' to avoid re-sending
                post.status = "reviewing"
                session.add(post)
                session.commit()

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
                if post.platform == "x":
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
                else:
                    await query.edit_message_text(f"❌ Platform '{post.platform}' not supported via bot yet.")
                    
            elif action == "reject":
                post.status = "rejected"
                session.add(post)
                session.commit()
                await query.edit_message_text("🚫 Post rejected.")

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
                        return None
                    
                    item = manager.select_best_content(items, local_scout)
                    if not item:
                        return None
                        
                    draft_content = manager.generate_draft(local_scout, item)
                    return draft_content

                draft_content = await asyncio.to_thread(run_logic)
                
                if not draft_content:
                    await self.application.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"⚠️ Scout '{scout.name}' finished but found no suitable content."
                    )
                    return

                # Save draft to DB
                with next(get_session()) as session:
                    # Check platforms
                    platforms = json.loads(scout.platforms) if scout.platforms else []
                    primary_platform = platforms[0] if platforms else "x"
                    
                    db_post = PostModel(
                        content=draft_content,
                        platform=primary_platform,
                        status="pending_review",
                        created_at=datetime.utcnow()
                    )
                    session.add(db_post)
                    session.commit()
                    
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"✅ Scout '{scout.name}' finished! Draft created."
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
                await self.application.bot.send_message(
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
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"📝 **Review Draft**\n\n{post.content}\n\nPlatform: {post.platform}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                post.status = "reviewing"
                session.add(post)
                session.commit()
