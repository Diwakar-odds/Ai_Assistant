import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, User, Bot, Search, Download, Mic, Sparkles, Activity, Layers, X } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

const ChatDetail = () => {
  const { chatMessages, sessionActivities, isAITyping, openChainMonitor, currentSession } = useDashboard();
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredMessages = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return chatMessages;
    return chatMessages.filter((m) =>
      m.text.toLowerCase().includes(q) ||
      (m.source || '').toLowerCase().includes(q) ||
      (m.provider || '').toLowerCase().includes(q) ||
      (m.agent_name || m.agent_id || '').toLowerCase().includes(q)
    );
  }, [chatMessages, searchQuery]);

  const handleExport = () => {
    const payload = {
      exported_at: new Date().toISOString(),
      session_id: currentSession?.id || null,
      message_count: chatMessages.length,
      messages: chatMessages,
      activities: sessionActivities,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pulsar-chat-${currentSession?.id || Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-2xl font-bold text-white mb-1">Chat History</h3>
          <p className="text-[#9CA3AF]">View, search, and export your conversations and orchestration logs</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setShowSearch((prev) => !prev);
              if (showSearch) setSearchQuery('');
            }}
            className="px-4 py-2 bg-[#3B82F6]/20 text-[#3B82F6] rounded-lg hover:bg-[#3B82F6]/30 transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <Search className="w-4 h-4" />
            Search
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={chatMessages.length === 0 && sessionActivities.length === 0}
            className="px-4 py-2 bg-[#10B981]/20 text-[#10B981] rounded-lg hover:bg-[#10B981]/30 disabled:opacity-50 transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {showSearch && (
        <div className="relative">
          <Search className="w-4 h-4 text-[#6B7280] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter messages by text, source, provider, or agent..."
            className="w-full bg-[#1F2228] border border-[#3B82F6]/40 rounded-lg pl-10 pr-9 py-2.5 text-sm text-white placeholder-[#6B7280] focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6 max-h-[600px] overflow-y-auto">
        <div className="space-y-4">
          {filteredMessages.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="w-16 h-16 text-[#3B82F6] mx-auto mb-4 opacity-50" />
              <p className="text-[#9CA3AF]">
                {chatMessages.length === 0 ? 'No chat messages yet' : 'No messages match your search'}
              </p>
              <p className="text-sm text-[#6B7280] mt-2">
                {chatMessages.length === 0
                  ? 'Start a conversation to see messages here'
                  : 'Try another keyword or clear the filter'}
              </p>
            </div>
          ) : (
            filteredMessages.map((message, index) => {
              const srcLow = (message.source || '').toLowerCase();
              const isOrb = srcLow.includes('companion') || srcLow.includes('orb');
              const isVoiceMsg =
                message.type === 'user' &&
                Boolean(
                  message.isVoice ||
                    srcLow.includes('voice') ||
                    srcLow.includes('companion') ||
                    srcLow.includes('whisper') ||
                    srcLow.includes('google')
                );

              return (
                <motion.div
                  key={message.message_id || `${message.id}_${index}`}
                  className={`flex gap-4 ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.03, 0.3) }}
                >
                  <div className={`p-3 rounded-full h-fit ${message.type === 'user' ? 'bg-[#3B82F6]/20' : 'bg-[#10B981]/20'}`}>
                    {message.type === 'user' ? (
                      <User className="w-5 h-5 text-[#3B82F6]" />
                    ) : (
                      <Bot className="w-5 h-5 text-[#10B981]" />
                    )}
                  </div>
                  <div className={`flex-1 max-w-[75%] ${message.type === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                    <div
                      className={`px-4 py-3 rounded-lg ${
                        message.type === 'user'
                          ? 'bg-[#3B82F6]/20 border border-[#3B82F6]/30'
                          : 'bg-[#2A2D35] border border-[#3A3D45]'
                      }`}
                    >
                      <div className="flex flex-wrap items-center gap-1.5 mb-1">
                        {isVoiceMsg && (
                          <span className={`inline-flex items-center gap-1 text-xs font-medium ${isOrb ? 'text-amber-300' : 'text-[#60A5FA]'}`}>
                            <Mic className="w-3.5 h-3.5" />
                            <span>{isOrb ? 'Orb Voice' : 'Voice'}</span>
                          </span>
                        )}
                        {message.type === 'ai' && isOrb && (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-300">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Orb Reply</span>
                          </span>
                        )}
                        {(message.agent_name || message.agent_id) && (
                          <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
                            <Bot className="w-3 h-3" />
                            <span>{message.agent_name || message.agent_id}</span>
                          </span>
                        )}
                        {message.provider && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#16181D] text-[#9CA3AF] border border-[#3A3D45]">
                            {message.provider}{message.model ? ` · ${message.model}` : ''}
                          </span>
                        )}
                        {message.chain_id && (
                          <button
                            type="button"
                            onClick={() => openChainMonitor(message.chain_id)}
                            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-[#00f3ff] border border-cyan-500/30 transition-colors"
                          >
                            <Layers className="w-3 h-3" />
                            <span>
                              Chain {typeof message.total_steps === 'number' ? `(${message.steps_completed ?? 0}/${message.total_steps})` : message.chain_id.slice(0, 12)}
                            </span>
                          </button>
                        )}
                      </div>

                      <p className="text-white whitespace-pre-wrap">{message.text}</p>
                    </div>
                    <span className="text-xs text-[#6B7280] mt-1 px-1">{message.time}</span>
                  </div>
                </motion.div>
              );
            })
          )}

          {isAITyping && (
            <motion.div
              className="flex gap-4 flex-row"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="p-3 rounded-full bg-[#10B981]/20">
                <Bot className="w-5 h-5 text-[#10B981]" />
              </div>
              <div className="flex-1 max-w-[70%] items-start flex flex-col">
                <div className="px-4 py-3 rounded-lg bg-[#2A2D35] border border-[#3A3D45] flex items-center gap-1.5 h-12">
                  <div className="w-2 h-2 bg-[#10B981] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-[#10B981] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-[#10B981] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-white">{chatMessages.length}</p>
          <p className="text-sm text-[#9CA3AF] mt-1">Total Messages</p>
        </div>
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-white">{chatMessages.filter(m => m.type === 'user').length}</p>
          <p className="text-sm text-[#9CA3AF] mt-1">Your Messages</p>
        </div>
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-white">{chatMessages.filter(m => m.type === 'ai').length}</p>
          <p className="text-sm text-[#9CA3AF] mt-1">AI Responses</p>
        </div>
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-4 text-center">
          <p className="text-2xl font-bold text-sky-400">{sessionActivities.length}</p>
          <p className="text-sm text-[#9CA3AF] mt-1 flex items-center justify-center gap-1">
            <Activity className="w-3.5 h-3.5 text-sky-400" />
            <span>Activities</span>
          </p>
        </div>
      </div>

      {sessionActivities.length > 0 && (
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400" />
              <span>Session Activity Timeline</span>
            </h4>
            <span className="text-xs text-[#9CA3AF]">{sessionActivities.length} events</span>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {sessionActivities.slice(-30).map((act, idx) => (
              <div
                key={act.id || `detail_act_${idx}`}
                className="flex items-start justify-between gap-3 bg-[#17191E] border border-[#252830] rounded-md px-3 py-2 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-[#252A38] text-sky-300 font-medium text-[10px]">
                      {act.kind}
                    </span>
                    {act.source && <span className="text-[10px] text-[#9CA3AF]">{act.source}</span>}
                    <span className="text-white font-medium truncate">{act.title}</span>
                  </div>
                  {act.detail && <p className="text-[#9CA3AF] mt-1 whitespace-pre-wrap break-words">{act.detail}</p>}
                </div>
                <span className="text-[10px] font-mono text-[#6B7280] shrink-0">{act.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatDetail;
