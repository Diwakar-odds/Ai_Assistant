# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

#!/usr/bin/env python3
"""
MCP CLI Utility - Command Line Interface for MCP Server Management

This utility provides command-line access to manage and test MCP servers.

Usage:
    python -m ai_assistant.cli.mcp_cli list                    # List configured servers
    python -m ai_assistant.cli.mcp_cli status                  # Show connection status
    python -m ai_assistant.cli.mcp_cli tools [SERVER]         # List tools from server(s)
    python -m ai_assistant.cli.mcp_cli call SERVER TOOL ARGS  # Call a tool
    python -m ai_assistant.cli.mcp_cli test                    # Run tests
    python -m ai_assistant.cli.mcp_cli enable SERVER           # Enable a server
    python -m ai_assistant.cli.mcp_cli disable SERVER          # Disable a server
"""

import sys
import os
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from ai_assistant.integrations.mcp_manager import MCPManager
    from ai_assistant.integrations.mcp_client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.error("❌ MCP not available. Install with: pip install mcp")
    sys.exit(1)


class MCPCli:
    """CLI interface for MCP management"""
    
    def __init__(self):
        self.manager: Optional[MCPManager] = None
        self.config_path = project_root / "config" / "mcp_servers.json"
    
    async def initialize(self):
        """Initialize MCP manager"""
        self.manager = MCPManager(str(self.config_path))
        success = await self.manager.initialize()
        if not success:
            logger.error("❌ Failed to initialize MCP manager")
            return False
        return True
    
    async def list_servers(self):
        """List all configured MCP servers"""
        print("\n📋 Configured MCP Servers\n")
        print("=" * 80)
        
        if not self.manager:
            await self.initialize()
        
        servers = self.manager.config.get('servers', {})
        
        if not servers:
            print("No servers configured.")
            print(f"Add servers to: {self.config_path}")
            return
        
        enabled = self.manager.get_enabled_servers()
        failed = self.manager.get_failed_servers()
        
        for name, config in servers.items():
            status = "🟢 CONNECTED" if name in enabled else "🔴 FAILED" if name in failed else "⚪ DISABLED"
            print(f"\n{status} {name}")
            print(f"  Description: {config.get('description', 'N/A')}")
            print(f"  Command: {config.get('command')} {' '.join(config.get('args', []))[:50]}...")
            print(f"  Category: {config.get('category', 'N/A')}")
            print(f"  Enabled: {config.get('enabled', False)}")
    
    async def show_status(self):
        """Show connection status"""
        if not self.manager:
            await self.initialize()
        
        status = self.manager.get_status()
        
        print("\n📊 MCP Manager Status\n")
        print("=" * 80)
        print(f"Initialized: {'✅' if status['initialized'] else '❌'}")
        print(f"Available: {'✅' if status['available'] else '❌'}")
        print(f"Total Servers: {status['total_servers']}")
        print(f"Connected: {len(status['enabled_servers'])}")
        logger.error(f"Failed: {len(status['failed_servers'])}")
        print(f"Cache Size: {status['cache_size']}")
        
        if status['enabled_servers']:
            print(f"\n✅ Connected Servers: {', '.join(status['enabled_servers'])}")
        
        if status['failed_servers']:
            print(f"\n❌ Failed Servers: {', '.join(status['failed_servers'])}")
    
    async def list_tools(self, server_name: Optional[str] = None):
        """List tools from server(s)"""
        if not self.manager:
            await self.initialize()
        
        print("\n🔧 Available MCP Tools\n")
        print("=" * 80)
        
        if server_name:
            # List tools from specific server
            if server_name not in self.manager.get_enabled_servers():
                logger.error(f"❌ Server '{server_name}' is not connected")
                return
            
            tools = await self.manager.get_server_tools(server_name, use_cache=False)
            
            print(f"\n{server_name} ({len(tools)} tools):")
            for tool in tools:
                print(f"\n  📌 {tool['name']}")
                print(f"     {tool.get('description', 'No description')}")
                if 'inputSchema' in tool:
                    props = tool['inputSchema'].get('properties', {})
                    if props:
                        print(f"     Parameters: {', '.join(props.keys())}")
        else:
            # List tools from all servers
            all_tools = await self.manager.get_all_tools(use_cache=False)
            
            for server, tools in all_tools.items():
                print(f"\n{server} ({len(tools)} tools):")
                for tool in tools[:5]:  # Limit to 5 per server
                    print(f"  - {tool['name']}: {tool.get('description', 'No description')[:60]}...")
                
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more tools")
    
    async def call_tool(self, server_name: str, tool_name: str, args_json: str):
        """Call an MCP tool"""
        if not self.manager:
            await self.initialize()
        
        print(f"\n🔧 Calling {server_name}.{tool_name}\n")
        print("=" * 80)
        
        # Parse arguments
        try:
            args = json.loads(args_json)
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON arguments: {args_json}")
            return
        
        # Call tool
        result = await self.manager.call_tool(server_name, tool_name, args)
        
        if result:
            print("\n✅ Success!\n")
            print(json.dumps(result, indent=2))
        else:
            print("\n❌ Tool call failed")
    
    async def test_connection(self):
        """Test MCP connections"""
        print("\n🧪 Testing MCP Connections\n")
        print("=" * 80)
        
        if not self.manager:
            await self.initialize()
        
        enabled = self.manager.get_enabled_servers()
        
        if not enabled:
            print("No servers enabled. Enable servers in config/mcp_servers.json")
            return
        
        for server_name in enabled:
            print(f"\nTesting {server_name}...")
            try:
                tools = await self.manager.get_server_tools(server_name, use_cache=False)
                print(f"  ✅ Connected - {len(tools)} tools available")
            except Exception as e:
                print(f"  ❌ Failed - {str(e)}")
    
    async def enable_server(self, server_name: str):
        """Enable a server in configuration"""
        print(f"\n🟢 Enabling server: {server_name}\n")
        
        # Load config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if server_name not in config.get('servers', {}):
            logger.error(f"❌ Server '{server_name}' not found in configuration")
            return
        
        # Enable server
        config['servers'][server_name]['enabled'] = True
        
        # Save config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✅ Server '{server_name}' enabled")
        print("   Restart or reload manager to connect")
    
    async def disable_server(self, server_name: str):
        """Disable a server in configuration"""
        print(f"\n🔴 Disabling server: {server_name}\n")
        
        # Load config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if server_name not in config.get('servers', {}):
            logger.error(f"❌ Server '{server_name}' not found in configuration")
            return
        
        # Disable server
        config['servers'][server_name]['enabled'] = False
        
        # Save config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✅ Server '{server_name}' disabled")


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MCP Server Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ai_assistant.cli.mcp_cli list
  python -m ai_assistant.cli.mcp_cli status
  python -m ai_assistant.cli.mcp_cli tools filesystem
  python -m ai_assistant.cli.mcp_cli call filesystem read_file '{"path": "config.json"}'
  python -m ai_assistant.cli.mcp_cli enable postgres
        """
    )
    
    parser.add_argument('command', choices=[
        'list', 'status', 'tools', 'call', 'test', 'enable', 'disable'
    ], help='Command to execute')
    
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    args = parser.parse_args()
    
    cli = MCPCli()
    
    try:
        if args.command == 'list':
            await cli.list_servers()
        
        elif args.command == 'status':
            await cli.show_status()
        
        elif args.command == 'tools':
            server_name = args.args[0] if args.args else None
            await cli.list_tools(server_name)
        
        elif args.command == 'call':
            if len(args.args) < 3:
                print("Usage: call <server> <tool> <json_args>")
                return
            await cli.call_tool(args.args[0], args.args[1], args.args[2])
        
        elif args.command == 'test':
            await cli.test_connection()
        
        elif args.command == 'enable':
            if not args.args:
                print("Usage: enable <server>")
                return
            await cli.enable_server(args.args[0])
        
        elif args.command == 'disable':
            if not args.args:
                print("Usage: disable <server>")
                return
            await cli.disable_server(args.args[0])
    
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
