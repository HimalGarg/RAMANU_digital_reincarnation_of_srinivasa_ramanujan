"""
demo.py — Ramanujan Digital Twin Interactive Demo
===================================================
Rich CLI chatbot interface for conversing with the Digital Twin
of Srinivasa Ramanujan.
"""

import os
import sys
import json
import subprocess

# Force UTF-8 encoding on Windows to prevent UnicodeEncodeError with Rich/emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.markdown import Markdown
from rich import box

# ─── Constants ────────────────────────────────────────────────────────────────

HEADER_ART = r"""
[bold yellow]
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║      ██████   █████  ███    ███  █████  ███    ██ ██    ██   ║
    ║      ██   ██ ██   ██ ████  ████ ██   ██ ████   ██ ██    ██   ║
    ║      ██████  ███████ ██ ████ ██ ███████ ██ ██  ██ ██    ██   ║
    ║      ██   ██ ██   ██ ██  ██  ██ ██   ██ ██  ██ ██ ██    ██   ║
    ║      ██   ██ ██   ██ ██      ██ ██   ██ ██   ████  ██████    ║
    ║                                                              ║
    ║            D I G I T A L   T W I N   v 1 . 0                ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
[/bold yellow]
"""

SUBTITLE = "[dim]Srinivasa Ramanujan FRS (1887–1920)[/dim]"

WELCOME_MESSAGE = (
    "Namaskaram. I am Srinivasa Ramanujan, of Kumbakonam, Tamil Nadu. "
    "I have been thinking about numbers — as I always do — and I am "
    "glad of your company.\n\n"
    "I have spent my life in the company of infinite series, continued "
    "fractions, and the deep patterns that hide within the integers. "
    "If you are curious about mathematics, or about my life and work, "
    "I should be happy to share what I know.\n\n"
    "Come, let us explore together. What would you like to discuss?"
)

FAREWELL_MESSAGE = (
    "Numbers are eternal. The identities in my notebooks will outlive "
    "us both, as they have outlived me once already. I am grateful for "
    "our conversation. Until we meet again — may Namagiri guide your "
    "path through the infinite."
)

HELP_TEXT = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]/stats[/cyan]     — View system status (RAG, memory, model info)
  [cyan]/reset[/cyan]     — Reset session memory (start fresh)
  [cyan]/memory[/cyan]    — View long-term memory summary
  [cyan]/visualize[/cyan] — Explicitly request a mathematical visualization (e.g. /visualize partitions)
  [cyan]/help[/cyan]      — Show this help message
  [cyan]/quit[/cyan]      — Save memories and exit

