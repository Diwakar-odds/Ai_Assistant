import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';

interface _Message {
  id: number;
  type: 'user' | 'ai';
  text: string;
  time: string;
}

interface _VoiceCommand {
  id: number;
  command: string;
  time: string;
}

const ChatVoiceHistory = () => {
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const voiceScrollRef = useRef<HTMLDivElement>(null);
  const { chatMessages, voiceCommands, setSelectedView } = useDashboard();

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg overflow-hidden flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-[#1F2228]">
        <div 
          className="p-3 sm:p-3 cursor-pointer hover:bg-[#1F2228]/30 transition-all active:bg-[#1F2228]/50" 
          onClick={() => setSelectedView('chat')}
        >
          <h3 className="text-sm sm:text-sm font-medium text-white mb-2">Chat History</h3>
          <div
            ref={chatScrollRef}
            className="space-y-2 max-h-[150px] sm:max-h-[120px] overflow-y-auto scrollbar-thin scrollbar-thumb-[#3B82F6] scrollbar-track-[#1F2228]"
          >
            {chatMessages.length === 0 ? (
              <p className="text-xs text-[#6B7280] text-center py-4">No messages yet</p>
            ) : (
              chatMessages.map((message, index) => (
                <motion.div
                  key={message.id}
                  className={`${message.type === 'user'
                      ? 'bg-[#3B82F6]/15 ml-auto'
                      : 'bg-[#1F2228]'
                    } p-3 rounded-lg max-w-[90%]`}
                  initial={{ opacity: 0, x: message.type === 'user' ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <p className="text-xs text-white mb-1">{message.text}</p>
                  <span className="text-[10px] text-[#6B7280]">{message.time}</span>
                </motion.div>
              ))
            )}
          </div>
        </div>

        <div 
          className="p-3 sm:p-4 cursor-pointer hover:bg-[#1F2228]/30 transition-all active:bg-[#1F2228]/50" 
          onClick={() => setSelectedView('voice')}
        >
          <h3 className="text-sm font-medium text-white mb-2 sm:mb-3">Voice History</h3>
          <div
            ref={voiceScrollRef}
            className="space-y-2 sm:space-y-2.5 max-h-[150px] sm:max-h-[180px] overflow-y-auto scrollbar-thin scrollbar-thumb-[#3B82F6] scrollbar-track-[#1F2228]"
          >
            {voiceCommands.length === 0 ? (
              <p className="text-xs text-[#6B7280] text-center py-4">No voice commands yet</p>
            ) : (
              voiceCommands.map((command, index) => (
                <motion.div
                  key={command.id}
                  className="p-3 bg-[#1F2228] rounded-lg hover:bg-[#1F2228]/80 transition-colors cursor-pointer group"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ scale: 1.02 }}
                >
                  <p className="text-xs text-[#9CA3AF] group-hover:text-white transition-colors">
                    {command.command}
                  </p>
                  <span className="text-[10px] text-[#6B7280] mt-1 block">{command.time}</span>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ChatVoiceHistory;
