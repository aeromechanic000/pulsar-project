import os, sys, asyncio, json
import argparse, logging
from contextlib import AsyncExitStack
from typing import Optional, Dict, List, Tuple, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

from memory import *
from task import *
from provider import *
from utils import *

class MCPServerManager:
    """Manages multiple MCP server connections"""
    
    def __init__(self):
        self.servers: Dict[str, Dict] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
    
    async def load_servers_config(self, configs):
        """Load server configurations from JSON file"""
        self.servers = configs
        add_log(f"Loaded {len(self.servers)} MCP server configurations")
    
    async def connect_all_servers(self):
        """Connect to all configured servers"""
        for server_name, server_config in self.servers.items():
            try:
                await self._connect_server(server_name, server_config)
                add_log(f"Connected to MCP server: {server_name}", label = "success")
            except Exception as e:
                add_log(f"Failed to connect to MCP server {server_name}: {e}", label = "error")
    
    async def _connect_server(self, server_name: str, server_config: Dict):
        """Connect to a single MCP server"""
        command = server_config["command"]
        args = server_config.get("args", [])
        env = server_config.get("env")
        
        server_params = StdioServerParameters(
            command = command,
            args=args,
            env=env
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await session.initialize()
        self.sessions[server_name] = session
    
    async def get_tools(self) -> Dict[str, Any]:
        """Get all available tools from all connected servers"""
        all_tools = {}
        
        for server_name, session in self.sessions.items():
            try:
                response = await session.list_tools()
                for tool in response.tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                        "server": server_name
                    }
                    all_tools[tool.name] = tool_info
            except Exception as e:
                add_log(f"Error getting tools from {server_name}: {e}", label = "error")
        
        return all_tools
    
    async def call_tool(self, tool_name: str, tool_args: Dict) -> Any:
        """Call a tool on the appropriate server"""
        # Find which server has this tool
        for server_name, session in self.sessions.items():
            try:
                response = await session.list_tools()
                tool_names = [tool.name for tool in response.tools]
                
                if tool_name in tool_names:
                    result = await session.call_tool(tool_name, tool_args)
                    return result
            except Exception as e:
                add_log(f"Error calling tool {tool_name} on {server_name}: {e}", label = "error")
        
        raise ValueError(f"Tool {tool_name} not found on any connected server")
    
    async def cleanup(self):
        """Clean up all server connections"""
        await self.exit_stack.aclose()

