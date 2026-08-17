import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { History, Mic, MessageSquare } from 'lucide-react';
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
    // Combine chatMessages and voiceCommands into a single timeline
    const combined: ConversationMessage[] = [];

    // Add chat messages
    chatMessages.forEach(msg => {
      combined.push({
        ...msg,
        isVoice: false
      });
    });

    // Add voice commands (these are user inputs)
    voiceCommands.forEach(cmd => {
      combined.push({
        id: cmd.id + 10000, // Offset to avoid ID collision
        type: 'user',
        text: cmd.command,
        time: cmd.time,
        isVoice: true
      });
    });

    // Sort by ID (chronological order)
    combined.sort((a, b) => a.id - b.id);

    setConversation(combined);
  }, [chatMessages, voiceCommands]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation]);

  return (
    <>
      <motion.div
        className="glass-panel rounded-lg overflow-hidden flex-1 min-h-0 flex flex-col w-full"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {/* Header with History Button */}
        <div className="flex items-center justify-between p-3 border-b border-[#1F2228]">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#3B82F6]" />
            <h3 className="text-sm font-medium text-white">Ongoing Conversation</h3>
          </div>
          <div className="flex gap-2">
            <motion.button
              onClick={() => startNewSession?.()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#3B82F6]/20 text-[#3B82F6] rounded-lg hover:bg-[#3B82F6]/30 transition-all text-xs font-medium"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <span className="text-lg leading-none">+</span>
              New
            </motion.button>
            <motion.button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-neon-cyan/20 text-neon-cyan rounded-lg hover:bg-neon-cyan/30 transition-all text-xs font-medium"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <History className="w-3.5 h-3.5" />
              History
            </motion.button>
          </div>
        </div>

        {/* Session Info */}
        {currentSession && (
          <div className="px-3 py-2 bg-[#1F2228]/50 border-b border-[#1F2228]">
            <p className="text-xs text-[#9CA3AF]">
              Session started: <span className="text-white">{currentSession.startTime}</span>
            </p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              Messages: <span className="text-[#3B82F6]">{conversation.length}</span>
            </p>
          </div>
        )}

        {/* Conversation Display */}
        <div
          ref={scrollRef}
          className="flex-1 p-3 space-y-3 overflow-y-auto scrollbar-thin scrollbar-thumb-[#3B82F6] scrollbar-track-[#1F2228]"
        >
          {conversation.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <MessageSquare className="w-12 h-12 text-[#3B82F6]/30 mb-3" />
              <p className="text-sm text-[#6B7280]">No conversation yet</p>
              <p className="text-xs text-[#6B7280]/60 mt-1">
                Start talking or type a message
              </p>
            </div>
          ) : (
            conversation.map((message, index) => (
              <motion.div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
              >
                <div
                  className={`max-w-[85%] rounded-lg p-3 ${message.type === 'user'
                    ? 'bg-neon-cyan/20 border border-neon-cyan/30'
                    : 'bg-[#1F2228] border border-[#2A2D35]'
                    }`}
                >
                  {/* Message Header */}
                  <div className="flex items-center gap-2 mb-1.5">
                    {message.type === 'user' ? (
                      <>
                        {message.isVoice && (
                          <Mic className="w-3 h-3 text-[#3B82F6]" />
                        )}
                        <span className="text-xs font-medium text-neon-cyan">You</span>
                      </>
                    ) : (
                      <span className="text-xs font-medium text-[#10B981]">AI Assistant</span>
                    )}
                  </div>

                  {/* Message Text */}
                  <p className="text-sm text-white leading-relaxed break-words">
                    {message.text}
                  </p>

                  {/* Timestamp */}
                  <span className="text-[10px] text-[#6B7280] block mt-1.5">
                    {message.time}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </div>

        {/* Footer Stats */}
        <div className="px-3 py-2 bg-[#1F2228]/30 border-t border-[#1F2228] flex justify-around">
          <div className="text-center">
            <p className="text-xs text-[#9CA3AF]">Your Messages</p>
            <p className="text-sm font-semibold text-white">
              {conversation.filter(m => m.type === 'user').length}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-[#9CA3AF]">AI Responses</p>
            <p className="text-sm font-semibold text-white">
              {conversation.filter(m => m.type === 'ai').length}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-[#9CA3AF]">Voice Input</p>
            <p className="text-sm font-semibold text-[#3B82F6]">
              {conversation.filter(m => m.isVoice).length}
            </p>
          </div>
        </div>
      </motion.div>

      {/* History Modal */}
      <HistoryModal isOpen={showHistory} onClose={() => setShowHistory(false)} />
    </>
  );
};

export default ConversationTracker;
