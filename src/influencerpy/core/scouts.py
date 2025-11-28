import json
import os
from typing import List, Optional
from datetime import datetime
from sqlmodel import select

from strands import Agent
from influencerpy.tools.rss_tool import rss
from influencerpy.tools.http_tool import http_request
from influencerpy.tools.image_generation import generate_image_stability
from influencerpy.tools.search import google_search
from influencerpy.tools.reddit import reddit
from influencerpy.tools.arxiv_tool import arxiv_search

from influencerpy.database import get_session, ScoutModel, ScoutFeedbackModel, ScoutCalibrationModel
from influencerpy.core.models import ContentItem
from influencerpy.config import ConfigManager
from influencerpy.providers.gemini import GeminiProvider
from influencerpy.providers.anthropic import AnthropicProvider
from influencerpy.core.interfaces import AgentProvider
from influencerpy.logger import get_scout_logger
import logging

class ScoutManager:
    def __init__(self):
        self.session = next(get_session())
        self.config_manager = ConfigManager()

    def _get_agent_provider(self, provider_name: str = None, model_id: str = None, temperature: float = 0.7) -> AgentProvider:
        """Factory to get the appropriate agent provider."""
        if not provider_name:
            provider_name = self.config_manager.get("ai.default_provider", "gemini")
            
        if provider_name == "gemini":
            if not model_id:
                model_id = self.config_manager.get("ai.providers.gemini.default_model", "gemini-pro")
            return GeminiProvider(model_id=model_id, temperature=temperature)
            
        elif provider_name == "anthropic":
            if not model_id:
                model_id = self.config_manager.get("ai.providers.anthropic.default_model", "claude-3-opus")
            return AnthropicProvider(model_id=model_id, temperature=temperature)
            
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def create_scout(self, name: str, type: str, config: dict, prompt_template: str = None, schedule_cron: str = None, platforms: list = None, telegram_review: bool = False) -> ScoutModel:
        """Create a new Scout configuration."""
        scout = ScoutModel(
            name=name,
            type=type,
            config_json=json.dumps(config),
            prompt_template=prompt_template,
            schedule_cron=schedule_cron,
            platforms=json.dumps(platforms or []),
            telegram_review=telegram_review
        )
        self.session.add(scout)
        self.session.commit()
        self.session.refresh(scout)
        return scout

    def update_scout(self, scout: ScoutModel, name: str = None, config: dict = None, schedule_cron: str = None, prompt_template: str = None, telegram_review: bool = None) -> ScoutModel:
        """Update an existing Scout."""
        if name:
            scout.name = name
        if config:
            scout.config_json = json.dumps(config)
        if schedule_cron is not None: # Allow clearing schedule with empty string if needed, but None means no change
            scout.schedule_cron = schedule_cron
        if prompt_template is not None:
            scout.prompt_template = prompt_template
        if telegram_review is not None:
            scout.telegram_review = telegram_review
            
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

    def run_scout(self, scout: ScoutModel, limit: int = 10, override_query: str = None, override_config: dict = None) -> List[ContentItem]:
        """Execute a scout to fetch content."""
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
            
            # Check for tools
            tools_config = config.get("tools", [])
            if tools_config:
                # Initialize Agent with selected tools
                agent_tools = []
                if "rss" in tools_config:
                    agent_tools.append(rss)
                if "http_request" in tools_config:
                    agent_tools.append(http_request)
                if "google_search" in tools_config:
                    agent_tools.append(google_search)
                if "reddit" in tools_config:
                    agent_tools.append(reddit)
                if "arxiv" in tools_config:
                    agent_tools.append(arxiv_search)
                
                # Check for image generation
                if config.get("image_generation"):
                    agent_tools.append(generate_image_stability)

                # Check for meta scout (Agents as Tools)
                if scout.type == "meta":
                    from influencerpy.core.meta_scout import create_scout_tool
                    child_scout_names = config.get("child_scouts", [])
                    for name in child_scout_names:
                        child_scout = self.get_scout(name)
                        if child_scout:
                            # Create a tool for this scout
                            # Pass self (ScoutManager) to the factory
                            tool_func = create_scout_tool(child_scout, self)
                            agent_tools.append(tool_func)
                            logger.info(f"Added child scout tool: {tool_func.tool_name}")
                    
                if agent_tools:
                    logger.info(f"Initializing agent with tools: {[t.tool_name for t in agent_tools]}")
                    try:
                        # Get provider/model from config or default
                        provider = self._get_agent_provider() 
                        
                        # Let's create a new Agent here using the configured model
                        # We need to get the model configuration
                        gen_config = config.get("generation_config", {})
                        provider_name = gen_config.get("provider", "gemini")
                        
                        # We only support Gemini for tools right now as per user request (search tool uses Gemini)
                        # And Strands Agent needs a model.
                        
                        from strands.models.gemini import GeminiModel
                        from strands.handlers.callback_handler import null_callback_handler
                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY not found")
                            
                        model_id = gen_config.get("model_id", "gemini-2.5-flash") # Default for tools
                        
                        model = GeminiModel(
                            client_args={"api_key": api_key},
                            model_id=model_id,
                            params={"temperature": 0.7}
                        )
                        
                        agent = Agent(
                            model=model, 
                            tools=agent_tools,
                            callback_handler=null_callback_handler()
                        )
                        
                        query = override_query or config.get("query")
                        url = config.get("url")
                        feeds = config.get("feeds", [])
                        subreddits = config.get("subreddits", [])
                        
                        if url:
                            goal = f"Analyze the content at: {url}"
                            if query:
                                goal += f" Focus on: '{query}'."
                        elif feeds:
                            feed_list = "\n- ".join(feeds)
                            goal = f"Find interesting content from the following RSS feeds:\n{feed_list}\n\nUse the 'rss' tool with action='fetch' to read these feeds."
                            if query:
                                goal += f" Filter for content related to: '{query}'."
                        elif subreddits:
                            sub_list = ", ".join(subreddits)
                            goal = f"Find interesting content from the following subreddits: {sub_list}. Use the 'reddit' tool."
                            if query:
                                goal += f" Filter for content related to: '{query}'."
                        elif "arxiv" in tools_config:
                            date_filter = config.get("date_filter")
                            days_back_map = {
                                "today": 1,
                                "week": 7,
                                "month": 30
                            }
                            days = days_back_map.get(date_filter)
                            
                            if days:
                                goal = f"Find research papers about: \"{query or 'latest research'}\" published within the last {days} days. Use the 'arxiv_search' tool with days_back={days}."
                            else:
                                goal = f"Find research papers about: \"{query or 'latest research'}\". Use the 'arxiv_search' tool."
                        elif scout.type == "meta":
                            orchestration_prompt = config.get("orchestration_prompt", "Coordinate the child scouts to find interesting content.")
                            goal = f"Orchestrate the child scouts to: {orchestration_prompt}. Use the available scout tools."
                        else:
                            goal = f"Find interesting content about: \"{query or 'latest news'}\""
                            
                        prompt = f"""
                        You are a content scout. Your goal is to: {goal}.
                        
                        Use your tools to find relevant articles, news, or posts.
                        
                        Return a JSON list of at most {limit} items. 
                        Each item must have:
                        - "title": str
                        - "url": str
                        - "summary": str (brief summary)
                        - "sources": List[str] (list of source URLs or titles used)
                        
                        Output ONLY valid JSON.
                        """
                        
                        if config.get("image_generation"):
                            prompt += """
                            
                            ALSO: Generate an image that represents the most interesting content you found.
                            Use the 'generate_image_stability' tool.
                            The image should be high quality and relevant to the content.
                            
                            In your JSON output, add an "image_path" field to the item that corresponds to the generated image.
                            The tool will save the image and return the path (or you can infer it from the tool output).
                            If no image was generated, omit the field.
                            """
                        
                        logger.info("Executing agent...")
                        response = agent(prompt)
                        logger.info("Agent execution completed.")
                        
                        # Parse JSON response
                        # Clean markdown code blocks if present
                        text = str(response).strip()
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.endswith("```"):
                            text = text[:-3]
                            
                        data = json.loads(text.strip())
                        if isinstance(data, list):
                            for i, entry in enumerate(data):
                                items.append(ContentItem(
                                    source_id=f"scout_gen_{int(datetime.utcnow().timestamp())}_{i}",
                                    title=entry.get("title", "No Title"),
                                    url=entry.get("url", "#"),
                                    summary=entry.get("summary", ""),
                                    metadata={"sources": entry.get("sources", [])}
                                ))
                            logger.info(f"Agent found {len(items)} items.")
                                
                    except Exception as e:
                        logger.error(f"Agent execution failed: {e}", exc_info=True)
            
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
        
        system_prompt = scout.prompt_template or "Summarize this content and highlight key takeaways for a social media audience."
        
        prompt = f"""You are selecting the BEST content for social media posting.

Scout Goal: {system_prompt}

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
        
        system_prompt = scout.prompt_template or "Summarize this content and highlight key takeaways for a social media audience."
        
        prompt = f"""
        {system_prompt}
        
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
            return agent.generate(prompt)
        except Exception as e:
            # Propagate ValueError for missing key handling in main.py
            if "GEMINI_API_KEY" in str(e):
                raise ValueError("GEMINI_API_KEY not found")
            return f"{item.title}\n{item.url} (Error generating draft: {e})"
