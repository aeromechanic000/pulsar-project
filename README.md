
# <img src="https://s2.loli.net/2025/07/27/jUGXP8YpAF3yksd.png" alt="Minecraft AI" width="32" height="32"> Pulsar Agent

**Pulsar Agent** is an open-source, evolving LLM agent framework designed to integrate seamlessly with Claude's [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server ecosystem. It features intelligent task workflows, contextual memory, and tool usage.

<i class="fa fa-home" aria-hidden="true"></i> [Pulsar Agent Website](https://pulsar-agent.cc)

## Community

Pulsar Agent is inspired by our work in the Minecraft AI project, where we build robust and extensible LLM agents to act as the cognitive core for in-game AI characters. These agents need to reason, reflect, and coordinate with others—driving the need for modular, prompt-driven architectures like PandexAgent.

We welcome collaboration, discussion, and ideas. Join us in the Minecraft AI Discord server to connect with our community and explore how Pulsar and other tools are shaping AI in virtual environments.

<i class="fa fa-comments" aria-hidden="true"></i> Join the Minecraft AI Discord

<a href="https://discord.gg/RKjspnTBmb" target="_blank"><img src="https://s2.loli.net/2025/04/18/CEjdFuZYA4pKsQD.png" alt="Official Discord Server" width="180" height="36"></a>


## Key Features

### 1. **Modular MCP Integration**
- Connects to **multiple MCP servers** using Claude’s protocol.
- Acts as a standalone **MCP client** with full tool discovery and execution.
- Provides uniform access to distributed toolsets from various servers.

### 2. **Task-Centric Architecture**
- Uses a **TaskManager** to manage task contexts and workflows.
- Developers can create custom task types (e.g., planning, research).
- Logs and state are persistently tracked per task for traceability.

### 3. **Memory-Driven Agent Intelligence**
- Built-in **Memory module** for long-term context accumulation.
- Extracts and stores structured information to **enhance reasoning** and **multi-turn interaction**.
- Supports memory operations dynamically invoked by LLM.

### 4. **Web-based Interaction**
- A full-featured **Flask app** (in `app.py`) provides:
  - RESTful APIs for task/memory/tool interactions.
  - Live chat interface powered by WebSocket.
  - Task visualization, memory inspection, and tool usage monitoring.

### 5. **Command-Line Client Mode**
- `client.py` provides an interactive terminal chat loop.
- Full memory/tool introspection, and task control from the CLI.

---

## Quick Start

In the default `configs.json`, Ollama with model `llama3.2` is used, make sure you have Ollama running correctly, or you can refer to the `configs-exmaple-1.json` to use other OpenAI compatible API. 

**NOTE:** You can use [Pollinations AI](https://pollinations.ai/) without registration as the LLM provider. Just change the `name` of `provider` section to `Pollinations`. 

```bash
git clone https://github.com/aeromechanic000/pulsar-project.git
cd pulsar-project
uv run app.py
```

* Add `--save-logs` to enable logging into `./logs/`.
* Navigate to `http://localhost:9898` in your browser.

###  CLI Client Mode

Run the standalone agent client:

```bash
uv run client.py
```

Options:

* `--config-path <path>`: specify a custom config file (default: `configs.json`)
* `--save-logs`: enable detailed logging of prompts, responses, and actions

---

## Project Structure

```text
.
├── app.py              # Flask Web API + WebSocket for UI
├── client.py           # CLI-based LLM agent interface
├── memory/             # Memory extraction and operations
├── task/               # Task definitions and task manager
├── provider/           # LLM provider interfaces
├── templates/          # HTML frontend (if provided)
├── static/             # Static assets
├── configs.json        # Example config file
├── logs/               # Log outputs
└── data/               # Agent memory and task state persistence
```

---

## API Endpoints

Flask app provides REST APIs:

* `POST /api/initialize`: initialize agent with config
* `POST /api/chat`: submit query to agent
* `GET /api/config`: fetch current agent + tool status
* `GET /api/tasks`: view all tasks
* `GET /api/memory`: view memory summary
* `GET /api/tools`: list tools from all connected MCP servers

---

## Structured Resposne

Agent LLM will generate JSON responses with:

* `think`: reasoning
* `text`: final answer
* `mem_op`: memory operation (if needed)
* `tool`: tool usage (if needed)
* `finished`: whether interaction is complete

---

## Logs and Configuration

* Logs are stored in `./logs/` if `--save-logs` is enabled.
* Agent behavior is controlled via `configs.json`:

  * Provider selection
  * MCP server addresses
  * Task workflow configuration
  * Memory strategies

---

## Contributing

Contributions are welcome! Feel free to fork, file issues, or submit PRs. For major changes, please open a discussion first.

---

## License

MIT License © 2025 \[aeromechanic]

