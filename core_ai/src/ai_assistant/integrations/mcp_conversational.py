"""
MCP Integration Enhancement for Conversational AI

This module extends the AdvancedConversationalAI class to support MCP tool calling,
allowing the AI to use external MCP servers for enhanced capabilities.

Usage:
    This module patches the existing conversational AI to add MCP awareness.
    Import after conversational_ai to extend functionality.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any

try:
    from ai_assistant.integrations.mcp_manager import get_mcp_manager
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP manager not available")


class MCPConversationalEnhancer:
    """
    Enhances conversational AI with MCP tool calling capabilities
    """
    
    def __init__(self, conversational_ai=None):
        """
        Initialize MCP enhancer
        
        Args:
            conversational_ai: Instance of AdvancedConversationalAI to enhance
        """
        self.logger = logging.getLogger(__name__)
        self.conversational_ai = conversational_ai
        self.mcp_manager = None
        self.mcp_enabled = False
        self.available_tools = {}
        
        if MCP_AVAILABLE:
            self.logger.info("✅ MCP integration available for conversational AI")
        else:
            self.logger.warning("⚠️  MCP not available - install with: pip install mcp")
    
    async def initialize(self):
        """Initialize MCP manager and load available tools"""
        if not MCP_AVAILABLE:
            return False
        
        try:
            self.mcp_manager = await get_mcp_manager()
            
            if self.mcp_manager and self.mcp_manager.initialized:
                # Load available tools
                self.available_tools = await self.mcp_manager.get_all_tools()
                self.mcp_enabled = True
                
                tool_count = sum(len(tools) for tools in self.available_tools.values())
                self.logger.info(f"✅ MCP integration initialized with {tool_count} tools")
                return True
            else:
                self.logger.warning("MCP manager not initialized")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP integration: {e}")
            return False
    
    async def check_and_call_mcp_tool(self, user_message: str) -> Optional[str]:
        """
        Check if user message can be handled by an MCP tool and call it
        
        Args:
            user_message: User's input message
            
        Returns:
            Tool result if matched and executed, None otherwise
        """
        if not self.mcp_enabled or not self.mcp_manager:
            return None
        
        message_lower = user_message.lower()
        
        # File operations
        if any(phrase in message_lower for phrase in ['read file', 'open file', 'show file']):
            return await self._handle_file_read(user_message)
        
        # Database queries
        if any(phrase in message_lower for phrase in ['query database', 'search database', 'database query']):
            return await self._handle_database_query(user_message)
        
        # Web search
        if any(phrase in message_lower for phrase in ['search web', 'search online', 'find on web']):
            return await self._handle_web_search(user_message)
        
        # GitHub operations
        if any(phrase in message_lower for phrase in ['github', 'git repo', 'repository']):
            return await self._handle_github_operation(user_message)
        
        return None
    
    async def _handle_file_read(self, message: str) -> Optional[str]:
        """Handle file reading via filesystem MCP server"""
        try:
            # Extract file path from message (simple extraction)
            # In production, use better NLP for extraction
            import re
            
            # Try to find quoted path
            quoted_match = re.search(r'["\']([^"\']+)["\']', message)
            if quoted_match:
                file_path = quoted_match.group(1)
            else:
                # Try to find path-like string
                path_match = re.search(r'([A-Za-z]:[/\\].+|/[/\w]+)', message)
                if path_match:
                    file_path = path_match.group(1)
                else:
                    return "Please specify the file path in quotes, e.g., 'read file \"config.json\"'"
            
            # Call filesystem MCP tool
            result = await self.mcp_manager.call_tool(
                "filesystem",
                "read_file",
                {"path": file_path}
            )
            
            if result:
                # Format result for user
                return f"📄 File contents of {file_path}:\n\n{result}"
            else:
                return f"❌ Could not read file: {file_path}"
                
        except Exception as e:
            self.logger.error(f"Error reading file via MCP: {e}")
            return f"❌ Error reading file: {str(e)}"
    
    async def _handle_database_query(self, message: str) -> Optional[str]:
        """Handle database queries via PostgreSQL/SQLite MCP server"""
        try:
            # Extract SQL query (simple extraction - improve with NLP)
            import re
            
            # Look for SQL keywords
            sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE).+', message, re.IGNORECASE)
            if not sql_match:
                return "Please provide a SQL query, e.g., 'query database: SELECT * FROM users'"
            
            sql_query = sql_match.group(0)
            
            # Try postgres first, then sqlite
            for server in ["postgres", "sqlite"]:
                if server in self.mcp_manager.get_enabled_servers():
                    result = await self.mcp_manager.call_tool(
                        server,
                        "query",
                        {"sql": sql_query}
                    )
                    
                    if result:
                        return f"📊 Query results:\n\n{result}"
            
            return "❌ No database server available. Enable postgres or sqlite in config/mcp_servers.json"
            
        except Exception as e:
            self.logger.error(f"Error executing database query via MCP: {e}")
            return f"❌ Database query error: {str(e)}"
    
    async def _handle_web_search(self, message: str) -> Optional[str]:
        """Handle web search via Brave Search MCP server"""
        try:
            # Extract search query
            search_terms = message.lower().replace('search web', '').replace('search online', '').replace('find on web', '').strip()
            
            if not search_terms:
                return "Please specify what to search for"
            
            # Check if brave-search is enabled
            if "brave-search" in self.mcp_manager.get_enabled_servers():
                result = await self.mcp_manager.call_tool(
                    "brave-search",
                    "web_search",
                    {"query": search_terms}
                )
                
                if result:
                    return f"🔍 Search results for '{search_terms}':\n\n{result}"
            
            return "❌ Web search not available. Enable brave-search in config/mcp_servers.json"
            
        except Exception as e:
            self.logger.error(f"Error performing web search via MCP: {e}")
            return f"❌ Web search error: {str(e)}"
    
    async def _handle_github_operation(self, message: str) -> Optional[str]:
        """Handle GitHub operations via GitHub MCP server"""
        try:
            message_lower = message.lower()
            
            if "github" not in self.mcp_manager.get_enabled_servers():
                return "❌ GitHub integration not available. Enable github in config/mcp_servers.json"
            
            # Search repositories
            if 'search' in message_lower and ('repo' in message_lower or 'repository' in message_lower):
                # Extract search term
                search_term = message.lower().replace('github', '').replace('search', '').replace('repo', '').replace('repository', '').strip()
                
                result = await self.mcp_manager.call_tool(
                    "github",
                    "search_repositories",
                    {"query": search_term}
                )
                
                if result:
                    return f"🐙 GitHub repositories for '{search_term}':\n\n{result}"
            
            return "GitHub operations available: search repositories, list issues, create issue"
            
        except Exception as e:
            self.logger.error(f"Error with GitHub operation via MCP: {e}")
            return f"❌ GitHub error: {str(e)}"
    
    def get_available_mcp_tools_description(self) -> str:
        """Get a description of available MCP tools for the AI to use"""
        if not self.mcp_enabled or not self.available_tools:
            return ""
        
        descriptions = ["Available MCP capabilities:"]
        
        for server_name, tools in self.available_tools.items():
            descriptions.append(f"\n{server_name}:")
            for tool in tools[:5]:  # Limit to 5 tools per server
                descriptions.append(f"  - {tool['name']}: {tool.get('description', 'No description')}")
        
        return "\n".join(descriptions)


# Global enhancer instance
_global_enhancer: Optional[MCPConversationalEnhancer] = None


async def get_mcp_enhancer(conversational_ai=None) -> MCPConversationalEnhancer:
    """Get or create the global MCP enhancer"""
    global _global_enhancer
    
    if _global_enhancer is None:
        _global_enhancer = MCPConversationalEnhancer(conversational_ai)
        await _global_enhancer.initialize()
    
    return _global_enhancer


# Convenience function to enhance a conversational AI instance
async def enhance_with_mcp(conversational_ai):
    """
    Enhance an existing conversational AI instance with MCP capabilities
    
    Args:
        conversational_ai: Instance of AdvancedConversationalAI
        
    Returns:
        Enhanced conversational AI with MCP support
    """
    enhancer = await get_mcp_enhancer(conversational_ai)
    
    # Patch the process_message method to check MCP tools first
    original_process_message = conversational_ai.process_message
    
    def enhanced_process_message(message: str, role: str = "user") -> str:
        """Enhanced process_message that checks MCP tools first"""
        # Try MCP tools first
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                mcp_result = None
            else:
                # Create new event loop if needed
                mcp_result = asyncio.run(enhancer.check_and_call_mcp_tool(message))
            
            if mcp_result:
                return mcp_result
        except Exception as e:
            logging.error(f"MCP tool check error: {e}")
        
        # Fall back to original processing
        return original_process_message(message, role)
    
    # Replace the method
    conversational_ai.process_message = enhanced_process_message
    conversational_ai.mcp_enhancer = enhancer
    
    logging.info("✅ Conversational AI enhanced with MCP capabilities")
    return conversational_ai


if __name__ == "__main__":
    # Test MCP enhancement
    async def test():
        logging.basicConfig(level=logging.INFO)
        
        print("\n🧪 Testing MCP Conversational Enhancement...\n")
        
        enhancer = MCPConversationalEnhancer()
        success = await enhancer.initialize()
        
        if success:
            print(f"✅ MCP enhancer initialized")
            print(f"\n{enhancer.get_available_mcp_tools_description()}")
        else:
            print("❌ MCP enhancer initialization failed")
            print("💡 Enable MCP servers in config/mcp_servers.json")
    
    asyncio.run(test())
