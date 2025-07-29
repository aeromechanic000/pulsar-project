
# <img src="https://s2.loli.net/2025/07/27/jUGXP8YpAF3yksd.png" alt="Minecraft AI" width="32" height="32"> Pulsar Agent

**Pulsar Agent** is an open-source, evolving LLM agent framework designed to integrate seamlessly with Claude's [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server ecosystem. It features intelligent task workflows, contextual memory, and tool usage.

🌐 [Pulsar Agent Website](https://pulsar-agent.cc)

<!-- <table>
<tr>
    <td><img src="https://s2.loli.net/2025/07/28/tFng6xLJkY7wdbc.gif" alt="Pulsar Agent" width="380" height="220"></td>
    <td><img src="https://s2.loli.net/2025/07/28/eaTQ83lsfpUABKS.gif" alt="Pulsar Agent" width="380" height="220"></td>
</tr>
</table> -->


## Community

Pulsar Agent is inspired by our work in the Minecraft AI project, where we build robust and extensible LLM agents to act as the cognitive core for in-game AI characters. These agents need to reason, reflect, and coordinate with others—driving the need for modular, prompt-driven architectures like PandexAgent.

We welcome collaboration, discussion, and ideas. Join us in the Minecraft AI Discord server to connect with our community and explore how Pulsar and other tools are shaping AI in virtual environments.

💬 Join the Minecraft AI Discord

<a href="https://discord.gg/RKjspnTBmb" target="_blank"><img src="https://s2.loli.net/2025/04/18/CEjdFuZYA4pKsQD.png" alt="Official Discord Server" width="180" height="36"></a>


## Key Features

![pulsar-1.gif](https://s2.loli.net/2025/07/28/tFng6xLJkY7wdbc.gif)

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

### Download The Source Code

```bash
git clone https://github.com/aeromechanic000/pulsar-project.git
cd pulsar-project
```

### Configure The LLM API

In the default `configs.json`, Pollinations AI (https://pollinations.ai/) is used. You can refer to the `configs-exmaple-1.json` to use other OpenAI compatible API, or `configs-exmaple-2.json` to use locally deployed Ollama. 

A full list of supported APIs and models is available in the table below.

<table>
<tr>
    <td> <b>API</b> </td> 
    <td> <b>Model</b> </td>
    <td> <b>Example</b> </td>
</tr>
<tr>
    <td> OpenAI </td>
    <td> gpt-4.1, gpt-4o <br> <a href="https://platform.openai.com/docs/models">full list of models</a> </td>
    <td> "provider" : {"name" : "OpenAI", "model" : "gpt-4o", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> Gemini </td>
    <td> gemini-2.5-flash-preview-05-20 <br> <a href="https://ai.google.dev/gemini-api/docs/models">full list of models</a> </td>
    <td> "provider" : {"name" : "Gemini", "model" : "gemini-2.5-flash-preview-05-20", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> Anthropic </td>
    <td> claude-opus-4-20250514 <br> <a href="https://docs.anthropic.com/en/docs/about-claude/models/overview">full list of models</a> </td>
    <td> "provider" : {"name" : "Anthropic", "model" : "claude-opus-4-20250614", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> Doubao </td>
    <td> doubao-1-5-pro-32k-250115 <br> <a href="https://www.volcengine.com/docs/82379/1330310">full list of models</a> </td>
    <td> "provider" : {"name" : "Doubao", "model" : "doubao-1-5-pro-32k-250115", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> Qwen </td>
    <td> qwen-max, qwen-plus <br> <a href="https://help.aliyun.com/zh/model-studio/getting-started/models">full list of models</a> </td>
    <td> "provider" : {"name" : "Qwen", "model" : "qwen-max", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> <a href="https://pollinations.ai/">Pollinations</a> </td>
    <td> openai-large, gemini, deepseek <br> <a href="https://text.pollinations.ai/models">full list of models</a> </td>
    <td> "provider" : {"name" : "Pollinations"} </td>
</tr>
<tr>
    <td> OpenRouter </td>
    <td> deepseek/deepseek-chat-v3-0324:free <br> <a href="https://openrouter.ai/models">full list of models</a> </td>
    <td> "OpenRouter" : {"name" : "OpenRouter", "model" : "deepseek/deepseek-chat-v3-0324:free", "api_key" : "[your_api_key]"} </td>
</tr>
<tr>
    <td> <a href="https://ollama.com/">Ollama</a> </td>
    <td> llama3.2, llama3.1 <br> <a href="https://ollama.com/library">full list of models</a> </td>
    <td> "provider" : {"name" : "Ollama", "model" : "llama3.1", "base_url" : "http://127.0.0.1:11434"} </td>
</tr>
</table>

### Configure The LLM API

For the MCP servers to work correctly, complete the absolute paths in the `mcpServers` section of `configs.json`.

```
"mcpServers" : {
  "weather": {
      "command": "[absolute_path_to_uv]/uv",
      "args": [
        "--directory",
        "[absolute_path_to_pulsar]/pulsar-project/mcp_servers/weather",
        "run",
        "weather.py"
      ]
  } 
}
```

### Start The Web Application

```bash
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

