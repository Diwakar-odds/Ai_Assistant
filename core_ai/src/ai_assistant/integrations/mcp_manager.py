# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
MCP Manager - Centralized Management for Model Context Protocol Servers

This module provides high-level management for MCP server connections,
including automatic loading from config, connection pooling, and easy tool access.

Features:
- Auto-load server configurations from config/mcp_servers.json
- Manage multiple concurrent MCP server connections
- Provide unified interface for tool discovery and execution
- Handle connection lifecycle and error recovery
- Cache tool/resource listings for performance

Usage:
    manager = MCPManager()
    await manager.initialize()
    
    # List all available tools across all servers
    tools = await manager.get_all_tools()
    
    # Call a tool
    result = await manager.call_tool("filesystem", "read_file", {"path": "config.json"})
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta

try:
    from .mcp_client import MCPClient, MCPServerConfig
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from mcp_client import MCPClient, MCPServerConfig
        MCP_CLIENT_AVAILABLE = True
    except ImportError:
        MCP_CLIENT_AVAILABLE = False
        logging.warning("MCP client not available")


class MCPManager:
    """
    High-level manager for MCP server connections and tool execution
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP Manager
        
        Args:
            config_path: Path to mcp_servers.json config file
        """
        self.logger = logging.getLogger(__name__)
        
        # Set config path
        if config_path is None:
            # Default to config/mcp_servers.json
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "mcp_servers.json"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.client: Optional[MCPClient] = None
        self.initialized = False
        
        # Cache for tools and resources
        self.tools_cache: Dict[str, List[Dict]] = {}
        self.resources_cache: Dict[str, List[Dict]] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
        
        # Track initialization status
        self.enabled_servers: List[str] = []
        self.failed_servers: List[str] = []
        
        if not MCP_CLIENT_AVAILABLE:
            self.logger.error("MCP client not available. Install with: pip install mcp")
            self.available = False
        else:
            self.available = True
            self.logger.info("✅ MCP Manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the MCP manager by loading config and connecting to enabled servers
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.available:
            self.logger.error("MCP not available")
            return False
        
        try:
            # Load configuration
            if not self._load_config():
                self.logger.error("Failed to load MCP configuration")
                return False
            
            # Create MCP client
            self.client = MCPClient()
            
            # Connect to enabled servers
            await self._connect_servers()
            
            self.initialized = True
            self.logger.info(f"✅ MCP Manager initialized with {len(self.enabled_servers)} servers")
            
            if self.failed_servers:
                self.logger.warning(f"⚠️  {len(self.failed_servers)} servers failed to connect: {self.failed_servers}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Manager: {e}")
            return False
    
    def _load_config(self) -> bool:
        """Load MCP server configuration from JSON file"""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Config file not found: {self.config_path}")
                self.logger.info("Creating default config...")
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            self.logger.info(f"📄 Loaded MCP config from {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load MCP config: {e}")
            return False
    
    def _create_default_config(self):
        """Create a default configuration file"""
        default_config = {
            "servers": {},
            "categories": {},
            "notes": ["Add MCP server configurations here"]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        self.logger.info(f"✅ Created default config at {self.config_path}")
    
    async def _connect_servers(self):
        """Connect to all enabled servers from configuration"""
        servers = self.config.get('servers', {})
        
        for server_name, server_config in servers.items():
            if not server_config.get('enabled', False):
                self.logger.debug(f"⏭️  Skipping disabled server: {server_name}")
                continue
            
            try:
                # Replace environment variables in args and env
                args = self._replace_env_vars(server_config.get('args', []))
                env = self._replace_env_vars(server_config.get('env', {}))
                
                # Connect to server
                success = await self.client.connect(
                    name=server_name,
                    command=server_config['command'],
                    args=args,
                    env=env,
                    description=server_config.get('description', '')
                )
                
                if success:
                    self.enabled_servers.append(server_name)
                    self.logger.info(f"✅ Connected to MCP server: {server_name}")
                else:
                    self.failed_servers.append(server_name)
                    self.logger.error(f"❌ Failed to connect to: {server_name}")
                    
            except Exception as e:
                self.failed_servers.append(server_name)
                self.logger.error(f"❌ Error connecting to {server_name}: {e}")
    
    def _replace_env_vars(self, data):
        """Replace ${VAR} placeholders with environment variables"""
        if isinstance(data, str):
            # Replace ${VAR} with environment variable value
            if '${' in data:
                import re
                matches = re.findall(r'\$\{([^}]+)\}', data)
                for var in matches:
                    value = os.getenv(var, '')
                    if not value:
                        self.logger.warning(f"Environment variable not set: {var}")
                    data = data.replace(f'${{{var}}}', value)
            return data
        
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        
        elif isinstance(data, dict):
            return {k: self._replace_env_vars(v) for k, v in data.items()}
        
        return data
    
    async def get_all_tools(self, use_cache: bool = True) -> Dict[str, List[Dict]]:
        """
        Get all tools from all connected servers
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary mapping server names to their tools
        """
        if not self.initialized:
            self.logger.error("Manager not initialized")
            return {}
        
        all_tools = {}
        
        for server_name in self.enabled_servers:
            # Check cache
            if use_cache and server_name in self.tools_cache:
                cache_time = self.cache_timestamp.get(server_name)
                if cache_time and datetime.now() - cache_time < self.cache_ttl:
                    all_tools[server_name] = self.tools_cache[server_name]
                    continue
            
            # Fetch from server
            try:
                tools = await self.client.list_tools(server_name)
                all_tools[server_name] = tools
                
                # Update cache
                self.tools_cache[server_name] = tools
                self.cache_timestamp[server_name] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error getting tools from {server_name}: {e}")
                all_tools[server_name] = []
        
        return all_tools
    
    async def get_server_tools(self, server_name: str, use_cache: bool = True) -> List[Dict]:
        """
        Get tools from a specific server
        
        Args:
            server_name: Name of the server
            use_cache: Whether to use cached results
            
        Returns:
            List of tool definitions
        """
        if not self.initialized:
            self.logger.error("Manager not initialized")
            return []
        
        if server_name not in self.enabled_servers:
            self.logger.error(f"Server not connected: {server_name}")
            return []
        
        # Check cache
        if use_cache and server_name in self.tools_cache:
            cache_time = self.cache_timestamp.get(server_name)
            if cache_time and datetime.now() - cache_time < self.cache_ttl:
                return self.tools_cache[server_name]
        
        # Fetch from server
        try:
            tools = await self.client.list_tools(server_name)
            
            # Update cache
            self.tools_cache[server_name] = tools
            self.cache_timestamp[server_name] = datetime.now()
            
            return tools
            
        except Exception as e:
            self.logger.error(f"Error getting tools from {server_name}: {e}")
            return []
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Call a tool on a specific server
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result or None on error
        """
        if not self.initialized:
            self.logger.error("Manager not initialized")
            return None
        
        if server_name not in self.enabled_servers:
            self.logger.error(f"Server not connected: {server_name}")
            return None
        
        try:
            result = await self.client.call_tool(server_name, tool_name, arguments)
            return result
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            return None
    
    async def find_and_call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Find a tool by name across all servers and call it
        
        Args:
            tool_name: Name of the tool to find and call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result or None if not found/error
        """
        # Get all tools
        all_tools = await self.get_all_tools()
        
        # Find the tool
        for server_name, tools in all_tools.items():
            for tool in tools:
                if tool['name'] == tool_name:
                    self.logger.info(f"🔍 Found tool '{tool_name}' on server '{server_name}'")
                    return await self.call_tool(server_name, tool_name, arguments)
        
        self.logger.error(f"Tool '{tool_name}' not found on any connected server")
        return None
    
    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration info for a specific server"""
        return self.config.get('servers', {}).get(server_name)
    
    def get_enabled_servers(self) -> List[str]:
        """Get list of enabled server names"""
        return self.enabled_servers.copy()
    
    def get_failed_servers(self) -> List[str]:
        """Get list of servers that failed to connect"""
        return self.failed_servers.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall status of the MCP manager"""
        return {
            "initialized": self.initialized,
            "available": self.available,
            "enabled_servers": self.enabled_servers,
            "failed_servers": self.failed_servers,
            "total_servers": len(self.config.get('servers', {})),
            "cache_size": len(self.tools_cache)
        }
    
    async def reload_config(self):
        """Reload configuration and reconnect to servers"""
        self.logger.info("🔄 Reloading MCP configuration...")
        
        # Clear state
        self.enabled_servers = []
        self.failed_servers = []
        self.tools_cache = {}
        self.resources_cache = {}
        self.cache_timestamp = {}
        
        # Reload
        await self.initialize()
    
    def clear_cache(self):
        """Clear the tools and resources cache"""
        self.tools_cache = {}
        self.resources_cache = {}
        self.cache_timestamp = {}
        self.logger.info("🗑️  Cache cleared")


# Global manager instance
_global_manager: Optional[MCPManager] = None


async def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager instance"""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = MCPManager()
        await _global_manager.initialize()
    
    return _global_manager


# Convenience functions for easy access
async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
    """
    Simplified function to call an MCP tool without managing instances
    
    Args:
        tool_name: Name of the tool to call
        arguments: Arguments for the tool
        
    Returns:
        Tool execution result or None on error
    """
    manager = await get_mcp_manager()
    return await manager.find_and_call_tool(tool_name, arguments)


async def get_mcp_tools() -> Dict[str, List[Dict]]:
    """Get all available MCP tools"""
    manager = await get_mcp_manager()
    return await manager.get_all_tools()


if __name__ == "__main__":
    # Test the MCP manager
    async def test_manager():
        """Test MCP manager functionality"""
        logging.basicConfig(level=logging.INFO)
        
        print("\n🧪 Testing MCP Manager...\n")
        
        manager = MCPManager()
        success = await manager.initialize()
        
        if success:
            logger.info(f"✅ Manager initialized")
            print(f"📊 Status: {manager.get_status()}")
            
            # List all tools
            all_tools = await manager.get_all_tools()
            print(f"\n📋 Available tools across all servers:")
            for server, tools in all_tools.items():
                print(f"  {server}: {len(tools)} tools")
                for tool in tools[:3]:  # Show first 3
                    print(f"    - {tool['name']}: {tool['description']}")
        else:
            logger.error("❌ Failed to initialize manager")
            print("💡 Make sure to configure servers in config/mcp_servers.json")
    
    asyncio.run(test_manager())