Just type your question or message to chat with Ramanujan.
"""

console = Console()


# Notebook excerpts loading functions removed.


def print_header():
    """Print the startup header."""
    console.print(HEADER_ART)
    console.print(SUBTITLE, justify="center")
    console.print()


def print_initialization(twin):
    """Print initialization checklist."""
    console.print(
        Panel(
            "[green]✓[/green] All systems initialized successfully",
            title="[bold]System Status[/bold]",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    stats = twin.introspect()
    info_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    info_table.add_column("Key", style="dim")
    info_table.add_column("Value", style="bold")
    info_table.add_row("Knowledge Base", f"{stats['rag_documents']} documents loaded")
    info_table.add_row("Model", stats["model"])
    info_table.add_row("Persona", f"{stats['scientist']} v{stats['persona_version']}")
    info_table.add_row("Knowledge Cutoff", str(stats["knowledge_cutoff"]))
    console.print(info_table)
    console.print()


def print_welcome():
    """Print Ramanujan's welcome message."""
    console.print(
        Panel(
            WELCOME_MESSAGE,
            title="[bold yellow]Ramanujan[/bold yellow]",
            border_style="yellow",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )
    console.print()


def display_response(response_text: str):
    """Display Ramanujan's response in a styled panel."""
    console.print(
        Panel(
            response_text,
            title="[bold yellow]Ramanujan[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()


def display_stats(twin):
    """Display system stats as a rich table."""
    stats = twin.introspect()

    table = Table(
        title="Digital Twin System Status",
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        title_style="bold cyan",
    )
    table.add_column("Component", style="bold", width=25)
    table.add_column("Value", style="green")

    table.add_row("Scientist", stats["scientist"])
    table.add_row("Persona Version", stats["persona_version"])
    table.add_row("Knowledge Cutoff", str(stats["knowledge_cutoff"]))
    table.add_row("LLM Model", stats["model"])
    table.add_row("─" * 20, "─" * 20)
    table.add_row("RAG Documents", str(stats["rag_documents"]))
    table.add_row("RAG Collection", stats["rag_collection"])
    table.add_row("─" * 20, "─" * 20)
    table.add_row("Session Turns", str(stats["short_term_turns"]))
    table.add_row("Session Tokens (est.)", str(stats["short_term_tokens"]))
    table.add_row("Long-term Entries", str(stats["long_term_entries"]))

    console.print(table)
    console.print()


# Notebook display function removed.


def run_visualization(payload: dict):
    """Compiles and opens the mathematical visualization using Manim in a subprocess."""
    console.print("\n[bold yellow]✨ Ramanujan is drawing a mathematical diagram...[/bold yellow]")
    console.print("[dim]Generating animation using Manim in the background. Please wait...[/dim]\n")

    temp_json_path = "data/visualizations/temp_config.json"
    os.makedirs(os.path.dirname(temp_json_path), exist_ok=True)
    with open(temp_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    output_path = os.path.abspath("data/visualizations/output.mp4")

    try:
        # Run scripts/render_visual.py
        cmd = [
            sys.executable,
            "scripts/render_visual.py",
            "--json", temp_json_path,
            "--output", output_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            console.print(f"[bold green]✓ Animation successfully rendered to:[/bold green] {output_path}")
            console.print("[green]Opening media player to display the animation...[/green]\n")
            if sys.platform == "win32":
                os.startfile(output_path)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.run([opener, output_path])
        else:
            console.print(f"[red]Error rendering animation:[/red]\n{result.stderr}")
    except Exception as e:
        console.print(f"[red]Failed to launch animation renderer: {e}[/red]\n")


def handle_command(command: str, twin) -> bool:
    """
    Handle a special command.

    Returns True if the application should continue, False if it should exit.
    """
    cmd = command.strip().lower()

    if cmd == "/help":
        console.print(HELP_TEXT)

    elif cmd == "/stats":
        display_stats(twin)

    elif cmd == "/reset":
        twin.reset_session()
        console.print(
            Panel(
                "Very well. Let us begin our conversation fresh, as though "
                "we are meeting for the first time. What shall we discuss?",
                title="[bold yellow]Ramanujan[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print()

    elif cmd == "/memory":
        summary = twin.long_term_memory.summarize()
        console.print(
            Panel(
                summary,
                title="[bold cyan]Long-Term Memory[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print()

    elif cmd.startswith("/visualize"):
        query = command[len("/visualize"):].strip().lower()
        if not query:
            console.print("[red]Please specify what you would like to visualize, e.g. /visualize partitions[/red]\n")
            return True

        prompt = f"Please explain and visualize this topic: {query}"
        with console.status(
            "[yellow]Formulating mathematical visualization...[/yellow]",
            spinner="dots",
        ):
            response = twin.think(prompt)

        display_response(response)

        # Fallback router: enforce correct visualization type if LLM is rate-limited or incorrect
        payload = twin.last_visual_payload
        if not payload:
            if any(kw in query for kw in ["fraction", "continued"]):
                payload = {
                    "visualization_type": "continued_fraction",
                    "parameters": {
                        "title": "Ramanujan Continued Fraction",
                        "terms": [1, 2, 3, 4, 5]
                    }
                }
            elif any(kw in query for kw in ["partition", "diagram", "young"]):
                payload = {
                    "visualization_type": "partition_grid",
                    "parameters": {
                        "n": 5
                    }
                }
            elif any(kw in query for kw in ["taxicab", "1729", "cube"]):
                payload = {
                    "visualization_type": "taxicab",
                    "parameters": {
                        "n": 1729,
                        "pairs": [[9, 10], [1, 12]]
                    }
                }

        # Clear the payload so it does not carry over
        twin.last_visual_payload = None

        if payload:
            run_visualization(payload)
        else:
            console.print("[yellow]No visualization template matched this query. Try continued fractions, partitions, or taxicab numbers.[/yellow]\n")

    elif cmd == "/quit":
        twin.long_term_memory.save()
        console.print(
            Panel(
                FAREWELL_MESSAGE,
                title="[bold yellow]Ramanujan[/bold yellow]",
                border_style="yellow",
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )
        console.print()
        return False

    else:
        console.print(f"[dim]Unknown command: {command}. Type /help for options.[/dim]")

    return True


def main():
    """Main entry point — run the interactive chat loop."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    console.clear()
    print_header()

    # Initialize the Digital Twin
    console.print("[bold]Initializing the Digital Twin...[/bold]\n")

    try:
        from agent.twin import RamanujanTwin
        twin = RamanujanTwin(verbose=True)
    except ValueError as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Please create a .env file with GEMINI_API_KEY=your_key_here[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Initialization error: {e}[/red]")
        sys.exit(1)

    console.print()

    # Check RAG status
    stats = twin.introspect()
    if stats["rag_documents"] == 0:
        console.print(
            Panel(
                "[yellow]⚠ Knowledge base is empty.[/yellow]\n\n"
                "Run the following commands to populate it:\n"
                "  [cyan]python scripts/ingest.py --input data/raw/ --output data/processed/[/cyan]\n"
                "  [cyan]python scripts/embed.py[/cyan]\n\n"
                "Continuing in persona-only mode (no RAG context).",
                title="Warning",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        console.print()

    print_initialization(twin)
    print_welcome()

    # ── Chat Loop ─────────────────────────────────────────────────────────
    while True:
        try:
            user_input = console.input("[bold cyan]\\[You] >> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            twin.long_term_memory.save()
            console.print(
                Panel(
                    FAREWELL_MESSAGE,
                    title="[bold yellow]Ramanujan[/bold yellow]",
                    border_style="yellow",
                    box=box.DOUBLE,
                    padding=(1, 2),
                )
            )
            break

        if not user_input:
            continue

        # Handle special commands
        if user_input.startswith("/"):
            should_continue = handle_command(user_input, twin)
            if not should_continue:
                break
            continue

        # Generate response with spinner
        with console.status(
            "[yellow]Consulting the notebooks...[/yellow]",
            spinner="dots",
        ):
            response = twin.think(user_input)

        display_response(response)

        # Trigger visualization rendering if a payload is set by the twin
        if twin.last_visual_payload:
            payload = twin.last_visual_payload
            twin.last_visual_payload = None
            run_visualization(payload)


if __name__ == "__main__":
    main()
