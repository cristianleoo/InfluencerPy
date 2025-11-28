import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from influencerpy.core.scouts import ScoutManager
from influencerpy.logger import get_app_logger
from influencerpy.database import ScoutModel

logger = get_app_logger("scheduler")

class ScoutScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.manager = ScoutManager()
        
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.load_jobs()
            self.scheduler.start()
            logger.info("Scheduler started.")
            
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped.")

    def load_jobs(self):
        """Load scouts from DB and schedule them."""
        self.scheduler.remove_all_jobs()
        scouts = self.manager.list_scouts()
        
        count = 0
        for scout in scouts:
            if scout.schedule_cron:
                try:
                    # Parse cron string: "minute hour day month day_of_week"
                    # APScheduler expects kwargs or a string
                    self.scheduler.add_job(
                        self._run_scout_job,
                        CronTrigger.from_crontab(scout.schedule_cron),
                        args=[scout.id],
                        id=f"scout_{scout.id}",
                        name=f"Run Scout: {scout.name}",
                        replace_existing=True
                    )
                    count += 1
                    logger.info(f"Scheduled scout '{scout.name}' with cron: {scout.schedule_cron}")
                except Exception as e:
                    logger.error(f"Failed to schedule scout '{scout.name}': {e}")
        
        logger.info(f"Loaded {count} scheduled jobs.")

    async def _run_scout_job(self, scout_id: int):
        """Job execution wrapper."""
        # Re-fetch scout to get latest config
        scout = self.manager.session.get(ScoutModel, scout_id)
        if not scout:
            logger.warning(f"Scout {scout_id} not found during job execution.")
            return

        logger.info(f"Executing scheduled run for scout: {scout.name}")
        
        # Run in thread pool to avoid blocking async loop if run_scout is sync
        # But wait, run_scout calls Agent which might be sync or async. 
        # Strands Agent is sync. So we should run it in a thread.
        try:
            items = await asyncio.to_thread(self.manager.run_scout, scout)
            
            # If Telegram review is enabled, we don't post automatically here.
            # The ScoutManager/Telegram integration logic handles the "Drafting" part?
            # Wait, run_scout only fetches items. It doesn't draft or post.
            # We need to generate drafts for the found items.
            
            if items:
                # Select best item
                best_item = await asyncio.to_thread(self.manager.select_best_content, items, scout)
                if best_item:
                    # Generate draft
                    draft_text = await asyncio.to_thread(self.manager.generate_draft, scout, best_item)
                    
                    # Save draft to DB
                    from influencerpy.database import get_session, PostModel
                    from datetime import datetime
                    import json
                    
                    with next(get_session()) as session:
                        # Check platforms
                        platforms = json.loads(scout.platforms) if scout.platforms else []
                        primary_platform = platforms[0] if platforms else "x"
                        
                        db_post = PostModel(
                            content=draft_text,
                            platform=primary_platform,
                            status="pending_review",
                            created_at=datetime.utcnow()
                        )
                        session.add(db_post)
                        session.commit()
                    
                    logger.info(f"Generated and saved draft for {scout.name}: {best_item.title}")
                    
        except Exception as e:
            logger.error(f"Error in scheduled job for {scout.name}: {e}", exc_info=True)
