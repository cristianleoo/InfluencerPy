"""System prompt dataclass for structured prompt composition."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class SystemPrompt:
    """
    Structured system prompt with separate components.
    Only user_instructions should be editable via UI.
    """
    # Hidden from users - system guardrails
    general_instructions: str = ""
    
    # Hidden from users - tool-specific guidance
    tool_instructions: str = ""
    
    # Hidden from users - platform-specific formatting
    platform_instructions: str = ""
    
    # Visible/editable by users
    user_instructions: str = ""
    
    def build(self, **context: Any) -> str:
        """
        Combine all components into final prompt.
        
        Args:
            **context: Additional context variables to inject (e.g., date, limit)
            
        Returns:
            Complete system prompt string
        """
        # Ensure date is always present in context
        if "date" not in context:
            context["date"] = datetime.utcnow().strftime('%Y-%m-%d')

        sections = []
        
        if self.general_instructions:
            sections.append(self.general_instructions)
        
        if self.tool_instructions:
            sections.append(self.tool_instructions)
        
        if self.user_instructions:
            sections.append(f"YOUR GOAL: {self.user_instructions}")
        
        if self.platform_instructions:
            sections.append(self.platform_instructions)
        
        # Add context variables (date, limit, etc.)
        if context:
            context_lines = []
            for key, value in context.items():
                context_lines.append(f"{key}: {value}")
            if context_lines:
                sections.append(f"CONTEXT:\n" + "\n".join(context_lines))
        
        return "\n\n".join(sections)
