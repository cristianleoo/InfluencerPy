import json
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from strands import Agent
from strands.tools.tools import PythonAgentTool
from strands_tools import rss, generate_image_stability
from strands_tools.browser import LocalChromiumBrowser
from strands.handlers.callback_handler import null_callback_handler
from influencerpy.tools.search import google_search
from influencerpy.tools.reddit import reddit
from influencerpy.tools.arxiv_tool import arxiv_search
from influencerpy.tools.http_tool import http_request
from influencerpy.core.interfaces import AgentProvider
from influencerpy.providers.gemini import GeminiProvider
from influencerpy.providers.anthropic import AnthropicProvider
from influencerpy.config import ConfigManager
from influencerpy.logger import get_scout_logger
from influencerpy.database import get_session
from influencerpy.types.schema import ScoutModel, ScoutFeedbackModel, ScoutCalibrationModel
from influencerpy.types.models import ContentItem
from influencerpy.types.scout import ScoutResponse
from influencerpy.core.telemetry import setup_langfuse
from sqlmodel import select

# Import new prompt components
from influencerpy.core.prompts import SystemPrompt
from influencerpy.types.prompts import (
    GENERAL_GUARDRAILS,
    build_tool_prompt,
    get_platform_instructions,
)

class ScoutManager:
    def __init__(self):
        self.session = next(get_session())
        self.config_manager = ConfigManager()
        # Initialize embedding manager (lazy load)
        from influencerpy.core.embeddings import EmbeddingManager
        self.embedding_manager = EmbeddingManager()

    def _get_agent_provider(self, provider_name: str = None, model_id: str = None, temperature: float = 0.7) -> AgentProvider:
        """Factory to get the appropriate agent provider."""
        if not provider_name:
            provider_name = self.config_manager.get("ai.default_provider", "gemini")
            
        if provider_name == "gemini":
            if not model_id:
                model_id = self.config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash")
            return GeminiProvider(model_id=model_id, temperature=temperature)
            
        elif provider_name == "anthropic":
            if not model_id:
                model_id = self.config_manager.get("ai.providers.anthropic.default_model", "claude-4.5-sonnet")
            return AnthropicProvider(model_id=model_id, temperature=temperature)
            
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def create_scout(self, name: str, type: str, config: dict, intent: str = "scouting", prompt_template: str = None, schedule_cron: str = None, platforms: list = None, telegram_review: bool = False) -> ScoutModel:
        """Create a new Scout configuration.
        
        Args:
            name: Scout name
            type: Scout type (rss, reddit, search, etc.)
            config: Configuration dict specific to scout type
            intent: "scouting" (find and list content) or "generation" (create social posts)
            prompt_template: Custom prompt for the scout
            schedule_cron: Cron schedule string
            platforms: List of platforms (only used for generation intent)
            telegram_review: Enable Telegram review workflow (only for generation)
        """
        scout = ScoutModel(
            name=name,
            type=type,
            config_json=json.dumps(config),
            intent=intent,
            prompt_template=prompt_template,
            schedule_cron=schedule_cron,
            platforms=json.dumps(platforms or []),
            telegram_review=telegram_review if intent == "generation" else False
        )
        self.session.add(scout)
        self.session.commit()
        self.session.refresh(scout)
        return scout

    def update_scout(self, scout: ScoutModel, name: str = None, config: dict = None, intent: str = None, schedule_cron: str = None, prompt_template: str = None, telegram_review: bool = None, platforms: list = None) -> ScoutModel:
        """Update an existing Scout."""
        if name:
            scout.name = name
        if config:
            scout.config_json = json.dumps(config)
        if intent:
            scout.intent = intent
            # Reset telegram_review if switching to scouting
            if intent == "scouting":
                scout.telegram_review = False
        if schedule_cron is not None: # Allow clearing schedule with empty string if needed, but None means no change
            scout.schedule_cron = schedule_cron
        if prompt_template is not None:
            scout.prompt_template = prompt_template
        if telegram_review is not None and (not intent or scout.intent == "generation"):
            scout.telegram_review = telegram_review
        if platforms is not None:
            scout.platforms = json.dumps(platforms)
            
        self.session.add(scout)
        self.session.commit()
        self.session.refresh(scout)
        return scout

    def delete_scout(self, scout: ScoutModel):
        """Delete a scout and its feedback."""
        # Delete associated feedback first (if not handled by cascade)
        feedbacks = self.session.exec(select(ScoutFeedbackModel).where(ScoutFeedbackModel.scout_id == scout.id)).all()
        for fb in feedbacks:
            self.session.delete(fb)
            
        self.session.delete(scout)
        self.session.commit()

    def list_scouts(self) -> List[ScoutModel]:
        """List all scouts."""
        return self.session.exec(select(ScoutModel)).all()

    def get_scout(self, name: str) -> Optional[ScoutModel]:
        """Get a scout by name."""
        return self.session.exec(select(ScoutModel).where(ScoutModel.name == name)).first()

    def _execute_agent_run(self, scout: ScoutModel, config: dict, agent_tools: list, limit: int, 
                          override_query: str = None, retry_attempt: int = 0, retry_modifications: dict = None) -> tuple[List[ContentItem], bool]:
        """Execute a single agent run and return deduplicated items.
        
        Returns:
            tuple: (items, should_retry) where should_retry indicates if retry makes sense
        """
        logger = get_scout_logger(scout.name)
        items = []
        should_retry = True  # Default: retry on empty results
        
        try:
            gen_config = config.get("generation_config", {})
            provider_name = gen_config.get("provider", "gemini")
                
            model_id = gen_config.get("model_id", "gemini-2.5-flash") # Default for tools
            # Get the provider/model
            temperature = gen_config.get("temperature", 0.7)
            provider = self._get_agent_provider(provider_name, model_id, temperature)
            model = provider.get_model()
            
            # Build trace attributes for Langfuse
            trace_attributes = {
                "session.id": scout.name,  # Scout name as session ID
                "user.id": "influencerpy",  # Application identifier
                "langfuse.tags": [
                    f"scout-type:{scout.type}",
                    f"provider:{provider_name}",
                    f"model:{model_id or 'default'}"
                ]
            }
            
            # Initialize agent with tools and tracing
            agent = Agent(
                model=model,
                tools=agent_tools,
                structured_output_model=None,
                callback_handler=null_callback_handler(),
                trace_attributes=trace_attributes
            )
            
            # Apply retry modifications if any
            query = override_query or config.get("query")
            url = config.get("url")
            feeds = config.get("feeds", [])
            subreddits = config.get("subreddits", [])
            tools_config = config.get("tools", [])
            reddit_sort = config.get("reddit_sort", "hot")
            sort_hint = ""
            
            if retry_modifications:
                if "query" in retry_modifications:
                    query = retry_modifications["query"]
                if "feeds" in retry_modifications:
                    feeds = retry_modifications["feeds"]
                if "subreddits" in retry_modifications:
                    subreddits = retry_modifications["subreddits"]
                if "reddit_sort" in retry_modifications:
                    reddit_sort = retry_modifications["reddit_sort"]
                if "sort_hint" in retry_modifications:
                    sort_hint = retry_modifications["sort_hint"]
            
            if scout.type == "meta":
                orchestration_prompt = config.get("orchestration_prompt", "Coordinate the available tools to find interesting content.")
                goal = f"Orchestrate the available tools to: {orchestration_prompt}."
                if override_query or query:
                    goal += f" Focus on: '{override_query or query}'."
            elif url:
                goal = f"Analyze the content at: {url}. Use the 'browser' tool to navigate to the URL and extract the text."
                if query:
                    goal += f" Focus on: '{query}'."
            elif feeds:
                goal = "Find interesting content from ALL your subscribed RSS feeds. Use the 'rss' tool to list available feeds, then read entries from EACH feed to gather diverse content across all sources."
                if query:
                    goal += f" Filter for content related to: '{query}'."
                if retry_attempt > 0:
                    goal += " Try exploring different feeds or looking further back in time to find new content."
            elif subreddits:
                sub_list = ", ".join(subreddits)
                goal = f"Find interesting content from the following subreddits: {sub_list}. Use the 'reddit' tool with sort='{reddit_sort}'."
                if query:
                    goal += f" Filter for content related to: '{query}'."
                if retry_attempt > 0:
                    if sort_hint:
                        goal += f" {sort_hint}."
                    else:
                        goal += " Try exploring different topics or sorting methods to find new content."
            elif "arxiv" in tools_config:
                date_filter = config.get("date_filter")
                days_back_map = {
                    "today": 1,
                    "week": 7,
                    "month": 30
                }
                days_back = days_back_map.get(date_filter)
                
                # On retry, expand the date range
                if retry_attempt > 0 and days_back:
                    days_back = min(days_back * 2, 90)  # Expand but cap at 90 days
                
                goal = f"Find research papers about: \"{query or 'latest research'}\". Use the 'arxiv' tool."
                if days_back:
                    goal += f" Filter for papers from the last {days_back} days."
                if retry_attempt > 0:
                    goal += " Try different search terms or categories to find new papers."
            else:
                goal = f"Find interesting content about: \"{query or 'latest news'}\""
                if retry_attempt > 0:
                    goal += " Try different search terms or angles to find new content."
            
            # Use custom prompt_template if provided, otherwise use auto-generated goal
            user_instructions = scout.prompt_template or goal
            
            # Build structured system prompt
            system_prompt = SystemPrompt(
                general_instructions=GENERAL_GUARDRAILS,
                tool_instructions=build_tool_prompt(tools_config),
                platform_instructions="",  # No platform formatting for content discovery
                user_instructions=user_instructions
            )
            
            # Build final prompt with context
            prompt = system_prompt.build(
                date=datetime.utcnow().strftime('%Y-%m-%d'),
                limit=limit
            )
            
            # Add image generation instructions if enabled
            if config.get("image_generation"):
                prompt += """

ALSO: Generate an image that represents the most interesting content you found.
Use the 'generate_image_stability' tool.
The image should be high quality and relevant to the content.

In your output, populate the "image_path" field for the item that corresponds to the generated image.
The tool will save the image and return the path (or you can infer it from the tool output).
                                If no image was generated, omit the field.
                                """
            
            if retry_attempt > 0:
                logger.info(f"Retry attempt {retry_attempt}: Executing agent with modified parameters...")
            else:
                logger.info("Executing agent...")
            
            try:
                response = agent(prompt, structured_output_model=ScoutResponse)
                logger.info("Agent execution completed.")
                
                data = response.structured_output.items
                for i, entry in enumerate(data):
                    # Check for duplicates via embeddings
                    content_text = f"{entry.title} {entry.summary or ''}"
                    if self.embedding_manager.is_similar(content_text):
                        logger.info(f"Skipping duplicate content: {entry.title}")
                        continue
                        
                    # Index the new content
                    self.embedding_manager.add_item(content_text, source_type="retrieved")
                    
                    items.append(ContentItem(
                        source_id=f"scout_gen_{int(datetime.utcnow().timestamp())}_{i}",
                        title=entry.title,
                        url=entry.url,
                        summary=entry.summary,
                        metadata={"sources": entry.sources, "image_path": entry.image_path}
                    ))
                logger.info(f"Agent found {len(items)} items (after deduplication).")
                
            except Exception as e:
                # Check if it's a structured output error
                from strands.types.exceptions import StructuredOutputException
                if isinstance(e, StructuredOutputException):
                    logger.error("Agent failed to return properly formatted response. This may indicate:")
                    logger.error("  - The prompt may need refinement")
                    logger.error("  - The model may be having difficulty with the task")
                    logger.error("  - Try simplifying your prompt or using a different model")
                    # Don't retry for structured output errors - they won't be fixed by changing parameters
                    raise
                else:
                    logger.error(f"Agent execution failed: {e}", exc_info=True)
                
        except Exception as e:
            # Outer catch for StructuredOutputException to prevent retries
            from strands.types.exceptions import StructuredOutputException
            if isinstance(e, StructuredOutputException):
                # Return empty but don't trigger duplicate retry logic
                should_retry = False  # Don't retry structured output errors
                return items, should_retry
            logger.error(f"Unexpected error in agent run: {e}", exc_info=True)
        
        return items, should_retry

    def _generate_retry_modifications(self, scout: ScoutModel, config: dict, query: str, retry_attempt: int) -> dict:
        """Generate modifications for retry attempts to find different content."""
        modifications = {}
        
        # For Reddit scouts, try different sorting methods and parameters
        if config.get("subreddits"):
            # Cycle through different sorting methods on retries
            sort_methods = ["hot", "new", "top", "rising"]
            current_sort = config.get("reddit_sort", "hot")
            
            # Try a different sort method
            try:
                current_index = sort_methods.index(current_sort)
                next_index = (current_index + retry_attempt) % len(sort_methods)
                modifications["reddit_sort"] = sort_methods[next_index]
            except ValueError:
                # If current sort isn't in our list, start with "new"
                modifications["reddit_sort"] = sort_methods[retry_attempt % len(sort_methods)]
            
            # Also modify the goal to instruct the agent to use the new sort
            sort_instructions = {
                "hot": "trending and popular",
                "new": "most recent and fresh",
                "top": "highest rated and best",
                "rising": "gaining momentum"
            }
            new_sort = modifications["reddit_sort"]
            modifications["sort_hint"] = f"Focus on {sort_instructions.get(new_sort, 'different')} content"
        
        # For RSS scouts, try different feeds or increase time range
        elif config.get("feeds"):
            # On retry, suggest exploring different feeds
            modifications["query"] = query + " (try different feeds or older entries)" if query else "try different feeds or older entries"
        
        # For search-based scouts, modify the query slightly
        elif query and "arxiv" not in config.get("tools", []):
            # Try adding variations to the query
            variations = [
                query + " recent developments",
                query + " latest updates",
                query + " new findings",
                "alternative perspectives on " + query
            ]
            if retry_attempt <= len(variations):
                modifications["query"] = variations[retry_attempt - 1]
        
        # For arxiv scouts, expand date range is handled in goal construction
        
        return modifications

    def run_scout(self, scout: ScoutModel, limit: int = 10, override_query: str = None, override_config: dict = None) -> List[ContentItem]:
        """Execute a scout to fetch content.
        
        If all items found are duplicates, the scout will automatically retry with modified
        parameters (e.g., different query variations, expanded date ranges, different feeds).
        The number of retries is configurable via the 'max_retries' config option (default: 2).
        """
        logger = get_scout_logger(scout.name)
        logger.info(f"Starting scout run: {scout.name}")
        
        # Capture Strands logs
        strands_logger = logging.getLogger("strands")
        strands_logger.setLevel(logging.DEBUG)
        
        # Find file handler to attach
        file_handler = None
        for h in logger.handlers:
            if isinstance(h, logging.FileHandler):
                file_handler = h
                break
        
        if file_handler:
            strands_logger.addHandler(file_handler)
            
        try:
            config = json.loads(scout.config_json)
            
            # Apply overrides
            if override_config:
                config.update(override_config)
                logger.info(f"Applied config overrides: {override_config}")
            
            items = []
            
            # Initialize Langfuse if enabled globally
            # We check if setup_langfuse returns True, which implies env vars are set.
            # We no longer check config.get("langfuse_enabled") per scout.
            if setup_langfuse():
                logger.info("Langfuse tracing enabled for this run.")
            else:
                # Silent fail or debug log if not configured, as it's optional
                logger.debug("Langfuse not configured or setup failed.")
            
            # Check for tools
            tools_config = config.get("tools", [])
            if tools_config:
                # Set scout_id in environment for RSS feed isolation
                os.environ["INFLUENCERPY_SCOUT_ID"] = str(scout.id)
                
                # Initialize Agent with selected tools
                agent_tools = []
                if "rss" in tools_config:
                    # Set environment variable for isolated RSS storage before tool execution
                    # Use scout name (sanitized) for isolation
                    safe_name = "".join(c for c in scout.name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
                    import tempfile
                    isolated_path = os.path.join(tempfile.gettempdir(), "strands_rss_feeds", safe_name)
                    os.environ["STRANDS_RSS_STORAGE_PATH"] = isolated_path
                    
                    # Import the local RSS tool
                    # Note: Since we modified src/influencerpy/tools/rss.py to use the env var dynamically via property,
                    # we don't need to reload or re-instantiate the manager. Setting the env var is enough 
                    # IF the tool reads it on access. 
                    # However, the rss_manager is instantiated at module level in the local rss.py.
                    # My previous edit to rss.py changed __init__ to pass, and added a property storage_path.
                    # This ensures that every time storage_path is accessed (e.g. by get_feed_file_path), 
                    # it reads the current env var.
                    
                    from influencerpy.tools import rss as local_rss
                    agent_tools.append(local_rss.rss)
                if "browser" in tools_config:
                    browser = LocalChromiumBrowser()
                    
                    # Wrap to ignore 'agent' and 'event_loop_cycle_id' argument injected by Strands
                    def browser_wrapper(browser_input, agent=None, event_loop_cycle_id=None, **kwargs):
                        try:
                            # browser_input is the tool_use object
                            tool_args = browser_input.get("input", {})
                            tool_use_id = browser_input.get("toolUseId")
                            
                            # Unpack arguments
                            if isinstance(tool_args, dict):
                                result = browser.browser(**tool_args)
                            else:
                                result = browser.browser(tool_args)
                            
                            response = {
                                "toolUseId": tool_use_id
                            }

                            if isinstance(result, dict):
                                response["status"] = result.get("status", "success")
                                response["output"] = result
                                if "content" in result:
                                    response["content"] = result["content"]
                                else:
                                    response["content"] = [{"json": result}]
                            elif isinstance(result, str):
                                response["status"] = "success"
                                response["output"] = result
                                response["content"] = [{"text": result}]
                            else:
                                response["status"] = "success"
                                response["output"] = result
                                response["content"] = [{"text": str(result)}]
                            
                            return response
                        except Exception as e:
                            return {
                                "status": "error", 
                                "output": str(e),
                                "content": [{"text": str(e)}],
                                "toolUseId": browser_input.get("toolUseId")
                            }

                    agent_tools.append(PythonAgentTool(
                        tool_name=browser.browser.tool_spec['name'],
                        tool_spec=browser.browser.tool_spec,
                        tool_func=browser_wrapper
                    ))
                if "google_search" in tools_config:
                    agent_tools.append(google_search)
                if "reddit" in tools_config:
                    agent_tools.append(reddit)
                if "arxiv" in tools_config:
                    agent_tools.append(arxiv_search)
                if "http_request" in tools_config:
                    agent_tools.append(http_request)
                
                # Check for image generation
                if config.get("image_generation"):
                    agent_tools.append(PythonAgentTool(
                        tool_name=generate_image_stability.TOOL_SPEC['name'],
                        tool_spec=generate_image_stability.TOOL_SPEC,
                        tool_func=generate_image_stability.generate_image_stability
                    ))

                if agent_tools:
                    logger.info(f"Initializing agent with tools: {[t.tool_name for t in agent_tools]}")
                    
                    # Get max retries from config (default 2)
                    max_retries = config.get("max_retries", 2)
                    query = override_query or config.get("query")
                    
                    # Initial run
                    retry_attempt = 0
                    items, should_retry = self._execute_agent_run(
                        scout, config, agent_tools, limit, override_query, retry_attempt
                    )
                    
                    # Retry if all items were duplicates (but not for structured output errors)
                    retry_count = 0
                    while len(items) == 0 and should_retry and retry_count < max_retries:
                        retry_count += 1
                        retry_attempt = retry_count
                        
                        logger.info(f"All items were duplicates. Retrying with different parameters (attempt {retry_count}/{max_retries})...")
                        
                        # Generate retry modifications
                        retry_modifications = self._generate_retry_modifications(
                            scout, config, query, retry_count
                        )
                        
                        # Execute retry
                        retry_items, should_retry = self._execute_agent_run(
                            scout, config, agent_tools, limit, override_query, retry_attempt, retry_modifications
                        )
                        
                        if retry_items:
                            items = retry_items
                            logger.info(f"Retry successful! Found {len(items)} new items.")
                            break
                        elif not should_retry:
                            logger.warning("Retry aborted due to model/prompt error (not duplicate content).")
                            break
                        else:
                            logger.info(f"Retry {retry_count} found no new items.")
                    
                    if len(items) == 0 and retry_count > 0 and should_retry:
                        logger.warning(f"All retry attempts exhausted. No new content found after {retry_count} retries.")
            
            # Update last run
            scout.last_run = datetime.utcnow()
            self.session.add(scout)
            self.session.commit()
            
            return items
        finally:
            # Cleanup Strands logger
            if file_handler:
                strands_logger.removeHandler(file_handler)

    def record_feedback(self, scout_id: int, item: ContentItem, action: str, feedback: str = None):
        """Record user feedback for optimization."""
        fb = ScoutFeedbackModel(
            scout_id=scout_id,
            content_url=item.url,
            action=action,
            feedback_text=feedback
        )
        self.session.add(fb)
        self.session.commit()

    def record_calibration(self, scout_id: int, content_url: str, draft: str, feedback: str):
        """Record calibration feedback for prompt refinement."""
        calibration = ScoutCalibrationModel(
            scout_id=scout_id,
            content_item_url=content_url,
            generated_draft=draft,
            user_feedback=feedback
        )
        self.session.add(calibration)
        self.session.commit()

    def get_calibration_count(self, scout_id: int) -> int:
        """Get the number of calibrations for a scout."""
        calibrations = self.session.exec(
            select(ScoutCalibrationModel).where(ScoutCalibrationModel.scout_id == scout_id)
        ).all()
        return len(calibrations)

    def apply_calibration_feedback(self, scout: ScoutModel, feedback: str):
        """Apply calibration feedback to refine the scout's system prompt."""
        
        current_prompt = scout.prompt_template or "Summarize this content and highlight key takeaways for a social media audience."
        
        # Meta-prompt to have the LLM refine the prompt itself
        optimizer_prompt = f"""
        You are an Expert Prompt Engineer.
        
        Your task is to improve a System Prompt based on user feedback about its output.
        
        Current System Prompt:
        "{current_prompt}"
        
        User Feedback on Output:
        "{feedback}"
        
        Instructions:
        1. Analyze the feedback to understand what was wrong or missing in the output.
        2. Rewrite the System Prompt to incorporate this new instruction/constraint naturally.
        3. Keep the core goal (summarizing/highlighting takeaways) but refine the tone/style instructions.
        4. Return ONLY the new System Prompt text. Do not add explanations.
        """
        
        try:
            agent = self._get_agent_provider() # Use default provider for optimization
            new_prompt = agent.generate(optimizer_prompt).strip()
            
            # Remove quotes if the LLM wrapped it
            if new_prompt.startswith('"') and new_prompt.endswith('"'):
                new_prompt = new_prompt[1:-1]
                
            scout.prompt_template = new_prompt
            self.session.add(scout)
            self.session.commit()
            return True
        except Exception as e:
            # Fallback: just append if AI fails
            return False

    def select_best_content(self, items: List[ContentItem], scout: ScoutModel) -> Optional[ContentItem]:
        """Use AI to select the best content item from a list."""
        if not items:
            return None
        
        if len(items) == 1:
            return items[0]
        
        # Build prompt with all items
        items_text = "\n\n".join([
            f"Option {i+1}:\nTitle: {item.title}\nURL: {item.url}\nSummary: {item.summary or 'N/A'}"
            for i, item in enumerate(items)
        ])
        
        # Build structured system prompt for content selection
        user_instructions = scout.prompt_template or "Select the best content for social media audience engagement."
        
        system_prompt = SystemPrompt(
            general_instructions=GENERAL_GUARDRAILS,
            tool_instructions="",  # No tools needed for selection
            platform_instructions="",  # No platform formatting yet
            user_instructions=user_instructions
        )
        
        prompt = system_prompt.build()
        
        prompt += f"""

Here are the available content options:

{items_text}

Analyze each option based on:
1. Relevance to the scout's goal
2. Engagement potential (interesting, timely, shareable)
3. Content quality and credibility

Respond with ONLY the number of the best option (e.g., "1" or "2" or "3").
"""
        
        try:
            agent = self._get_agent_provider()
            response = agent.generate(prompt).strip()
            
            # Extract number from response
            import re
            match = re.search(r'\d+', response)
            if match:
                selected_idx = int(match.group()) - 1
                if 0 <= selected_idx < len(items):
                    return items[selected_idx]
        except Exception as e:
            # Fall back to first item if AI selection fails
            pass
        
        return items[0]

    def optimize_scout(self, scout: ScoutModel) -> str:
        """
        Simple LLM-based optimizer.
        Analyzes feedback and suggests a better query/prompt.
        """
        # Fetch feedback
        feedbacks = self.session.exec(
            select(ScoutFeedbackModel).where(ScoutFeedbackModel.scout_id == scout.id)
        ).all()
        
        if not feedbacks:
            return "No feedback available to optimize."

        # Prepare context for LLM
        approved = [f.content_url for f in feedbacks if f.action == "approved"]
        rejected = [f"{f.content_url} (Reason: {f.feedback_text})" for f in feedbacks if f.action == "rejected"]
        
        config = json.loads(scout.config_json)
        current_query = config.get("query", "N/A")

        prompt = f"""
        You are an expert Search Query Optimizer.
        
        Current Query: "{current_query}"
        
        User Feedback:
        - Approved Items (Good): {len(approved)} items
        - Rejected Items (Bad): {len(rejected)} items
        
        Rejected Examples:
        {json.dumps(rejected[:5], indent=2)}
        
        Task:
        Analyze the rejected items and their reasons.
        Propose a refined search query that excludes the bad results while keeping the good ones.
        Return ONLY the new query string.
        """
        
        # Call LLM using default provider
        try:
            agent = self._get_agent_provider()
            new_query = agent.generate(prompt)
            
            # Update config
            config["query"] = new_query
            scout.config_json = json.dumps(config)
            self.session.add(scout)
            self.session.commit()
            
            return f"Optimization successful! New query: {new_query}"
        except Exception as e:
            return f"Optimization failed: {e}"

    def generate_draft(self, scout: ScoutModel, item: ContentItem) -> str:
        """Generate a draft post using the configured LLM."""
        config = json.loads(scout.config_json)
        gen_config = config.get("generation_config", {})

        provider_name = gen_config.get("provider", "gemini")
        model_id = gen_config.get("model_id") # Let factory handle default if None
        temperature = gen_config.get("temperature", 0.7)

        # Detect platform from scout config (default to "x" for Twitter)
        platforms = json.loads(scout.platforms) if scout.platforms else []
        platform = platforms[0] if platforms else "x"

        # Build structured system prompt for post generation
        user_instructions = scout.prompt_template or "Summarize this content and highlight key takeaways for a social media audience."

        system_prompt = SystemPrompt(
            general_instructions=GENERAL_GUARDRAILS,
            tool_instructions="",  # No tools needed for generation
            platform_instructions=get_platform_instructions(platform),
            user_instructions=user_instructions
        )

    def format_scouting_output(self, scout: ScoutModel, items: List[ContentItem]) -> str:
        """Format content items as a curated list (for scouting intent).
        
        Args:
            scout: The scout that found the content
            items: List of content items to format
            
        Returns:
            Formatted markdown text with titles, summaries, and links
        """
        output = []
        output.append(f"# 📚 {scout.name} - Content Discovery\n")
        output.append(f"*Found {len(items)} interesting item{'s' if len(items) != 1 else ''}*\n")
        
        for i, item in enumerate(items, 1):
            output.append(f"\n## {i}. {item.title}")
            output.append(f"\n{item.summary}\n")
            output.append(f"🔗 **Source:** {item.url}")
            
            # Add additional sources if available
            sources = item.metadata.get("sources")
            if sources and len(sources) > 0:
                output.append(f"\n📎 **Related:** {', '.join(sources[:3])}")
            
            output.append("\n" + "-" * 50)
        
        return "\n".join(output)
    
    def generate_draft(self, scout: ScoutModel, item: ContentItem) -> str:
        """Generate a draft post using the configured LLM (for generation intent)."""
        config = json.loads(scout.config_json)
        gen_config = config.get("generation_config", {})

        provider_name = gen_config.get("provider", "gemini")
        model_id = gen_config.get("model_id") # Let factory handle default if None
        temperature = gen_config.get("temperature", 0.7)

        # Detect platform from scout config (default to "x" for Twitter)
        platforms = json.loads(scout.platforms) if scout.platforms else []
        platform = platforms[0] if platforms else "x"

        # Build structured system prompt for post generation
        user_instructions = scout.prompt_template or "Summarize this content and highlight key takeaways for a social media audience."

        system_prompt = SystemPrompt(
            general_instructions=GENERAL_GUARDRAILS,
            tool_instructions="",  # No tools needed for generation
            platform_instructions=get_platform_instructions(platform),
            user_instructions=user_instructions
        )
        
        prompt = system_prompt.build()
        
        prompt += f"""

Content Title: {item.title}
Content URL: {item.url}
Content Summary: {item.summary or 'N/A'}

Generate a social media post based on the above.

CRITICAL OUTPUT INSTRUCTIONS:
1. Output ONLY the raw text of the social media post.
2. Do NOT include any conversational filler like "Here is the post" or "Sure!".
3. Do NOT use markdown code blocks (no ```).
4. Do NOT include the title or URL again unless it's naturally part of the post.
5. Start directly with the first word of the post.
        """
        
        try:
            agent = self._get_agent_provider(provider_name, model_id, temperature)
            draft = agent.generate(prompt)
            
            # Index the generated draft to prevent self-plagiarism
            self.embedding_manager.add_item(draft, source_type="generated")
            
            return draft
        except Exception as e:
            # Propagate ValueError for missing key handling in main.py
            if "GEMINI_API_KEY" in str(e):
                raise ValueError("GEMINI_API_KEY not found")
            return f"{item.title}\n{item.url} (Error generating draft: {e})"

    def regenerate_draft_from_feedback(self, post_content: str, feedback: str, platform: str = "x") -> str:
        """Regenerate a draft based on user feedback."""
        # Build system prompt
        system_prompt = SystemPrompt(
            general_instructions=GENERAL_GUARDRAILS,
            tool_instructions="",
            platform_instructions=get_platform_instructions(platform),
            user_instructions="Refine the social media post based on user feedback."
        )
        
        prompt = system_prompt.build()
        
        prompt += f"""
        
        Original Draft:
        "{post_content}"
        
        User Feedback:
        "{feedback}"
        
        Task:
        Rewrite the draft to incorporate the feedback.
        Keep the same core message unless the feedback says otherwise.
        
        CRITICAL OUTPUT INSTRUCTIONS:
        1. Output ONLY the raw text of the new post.
        2. Do NOT use markdown code blocks.
        3. Start directly with the first word.
        """
        
        try:
            agent = self._get_agent_provider() # Use default provider
            new_draft = agent.generate(prompt)
            
            # Index the new draft
            self.embedding_manager.add_item(new_draft, source_type="generated")
            
            return new_draft
        except Exception as e:
            return f"Error regenerating draft: {e}"
