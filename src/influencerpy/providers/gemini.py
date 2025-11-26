import os
from strands import Agent
from strands.handlers.callback_handler import null_callback_handler
from strands.models.gemini import GeminiModel
from influencerpy.core.interfaces import AgentProvider

class GeminiProvider(AgentProvider):
    """Gemini implementation using Strands Agents SDK."""
    
    def __init__(self, model_id: str = "gemini-pro", temperature: float = 0.7):
        self.model_id = model_id
        self.temperature = temperature
        self._agent = None
        
    def _get_agent(self) -> Agent:
        """Lazy initialization of the Strands Agent."""
        if self._agent:
            return self._agent
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
            
        model = GeminiModel(
            client_args={
                "api_key": api_key,
            },
            model_id=self.model_id,
            params={
                "temperature": self.temperature,
                "max_output_tokens": 2048,
            }
        )
        
        self._agent = Agent(
            model=model,
            callback_handler=null_callback_handler()
        )
        return self._agent

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using the configured Gemini model."""
        agent = self._get_agent()
        response = agent(prompt)
        return str(response).strip()
