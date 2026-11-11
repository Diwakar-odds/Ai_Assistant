import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { useDashboard, SessionActivity } from '../../contexts/DashboardContext';
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  History,
  MessageSquare,
  Mic,
  Plus,
  Radio,
  Sparkles,
  Zap,
} from 'lucide-react';
import HistoryModal from './HistoryModal';

interface ConversationMessage {
  id: number;
  message_id?: string;
  type: 'user' | 'ai';
  text: string;
  time: string;
  source?: string;
  isVoice: boolean;
  seq?: number;
  ts_ms?: number;
}

const isCompanionSource = (source?: string): boolean => {
  const s = (source || '').toLowerCase();
  return s.includes('companion') || s.includes('orb');
};

const isVoiceSource = (source?: string, isVoice?: boolean): boolean => {
  if (isVoice) return true;
  const s = (source || '').toLowerCase();
  return s.includes('voice') || s.includes('companion') || s.includes('whisper') || s.includes('google');
};

const getActivityBadgeStyle = (act: SessionActivity) => {
  const status = (act.status || '').toLowerCase();
  const kind = (act.kind || '').toLowerCase();
  if (status === 'error' || kind === 'error') {
    return {
      pill: 'bg-red-500/15 text-red-300 border-red-500/30',
      dot: 'bg-red-400',
      Icon: AlertCircle,
    };
  }
  if (kind === 'wake') {
    return {
      pill: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
      dot: 'bg-amber-400',
      Icon: Radio,
    };
  }
  if (kind === 'pre_report' || status === 'running') {
    return {
      pill: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
      dot: 'bg-sky-400',
      Icon: Sparkles,
    };
  }
  if (kind === 'action' || kind === 'command') {
    return {
      pill: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
      dot: 'bg-violet-400',
      Icon: Zap,
    };
  }
  if (kind === 'voice_input' || kind === 'text_input') {
    return {
      pill: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
      dot: 'bg-blue-400',
      Icon: Mic,
    };
  }
  return {
    pill: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    dot: 'bg-emerald-400',
    Icon: CheckCircle2,
  };
};

