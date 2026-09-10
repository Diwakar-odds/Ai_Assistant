import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Clock, 
  MessageSquare, 
  Trash2, 
  Calendar, 
  Search, 
  ArrowUpRight, 
  Sparkles,
  Bot,
  User,
  Mic,
  RotateCcw
} from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

interface HistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const HistoryModal = ({ isOpen, onClose }: HistoryModalProps) => {
  const { conversationHistory, loadSession, deleteSession, clearAllSessions } = useDashboard();
  const [searchQuery, setSearchQuery] = useState('');
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const handleLoadSession = (sessionId: string) => {
    loadSession?.(sessionId);
    onClose();
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession?.(sessionId);
  };

  // Helper: Format Date and Day cleanly
  const getSessionDateInfo = (session: any) => {
    let timestamp = session.startTimestamp;
    if (!timestamp && session.id && session.id.startsWith('session_')) {
      const parsed = parseInt(session.id.replace('session_', ''), 10);
      if (!isNaN(parsed) && parsed > 1000000000000) {
        timestamp = parsed;
      }
    }
    const d = timestamp ? new Date(timestamp) : new Date();
    const dayName = session.day || d.toLocaleDateString(undefined, { weekday: 'long' });
    const dateFormatted = session.date || d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = d.toDateString() === yesterday.toDateString();

    const tag = isToday ? 'Today' : isYesterday ? 'Yesterday' : dayName;

    return {
      day: dayName,
      date: dateFormatted,
      tag,
      displayString: `${tag} • ${dateFormatted}`,
      timestamp: timestamp || d.getTime()
    };
  };

  // Helper: Get meaningful preview, avoiding default bot greeting
  const getSessionPreview = (session: any): string => {
    // If preview exists and isn't the repetitive Jarvis welcome
    if (
      session.preview && 
      !session.preview.includes('At your service, Sir') && 
      !session.preview.includes('All systems online') &&
      !session.preview.includes('Ready for a new session')
    ) {
      return session.preview;
    }

    // Look for user message
    const userMsg = session.messages?.find((m: any) => m.type === 'user' && m.text?.trim()?.length > 0);
    if (userMsg) return userMsg.text.trim();

    // Look for voice command
    const voiceCmd = session.voiceCommands?.[0]?.command;
    if (voiceCmd) return voiceCmd.trim();

    // Look for first meaningful AI message
    const aiMsg = session.messages?.find((m: any) => 
      m.type === 'ai' && 
      m.text && 
      !m.text.includes('At your service') && 
      !m.text.includes('Ready for a new session')
    );
    if (aiMsg) return aiMsg.text.trim();

    return session.preview || 'Conversation Session';
  };

  // Helper: Compute accurate duration
  const getSessionDuration = (session: any): string => {
    let start = session.startTimestamp;
    if (!start && session.id && session.id.startsWith('session_')) {
      const parsed = parseInt(session.id.replace('session_', ''), 10);
      if (!isNaN(parsed) && parsed > 1000000000000) start = parsed;
    }
    const end = session.endTimestamp;

    if (start && end && end >= start) {
      const diff = end - start;
      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
      return `${minutes}m ${seconds}s`;
    }

    return session.duration || '1m 15s';
  };

