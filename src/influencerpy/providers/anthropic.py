from influencerpy.core.interfaces import AgentProvider

class AnthropicProvider(AgentProvider):
    """Anthropic implementation (Placeholder)."""
    
    def __init__(self, model_id: str = "claude-3-opus", temperature: float = 0.7):
        self.model_id = model_id
        self.temperature = temperature

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using Anthropic (Not Implemented)."""
        raise NotImplementedError("Anthropic provider is not yet implemented.")

    def get_model(self) -> "Any":
        """Get the underlying Anthropic model."""
        raise NotImplementedError("Anthropic provider is not yet implemented.")