const ConversationTracker = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'activity'>('chat');
  const {
    chatMessages,
    voiceCommands,
    sessionActivities,
    currentSession,
    startNewSession,
    isAITyping,
    isViewingHistory,
    resumeLiveSession,
  } = useDashboard();

  // Build unified chronological conversation directly from chatMessages (with deduplicated legacy fallback)
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);

  useEffect(() => {
    const combined: ConversationMessage[] = chatMessages.map(msg => ({
      id: msg.id,
      message_id: msg.message_id,
      type: msg.type,
      text: msg.text,
      time: msg.time,
      source: msg.source,
      isVoice: msg.type === 'user' && isVoiceSource(msg.source, msg.isVoice),
      seq: msg.seq,
      ts_ms: msg.ts_ms,
    }));

    let appendedLegacy = false;
    const seenIds = new Set(combined.map(m => m.message_id).filter(Boolean));
    voiceCommands.forEach(cmd => {
      if (cmd.message_id && seenIds.has(cmd.message_id)) return;
      const cmdText = (cmd.command || '').trim();
      if (!cmdText) return;
      const cmdTs = cmd.ts_ms || cmd.id || 0;
      const matched = combined.some(
        m =>
          m.type === 'user' &&
          m.text.trim() === cmdText &&
          Math.abs((m.ts_ms || m.id || 0) - cmdTs) < 8000
      );
      if (matched) return;
      appendedLegacy = true;
      combined.push({
        id: cmd.id,
        message_id: cmd.message_id,
        type: 'user',
        text: cmdText,
        time: cmd.time,
        source: cmd.source || 'legacy_voice',
        isVoice: true,
        ts_ms: cmd.ts_ms,
      });
    });

    if (appendedLegacy) {
      combined.sort((a, b) => (a.ts_ms || a.id) - (b.ts_ms || b.id));
    }

    setConversation(combined);
  }, [chatMessages, voiceCommands]);

  useEffect(() => {
    // Auto-scroll smoothly to bottom on new message or activity
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [conversation, sessionActivities, activeTab]);

  return (
    <>
      <motion.div
        className="bg-[#0D1017]/90 border border-[#1E222D] rounded-2xl overflow-hidden flex-1 min-h-0 flex flex-col w-full shadow-xl backdrop-blur-md"
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Header Row */}
        <div className="border-b border-[#1E222D] bg-[#121520]/60">
          <div className="flex items-center justify-between px-3.5 py-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <div
                className={`w-2 h-2 rounded-full ${
                  isViewingHistory ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'
                }`}
              />
              <h3 className="text-xs font-semibold text-white tracking-wide truncate">
                {isViewingHistory ? 'Archived Session' : 'Conversation'}
              </h3>
              <span className="text-[10px] font-medium text-[#64748B] px-1.5 py-0.2 rounded-full bg-[#181C28] border border-[#23293A]">
                {conversation.length}
              </span>
            </div>

            {/* Actions: Compact New & History */}
            <div className="flex items-center gap-1.5 shrink-0">
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

          {/* Segmented Chat / Activity Tabs + Back to Live link */}
          <div className="flex items-center justify-between px-3.5 pb-2 gap-2">
            <div className="flex items-center gap-1 bg-[#0B0D13] p-0.5 rounded-lg border border-[#1E2330]">
              <button
                onClick={() => setActiveTab('chat')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium transition-all ${
                  activeTab === 'chat'
                    ? 'bg-[#1E293B] text-white border border-[#3B82F6]/30 shadow-xs'
                    : 'text-[#64748B] hover:text-slate-300'
                }`}
              >
                <MessageSquare className="w-2.5 h-2.5" />
                <span>Chat</span>
              </button>
              <button
                onClick={() => setActiveTab('activity')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium transition-all ${
                  activeTab === 'activity'
                    ? 'bg-[#1E293B] text-white border border-[#3B82F6]/30 shadow-xs'
                    : 'text-[#64748B] hover:text-slate-300'
                }`}
              >
                <Activity className="w-2.5 h-2.5" />
                <span>Activity</span>
                <span className="text-[9px] text-[#94A3B8] ml-0.5">({sessionActivities.length})</span>
              </button>
            </div>

            {isViewingHistory && (
              <button
                onClick={() => resumeLiveSession?.()}
                className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-all"
                title="Return to active live session"
              >
                <ArrowLeft className="w-2.5 h-2.5" />
                <span>Live</span>
              </button>
            )}
          </div>
        </div>

        {/* Stream Body */}
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

          {activeTab === 'chat' ? (
            <>
              {conversation.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
                  <div className="w-10 h-10 rounded-xl bg-[#141722] border border-[#1E2330] flex items-center justify-center text-[#475569] mb-2.5">
                    <MessageSquare className="w-5 h-5 text-[#3B82F6]/50" />
                  </div>
                  <p className="text-xs font-medium text-slate-300">No messages yet</p>
                  <p className="text-[11px] text-[#64748B] mt-0.5">
                    Speak via Orb or type a command to start chatting
                  </p>
                </div>
              ) : (
                conversation.map((message, index) => {
                  const isUser = message.type === 'user';
                  const orbOriginated = isCompanionSource(message.source);

                  return (
                    <motion.div
                      key={message.message_id || `${message.id}_${index}`}
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
                        {/* Source / Voice badge */}
                        {isUser && message.isVoice && (
                          <div
                            className={`flex items-center gap-1 text-[10px] mb-1 font-medium ${
                              orbOriginated ? 'text-amber-300' : 'text-[#60A5FA]'
                            }`}
                          >
                            <Mic className="w-2.5 h-2.5" />
                            <span>{orbOriginated ? 'Orb Voice' : 'Voice input'}</span>
                          </div>
                        )}

                        {!isUser && orbOriginated && (
                          <div className="flex items-center gap-1 text-[10px] text-amber-300/90 mb-1 font-medium">
                            <Sparkles className="w-2.5 h-2.5" />
                            <span>Orb Reply</span>
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

              {/* AI Typing Indicator */}
              {isAITyping && (
                <motion.div
                  className="flex justify-start"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="relative max-w-[88%] px-4 py-3 bg-[#141722] border border-[#1E2330] rounded-2xl rounded-tl-xs flex items-center gap-1.5 h-9">
                    <div className="w-1.5 h-1.5 bg-[#3B82F6]/70 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-[#3B82F6]/70 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-[#3B82F6]/70 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </motion.div>
              )}
            </>
          ) : sessionActivities.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
              <div className="w-10 h-10 rounded-xl bg-[#141722] border border-[#1E2330] flex items-center justify-center text-[#475569] mb-2.5">
                <Activity className="w-5 h-5 text-[#3B82F6]/50" />
              </div>
              <p className="text-xs font-medium text-slate-300">No session activity yet</p>
              <p className="text-[11px] text-[#64748B] mt-0.5">
                Orb wakes, voice inputs, actions, and replies appear here
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {sessionActivities.map((act, idx) => {
                const { pill, dot, Icon } = getActivityBadgeStyle(act);
                const orbTag = isCompanionSource(act.source);
                return (
                  <motion.div
                    key={act.id || `act_${idx}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18 }}
                    className="bg-[#121622]/90 border border-[#1E2434] rounded-xl p-2.5 text-[11px]"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[9px] font-medium shrink-0 ${pill}`}>
                          <Icon className="w-2.5 h-2.5" />
                          <span>{act.kind}</span>
                        </span>
                        {act.source && (
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded bg-[#181D2B] border border-[#242B3E] truncate ${
                              orbTag ? 'text-amber-300' : 'text-[#94A3B8]'
                            }`}
                          >
                            {orbTag ? 'Orb' : act.source}
                          </span>
                        )}
                      </div>
                      <span className="text-[9px] font-mono text-[#64748B] shrink-0">{act.time}</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dot}`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-slate-200 font-medium leading-snug break-words">{act.title}</p>
                        {act.detail && (
                          <p className="text-[#94A3B8] text-[10px] mt-0.5 leading-relaxed whitespace-pre-wrap break-words">
                            {act.detail}
                          </p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* Minimalist Micro Footer */}
        {(conversation.length > 0 || sessionActivities.length > 0) && (
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