class Client:
    """Pulsar Agent client with multi-server support and configurable LLM providers"""
    
    def __init__(self) :
        self.provider, self.memory = None, None
        self.task_manager = TaskManager(self)
        self.server_manager = MCPServerManager()
        self.messages = []
    
    async def initialize(self, configs: str):
        """Initialize the client with server configurations"""
        self.configs = configs or {}

        provider_config = self.configs.get("provider", {})
        provider_name = provider_config.get("name", None)
        provider_cls = get_provider(provider_name) 

        if provider_cls is not None : 
            self.provider = provider_cls(provider_config)
            add_log(f"Using provider: {provider_name}")
        else:
            add_log(f"Unknown provider: {provider_name}", label = "error")

        await self.server_manager.load_servers_config(configs.get("mcpServers", {}))
        await self.server_manager.connect_all_servers()

        self.task_manager.load_config(self.configs.get("task", {}))
        self.memory = Memory(self, self.configs.get("memory", {}))

    async def get_config_info(self) :
        operations = await self.memory.get_operations()
        tools = await self.server_manager.get_tools()
    
        info = {
            "provider" : self.configs.get("provider", {}),
            "memory_operations_num" : len(operations),
            "memory_operations" : [
                {
                    "name" :  op['name'], 
                    "description" : op['description'],
                } for op in operations.values()
            ],
            "tools_num" : len(tools),
            "tools" : [
                {
                    "name" :  tool['name'], 
                    "description" : tool['description'],
                } for tool in tools.values() 
            ],
        }
        return info
    
    async def react(self, query) -> Tuple[Dict, bool] :
        response = {"content" : []}
        # Convert messages to a single prompt
        prompt = await self._context_to_prompt(query)
        add_log(f"Prompt: {prompt}", label="log", print = False)

        text_response = await self.provider.generate_response(prompt)
        add_log(f"Text response: {text_response}", label = "log", print = False)

        dict_response = self._extract_output(text_response)
        add_log(f"Dict response: {dict_response}", label = "log", print = False)

        if "think" in dict_response.keys() :  
            response["content"].append({"type": "think", "content": dict_response["think"]})
        if "text" in dict_response.keys() :  
            response["content"].append({"type": "text", "text": dict_response["text"]})
        if "mem_op" in dict_response.keys() :  
            name = dict_response["mem_op"].get("name", None)
            args = dict_response["mem_op"].get("args", {})
            if name is not None and len(name.strip()) > 0 : 
                op_call = {"type": "mem_op", "name" : name, "args": {}}
                operations = await self.memory.get_operations()
                if name in operations.keys() :
                    for key, value in args.items() :
                        if key in operations[name]["input_schema"]["properties"].keys() :
                            op_call["args"][key] = value
                    response["content"].append(op_call)

        if "tool" in dict_response.keys() :  
            name = dict_response["tool"].get("name", None)
            args = dict_response["tool"].get("args", {})
            if name is not None and len(name.strip()) > 0 :
                tool_call = {"type": "tool", "name" : name, "args": {}}
                tools = await self.server_manager.get_tools()
                if name in tools.keys() :
                    for key, value in args.items() :
                        if key in tools[name]["input_schema"]["properties"].keys() :
                            tool_call["args"][key] = value
                    response["content"].append(tool_call)

        add_log(f"Response: {response}", label = "log", print = False)
        return response, dict_response.get("finished", True)

    async def _context_to_prompt(self, query) -> str:
        """Convert message format to prompt string"""
        prompt_parts = ['''
I am an AI assistant, which is good at answer user's query from the conversations, based on the memory status and task status. In generating the response, I will consider to answer with four parts: 
1. Think: analyze the context and think about what to do next.
2. Text: the text response to the user's query.
3. Memory Operation: if I need to perform a memory operation, I will return the operation name and parameters. Make sure a memroy operation is really necessary and not redundant and not repetitive. 
4. Tool: if I need to use a tool, I will return the tool name and parameters. Make sure a memroy operation is really necessary and not redundant and not repetitive. 

Furthermore, you have to explicitly indicate if you have finished the generation of response, or need to perform more steps or stop and wait for user's next query. This is important if you need multiple steps to answer current query well. But be careful, if you are not sure what to do next, you should leave the decision to the user. MAKE SURE don't set 'finished' to true, if you are still working on preparing the final response.

The result should be formatted in **JSON** dictionary and enclosed in **triple backticks (` ``` ` )**  without labels like 'json', 'css', or 'data'.
- **Do not** generate redundant content other than the result in JSON format.
- **Do not** use triple backticks anywhere else in your answer.
- The JSON must include the following keys and values accordingly :
    - 'text': A JSON String for the text response to the user's query.
    - 'think': A JSON String for the description of the thinking process to response to the user's query.
    - 'mem_op': ONlY USED when you need to perform a memory operation (from the available memory operations), the value is a dictionary with the operation name and parameters: 
        - 'name': The name of the memory operation.
        - 'args': A dictionary of arguments for the operation.
    - 'tool': ONLY USED when you need to use a tool (from the available tools), the value is a dictionary with the tool name and parameters:
        - 'name': The name of the tool to use.
        - 'args': A dictionary of arguments for the tool.
    - 'finished': A JSON bool value indicating if your actions are finished, set 'true' to stop processing and send response to the user; set 'false' to continue the actions. When you used a tool or you need more steps to collect information to complete the response, you should set 'finished' to 'false'.
''']

        common_sense_text = await self.get_common_sense_context()
        add_log(f"Get common_sense_text: {common_sense_text}", label="log", print = False)
        if len(common_sense_text) > 0 : 
            prompt_parts.append(f"\n## Common Sense Information:\n{common_sense_text}")

        static_memory_text = await self.memory.get_static_context()
        add_log(f"Get static_memory_text: {static_memory_text}", label="log", print = False)
        if len(static_memory_text) > 0 : 
            prompt_parts.append(f"\n## Static Memory:\n{static_memory_text}")

        # Fix: Use task_manager instead of task
        static_task_text = await self.task_manager.get_static_context()
        add_log(f"Get static_task_text: {static_task_text}", label="log", print = False)
        if len(static_task_text) > 0 : 
            prompt_parts.append(f"\n## Static Task:\n{static_task_text}")
        
        dynamic_memory_text = await self.memory.get_dynamic_context(query)
        add_log(f"Get dynamic_memory_text: {dynamic_memory_text}", label="log", print = False)
        if len(dynamic_memory_text) > 0 : 
            prompt_parts.append(f"\n## Dynamic Memory:\n{dynamic_memory_text}")

        # Fix: Use task_manager instead of task
        dynamic_task_text = await self.task_manager.get_dynamic_context(query)
        add_log(f"Get dynamic_task_text: {dynamic_task_text}", label="log", print = False)
        if len(dynamic_task_text) > 0 : 
            prompt_parts.append(f"\n## Dynamic Task:\n{dynamic_task_text}")
            
        # Get all available tools
        tools = await self.server_manager.get_tools()
        # Format tools for LLM (remove server info for cleaner interface)
        if len(tools) > 0 :
            prompt_parts.append("\n## Available Tools:")
            for tool in tools.values() :
                prompt_parts.append(f"- {tool['name']}: '{tool['description']}")
                prompt_parts.append(f"  Input schema: {json.dumps(tool['input_schema'])}")
        
        prompt_parts.append("## Conversation History:")
        for msg in self.messages[:-1]:
            role = msg["role"].upper()
            content = msg["content"]
            prompt_parts.append(f"{role}: {content}")
        
        prompt_parts.append(f"\nUser Query: {self.messages[-1]['content']}")
        prompt_parts.append("\nYour Answer:\n")
        
        return "\n".join(prompt_parts)
    
    async def get_common_sense_context(self) : 
        common_sense_parts = [
            f"Curent date and time: {get_datetime()}"
        ]
        return "\n".join(common_sense_parts)

    def _extract_output(self, text: str) -> Dict:
        """Extract structured output from response text"""
        output = {}

        try : 
            content, data = split_content_and_json(text) 
            add_log(f"Extracted data: {data}", label="log", print = False)
            if "text" in data.keys() :
                output["text"] = data["text"]
            if "think" in data.keys() :
                output["think"] = data["think"]
            if isinstance(data.get("mem_op", None), Dict) and len(data["mem_op"]) > 0 :
                output["mem_op"] = data["mem_op"]
            if isinstance(data.get("tool", None), Dict) and len(data["tool"]) > 0:
                output["tool"] = data["tool"]
            if "finished" in data.keys() :
                output["finished"] = convert_to_boolean(data["finished"])
        except Exception as e:
            add_log(f"Error extracting output: {str(e)}", label="error")
        
        return output 

    async def process_query(self, query: str) -> str:
        """Process a query using the LLM and available tools"""
        self.messages.append({"role": "user", "content": query})
        new_message_index = len(self.messages) 
        
        max_iters = self.configs.get("max_iters", 5)
        iter = 0
        
        while iter < max_iters:
            iter += 1
            
            # Get LLM response
            response, finished = await self.react(query)
            need_next_interation = not finished 
            response_text = ""

            for content in response["content"]:
                if content["type"] == "text":
                    add_log("Process text resonse", print = False)
                    response_text = content["text"]
                    self.messages.append({
                        "role" : "assistant", 
                        "content" : response_text,
                    })
                
                elif content["type"] == "think":
                    add_log("Process think response", print = False)
                    response_text = content["content"]
                    self.messages.append({
                        "role" : "assistant", 
                        "content": f"[Think] {response_text}"
                    })

                elif content["type"] == "mem_op":
                    add_log("Process memory operation response", print = False)
                    need_next_interation = True 
                    op_name = content["name"]
                    op_args = content["args"]
                    
                    try:
                        # Execute memory operation call
                        result = await self.memory.call_operation(op_name, op_args)
                        
                        op_use_info = {
                            "name" : op_name, 
                            "args" : op_args,
                            "result" : "", 
                        }

                        if hasattr(result, "content") :
                            for content in result.content :
                                if content.type == "text" :
                                    op_use_info["result"] += f"{content.text}"
                                elif content.type == "value" :
                                    op_use_info["result"] += f"Value: {content.value}"
                        else :
                            op_use_info["result"] = str(result)

                        self.messages.append({
                            "role": "assistant",
                            "content": f"[Memory Operation Called] name: {op_name}, result: {op_use_info}"
                        })
                        
                    except Exception as e:
                        error_msg = f"Error calling tool {op_name}: {str(e)}"
                        add_log(error_msg, label = "error")
                        self.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                        })

                elif content["type"] == "tool":
                    add_log("Process tool response", print = False)
                    need_next_interation = True 
                    tool_name = content["name"]
                    tool_args = content["args"]
                    
                    try:
                        # Execute tool call
                        result = await self.server_manager.call_tool(tool_name, tool_args)
                        
                        tool_use_info = {
                            "name" : tool_name, 
                            "args" : tool_args,
                            "result" : "", 
                        }

                        if hasattr(result, "content") :
                            for content in result.content :
                                if content.type == "text" :
                                    tool_use_info["result"] += f"{content.text}"
                        else :
                            tool_use_info["result"] = str(result)

                        self.messages.append({
                            "role": "assistant",
                            "content": f"[Tool Called] name: {tool_name}, result: {tool_use_info}"
                        })
                        
                    except Exception as e:
                        error_msg = f"Error calling tool {tool_name}: {str(e)}"
                        add_log(error_msg, label = "error")
                        self.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                        })

            await self.task_manager.update(query, self.messages[new_message_index:])

            if not need_next_interation:
                break
            
        response = self.messages[new_message_index:]
        return response
    
    async def cleanup(self):
        """Clean up resources"""
        await self.server_manager.cleanup()

