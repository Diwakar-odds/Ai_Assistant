# MCP Client Support - Quick Start Guide

## 🎉 Installation Complete!

MCP (Model Context Protocol) client support has been successfully added to your AI assistant. This allows your AI to connect to and use external MCP servers for enhanced capabilities.

## 📦 What Was Added

### 1. **Core MCP Client** (`ai_assistant/integrations/mcp_client.py`)
- Low-level MCP protocol client
- Connect to any MCP server
- Call tools and read resources
- Async operation support

### 2. **MCP Manager** (`ai_assistant/integrations/mcp_manager.py`)
- High-level server management
- Auto-load from configuration
- Connection pooling
- Tool caching for performance

### 3. **Configuration** (`config/mcp_servers.json`)
- Pre-configured popular MCP servers
- Easy enable/disable
- Environment variable support

### 4. **Conversational AI Integration** (`ai_assistant/integrations/mcp_conversational.py`)
- Automatic MCP tool detection
- Natural language to MCP tool mapping
- Seamless integration with existing AI

### 5. **CLI Utility** (`ai_assistant/cli/mcp_cli.py`)
- Command-line server management
- Test connections
- Call tools directly
- Enable/disable servers

## 🚀 Quick Start

### Step 1: Install MCP Library
```bash
pip install mcp
```

### Step 2: Install MCP Servers (Optional)

**Filesystem Server** (recommended for testing):
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**PostgreSQL Server**:
```bash
pip install mcp-server-postgres
```

**GitHub Server**:
```bash
npm install -g @modelcontextprotocol/server-github
```

### Step 3: Configure Servers

Edit `config/mcp_servers.json` and enable desired servers:

```json
{
  "servers": {
    "filesystem": {
      "enabled": true,
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "f:/bn/assitant"]
    }
  }
}
```

### Step 4: Test Your Setup

```bash
# List configured servers
python -m ai_assistant.cli.mcp_cli list

# Check connection status
python -m ai_assistant.cli.mcp_cli status

# List available tools
python -m ai_assistant.cli.mcp_cli tools filesystem

# Test connections
python -m ai_assistant.cli.mcp_cli test
```

### Step 5: Use in Your AI

The MCP integration automatically enhances your conversational AI:

```python
# In your AI code
from ai_assistant.integrations.mcp_conversational import enhance_with_mcp
from ai_assistant.modules.conversational_ai import AdvancedConversationalAI

# Create AI instance
ai = AdvancedConversationalAI()

# Enhance with MCP capabilities (async)
import asyncio
ai = asyncio.run(enhance_with_mcp(ai))

# Now your AI can use MCP tools!
response = ai.process_message("read file config.json")
```

## 📚 Available MCP Servers

### File Operations
- **filesystem**: Local file access (read, write, search)
  - `npm install -g @modelcontextprotocol/server-filesystem`

### Databases
- **postgres**: PostgreSQL queries
  - `pip install mcp-server-postgres`
- **sqlite**: SQLite database
  - `pip install mcp-server-sqlite`

### Development
- **github**: GitHub repos, issues, PRs
  - `npm install -g @modelcontextprotocol/server-github`

### Web & Search
- **brave-search**: Web search
  - `npm install -g @modelcontextprotocol/server-brave-search`
  - Requires: BRAVE_API_KEY
- **puppeteer**: Browser automation
  - `npm install -g @modelcontextprotocol/server-puppeteer`

### Cloud Services
- **google-drive**: Google Drive access
  - `npm install -g @modelcontextprotocol/server-gdrive`
- **slack**: Slack integration
  - `npm install -g @modelcontextprotocol/server-slack`

### AI Enhancement
- **memory**: Long-term memory/knowledge graph
  - `npm install -g @modelcontextprotocol/server-memory`
- **sequential-thinking**: Enhanced reasoning
  - `npm install -g @modelcontextprotocol/server-sequential-thinking`

## 🔧 Usage Examples

### File Operations
```python
# Read a file
await mcp_manager.call_tool("filesystem", "read_file", {"path": "config.json"})

# List directory
await mcp_manager.call_tool("filesystem", "list_directory", {"path": "."})
```

### Database Queries
```python
# Query PostgreSQL
await mcp_manager.call_tool("postgres", "query", {
    "sql": "SELECT * FROM users LIMIT 10"
})
```

### Web Search
```python
# Search the web
await mcp_manager.call_tool("brave-search", "web_search", {
    "query": "Python MCP tutorial"
})
```

### GitHub Operations
```python
# Search repositories
await mcp_manager.call_tool("github", "search_repositories", {
    "query": "machine learning"
})
```

## 🎯 Natural Language Examples

Your AI can now understand these commands:

- "read file config.json" → Uses filesystem MCP
- "query database: SELECT * FROM users" → Uses postgres/sqlite MCP  
- "search web for Python tutorials" → Uses brave-search MCP
- "search github for AI projects" → Uses github MCP

## 📝 CLI Commands Reference

```bash
# Server Management
python -m ai_assistant.cli.mcp_cli list              # List all servers
python -m ai_assistant.cli.mcp_cli status            # Connection status
python -m ai_assistant.cli.mcp_cli enable filesystem # Enable server
python -m ai_assistant.cli.mcp_cli disable postgres  # Disable server

# Tool Discovery
python -m ai_assistant.cli.mcp_cli tools             # List all tools
python -m ai_assistant.cli.mcp_cli tools filesystem  # Tools from specific server

# Testing
python -m ai_assistant.cli.mcp_cli test              # Test all connections

# Direct Tool Calls
python -m ai_assistant.cli.mcp_cli call filesystem read_file '{"path": "README.md"}'
```

## 🔐 Security Notes

1. **Environment Variables**: Sensitive data (API keys, DB passwords) should be in environment variables, not config files
2. **File Access**: Filesystem server only accesses paths you specify
3. **Database**: Use read-only users for query-only access
4. **API Keys**: Store in `.env` file, reference as `${VAR_NAME}` in config

## 🐛 Troubleshooting

### "MCP library not installed"
```bash
pip install mcp
```

### "Server not found"
Install the MCP server first:
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

### "Connection failed"
1. Check server is installed
2. Verify command and args in config
3. Check environment variables are set
4. Test with CLI: `python -m ai_assistant.cli.mcp_cli test`

### "No tools available"
Enable at least one server in `config/mcp_servers.json`

## 🎓 Next Steps

1. **Enable Filesystem Server** - Great for testing
2. **Add Database Access** - Enable postgres/sqlite for data queries  
3. **Web Search** - Get Brave API key and enable search
4. **Custom Servers** - Add your own MCP servers to the config

## 📖 Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Servers List](https://github.com/modelcontextprotocol/servers)
- [Build Your Own MCP Server](https://modelcontextprotocol.io/docs/building-servers)

---

**Your AI now has superpowers! 🚀**

Questions? Check the logs in `logs/` or run with `--verbose` for debug output.
