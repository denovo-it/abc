# Copyright Axelera AI, 2025
"""
cli_ui.py
CLI display logic for LLM inference: rich panel chat, plain display, etc.
"""
import os
import time


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def clear_history():
    """
    Clear the console screen and print a message.
    This function is called when the user types "clear" in the CLI.
    """
    clear_screen()
    print("History cleared. Type 'exit' or 'quit' to exit.")
    return "!CLEAR_HISTORY!"  # Special return value to signal history clearing


def display_rich_factory(console):
    """
    Returns a display_fn for chat-like CLI with rich panels.
    Shows all previous history as static panels, the current user question as a panel,
    and the assistant's response as a live-updating panel (or incremental print for long responses).
    After streaming, redraws the full history only if incremental print was used.
    """

    def display_fn(user_input, response_stream, is_user, history=None):
        # Import rich only when needed
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.spinner import Spinner

        if history is None:
            history = []
        if is_user:
            console.print("[cyan]User:[/cyan] ", end="")
            user_input = input()
            if user_input.strip().lower() in {"exit", "quit"}:
                return user_input
            # Add special handling for "clear" command
            if user_input.strip().lower() == "clear":
                clear_screen()
                # Display clear message using console directly
                console.print(
                    "[bold green]History cleared. Type 'exit' or 'quit' to exit.[/bold green]"
                )
                return "!CLEAR_HISTORY!"  # Special return value to signal history clearing
            return user_input
        elif user_input == "Goodbye!":
            console.print("[bold red]Goodbye![/bold red]")
            return ""
        else:
            response = ""
            prev_response = ""
            lines_margin = 4  # Leave some space for prompt, etc.
            max_panel_height = console.size.height - lines_margin
            use_panel = True
            first_token_received = False
            panel_height = min(max_panel_height, 10)  # 10 is a safe guess for spinner panel
            used_incremental_print = False

            def render_history_with_user(history_to_render, user_input=None):
                clear_screen()
                for user, assistant in history_to_render:
                    console.print(
                        Panel(user, title="[cyan]User[/cyan]", style="cyan", expand=False)
                    )
                    console.print(
                        Panel(
                            Markdown(assistant),
                            title="[green]Assistant[/green]",
                            style="green",
                            expand=False,
                        )
                    )
                if user_input is not None:
                    console.print(
                        Panel(user_input, title="[cyan]User[/cyan]", style="cyan", expand=False)
                    )

            # Do NOT render static history before streaming the current response
            with Live(
                Panel(
                    Spinner("dots", text="Generating..."),
                    title="[green]Assistant[/green]",
                    style="green",
                    expand=False,
                ),
                refresh_per_second=30,
                console=console,
            ) as live:
                for new_text, stats_dict in response_stream:
                    response = new_text
                    if not first_token_received:
                        first_token_received = True
                    # Count lines in the response
                    response_lines = response.count('\n') + 1
                    if use_panel and response_lines > max_panel_height:
                        # Switch to incremental printing
                        use_panel = False
                        used_incremental_print = True
                        live.stop()
                        # Print only the new part
                        new_part = response[len(prev_response) :]
                        print(new_part, end='', flush=True)
                        prev_response = response
                        continue
                    if use_panel:
                        live.update(
                            Panel(
                                (
                                    response
                                    if first_token_received
                                    else Spinner("dots", text="Generating...")
                                ),
                                title="[green]Assistant[/green]",
                                style="green",
                                expand=False,
                            )
                        )
                    else:
                        # Print only the new part
                        new_part = response[len(prev_response) :]
                        print(new_part, end='', flush=True)
                        prev_response = response
                # After streaming, only redraw the full history if incremental print was used
                if used_incremental_print:
                    if user_input is not None and response.strip():
                        history_with_last = history + [(user_input, response)]
                    else:
                        history_with_last = history
                    render_history_with_user(history_with_last)
                    time.sleep(0.5)
            return response

    return display_fn


def display_plain(user_input, response_stream, is_user, history=None):
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    if is_user:
        user_input = input(f"{CYAN}User:{RESET} ")
        if user_input.strip().lower() in {"exit", "quit"}:
            return user_input
        # Add special handling for "clear" command
        if user_input.strip().lower() == "clear":
            clear_screen()
            print(f"{GREEN}History cleared. Type 'exit' or 'quit' to exit.{RESET}")
            return "!CLEAR_HISTORY!"  # Special return value to signal history clearing
        return user_input
    elif user_input == "Goodbye!":
        print("Goodbye!")
        return ""
    else:
        response = ""
        print(f"{GREEN}Assistant:{RESET} ", end="")
        for new_text, _ in response_stream:
            print(new_text[len(response) :], end='', flush=True)
            response = new_text
        print()
        return response
