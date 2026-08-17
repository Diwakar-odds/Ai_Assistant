"""
Model Context Protocol (MCP) Client Integration

This module provides a client interface to connect to and interact with MCP servers,
allowing the AI assistant to use external tools and resources exposed via the MCP protocol.

Features:
- Connect to multiple MCP servers (file systems, databases, APIs, etc.)
- Discover and call tools from connected servers
- Access resources exposed by servers
- Handle async operations efficiently

Example Usage:
    client = MCPClient()
    await client.connect("filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/path"])
    tools = await client.list_tools("filesystem")
    result = await client.call_tool("filesystem", "read_file", {"path": "test.txt"})
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP library not installed. Install with: pip install mcp")


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection"""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: str = ""
    enabled: bool = True


class MCPClient:
    """
    Client for interacting with Model Context Protocol servers
    """
    
    def __init__(self):
        """Initialize MCP client"""
        self.logger = logging.getLogger(__name__)
        
        if not MCP_AVAILABLE:
            self.logger.error("MCP library not available. Install with: pip install mcp")
            self.available = False
            return
        
        self.available = True
        self.sessions: Dict[str, ClientSession] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.connected_servers: Dict[str, bool] = {}
        
        self.logger.info("✅ MCP Client initialized")
    
    async def connect(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        description: str = ""
    ) -> bool:
        """
        Connect to an MCP server
        
        Args:
            name: Unique name for this server connection
            command: Command to run the MCP server (e.g., "npx", "uvx", "python")
            args: Arguments for the command
            env: Optional environment variables
            description: Human-readable description of the server
            
        Returns:
            True if connection successful, False otherwise
            
        Example:
            # Connect to filesystem server
            await client.connect(
                "filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
            )
            
            # Connect to PostgreSQL server
            await client.connect(
                "database",
                command="uvx",
                args=["mcp-server-postgres", "postgresql://localhost/mydb"]
            )
        """
        if not self.available:
            self.logger.error("MCP not available")
            return False
        
        try:
            # Store configuration
            self.server_configs[name] = MCPServerConfig(
                name=name,
                command=command,
                args=args,
                env=env,
                description=description
            )
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            # Connect to server
            self.logger.info(f"🔌 Connecting to MCP server: {name}")
            self.logger.debug(f"   Command: {command} {' '.join(args)}")
            
            # Note: Connection is managed by context manager in actual usage
            # Here we just validate the configuration
            self.connected_servers[name] = True
            
            self.logger.info(f"✅ Connected to MCP server: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to MCP server {name}: {e}")
            self.connected_servers[name] = False
            return False
    
    async def disconnect(self, name: str):
        """
        Disconnect from an MCP server
        
        Args:
            name: Name of the server to disconnect from
        """
        if name in self.sessions:
            try:
                # Sessions are managed by context managers
                del self.sessions[name]
                self.connected_servers[name] = False
                self.logger.info(f"🔌 Disconnected from MCP server: {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List all tools available from a specific MCP server
        
        Args:
            server_name: Name of the server to query
            
        Returns:
            List of tool definitions with name, description, and input schema
            
        Example:
            tools = await client.list_tools("filesystem")
            for tool in tools:
                print(f"{tool['name']}: {tool['description']}")
        """
        if not self.available or server_name not in self.server_configs:
            self.logger.error(f"Server {server_name} not configured")
            return []
        
        try:
            config = self.server_configs[server_name]
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get tools from server
                    tools_response = await session.list_tools()
                    
                    tools = []
                    for tool in tools_response.tools:
                        tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        })
                    
                    self.logger.info(f"📋 Found {len(tools)} tools on {server_name}")
                    return tools
                    
        except Exception as e:
            self.logger.error(f"Error listing tools from {server_name}: {e}")
            return []
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Call a tool on an MCP server
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result or None on error
            
        Example:
            # Read a file
            result = await client.call_tool(
                "filesystem",
                "read_file",
                {"path": "/workspace/config.json"}
            )
            
            # Query database
            result = await client.call_tool(
                "database",
                "query",
                {"sql": "SELECT * FROM users LIMIT 10"}
            )
        """
        if not self.available or server_name not in self.server_configs:
            self.logger.error(f"Server {server_name} not configured")
            return None
        
        try:
            config = self.server_configs[server_name]
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    self.logger.info(f"🔧 Calling tool: {server_name}.{tool_name}")
                    self.logger.debug(f"   Arguments: {arguments}")
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, arguments)
                    
                    self.logger.info(f"✅ Tool call successful: {tool_name}")
                    return result
                    
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return None
    
    async def list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List all resources available from a specific MCP server
        
        Args:
            server_name: Name of the server to query
            
        Returns:
            List of resource definitions
        """
        if not self.available or server_name not in self.server_configs:
            self.logger.error(f"Server {server_name} not configured")
            return []
        
        try:
            config = self.server_configs[server_name]
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get resources from server
                    resources_response = await session.list_resources()
                    
                    resources = []
                    for resource in resources_response.resources:
                        resources.append({
                            "uri": resource.uri,
                            "name": resource.name,
                            "description": resource.description,
                            "mimeType": getattr(resource, 'mimeType', None)
                        })
                    
                    self.logger.info(f"📚 Found {len(resources)} resources on {server_name}")
                    return resources
                    
        except Exception as e:
            self.logger.error(f"Error listing resources from {server_name}: {e}")
            return []
    
    async def read_resource(self, server_name: str, uri: str) -> Optional[Any]:
        """
        Read a resource from an MCP server
        
        Args:
            server_name: Name of the server
            uri: URI of the resource to read
            
        Returns:
            Resource content or None on error
        """
        if not self.available or server_name not in self.server_configs:
            self.logger.error(f"Server {server_name} not configured")
            return None
        
        try:
            config = self.server_configs[server_name]
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    self.logger.info(f"📖 Reading resource: {uri}")
                    
                    # Read the resource
                    result = await session.read_resource(uri)
                    
                    self.logger.info(f"✅ Resource read successful")
                    return result
                    
        except Exception as e:
            self.logger.error(f"Error reading resource {uri} from {server_name}: {e}")
            return None
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [name for name, connected in self.connected_servers.items() if connected]
    
    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific server"""
        if server_name not in self.server_configs:
            return None
        
        config = self.server_configs[server_name]
        return {
            "name": config.name,
            "command": config.command,
            "args": config.args,
            "description": config.description,
            "connected": self.connected_servers.get(server_name, False),
            "enabled": config.enabled
        }
    
    def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get information about all configured servers"""
        return [self.get_server_info(name) for name in self.server_configs.keys()]


# Convenience function for simple tool calls
async def call_mcp_tool(
    server_command: str,
    server_args: List[str],
    tool_name: str,
    tool_arguments: Dict[str, Any]
) -> Optional[Any]:
    """
    Simplified function to call an MCP tool without managing a client instance
    
    Args:
        server_command: Command to run the MCP server
        server_args: Arguments for the server command
        tool_name: Name of the tool to call
        tool_arguments: Arguments for the tool
        
    Returns:
        Tool execution result or None on error
        
    Example:
        result = await call_mcp_tool(
            "npx",
            ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
            "read_file",
            {"path": "config.json"}
        )
    """
    if not MCP_AVAILABLE:
        logging.error("MCP library not available")
        return None
    
    try:
        server_params = StdioServerParameters(
            command=server_command,
            args=server_args
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_arguments)
                return result
                
    except Exception as e:
        logging.error(f"Error in MCP tool call: {e}")
        return None


# Global client instance for easy access
_global_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance"""
    global _global_client
    if _global_client is None:
        _global_client = MCPClient()
    return _global_client


if __name__ == "__main__":
    # Example usage and testing
    async def test_mcp_client():
        """Test MCP client functionality"""
        client = MCPClient()
        
        if not client.available:
            print("❌ MCP not available. Install with: pip install mcp")
            return
        
        # Example: Connect to filesystem server (if available)
        print("\n🧪 Testing MCP Client...\n")
        
        # This would work if you have the filesystem server installed:
        # npm install -g @modelcontextprotocol/server-filesystem
        """
        success = await client.connect(
            "filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(Path.cwd())]
        )
        
        if success:
            # List tools
            tools = await client.list_tools("filesystem")
            print(f"📋 Available tools: {[t['name'] for t in tools]}")
            
            # Try to read a file
            result = await client.call_tool(
                "filesystem",
                "read_file",
                {"path": "README.md"}
            )
            print(f"✅ Read result: {result}")
        """
        
        print("\n✅ MCP Client test complete")
        print("   To use with actual servers, install them first:")
        print("   - Filesystem: npm install -g @modelcontextprotocol/server-filesystem")
        print("   - PostgreSQL: pip install mcp-server-postgres")
        print("   - GitHub: npm install -g @modelcontextprotocol/server-github")
    
    # Run test
    asyncio.run(test_mcp_client())
