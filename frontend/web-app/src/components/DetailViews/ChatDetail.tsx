import { motion } from 'framer-motion';
import { MessageSquare, User, Bot, Search, Download } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

const ChatDetail = () => {
  const { chatMessages } = useDashboard();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Chat History</h3>
          <p className="text-[#9CA3AF]">View and manage all your conversations</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-[#3B82F6]/20 text-[#3B82F6] rounded-lg hover:bg-[#3B82F6]/30 transition-colors flex items-center gap-2">
            <Search className="w-4 h-4" />
            Search
          </button>
          <button className="px-4 py-2 bg-[#10B981]/20 text-[#10B981] rounded-lg hover:bg-[#10B981]/30 transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6 max-h-[600px] overflow-y-auto">
        <div className="space-y-4">
          {chatMessages.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="w-16 h-16 text-[#3B82F6] mx-auto mb-4 opacity-50" />
              <p className="text-[#9CA3AF]">No chat messages yet</p>
              <p className="text-sm text-[#6B7280] mt-2">Start a conversation to see messages here</p>
            </div>
          ) : (
            chatMessages.map((message, index) => (
              <motion.div
                key={message.id}
                className={`flex gap-4 ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className={`p-3 rounded-full ${message.type === 'user' ? 'bg-[#3B82F6]/20' : 'bg-[#10B981]/20'}`}>
                  {message.type === 'user' ? (
                    <User className="w-5 h-5 text-[#3B82F6]" />
                  ) : (
                    <Bot className="w-5 h-5 text-[#10B981]" />
                  )}
                </div>
                <div className={`flex-1 max-w-[70%] ${message.type === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className={`px-4 py-3 rounded-lg ${
                    message.type === 'user' 
                      ? 'bg-[#3B82F6]/20 border border-[#3B82F6]/30' 
                      : 'bg-[#2A2D35] border border-[#3A3D45]'
                  }`}>
                    <p className="text-white">{message.text}</p>
                  </div>
                  <span className="text-xs text-[#6B7280] mt-1 px-1">{message.time}</span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
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
      </div>
    </div>
  );
};

export default ChatDetail;
