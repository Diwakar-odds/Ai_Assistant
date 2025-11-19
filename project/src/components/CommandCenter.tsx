import { useState, useEffect } from 'react';
import { Sparkles, Zap, Cloud, Music, Calendar, Activity, Search } from 'lucide-react';
import { io, Socket } from 'socket.io-client';
import LoadingSpinner from './LoadingSpinner';

const CommandCenter = () => {
  const [command, setCommand] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [pulseRings, setPulseRings] = useState<number[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [response, setResponse] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [quickActions] = useState([
    { label: 'Check Weather', icon: Cloud, command: 'What\'s the weather like today?', color: 'from-blue-400 to-cyan-500' },
    { label: 'Play Music', icon: Music, command: 'Play my favorite playlist on Spotify', color: 'from-purple-500 to-pink-600' },
    { label: 'Schedule Meeting', icon: Calendar, command: 'Schedule a meeting for 3 PM tomorrow', color: 'from-green-400 to-teal-500' },
    { label: 'System Status', icon: Activity, command: 'Show me system performance and CPU usage', color: 'from-orange-400 to-red-500' },
    { label: 'Open Apps', icon: Zap, command: 'Open Google Chrome browser', color: 'from-yellow-400 to-orange-500' },
    { label: 'Analyze Screen', icon: Search, command: 'Analyze what\'s currently on my screen', color: 'from-indigo-400 to-purple-500' }
  ]);

  useEffect(() => {
    // Initialize WebSocket connection
    const socketInstance = io();
    setSocket(socketInstance);

    socketInstance.on('connect', () => {
      setIsConnected(true);
      console.log('CommandCenter connected to YourDaddy Assistant backend');
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });

    socketInstance.on('command_response', (data) => {
      setResponse(data.response);
      setIsProcessing(false);
    });

    socketInstance.on('connect_error', () => {
      setIsConnected(false);
      setIsProcessing(false);
    });

    return () => {
      socketInstance.disconnect();
    };
  }, []);

  useEffect(() => {
    const allCommands = [
      'show weather', 'play music', 'open calculator', 'send email',
      'schedule meeting', 'set reminder', 'check calendar', 'system status',
      'run diagnostics', 'backup files', 'optimize performance', 'scan for updates'
    ];
    
    if (command) {
      const filtered = allCommands.filter((cmd) =>
        cmd.toLowerCase().includes(command.toLowerCase())
      );
      setSuggestions(filtered.slice(0, 4));
    } else {
      setSuggestions([]);
    }
  }, [command]);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseRings((prev) => [...prev, Date.now()]);
      setTimeout(() => {
        setPulseRings((prev) => prev.slice(1));
      }, 2000);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleCommand = async (commandText: string) => {
    if (!commandText.trim() || isProcessing) return;

    setIsProcessing(true);
    setResponse('');

    try {
      // Send via WebSocket if connected
      if (socket && isConnected) {
        socket.emit('command', { command: commandText });
        // isProcessing will be set to false when response is received
      } else {
        // Fallback to REST API
        const token = localStorage.getItem('yourdaddy-token');
        const response = await fetch('/api/command', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ command: commandText }),
        });
        
        if (response.ok) {
          const data = await response.json();
          setResponse(data.response);
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        setIsProcessing(false);
      }
      
      setCommand('');
    } catch (error) {
      console.error('Error sending command:', error);
      setResponse('Failed to process command. Please try again.');
      setIsProcessing(false);
    }
  };

  const handleQuickAction = (action: string) => {
    const actionCommand = quickActions.find(qa => qa.label.includes(action));
    if (actionCommand) {
      handleCommand(actionCommand.command);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative animate-fade-in">
      <div className="text-center mb-12">
        <h1 className="text-6xl font-bold mb-4 text-gradient">YourDaddy Assistant</h1>
        <p className="text-xl text-[#DDDDDD]">Your AI-Powered Command Center</p>
      </div>

      <div className="relative mb-16">
        <div className="relative w-64 h-64 flex items-center justify-center">
          {pulseRings.map((ring) => (
            <div
              key={ring}
              className="absolute w-64 h-64 rounded-full border-2 border-[#00CEC9] pulse-ring-animation"
            ></div>
          ))}

          <div className="relative w-48 h-48 rounded-full bg-gradient-to-br from-[#00CEC9] via-[#6C5CE7] to-[#E17055] flex items-center justify-center animate-breathe shadow-2xl shadow-[#00CEC9]/50">
            <div className="w-44 h-44 rounded-full bg-[#0A0E27] flex items-center justify-center">
              <Sparkles size={64} className="text-[#00CEC9] animate-pulse" />
            </div>
          </div>

          <div className="absolute top-0 right-0 w-4 h-4 bg-[#00B894] rounded-full animate-pulse shadow-lg shadow-[#00B894]/50"></div>
          <div className="absolute bottom-0 left-0 w-3 h-3 bg-[#E17055] rounded-full animate-pulse shadow-lg shadow-[#E17055]/50"></div>
        </div>

        {quickActions.map((action, index) => {
          const Icon = action.icon;

          return (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.command)}
              className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${action.color} flex items-center justify-center hover-lift cursor-pointer shadow-lg transition-transform duration-200 hover:scale-110 action-button-${index}`}
              title={action.label}
            >
              <Icon size={28} />
            </button>
          );
        })}
      </div>

      <div className="w-full max-w-3xl relative">
        <div className="glass-strong p-6 rounded-3xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-shrink-0">
              <Search size={24} className="text-[#00CEC9]" />
            </div>
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleCommand(command);
                }
              }}
              placeholder={isConnected ? "Type a command or ask me anything..." : "Connecting to assistant..."}
              disabled={!isConnected}
              className="flex-1 bg-transparent text-white text-xl outline-none placeholder-[#DDDDDD]/50 disabled:opacity-50"
            />
            <button 
              onClick={() => handleCommand(command)}
              disabled={!command.trim() || !isConnected || isProcessing}
              className="flex-shrink-0 px-6 py-3 bg-gradient-to-r from-[#00CEC9] to-[#6C5CE7] rounded-xl hover:scale-105 transition-transform font-semibold disabled:opacity-50 disabled:hover:scale-100"
              title="Send command"
            >
              {isProcessing ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <Zap size={20} />
              )}
            </button>
          </div>

          {suggestions.length > 0 && (
            <div className="border-t border-white/10 pt-4 space-y-2">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleCommand(suggestion)}
                  className="w-full text-left px-4 py-3 rounded-xl hover:bg-white/10 transition-colors text-[#DDDDDD] hover:text-white"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        {response && (
          <div className="mt-6">
            <div className="glass-strong p-6 rounded-3xl">
              <h3 className="text-lg font-semibold mb-3 text-[#00CEC9]">Assistant Response:</h3>
              <p className="text-white whitespace-pre-wrap">{response}</p>
            </div>
          </div>
        )}

        {isProcessing && !response && (
          <div className="mt-6">
            <div className="glass-strong p-6 rounded-3xl flex items-center justify-center gap-3">
              <LoadingSpinner size="sm" />
              <span className="text-[#DDDDDD]">Processing your command...</span>
            </div>
          </div>
        )}

        <div className="mt-6 flex items-center justify-center gap-4 text-sm text-[#DDDDDD]/70">
          <span className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full animate-pulse ${isConnected ? 'bg-[#00B894]' : 'bg-red-500'}`}></div>
            {isConnected ? 'Connected' : 'Connecting...'}
          </span>
          <span>•</span>
          <span>24/7 Monitoring</span>
          <span>•</span>
          <span>Ultra-Fast Response</span>
        </div>
      </div>
    </div>
  );
};

export default CommandCenter;
