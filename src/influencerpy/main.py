import os
import json
import time
from datetime import datetime
import typer
import pyfiglet
import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.markdown import Markdown
from dotenv import load_dotenv, set_key
from sqlmodel import select

from influencerpy.database import create_db_and_tables, get_session, PostModel
from influencerpy.platforms.x_platform import XProvider
from influencerpy.core.scouts import ScoutManager
from influencerpy.core.models import Platform, PostDraft
from influencerpy.logger import get_app_logger
from strands_tools import rss
from influencerpy.tools.reddit import reddit

from pathlib import Path

# Determine project root and load environment variables from there
# This ensures .env is loaded correctly even if running from another directory
PACKAGE_ROOT = Path(__file__).parent.resolve()
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=True)
else:
    load_dotenv(override=True)

app = typer.Typer(name="influencerpy", help="Premium Social Media Automation CLI")
console = Console()
logger = get_app_logger("app")

ENV_FILE = ".env"

def print_header(clear_screen: bool = False):
    """Print the stylized header."""
    if clear_screen:
        console.clear()
    title = pyfiglet.figlet_format("InfluencerPy", font="slant")
    console.print(Align.center(f"[bold magenta]{title}[/bold magenta]"))
    console.print(Align.center("[dim]Premium Social Media Automation[/dim]\n"))

def _setup_credentials():
    """Interactive credential setup with guide."""
    print_header()
    console.print(Panel.fit(
        "[bold cyan]Credential Setup Guide[/bold cyan]\n\n"
        "To use InfluencerPy, you need API keys for the platforms you want to automate.\n"
        "Currently supported: [bold]X (Twitter)[/bold].\n\n"
        "[yellow]How to get X API Keys:[/yellow]\n"
        "1. Go to [link=https://developer.twitter.com/en/portal/dashboard]X Developer Portal[/link]\n"
        "2. Create a Project and App.\n"
        "3. Generate [bold]Consumer Keys[/bold] (API Key & Secret).\n"
        "4. Generate [bold]Authentication Tokens[/bold] (Access Token & Secret) with [italic]Read and Write[/italic] permissions.\n",
        title="Setup Guide",
        border_style="cyan"
    ))
    
    console.print("\n[bold]Enter your keys below (leave empty to skip/keep existing):[/bold]\n")
    
    keys = [
        ("X_API_KEY", "X API Key"),
        ("X_API_SECRET", "X API Secret"),
        ("X_ACCESS_TOKEN", "X Access Token"),
        ("X_ACCESS_TOKEN_SECRET", "X Access Token Secret"),
    ]
    
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            f.write("")
            
    for key, label in keys:
        current = os.getenv(key)
        default_val = current if current else ""
        
        # Use questionary for password input
        value = questionary.password(
            f"{label}:", 
            default=default_val
        ).unsafe_ask()
        
        if value:
            set_key(ENV_FILE, key, value)
            os.environ[key] = value
            
    console.print("\n[bold green]✓ Credentials saved successfully![/bold green]")
    questionary.press_any_key_to_continue().unsafe_ask()

def _build_custom_schedule() -> str:
    """Interactive wizard to build a cron string with multi-select options."""
    freq = questionary.select(
        "Frequency:",
        choices=["Daily", "Weekly", "Monthly", "Interval (e.g. every 4 hours)"]
    ).unsafe_ask()
    
    if freq == "Daily":
        # Multi-select hours
        selected_hours = questionary.checkbox(
            "Select hours to run (you can select multiple):",
            choices=[f"{h:02d}:00" for h in range(24)]
        ).unsafe_ask()
        
        if not selected_hours:
            console.print("[yellow]No hours selected, defaulting to 09:00[/yellow]")
            return "0 9 * * *"
        
        # Extract hours from selections like "09:00" -> 9
        hours = [int(h.split(":")[0]) for h in selected_hours]
        hours_str = ",".join(str(h) for h in sorted(hours))
        return f"0 {hours_str} * * *"
        
    elif freq == "Weekly":
        # Multi-select days
        days_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        selected_days = questionary.checkbox(
            "Select days (you can select multiple):",
            choices=days_options
        ).unsafe_ask()
        
        if not selected_days:
            console.print("[yellow]No days selected, defaulting to Monday[/yellow]")
            return "0 9 * * 1"
        
        time = questionary.text("At what time? (HH:MM)", default="09:00").unsafe_ask()
        hour, minute = time.split(":")
        
        days_map = {
            "Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
            "Thursday": 4, "Friday": 5, "Saturday": 6
        }
        day_nums = [str(days_map[day]) for day in selected_days]
        days_str = ",".join(day_nums)
        
        return f"{int(minute)} {int(hour)} * * {days_str}"
        
    elif freq == "Monthly":
        day_num = questionary.text("Day of month (1-31):", default="1").unsafe_ask()
        time = questionary.text("At what time? (HH:MM)", default="09:00").unsafe_ask()
        hour, minute = time.split(":")
        return f"{int(minute)} {int(hour)} {day_num} * *"
        
    elif freq == "Interval (e.g. every 4 hours)":
        hours = questionary.text("Every how many hours?", default="4").unsafe_ask()
        return f"0 */{hours} * * *"
        
    return ""