async def chat_loop(client):
    """Run an interactive chat loop"""
    print("\nPulsar Agent Client Started!")
    print("Type your queries or 'quit' to exit.")
    print("Type 'mem_ops' to see available memory operations.")
    print("Type 'tools' to see available tools.")
    
    while True:
        try:
            query = input("\n[Query] ").strip()
            
            if query.lower() == 'quit':
                break
            
            if query.lower() == '/mem_ops':
                operations = await client.memory.get_operations()
                print("\nAvailable memory operations:")
                for op in operations :
                    print(f"   {op['name']}")
                    print(f"   {op['description']}")
                continue

            if query.lower() == '/tools':
                tools = await client.server_manager.get_tools()
                print("\nAvailable tools:")
                for tool in tools:
                    print(f"   {tool['name']} (from {tool['server']})")
                    print(f"   {tool['description']}")
                continue

            if query.lower().startswith('/task') :
                query_list = query.lower().split()
                if len(query_list) > 2 : 
                    command = query_list[1]
                    if command == 'new' : 
                        task_type = query_list[2]
                        task_id = client.task_manager.new_task(task_type)
                        if task_id : 
                            print(f"\nNew task created with id: {task_id}")
                        else :
                            print("\nFailed to create a new task.")
                        continue
                    elif command == 'load' :
                        task_id = query_list[2]
                        result = client.task_manager.load_task(task_id)
                        if result : 
                            print(f"\nLoaded task with id: {task_id}")
                        else :
                            print(f"\nFailed to load task with id: {task_id}.")
                        continue
                print("\nUsage: \n   - /task new <task_type>: create a new task of type 'plan'|'research'. \n   - /task load <task_id>: load a task by id.")
                continue

            response = await client.process_query(query)
            print(f"\n[Response] {"\n".join([msg["content"] for msg in response])}")
            
        except Exception as e:
            print(f"\n[Error] {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description="Setup and run the program.")
    parser.add_argument('--save-logs', action='store_true', help='Enable log saving')
    parser.add_argument('--config-path', type=str, default="configs.json", help='Path to the config file')

    args = parser.parse_args()
    
    if args.save_logs:
        logging.basicConfig(
            filename = os.path.join("./logs/client_log-%s.json" % (get_datetime_stamp())),
            filemode = 'a',
            format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt = '%H:%M:%S',
            level = logging.DEBUG, 
        )

    add_log("Usage: python client.py <config_json_path>")
    add_log("Example: python client.py configs.json")
    
    config_path = args.config_path

    add_log(f"Using configs: {config_path}")

    client = Client()
    
    try:
        await client.initialize(read_json(config_path))
        await chat_loop(client)
    finally:
        await client.cleanup()

if __name__ == "__main__":

    # Create necessary directories
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/memory', exist_ok=True)
    os.makedirs('data/task', exist_ok=True)

    

    asyncio.run(main())