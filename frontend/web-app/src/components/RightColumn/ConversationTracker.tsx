import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { History, Mic, MessageSquare, Plus, Sparkles } from 'lucide-react';
import HistoryModal from './HistoryModal';

interface ConversationMessage {
  id: number;
  type: 'user' | 'ai';
  text: string;
  time: string;
  isVoice: boolean;
}

const ConversationTracker = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const { chatMessages, voiceCommands, currentSession, startNewSession } = useDashboard();

  // Merge chat and voice into a unified conversation
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);

  useEffect(() => {
    const combined: ConversationMessage[] = [];

    // Add chat messages
    chatMessages.forEach(msg => {
      combined.push({
        ...msg,
        isVoice: false
      });
    });

    // Add voice commands (user inputs)
    voiceCommands.forEach(cmd => {
      combined.push({
        id: cmd.id + 10000,
        type: 'user',
        text: cmd.command,
        time: cmd.time,
        isVoice: true
      });
    });

    // Sort chronologically
    combined.sort((a, b) => a.id - b.id);
    setConversation(combined);
  }, [chatMessages, voiceCommands]);

  useEffect(() => {
    // Auto-scroll smoothly to bottom on new message
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [conversation]);

  return (
    <>
      <motion.div
        className="bg-[#0D1017]/90 border border-[#1E222D] rounded-2xl overflow-hidden flex-1 min-h-0 flex flex-col w-full shadow-xl backdrop-blur-md"
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Sleek Compact Header */}
        <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-[#1E222D] bg-[#121520]/60">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <h3 className="text-xs font-semibold text-white tracking-wide">Conversation</h3>
            <span className="text-[10px] font-medium text-[#64748B] px-1.5 py-0.2 rounded-full bg-[#181C28] border border-[#23293A]">
              {conversation.length}
            </span>
          </div>

          {/* Actions: Compact New & History */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => startNewSession?.()}
              title="Start New Session"
              className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-[#94A3B8] hover:text-white bg-[#181C28] hover:bg-[#222738] border border-[#23293A] rounded-lg transition-all"
            >
              <Plus className="w-3 h-3 text-[#3B82F6]" />
              <span>New</span>
            </button>
            <button
              onClick={() => setShowHistory(true)}
              title="View Conversation History"
              className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-[#60A5FA] bg-[#3B82F6]/10 hover:bg-[#3B82F6]/20 border border-[#3B82F6]/25 rounded-lg transition-all"
            >
              <History className="w-3 h-3 text-[#60A5FA]" />
              <span>History</span>
            </button>
          </div>
        </div>

        {/* Conversation Stream */}
        <div
          ref={scrollRef}
          className="flex-1 p-3 space-y-2.5 overflow-y-auto custom-scrollbar"
        >
          {/* Centered Session Start Marker */}
          {currentSession && (
            <div className="flex justify-center my-1">
              <span className="text-[10px] text-[#64748B] bg-[#141722]/80 px-2.5 py-0.5 rounded-full border border-[#1E2330]">
                Session started at {currentSession.startTime}
              </span>
            </div>
          )}

          {conversation.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
              <div className="w-10 h-10 rounded-xl bg-[#141722] border border-[#1E2330] flex items-center justify-center text-[#475569] mb-2.5">
                <MessageSquare className="w-5 h-5 text-[#3B82F6]/50" />
              </div>
              <p className="text-xs font-medium text-slate-300">No messages yet</p>
              <p className="text-[11px] text-[#64748B] mt-0.5">
                Speak or send a command to start chatting
              </p>
            </div>
          ) : (
            conversation.map((message, index) => {
              const isUser = message.type === 'user';

              return (
                <motion.div
                  key={message.id}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div
                    className={`relative max-w-[88%] px-3 py-2 text-xs leading-relaxed shadow-sm break-words ${
                      isUser
                        ? 'bg-[#2563EB]/15 border border-[#3B82F6]/30 text-slate-100 rounded-2xl rounded-tr-xs'
                        : 'bg-[#141722] border border-[#1E2330] text-slate-200 rounded-2xl rounded-tl-xs'
                    }`}
                  >
                    {/* Optional subtle Voice or Bot badge */}
                    {isUser && message.isVoice && (
                      <div className="flex items-center gap-1 text-[10px] text-[#60A5FA] mb-1 font-medium">
                        <Mic className="w-2.5 h-2.5" />
                        <span>Voice input</span>
                      </div>
                    )}

                    {/* Message Body */}
                    <p className="whitespace-pre-wrap">{message.text}</p>

                    {/* Timestamp */}
                    <div className={`text-[9px] mt-1 text-right ${isUser ? 'text-blue-300/60' : 'text-[#64748B]'}`}>
                      {message.time}
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>

        {/* Minimalist Micro Footer */}
        {conversation.length > 0 && (
          <div className="px-3 py-1.5 bg-[#121520]/40 border-t border-[#1E222D] flex items-center justify-between text-[10px] text-[#64748B]">
            <div className="flex items-center gap-2.5">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#3B82F6]" />
                <span>You: {conversation.filter(m => m.type === 'user').length}</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>AI: {conversation.filter(m => m.type === 'ai').length}</span>
              </span>
              {conversation.some(m => m.isVoice) && (
                <span className="flex items-center gap-1">
                  <Mic className="w-2.5 h-2.5 text-[#F59E0B]" />
                  <span>Voice: {conversation.filter(m => m.isVoice).length}</span>
                </span>
              )}
            </div>
            <span className="text-[#475569]">Pulsar Chat</span>
          </div>
        )}
      </motion.div>

      {/* History Modal */}
      <HistoryModal isOpen={showHistory} onClose={() => setShowHistory(false)} />
    </>
  );
};

export default ConversationTracker;
