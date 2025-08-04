
import os, json, shutil, argparse, asyncio, time 
from datetime import datetime, timedelta
import requests, subprocess
from requests.exceptions import Timeout

from typing import Optional, Dict, List, Tuple, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
load_dotenv()  # load environment variables from .env

from utils import *

INDEX_PATH = "mcp_servers_index.json"
MCP_SERVERS_DIR = ".mcp_servers"

def download_files(root, files) : 
    for file in files : 
        if file.get("path", None) : 
            src = file["path"]
            dest = os.path.join(root, file["name"])

            if os.path.exists(dest) : 
                add_log(f"File '{dest}' already exists.")
                return 

            try :
                response = requests.get(src, timeout = 3000)
                if response.status_code == 200:
                    with open(dest, 'w') as f:
                        f.write(response.text)
                    add_log(f"File downloaded successfully to {dest}.", label = "success")
                else:
                    add_log(f"Failed to download file. Status code: {response.status_code}", label = "error")
            except Timeout as e : 
                add_log(f"Timeout to download file {src}: {str(e)}", label = "error")
                add_log(f"Try to download the files later or download and place the files in {MCP_SERVERS_DIR} mannualy.", label = "warning")
            except Exception as e : 
                add_log(f"Error in downloading file {src}: {str(e)}", label = "error")
                add_log(f"Try to download the files later or download and place the files in {MCP_SERVERS_DIR} mannualy.", label = "warning")
        elif not file.get("path", None) : 
            dest = os.path.join(root, file["name"])
            os.makedirs(dest, exist_ok = True)
            download_files(dest, file["files"])

def load_mcp_servers_index():
    """Load MCP server index."""
    if os.path.exists(INDEX_PATH):
        try :
            return read_json(INDEX_PATH)
        except Exception as e:
            add_log(f"Error in retrieving MCP server index: {e}", label = "error")
    return {}

def install_dependencies(dependencies):
    if not dependencies:
        return True  
    try:
        subprocess.check_call(
            ["uv", "add"] + dependencies,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        add_log(f"Failed to install dependencies: {e.stderr}", label = "error")
        return False

def install_server(server_name):
    """Install MCP Server of given name 'server_name'）"""
    index = load_mcp_servers_index()
    if server_name not in index:
        add_log(f"Cannot find MCP Server: {server_name}", label = "error")
        return

    server_info = index[server_name]
    server_dir = os.path.join(MCP_SERVERS_DIR, server_name)
    config_path = os.path.join(server_dir, "config.json")

    if os.path.isfile(config_path) : 
        add_log(f"MCP server '{server_name}' already installed.", label = "warning")
        return

    config_data = {}
    if server_info.get("type", None) == "uv_run" :
        dependencies = server_info.get("dependencies", [])
        if not install_dependencies(dependencies):
            add_log("Error: failed to install dependencies.", label = "error")

        which_uv_result = subprocess.run(
            ['which', 'uv'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        config_data = {
            "command" : which_uv_result.stdout.strip(), 
            "args" : [
                "--directory",
                f"{os.path.dirname(os.path.abspath(__file__))}/.mcp_servers/{server_name}",
                "run", 
                f"{server_info["entry"]}",
            ],
        }
    
    if len(config_data) > 0 :
        os.makedirs(server_dir, exist_ok = True)
        download_files(server_dir, server_info.get("files", []))
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent = 2)
        add_log(f"MCP server '{server_name}' has been successfully installed.", label = "success")
    else :
        add_log(f"Invalid configuration for MCP server: {server_name}", label = "error")
 
def collect_mcp_server_configs(base_dir: str = ".mcp_servers") -> Dict[str, Any]:
    """
    Explore the .mcp_servers directory and collect configurations from each server folder.
    
    Args:
        base_dir (str): Path to the base directory containing MCP server folders
        
    Returns:
        Dict[str, Any]: Dictionary with server names as keys and their configurations as values
    """
    configs = {}
    
    # Check if the base directory exists
    if not os.path.exists(base_dir):
        add_log(f"Directory '{base_dir}' does not exist", label = "warning")
        return configs
    
    # Iterate through all items in the base directory
    for item in os.listdir(base_dir):
        server_path = os.path.join(base_dir, item)
        
        # Check if it's a directory
        if os.path.isdir(server_path):
            server_name = item
            config_file = os.path.join(server_path, "config.json")
            
            # Check if config.json exists in the server directory
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    configs[server_name] = config_data
                    add_log(f"Loaded config for server: {server_name}")
                except json.JSONDecodeError as e:
                    add_log(f"Error parsing JSON in {config_file}: {e}", label = "error")
                except Exception as e:
                    add_log(f"Error reading {config_file}: {e}", label = "error")
            else:
                add_log(f"No config.json found in {server_path}", label = "warning")
    
    return configs

def remove_server(server_name):
    server_dir = os.path.join(MCP_SERVERS_DIR, server_name)
    if not os.path.exists(server_dir):
        add_log(f"MCP server {server_name} is not installed.", label = "warning")
        return
    shutil.rmtree(server_dir)
    add_log(f"Deleted {server_name}.")

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

async def list_servers() : 
    manager = MCPServerManager()
    configs = collect_mcp_server_configs()
    await manager.load_servers_config(configs)
    await manager.connect_all_servers()
    tools = await manager.get_tools()
    print("\nInstalled servers and available tools:")
    current_server = None
    for tool in tools.values() :
        if current_server is None or current_server != tool["server"] : 
            print(f"{tool['server']}:")
            current_server = tool["server"]
        print(f"    - {tool['name']}: {tool['description']}")
    await manager.cleanup()

async def main():
    parser = argparse.ArgumentParser(description="MCP Server Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    install_parser = subparsers.add_parser("install", help = "Install MCP server.")
    install_parser.add_argument("name", help="MCP server name.")
    
    remove_parser = subparsers.add_parser("remove", help = "Delete installed MCP server.")
    remove_parser.add_argument("name", help="MCP server name")
    
    subparsers.add_parser("list", help="List MCP servers.")
    
    args = parser.parse_args()
    
    if args.command == "install":
        install_server(args.name)
    elif args.command == "remove":
        remove_server(args.name)
    elif args.command == "list":
        await list_servers()

os.makedirs('.mcp_servers', exist_ok=True)

if __name__ == "__main__":
    asyncio.run(main())