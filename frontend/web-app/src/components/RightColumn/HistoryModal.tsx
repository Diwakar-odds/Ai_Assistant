import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, MessageSquare, Trash2 } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

interface HistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const HistoryModal = ({ isOpen, onClose }: HistoryModalProps) => {
  const { conversationHistory, loadSession, deleteSession } = useDashboard();

  const handleLoadSession = (sessionId: string) => {
    loadSession?.(sessionId);
    onClose();
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession?.(sessionId);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-[101] flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-[#16181D] border border-[#1F2228] rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col shadow-2xl"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[#1F2228] bg-[#1F2228]/50">
                <div className="flex items-center gap-3">
                  <Clock className="w-5 h-5 text-[#3B82F6]" />
                  <h2 className="text-lg font-semibold text-white">Conversation History</h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-[#2A2D35] rounded-lg transition-colors"
                  aria-label="Close history modal"
                >
                  <X className="w-5 h-5 text-[#9CA3AF]" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {!conversationHistory || conversationHistory.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Clock className="w-16 h-16 text-[#3B82F6]/30 mb-4" />
                    <p className="text-lg text-[#9CA3AF]">No previous sessions</p>
                    <p className="text-sm text-[#6B7280] mt-2">
                      Your conversation history will appear here
                    </p>
                  </div>
                ) : (
                  conversationHistory.map((session, index) => (
                    <motion.div
                      key={session.id}
                      className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-4 hover:border-[#3B82F6]/50 transition-all cursor-pointer group"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => handleLoadSession(session.id)}
                      whileHover={{ scale: 1.01 }}
                    >
                      {/* Session Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Clock className="w-4 h-4 text-[#3B82F6]" />
                            <span className="text-sm font-medium text-white">
                              {session.startTime}
                            </span>
                            {session.endTime && (
                              <span className="text-xs text-[#6B7280]">
                                - {session.endTime}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 mt-2">
                            <div className="flex items-center gap-1.5">
                              <MessageSquare className="w-3.5 h-3.5 text-[#9CA3AF]" />
                              <span className="text-xs text-[#9CA3AF]">
                                {session.messageCount} messages
                              </span>
                            </div>
                            <div className="text-xs text-[#6B7280]">
                              Duration: {session.duration || 'Active'}
                            </div>
                          </div>
                        </div>

                        {/* Delete Button */}
                        <button
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          className="p-2 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded-lg transition-all"
                          aria-label="Delete session"
                        >
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>

                      {/* Preview of first message */}
                      {session.preview && (
                        <div className="bg-[#16181D] rounded p-2 border border-[#2A2D35]">
                          <p className="text-xs text-[#9CA3AF] line-clamp-2">
                            {session.preview}
                          </p>
                        </div>
                      )}

                      {/* Stats */}
                      <div className="flex gap-4 mt-3 pt-3 border-t border-[#2A2D35]">
                        <div className="text-xs">
                          <span className="text-[#6B7280]">User: </span>
                          <span className="text-[#3B82F6] font-medium">
                            {session.userMessageCount}
                          </span>
                        </div>
                        <div className="text-xs">
                          <span className="text-[#6B7280]">AI: </span>
                          <span className="text-[#10B981] font-medium">
                            {session.aiMessageCount}
                          </span>
                        </div>
                        <div className="text-xs">
                          <span className="text-[#6B7280]">Voice: </span>
                          <span className="text-[#F59E0B] font-medium">
                            {session.voiceCount}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-[#1F2228] bg-[#1F2228]/30">
                <div className="flex items-center justify-between text-xs text-[#6B7280]">
                  <span>
                    Total Sessions: {conversationHistory?.length || 0}
                  </span>
                  <button
                    onClick={onClose}
                    className="px-4 py-2 bg-[#3B82F6] text-white rounded-lg hover:bg-[#3B82F6]/80 transition-colors text-sm font-medium"
                  >
                    Close
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default HistoryModal;