  // Sort sessions strictly newest first, and filter by search
  const filteredSessions = useMemo(() => {
    if (!conversationHistory) return [];

    const sorted = [...conversationHistory].sort((a, b) => {
      const timeA = a.startTimestamp || (a.id?.startsWith('session_') ? parseInt(a.id.replace('session_', ''), 10) : 0) || 0;
      const timeB = b.startTimestamp || (b.id?.startsWith('session_') ? parseInt(b.id.replace('session_', ''), 10) : 0) || 0;
      return timeB - timeA; // Descending (Newest first)
    });

    if (!searchQuery.trim()) return sorted;

    const q = searchQuery.toLowerCase();
    return sorted.filter(session => {
      const preview = getSessionPreview(session).toLowerCase();
      const dateInfo = getSessionDateInfo(session);
      const hasInMessages = session.messages?.some((m: any) => m.text?.toLowerCase()?.includes(q));
      return (
        preview.includes(q) ||
        dateInfo.day.toLowerCase().includes(q) ||
        dateInfo.date.toLowerCase().includes(q) ||
        session.startTime?.toLowerCase()?.includes(q) ||
        session.endTime?.toLowerCase()?.includes(q) ||
        hasInMessages
      );
    });
  }, [conversationHistory, searchQuery]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/75 backdrop-blur-md z-[100]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal Container */}
          <motion.div
            className="fixed inset-0 z-[101] flex items-center justify-center p-3 sm:p-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-[#0E1015]/95 border border-[#1E222D] rounded-2xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] backdrop-blur-xl"
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              transition={{ type: 'spring', damping: 26, stiffness: 320 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-5 border-b border-[#1E222D] bg-[#13161F]/60 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#3B82F6]/20 to-[#60A5FA]/10 border border-[#3B82F6]/30 flex items-center justify-center text-[#60A5FA]">
                      <Clock className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h2 className="text-base font-semibold text-white tracking-wide">
                          Conversation History
                        </h2>
                        <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-full bg-[#1E2330] text-[#94A3B8] border border-[#282F40]">
                          {conversationHistory?.length || 0} Sessions
                        </span>
                      </div>
                      <p className="text-xs text-[#64748B] mt-0.5">
                        Resume your past interactions and review chat records
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {conversationHistory && conversationHistory.length > 0 && (
                      <button
                        onClick={() => setShowClearConfirm(true)}
                        className="px-2.5 py-1.5 text-xs text-[#64748B] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all flex items-center gap-1.5 mr-1"
                        title="Clear all sessions"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Clear All</span>
                      </button>
                    )}
                    <button
                      onClick={onClose}
                      className="p-2 text-[#94A3B8] hover:text-white hover:bg-[#1E222D] rounded-xl transition-all"
                      aria-label="Close history modal"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Search Bar */}
                <div className="relative">
                  <Search className="w-4 h-4 text-[#64748B] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by topic, message, or date..."
                    className="w-full bg-[#161922] border border-[#232836] focus:border-[#3B82F6]/60 rounded-xl pl-10 pr-10 py-2 text-xs sm:text-sm text-slate-200 placeholder-[#475569] outline-none transition-all"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[#64748B] hover:text-slate-300 p-1"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Clear All Confirmation Bar */}
              <AnimatePresence>
                {showClearConfirm && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="bg-red-500/10 border-b border-red-500/20 px-5 py-3 flex items-center justify-between text-xs text-red-300 overflow-hidden"
                  >
                    <span>Are you sure you want to delete all conversation history?</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          clearAllSessions?.();
                          setShowClearConfirm(false);
                        }}
                        className="px-3 py-1 bg-red-500 text-white rounded-md font-medium hover:bg-red-600 transition-colors"
                      >
                        Yes, Delete All
                      </button>
                      <button
                        onClick={() => setShowClearConfirm(false)}
                        className="px-3 py-1 bg-[#1E2330] text-slate-300 rounded-md hover:bg-[#282F40] transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Session Cards List */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-3 custom-scrollbar">
                {filteredSessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-[#161922] border border-[#232836] flex items-center justify-center text-[#475569] mb-3">
                      <MessageSquare className="w-7 h-7" />
                    </div>
                    <p className="text-sm font-medium text-slate-300">
                      {searchQuery ? 'No matching conversations found' : 'No previous conversations'}
                    </p>
                    <p className="text-xs text-[#64748B] mt-1 max-w-xs">
                      {searchQuery
                        ? 'Try searching with a different keyword or topic'
                        : 'Your chat history will be automatically recorded here as you talk with Pulsar'}
                    </p>
                  </div>
                ) : (
                  filteredSessions.map((session, index) => {
                    const dateInfo = getSessionDateInfo(session);
                    const previewText = getSessionPreview(session);
                    const durationText = getSessionDuration(session);

                    return (
                      <motion.div
                        key={session.id}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(index * 0.04, 0.3) }}
                        onClick={() => handleLoadSession(session.id)}
                        className="group relative bg-[#13161F]/80 hover:bg-[#181B26] border border-[#1E222D] hover:border-[#3B82F6]/40 rounded-xl p-4 transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md"
                      >
                        {/* Top Row: Date, Day, Time Range & Duration */}
                        <div className="flex items-center justify-between gap-2 mb-2.5">
                          <div className="flex flex-wrap items-center gap-2">
                            {/* Date Badge */}
                            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#1A1E29] border border-[#262C3D] text-[11px] font-medium text-[#93C5FD]">
                              <Calendar className="w-3 h-3 text-[#3B82F6]" />
                              <span>{dateInfo.displayString}</span>
                            </div>

                            {/* Time Range */}
                            <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                              <Clock className="w-3 h-3 text-[#64748B]" />
                              <span className="font-mono text-[11px] text-slate-300">
                                {session.startTime || 'Started'}
                              </span>
                              {session.endTime && (
                                <>
                                  <span className="text-[#475569]">—</span>
                                  <span className="font-mono text-[11px] text-[#94A3B8]">
                                    {session.endTime}
                                  </span>
                                </>
                              )}
                            </div>

                            {/* Duration Badge */}
                            <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-[#3B82F6]/10 text-[#60A5FA] border border-[#3B82F6]/20">
                              ⏱ {durationText}
                            </span>
                          </div>

                          {/* Delete Action */}
                          <button
                            onClick={(e) => handleDeleteSession(session.id, e)}
                            className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/15 rounded-lg text-[#64748B] hover:text-red-400 transition-all"
                            title="Delete this session"
                            aria-label="Delete session"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Middle Row: Meaningful Conversation Preview */}
                        <div className="my-2.5 pl-3 border-l-2 border-[#3B82F6]/40 group-hover:border-[#3B82F6] transition-colors">
                          <p className="text-xs sm:text-[13px] text-slate-200 font-medium line-clamp-2 leading-relaxed">
                            "{previewText}"
                          </p>
                        </div>

                        {/* Bottom Row: Metrics & Quick Resume Action */}
                        <div className="flex items-center justify-between pt-2.5 mt-2 border-t border-[#1C202B]">
                          <div className="flex items-center gap-3 text-[11px]">
                            {/* Message count */}
                            <div className="flex items-center gap-1 text-[#94A3B8]">
                              <MessageSquare className="w-3 h-3 text-[#64748B]" />
                              <span>{session.messageCount || session.messages?.length || 0} msgs</span>
                            </div>

                            {/* User messages count */}
                            <div className="flex items-center gap-1 text-[#64748B]">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#3B82F6]" />
                              <span>User:</span>
                              <span className="text-slate-300 font-medium">
                                {session.userMessageCount ?? session.messages?.filter((m: any) => m.type === 'user').length ?? 0}
                              </span>
                            </div>

                            {/* AI messages count */}
                            <div className="flex items-center gap-1 text-[#64748B]">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                              <span>AI:</span>
                              <span className="text-slate-300 font-medium">
                                {session.aiMessageCount ?? session.messages?.filter((m: any) => m.type === 'ai').length ?? 0}
                              </span>
                            </div>

                            {/* Voice commands count */}
                            {(session.voiceCount || 0) > 0 && (
                              <div className="flex items-center gap-1 text-[#64748B]">
                                <Mic className="w-3 h-3 text-[#F59E0B]" />
                                <span className="text-[#F59E0B] font-medium">{session.voiceCount}</span>
                              </div>
                            )}
                          </div>

                          {/* Resume CTA */}
                          <div className="flex items-center gap-1 text-[11px] font-medium text-[#60A5FA] opacity-0 group-hover:opacity-100 transition-all translate-x-1 group-hover:translate-x-0">
                            <span>Resume</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </div>
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </div>

              {/* Footer */}
              <div className="p-4 px-5 border-t border-[#1E222D] bg-[#13161F]/40 flex items-center justify-between">
                <div className="text-xs text-[#64748B]">
                  Showing <span className="text-slate-300 font-medium">{filteredSessions.length}</span> of{' '}
                  <span className="text-slate-300 font-medium">{conversationHistory?.length || 0}</span> sessions
                </div>
                <button
                  onClick={onClose}
                  className="px-4 py-1.5 bg-[#1E2330] hover:bg-[#282F40] text-slate-200 rounded-xl text-xs font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default HistoryModal;