def _create_scout_flow(manager):
    """Interactive flow to create a new scout."""
    while True:
        name = questionary.text("Scout Name (e.g., 'Daily AI'):").unsafe_ask()
        if not name or not name.strip():
            console.print("[red]Name cannot be empty.[/red]")
            continue
        
        if manager.get_scout(name):
            console.print(f"[red]A scout with the name '{name}' already exists. Please choose another.[/red]")
            continue
        break
    
    type_choice = questionary.select(
        "Scout Type:",
        choices=[
            questionary.Choice(
                title="🔍 Search (Discover new content by keyword)",
                value="search"
            ),
            questionary.Choice(
                title="📡 RSS (Follow specific feed URLs)",
                value="rss"
            ),
            questionary.Choice(
                title="👾 Reddit (Follow subreddits)",
                value="reddit"
            ),
            questionary.Choice(
                title="🌐 HTTP Request (Monitor a specific URL)",
                value="http_request"
            )
        ]
    ).unsafe_ask()
    
    config = {}
    if type_choice == "search":
        query = questionary.text("Search Query (e.g. 'AI Agents'):").unsafe_ask()
        config["query"] = query
        config["tools"] = ["google_search"]
    elif type_choice == "rss":
        while True:
            feed = questionary.text("RSS Feed URL:").unsafe_ask()
            with console.status("Validating feed..."):
                # Validate using strands rss tool fetch
                try:
                    result = rss(action="fetch", url=feed, max_entries=1)
                    if isinstance(result, list) and len(result) > 0:
                        config["feeds"] = [feed]
                        config["tools"] = ["rss"]
                        break
                    else:
                        console.print("[red]Invalid RSS feed or empty.[/red]")
                        if not questionary.confirm("Try another URL?").unsafe_ask():
                            return # Cancel creation
                except Exception:
                    console.print("[red]Error validating RSS feed.[/red]")
                    if not questionary.confirm("Try another URL?").unsafe_ask():
                        return # Cancel creation
    elif type_choice == "reddit":
        while True:
            subreddit = questionary.text("Subreddit Name (e.g. 'arcteryx'):").unsafe_ask()
            with console.status("Validating subreddit..."):
                try:
                    # Validate using reddit tool
                    result = reddit(subreddit=subreddit, limit=1)
                    if isinstance(result, list) and len(result) > 0:
                        config["subreddits"] = [subreddit]
                        config["tools"] = ["reddit"]
                        break
                    elif isinstance(result, dict) and "error" in result:
                        console.print(f"[red]Error: {result['error']}[/red]")
                        if not questionary.confirm("Try another name?").unsafe_ask():
                            return
                    else:
                        console.print("[red]Subreddit not found or empty.[/red]")
                        if not questionary.confirm("Try another name?").unsafe_ask():
                            return
                except Exception as e:
                    console.print(f"[red]Error validating subreddit: {e}[/red]")
                    if not questionary.confirm("Try another name?").unsafe_ask():
                        return
    elif type_choice == "http_request":
        url = questionary.text("Target URL:").unsafe_ask()
        config["url"] = url
        config["tools"] = ["http_request"]

    # Scheduling
    schedule_choice = questionary.select(
        "Schedule:",
        choices=[
            questionary.Choice("None (Manual Run)", value=None),
            questionary.Choice("Daily (Every morning)", value="0 9 * * *"),
            questionary.Choice("Hourly", value="0 * * * *"),
            questionary.Choice("Create with AI", value="interactive"),
            questionary.Choice("Custom Cron (Advanced)", value="custom")
        ]
    ).unsafe_ask()
    
    schedule_cron = schedule_choice
    if schedule_choice == "custom":
        schedule_cron = questionary.text("Enter Cron Expression (e.g. '0 12 * * 1'):").unsafe_ask()
    elif schedule_choice == "interactive":
        schedule_cron = _build_custom_schedule()
        
    # Tone & Style
    tone = questionary.select(
        "Content Tone:",
        choices=["Professional", "Casual", "Witty", "Urgent", "Inspirational"]
    ).unsafe_ask()
    
    style = questionary.select(
        "Content Style:",
        choices=["Concise", "Detailed", "Storytelling", "Bullet Points"]
    ).unsafe_ask()
    
    prompt_template = f"Summarize this content and highlight key takeaways for a social media audience. Tone: {tone}. Style: {style}."

    # Advanced Configuration
    if questionary.confirm("Configure Advanced Settings (System Prompt, Model, Temperature)?", default=False).unsafe_ask():
        prompt_template = questionary.text(
            "System Prompt:", 
            default=prompt_template
        ).unsafe_ask()
        
        model_id = questionary.text("Model ID:", default="gemini-pro").unsafe_ask()
        temperature = questionary.text("Temperature (0.0 - 1.0):", default="0.7").unsafe_ask()
        config["generation_config"] = {
            "model_id": model_id,
            "temperature": float(temperature)
        }
    
    # Platform Selection
    telegram_review = questionary.confirm(
        "Enable review on Telegram before posting?",
        default=False
    ).unsafe_ask()
    
    # Multi-platform selection (checkbox)
    platform_choices = questionary.checkbox(
        "Select platforms to post to:",
        choices=["X (Twitter)"]  # Add more platforms here as they're implemented
    ).unsafe_ask()
    
    # Map display names to internal platform IDs
    platforms = []
    if "X (Twitter)" in platform_choices:
        platforms.append("x")
    
    manager.create_scout(
        name, type_choice, config, 
        prompt_template=prompt_template, 
        schedule_cron=schedule_cron, 
        platforms=platforms,
        telegram_review=telegram_review
    )
    console.print(f"[green]Scout '{name}' created successfully![/green]")

