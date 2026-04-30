import datetime
import json
import sys
from ollama import chat
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.status import Status

# --- Configuration ---
MODEL = "qwen3.6:27b-coding-mxfp8"
VERBOSE = True  # Toggle this to show/hide the prompt and tool payloads
console = Console()

# --- Tool Implementations ---

def get_current_time():
    """Returns the current date and time."""
    now = datetime.datetime.now()
    return {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": "UTC" # Simplified
    }

def get_weather(zip_code: str):
    """Returns mock weather data for a given zip code."""
    return {
        "zip_code": zip_code,
        "temperature": "72°F",
        "condition": "Partly Cloudy",
        "humidity": "45%",
        "wind": "10 mph",
        "forecast": "Expected to stay clear throughout the evening."
    }

# Map tool names to actual functions
TOOL_MAP = {
    "get_current_time": get_current_time,
    "get_weather": get_weather
}

def run_cli():
    console.print(Panel.fit(
        "[bold blue]Lumina AI Assistant[/bold blue]\n[dim]Direct Ollama Integration with Local Tools[/dim]",
        border_style="blue"
    ))
    console.print("[italic cyan]Type 'exit' or 'quit' to stop.[/italic cyan]\n")

    messages = [
        {"role": "system", "content": "You are a helpful assistant with access to local tools. Use them when needed to provide accurate information."}
    ]

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
            
            if user_input.lower() in ["exit", "quit"]:
                console.print("\n[bold red]Goodbye![/bold red]")
                break
            
            messages.append({"role": "user", "content": user_input})
            
            process_interaction(messages)
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted. Goodbye![/bold red]")
            break

def process_interaction(messages):
    """Handles the loop of sending messages to Ollama and executing tools."""
    
    with Status("[bold blue]Lumina is thinking...[/bold blue]", spinner="dots") as status:
        while True:
            tool_definitions = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "description": "Get the current date, time, and day of the week. Use this when the user asks for 'today', 'now', or current time.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather for a specific zip code.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "zip_code": {
                                    "type": "string",
                                    "description": "The zip code to check weather for"
                                }
                            },
                            "required": ["zip_code"]
                        }
                    }
                }
            ]

            if VERBOSE:
                # Convert Message objects to dicts for JSON serialization
                serializable_messages = [
                    msg if isinstance(msg, dict) else msg.model_dump() 
                    for msg in messages
                ]
                console.print("\n[bold magenta]DEBUG: Sending Payload to Ollama[/bold magenta]")
                console.print("[dim]Messages:[/dim]")
                console.print_json(data=serializable_messages)
                console.print("[dim]Tools Available:[/dim]")
                console.print_json(data=tool_definitions)
                console.print("-" * 40)

            response = chat(
                model=MODEL,
                messages=messages,
                tools=tool_definitions
            )

            # Add the assistant's response to the history
            messages.append(response.message)

            # Check if the model wants to call tools
            if response.message.tool_calls:
                for tool in response.message.tool_calls:
                    func_name = tool.function.name
                    args = tool.function.arguments
                    
                    console.print(f"[dim yellow]⚙️ Executing: {func_name}({args})[/dim yellow]")
                    
                    if func_name in TOOL_MAP:
                        result = TOOL_MAP[func_name](**args)
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(result),
                            "name": func_name
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "content": json.dumps({"error": "Tool not found"}),
                            "name": func_name
                        })
                
                # Continue the loop to let the model process the tool results
                status.update("[bold blue]Processing tool results...[/bold blue]")
                continue
            
            # If no tool calls, display the final response and exit the loop
            console.print("\n[bold blue]Lumina[/bold blue]")
            console.print(Markdown(response.message.content or ""))
            console.print()
            break

if __name__ == "__main__":
    run_cli()
