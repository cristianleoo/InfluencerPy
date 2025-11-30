"""Test the SystemPrompt dataclass."""
from influencerpy.core.prompts import SystemPrompt
from influencerpy.types.prompts import (
    GENERAL_GUARDRAILS,
    build_tool_prompt,
    get_platform_instructions,
)


def test_basic_prompt():
    """Test basic prompt construction."""
    prompt = SystemPrompt(
        general_instructions="You are a helpful assistant.",
        tool_instructions="Use tool A and tool B.",
        platform_instructions="Format for Twitter.",
        user_instructions="Find AI news"
    )
    
    result = prompt.build()
    
    assert "You are a helpful assistant" in result
    assert "Use tool A and tool B" in result
    assert "Format for Twitter" in result
    assert "YOUR GOAL: Find AI news" in result
    print("✅ Basic prompt test passed")


def test_with_context():
    """Test prompt with context variables."""
    prompt = SystemPrompt(
        general_instructions=GENERAL_GUARDRAILS,
        user_instructions="Find tech articles"
    )
    
    result = prompt.build(date="2025-11-28", limit=5)
    
    assert "CONTEXT:" in result
    assert "date: 2025-11-28" in result
    assert "limit: 5" in result
    print("✅ Context injection test passed")


def test_tool_instructions():
    """Test tool instructions builder."""
    tools = ["google_search", "rss", "arxiv"]
    instructions = build_tool_prompt(tools)
    
    assert "google_search" in instructions
    assert "rss" in instructions
    assert "arxiv" in instructions
    assert "AVAILABLE TOOLS:" in instructions
    print("✅ Tool instructions test passed")


def test_platform_instructions():
    """Test platform instructions."""
    x_instructions = get_platform_instructions("x")
    linkedin_instructions = get_platform_instructions("linkedin")
    unknown = get_platform_instructions("unknown")
    
    assert "280 characters" in x_instructions
    assert "3000 characters" in linkedin_instructions
    assert unknown == ""
    print("✅ Platform instructions test passed")


def test_empty_components():
    """Test handling of empty components."""
    prompt = SystemPrompt(
        general_instructions="",
        tool_instructions="",
        platform_instructions="",
        user_instructions="Find content"
    )
    
    result = prompt.build()
    
    assert "YOUR GOAL: Find content" in result
    # Empty components shouldn't add extra newlines
    assert result.count("\n\n") <= 1
    print("✅ Empty components test passed")


def test_full_scout_prompt():
    """Test a complete scout scenario with all components."""
    tools = ["google_search", "rss"]
    tool_prompt = build_tool_prompt(tools)
    platform_prompt = get_platform_instructions("x")
    
    prompt = SystemPrompt(
        general_instructions=GENERAL_GUARDRAILS,
        tool_instructions=tool_prompt,
        platform_instructions=platform_prompt,
        user_instructions="Find trending AI news"
    )
    
    result = prompt.build(date="2025-11-28", limit=10)
    
    # Check all components are present
    assert "professional content scout" in result.lower()
    assert "google_search" in result
    assert "rss" in result
    assert "280 characters" in result
    assert "YOUR GOAL: Find trending AI news" in result
    assert "date: 2025-11-28" in result
    assert "limit: 10" in result
    print("✅ Full scout prompt test passed")


def test_linkedin_platform():
    """Test LinkedIn-specific formatting."""
    linkedin = get_platform_instructions("linkedin")
    
    assert "professional" in linkedin.lower()
    assert "3000 characters" in linkedin.lower()
    print("✅ LinkedIn platform test passed")


def test_multiple_tools():
    """Test building instructions for multiple tools."""
    all_tools = ["google_search", "rss", "reddit", "arxiv", "browser"]
    instructions = build_tool_prompt(all_tools)
    
    for tool in all_tools:
        assert tool in instructions
    
    assert instructions.count("TOOL:") == len(all_tools)
    print("✅ Multiple tools test passed")


if __name__ == "__main__":
    test_basic_prompt()
    test_with_context()
    test_tool_instructions()
    test_platform_instructions()
    test_empty_components()
    test_full_scout_prompt()
    test_linkedin_platform()
    test_multiple_tools()
    
    print("\n✅ All SystemPrompt tests passed!")
    print(f"Total: 8 tests")
