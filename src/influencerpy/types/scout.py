from typing import List, Optional
from pydantic import BaseModel, Field

class ScoutItem(BaseModel):
    """A single content item found by the scout."""
    title: str = Field(description="The title of the content.")
    url: str = Field(description="The URL of the content.")
    summary: str = Field(description="A brief summary of the content.")
    sources: List[str] = Field(description="List of source URLs or titles used to find this content.", default_factory=list)
    image_path: Optional[str] = Field(description="Path to the generated image, if any.", default=None)

class ScoutResponse(BaseModel):
    """The response from the scout agent."""
    items: List[ScoutItem] = Field(description="List of content items found.")
