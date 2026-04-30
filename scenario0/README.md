# Lumina AI - Ollama CLI Assistant

A high-end CLI application that demonstrates direct tool calling with local Ollama, without the need for an MCP server.

## Features
- **Interactive CLI**: A beautiful terminal interface powered by `rich`.
- **Real-time Tools**: 
  - `get_current_time`: Fetches the actual system time.
  - `get_weather`: Provides mock weather data for any zip code.
- **Direct Ollama Integration**: Uses the official `ollama` Python SDK for robust tool calling.
- **Visual Excellence**: Includes status spinners, markdown rendering, and colored panels for a premium terminal experience.

## How to Run

1. **Ensure Ollama is running**: Make sure you have Ollama installed and running on your machine.
2. **Setup Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Start the assistant**:
   ```bash
   python app.py
   ```

## Architecture
- **Tool Mapping**: Tools are defined as Python functions and mapped to JSON schemas that Ollama understands.
- **Conversation Loop**: The script manages a message history, detecting when the model requests a tool call, executing it locally, and feeding the result back to the model automatically.