@app.command()
def init():
    """Initialize the database and configuration."""
    create_db_and_tables()
    console.print("[green]Database initialized successfully![/green]")
    
    if questionary.confirm("Do you want to set up credentials now?").unsafe_ask():
        _setup_credentials()

@app.command()
def configure():
    """Update credentials interactively."""
    _setup_credentials()

@app.command()
def news(
    limit: int = typer.Option(5, help="Number of news items to fetch")
):
    """Fetch and display latest AI news."""
    feeds = [
        "https://news.google.com/rss/search?q=artificial+intelligence",
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
    ]
    
    items = []
    with console.status("[bold green]Fetching news..."):
        for feed_url in feeds:
            try:
                # Use strands rss tool fetch action
                result = rss(action="fetch", url=feed_url, max_entries=limit)
                if isinstance(result, list):
                    for entry in result:
                        # Convert RSS entry to simpler object for display
                        items.append({
                            "title": entry.get("title", "No Title"),
                            "url": entry.get("link", "#"),
                            "published": entry.get("published", "Unknown"),
                            "source": feed_url
                        })
            except Exception as e:
                console.print(f"[red]Error fetching {feed_url}: {e}[/red]")

    # Sort roughly if possible, otherwise just display
    # Strands RSS tool returns formatted dates string, simple sort might not work perfectly but is okay for display
    
    # Slice to limit total
    items = items[:limit]

    table = Table(title="Latest AI News", show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Source", style="dim")

    for item in items:
        # Truncate date for display
        date_str = str(item["published"])[:10]
        table.add_row(
            date_str,
            item["title"],
            item["source"][:30] + "..."
        )

    console.print(table)
    
    # Interactive selection
    if questionary.confirm("Do you want to draft a post from one of these?").unsafe_ask():
        choices = [
            questionary.Choice(
                title=f"{i['title']}",
                value=i
            ) for i in items
        ]
        
        selected_item = questionary.select(
            "Select a news item:",
            choices=choices
        ).unsafe_ask()
        
        if not selected_item:
            return

        console.print(f"\n[bold]Selected:[/bold] {selected_item['title']}")
        
        content = questionary.text(
            "Edit your tweet content:",
            default=f"Checking out: {selected_item['title']}\n{selected_item['url']}",
            multiline=True
        ).unsafe_ask()
        
        if questionary.confirm("Post to X now?").unsafe_ask():
            provider = XProvider()
            if provider.authenticate():
                draft = PostDraft(content=content, platforms=[Platform.X])
                try:
                    with console.status("[bold green]Posting..."):
                        post_id = provider.post(draft)
                    
                    console.print(Panel(f"[bold green]Success![/bold green]\nTweet ID: {post_id}", border_style="green"))
                    
                    # Save to DB
                    with next(get_session()) as session:
                        db_post = PostModel(
                            content=content,
                            platform="x",
                            status="posted",
                            external_id=post_id,
                            posted_at=datetime.utcnow()
                        )
                        session.add(db_post)
                        session.commit()
                        
                except Exception as e:
                    console.print(f"[bold red]Error:[/bold red] {e}")
            else:
                console.print("[bold red]Authentication failed. Please run 'configure'.[/bold red]")

@app.command()
def history():
    """View posting history."""
    with next(get_session()) as session:
        posts = session.exec(select(PostModel).order_by(PostModel.created_at.desc())).all()
    
    table = Table(title="Post History", show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Content", style="white")
    table.add_column("Platform", style="magenta")
    table.add_column("Status", style="green")
    
    for post in posts:
        table.add_row(
            post.created_at.strftime("%Y-%m-%d %H:%M"),
            (post.content[:50] + "...") if post.content else "",
            post.platform,
            post.status
        )
    console.print(table)

@app.command()
def scouts():
    """Manage your Scouts (Tools)."""
    manager = ScoutManager()
    print_header(clear_screen=True)
    
    while True:
        choice = questionary.select(
            "Scout Manager",
            choices=[
                "List Scouts",
                "Create New Scout",
                "Run Scout",
                "Calibrate Scout",
                "Update Scout",
                "Delete Scout",
                "Optimize Scout",
                "Back to Main Menu"
            ]
        ).unsafe_ask()
        
        if choice == "Back to Main Menu":
            break
            
        elif choice == "List Scouts":
            scouts = manager.list_scouts()
            
            if not scouts:
                console.print(Panel("[yellow]No scouts found.[/yellow]", title="Your Scouts"))
                if questionary.confirm("Would you like to create one now?").unsafe_ask():
                    _create_scout_flow(manager)
                    scouts = manager.list_scouts()
                else:
                    continue

            if choice == "List Scouts": # Check again in case we didn't jump to create
                table = Table(title="Your Scouts")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Last Run", style="green")
                
                for s in scouts:
                    table.add_row(s.name, s.type, str(s.last_run) if s.last_run else "-")
                console.print(table)
            
        elif choice == "Create New Scout":
            _create_scout_flow(manager)
            
        elif choice == "Run Scout":
            scouts = manager.list_scouts()
            if not scouts:
                console.print("[red]No scouts found.[/red]")
                continue
                
            s_choice = questionary.select(
                "Select Scout:",
                choices=[s.name for s in scouts]
            ).unsafe_ask()
            
            scout = manager.get_scout(s_choice)
            
            # Fetch content with status message
            try:
                with console.status(f"Fetching content for {scout.name}..."):
                    items = manager.run_scout(scout)
            except Exception as e:
                console.print(f"[red]Error fetching content: {e}[/red]")
                continue

            if not items:
                console.print("[yellow]No content found matching criteria.[/yellow]")
                continue

            # Select best content with AI
            with console.status("Selecting best content..."):
                item = manager.select_best_content(items, scout)
            
            if not item:
                # Fallback just in case
                item = items[0]

            console.print(Panel(f"[bold]{item.title}[/bold]\n{item.url}\n\n[dim]{item.summary}[/dim]", title="Selected Best Content", border_style="blue"))

            # Generate Draft
            draft_content = ""
            try:
                with console.status("Generating draft..."):
                    draft_content = manager.generate_draft(scout, item)
            except ValueError as e:
                if "GEMINI_API_KEY" in str(e):
                    console.print("[yellow]Gemini API Key not found.[/yellow]")
                    key = questionary.password("Enter your Gemini API Key:").unsafe_ask()
                    if key:
                        set_key(ENV_FILE, "GEMINI_API_KEY", key)
                        os.environ["GEMINI_API_KEY"] = key
                        console.print("[green]Key saved! Retrying...[/green]")
                        try:
                            with console.status("Generating draft..."):
                                draft_content = manager.generate_draft(scout, item)
                        except Exception as e2:
                            console.print(f"[red]Error: {e2}[/red]")
                            draft_content = f"{item.title}\n{item.url}"
                    else:
                        console.print("[red]No key provided. Using title/url only.[/red]")
                        draft_content = f"{item.title}\n{item.url}"
                else:
                    console.print(f"[red]Error: {e}[/red]")
                    draft_content = f"{item.title}\n{item.url}"
            except Exception as e:
                console.print(f"[red]Error generating draft: {e}[/red]")
                draft_content = f"{item.title}\n{item.url}"

            # Check if scout has platforms configured
            platforms = json.loads(scout.platforms) if scout.platforms else []
            
            if platforms:
                # Auto-post mode
                console.print(Panel(draft_content, title="AI Draft (Auto-Posting)", border_style="cyan"))
                
                # Check if Telegram review is enabled
                if scout.telegram_review:
                    console.print("[yellow]Telegram review is enabled but not yet implemented.[/yellow]")
                    console.print("[yellow]Posting directly for now...[/yellow]")
                
                # Post to all configured platforms
                for platform in platforms:
                    console.print(f"[cyan]Posting to {platform.upper()}...[/cyan]")
                    try:
                        if platform == "x":
                            from influencerpy.platforms.x_platform import XProvider
                            provider = XProvider()
                            if not provider.authenticate():
                                console.print("[bold red]Authentication failed. Missing X API credentials.[/bold red]")
                                if questionary.confirm("Setup credentials now?").unsafe_ask():
                                    _setup_credentials()
                                    # Try again
                                    if provider.authenticate():
                                        provider.post(draft_content)
                                        console.print(f"[green]Posted to {platform.upper()} successfully![/green]")
                                    else:
                                         console.print(f"[red]Still failed to authenticate.[/red]")
                            else:
                                provider.post(draft_content)
                                console.print(f"[green]Posted to {platform.upper()} successfully![/green]")
                        else:
                            console.print(f"[red]Platform '{platform}' not yet supported[/red]")
                    except Exception as e:
                        console.print(f"[red]Error posting to {platform}: {e}[/red]")
            else:
                # Manual review mode
                while True:
                    # Show Draft
                    console.print(Panel(draft_content, title="AI Draft", border_style="cyan"))
                    
                    review_action = questionary.select(
                        "Review Draft:",
                        choices=["Accept (Edit & Post)", "Redraft (Try Again)", "Skip", "Reject", "Stop"]
                    ).unsafe_ask()
                    
                    if review_action == "Redraft (Try Again)":
                        # Regenerate draft
                        try:
                            with console.status("Regenerating draft..."):
                                draft_content = manager.generate_draft(scout, item)
                        except Exception as e:
                            console.print(f"[red]Error regenerating: {e}[/red]")
                        continue
                    elif review_action == "Skip":
                        break 
                    elif review_action == "Reject":
                        reason = questionary.text("Reason (optional):").unsafe_ask()
                        manager.record_feedback(scout.id, item, "rejected", reason)
                        break 
                    elif review_action == "Stop":
                        break
                    elif review_action == "Accept (Edit & Post)":
                        content = questionary.text("Tweet Content:", default=draft_content).unsafe_ask()
                        
                        # Post Logic
                        console.print(f"[cyan]Posting: {content}[/cyan]")
                        
                        # Select platform
                        platform = questionary.select(
                            "Select Platform:",
                            choices=["X (Twitter)", "Skip"]
                        ).unsafe_ask()
                        
                        if platform == "X (Twitter)":
                            from influencerpy.platforms.x_platform import XProvider
                            try:
                                provider = XProvider()
                                if not provider.authenticate():
                                     console.print("[bold red]Authentication failed. Missing credentials.[/bold red]")
                                     if questionary.confirm("Setup credentials now?").unsafe_ask():
                                         _setup_credentials()
                                         if provider.authenticate():
                                             provider.post(content)
                                             console.print("[green]Posted successfully![/green]")
                                else:
                                    provider.post(content)
                                    console.print("[green]Posted successfully![/green]")
                            except Exception as e:
                                console.print(f"[red]Error posting: {e}[/red]")
                        break # Exit review loop after posting

        elif choice == "Calibrate Scout":
            scouts = manager.list_scouts()
            if not scouts:
                console.print("[red]No scouts found.[/red]")
                continue
            
            s_choice = questionary.select("Select Scout to Calibrate:", choices=[s.name for s in scouts]).unsafe_ask()
            scout = manager.get_scout(s_choice)
            
            calibration_count = manager.get_calibration_count(scout.id)
            console.print(f"[cyan]Current calibrations: {calibration_count}[/cyan]")
            
            # Calibration loop
            while True:
                # Fetch one content item
                with console.status(f"Fetching content for calibration..."):
                    items = manager.run_scout(scout, limit=1)
                
                if not items:
                    console.print("[yellow]No content found. Try again later.[/yellow]")
                    break
                
                item = items[0]
                console.print(Panel(f"[bold]{item.title}[/bold]\n{item.url}", border_style="blue"))
                
                # Generate draft
                try:
                    with console.status("Generating draft..."):
                        draft = manager.generate_draft(scout, item)
                except Exception as e:
                    console.print(f"[red]Error generating draft: {e}[/red]")
                    break
                
                console.print(Panel(draft, title="Generated Draft", border_style="cyan"))
                
                # Get feedback
                feedback = questionary.text(
                    "Provide feedback (or press Enter to finish calibration):",
                    multiline=False
                ).unsafe_ask()
                
                if not feedback or feedback.strip() == "":
                    console.print("[green]Calibration session ended.[/green]")
                    break
                
                # Record calibration
                manager.record_calibration(scout.id, item.url, draft, feedback)
                
                with console.status("Optimizing system prompt with AI..."):
                    if manager.apply_calibration_feedback(scout, feedback):
                        console.print("[green]System prompt refined successfully![/green]")
                    else:
                        console.print("[yellow]Could not refine prompt with AI (using previous version).[/yellow]")
                
                calibration_count += 1
                console.print(f"[green]Calibration recorded! Total: {calibration_count}[/green]")

        elif choice == "Optimize Scout":
            scouts = manager.list_scouts()
            if not scouts:
                console.print("[red]No scouts found.[/red]")
                continue
                
            s_choice = questionary.select("Select Scout to Optimize:", choices=[s.name for s in scouts]).unsafe_ask()
            scout = manager.get_scout(s_choice)
            
            # Check calibration count
            calibration_count = manager.get_calibration_count(scout.id)
            
            if calibration_count < 20:
                console.print(Panel(
                    f"[yellow]Optimization requires at least 20 calibrations.\n\nCurrent calibrations: {calibration_count}\nRemaining: {20 - calibration_count}\n\nUse 'Calibrate Scout' to provide more feedback.[/yellow]",
                    title="Optimization Locked",
                    border_style="yellow"
                ))
                continue
            
            console.print("[yellow]DsPy-based optimization will be available in a future release.[/yellow]")
            console.print(f"[cyan]This scout has {calibration_count} calibrations ready for optimization![/cyan]")

        elif choice == "Update Scout":
            scouts = manager.list_scouts()
            if not scouts:
                console.print("[red]No scouts found.[/red]")
                continue
                
            s_choice = questionary.select("Select Scout to Update:", choices=[s.name for s in scouts]).unsafe_ask()
            scout = manager.get_scout(s_choice)
            
            # What to update?
            update_field = questionary.select(
                "What do you want to update?",
                choices=["Name", "Configuration (Query/Feed)", "Tools", "System Prompt", "Advanced Settings (Model/Temp)", "Schedule", "Cancel"]
            ).unsafe_ask()
            
            if update_field == "Cancel":
                continue
                
            if update_field == "Tools":
                config = json.loads(scout.config_json)
                current_tools = config.get("tools", [])
                
                new_tools = questionary.checkbox(
                    "Select Tools:",
                    choices=[
                        questionary.Choice("rss", checked="rss" in current_tools),
                        questionary.Choice("http_request", checked="http_request" in current_tools),
                        questionary.Choice("google_search", checked="google_search" in current_tools),
                        questionary.Choice("reddit", checked="reddit" in current_tools)
                    ]
                ).unsafe_ask()
                
                config["tools"] = new_tools
                manager.update_scout(scout, config=config)
                console.print("[green]Tools updated![/green]")

            elif update_field == "Name":
                while True:
                    new_name = questionary.text("New Name:", default=scout.name).unsafe_ask()
                    if not new_name or not new_name.strip():
                        console.print("[red]Name cannot be empty.[/red]")
                        continue
                    
                    if new_name != scout.name and manager.get_scout(new_name):
                        console.print(f"[red]A scout with the name '{new_name}' already exists.[/red]")
                        continue
                    break
                    
                manager.update_scout(scout, name=new_name)
                console.print(f"[green]Scout renamed to '{new_name}'![/green]")
                
            elif update_field == "System Prompt":
                new_prompt = questionary.text("New System Prompt:", default=scout.prompt_template or "").unsafe_ask()
                manager.update_scout(scout, prompt_template=new_prompt)
                console.print("[green]System Prompt updated![/green]")

            elif update_field == "Advanced Settings (Model/Temp)":
                config = json.loads(scout.config_json)
                gen_config = config.get("generation_config", {})
                
                current_provider = gen_config.get("provider", "gemini")
                provider = questionary.select(
                    "AI Provider:",
                    choices=["gemini", "anthropic"],
                    default=current_provider
                ).unsafe_ask()
                
                default_model = "gemini-pro" if provider == "gemini" else "claude-3-opus"
                current_model = gen_config.get("model_id", default_model)
                
                model_id = questionary.text("Model ID:", default=current_model).unsafe_ask()
                temperature = questionary.text("Temperature (0.0 - 1.0):", default=str(gen_config.get("temperature", 0.7))).unsafe_ask()
                
                config["generation_config"] = {
                    "provider": provider,
                    "model_id": model_id,
                    "temperature": float(temperature)
                }
                manager.update_scout(scout, config=config)
                console.print("[green]Advanced settings updated![/green]")

            elif update_field == "Configuration (Query/Feed)":
                config = json.loads(scout.config_json)
                if scout.type == "search":
                    new_query = questionary.text("New Search Query:", default=config.get("query", "")).unsafe_ask()
                    config["query"] = new_query
                elif scout.type == "rss":
                    while True:
                        current_feed = config.get("feeds", [""])[0]
                        new_feed = questionary.text("New RSS Feed URL:", default=current_feed).unsafe_ask()
                        with console.status("Validating feed..."):
                            try:
                                result = rss(action="fetch", url=new_feed, max_entries=1)
                                if isinstance(result, list) and len(result) > 0:
                                    config["feeds"] = [new_feed]
                                    break
                                else:
                                    console.print("[red]Invalid RSS feed.[/red]")
                                    if not questionary.confirm("Try again?").unsafe_ask():
                                        break
                            except Exception:
                                console.print("[red]Error validating feed.[/red]")
                                if not questionary.confirm("Try again?").unsafe_ask():
                                    break
                elif scout.type == "reddit":
                    while True:
                        current_sub = config.get("subreddits", [""])[0]
                        new_sub = questionary.text("New Subreddit:", default=current_sub).unsafe_ask()
                        with console.status("Validating subreddit..."):
                            try:
                                result = reddit(subreddit=new_sub, limit=1)
                                if isinstance(result, list) and len(result) > 0:
                                    config["subreddits"] = [new_sub]
                                    break
                                else:
                                    console.print("[red]Invalid subreddit or empty.[/red]")
                                    if not questionary.confirm("Try again?").unsafe_ask():
                                        break
                            except Exception as e:
                                console.print(f"[red]Error validating: {e}[/red]")
                                if not questionary.confirm("Try again?").unsafe_ask():
                                    break
                
                manager.update_scout(scout, config=config)
                console.print("[green]Configuration updated![/green]")
                
            elif update_field == "Schedule":
                schedule_choice = questionary.select(
                    "New Schedule:",
                    choices=[
                        questionary.Choice("None (Manual Run)", value="none"), # Use string 'none' to distinguish from cancel
                        questionary.Choice("Daily (Every morning)", value="0 9 * * *"),
                        questionary.Choice("Hourly", value="0 * * * *"),
                        questionary.Choice("Create with AI", value="interactive"),
                        questionary.Choice("Custom Cron (Advanced)", value="custom")
                    ]
                ).unsafe_ask()
                
                new_cron = None
                if schedule_choice == "none":
                    new_cron = "" # Empty string to clear
                elif schedule_choice == "custom":
                    new_cron = questionary.text("Enter Cron Expression:", default=scout.schedule_cron or "").unsafe_ask()
                elif schedule_choice == "interactive":
                    new_cron = _build_custom_schedule()
                else:
                    new_cron = schedule_choice
                    
                manager.update_scout(scout, schedule_cron=new_cron)
                console.print("[green]Schedule updated![/green]")

        elif choice == "Delete Scout":
            scouts = manager.list_scouts()
            if not scouts:
                console.print("[red]No scouts found.[/red]")
                continue
                
            s_choice = questionary.select("Select Scout to Delete:", choices=[s.name for s in scouts]).unsafe_ask()
            scout = manager.get_scout(s_choice)
            
            if questionary.confirm(f"Are you sure you want to delete '{scout.name}'? This cannot be undone.", default=False).unsafe_ask():
                manager.delete_scout(scout)
                console.print(f"[green]Scout '{scout.name}' deleted.[/green]")
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")

# ... (Update main menu to include Scouts)

from influencerpy.config import ConfigManager

def _setup_config_wizard():
    """Interactive wizard to setup AI configuration."""
    print_header(clear_screen=True)
    console.print("[bold cyan]AI Configuration Wizard[/bold cyan]\n")
    
    config_manager = ConfigManager()
    
    # Select Default Provider
    current_provider = config_manager.get("ai.default_provider", "gemini")
    provider = questionary.select(
        "Select Default AI Provider:",
        choices=["gemini", "anthropic"],
        default=current_provider
    ).unsafe_ask()
    config_manager.set("ai.default_provider", provider)
    
    # Configure Provider Settings
    if provider == "gemini":
        current_model = config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash")
        model_id = questionary.text("Default Gemini Model ID:", default=current_model).unsafe_ask()
        config_manager.set("ai.providers.gemini.default_model", model_id)
        
    elif provider == "anthropic":
        current_model = config_manager.get("ai.providers.anthropic.default_model", "claude-3-opus")
        model_id = questionary.text("Default Claude Model ID:", default=current_model).unsafe_ask()
        config_manager.set("ai.providers.anthropic.default_model", model_id)
        
    console.print("\n[green]Configuration saved successfully![/green]")
    time.sleep(1.5)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Premium Social Media Automation CLI.
    """
    if ctx.invoked_subcommand is None:
        logger.info("Application started")
        # Ensure DB is ready
        create_db_and_tables()
        
        # Check Config
        config_manager = ConfigManager()
        if not config_manager.exists():
            print_header()
            console.print("[bold yellow]Welcome! Let's configure your AI settings.[/bold yellow]")
            if questionary.confirm("Start configuration wizard?").unsafe_ask():
                _setup_config_wizard()
            else:
                config_manager.ensure_config_exists() # Create defaults
        
        # First run check
        if not os.path.exists(ENV_FILE) or not os.getenv("X_API_KEY"):
            print_header()
            console.print("[bold yellow]Welcome! It looks like your first time here.[/bold yellow]")
            if questionary.confirm("Do you want to run the setup wizard?").unsafe_ask():
                _setup_credentials()
                load_dotenv(override=True)

    # ... (rest of main)


    # Interactive Menu Mode
    while True:
        try:
            # Don't clear screen in loop to allow scrolling history
            print_header(clear_screen=False) 
            
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "Manage Scouts",
                    "Fetch News & Draft",
                    "View History",
                    "Configure AI Settings",
                    "Configure Credentials",
                    "Exit"
                ]
            ).unsafe_ask()
            
            if choice == "Manage Scouts":
                scouts()
            elif choice == "Fetch News & Draft":
                news(limit=5)
            elif choice == "View History":
                history()
            elif choice == "Configure AI Settings":
                _setup_config_wizard()
            elif choice == "Configure Credentials":
                _setup_credentials()
            elif choice == "Exit":
                console.print("[yellow]Goodbye![/yellow]")
                logger.info("Application shutdown")
                break
                
        except KeyboardInterrupt:
            console.print("\n") # Newline for cleanliness
            if questionary.confirm("Do you want to quit the application?", default=False).ask():
                console.print("[yellow]Goodbye![/yellow]")
                break
            else:
                continue # Back to main menu
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            if questionary.confirm("Do you want to continue?", default=True).ask():
                continue
            else:
                break

if __name__ == "__main__":
    app()
