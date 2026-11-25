# Architecture

ReidX runs the terminal and its workspace server. LiteLLM maps stable role aliases to chat models and routes `nomic-embed` to Ollama. The memory MCP keeps Markdown and a SQLite index in the installation's memory directory.
