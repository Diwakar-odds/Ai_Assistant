import { motion } from 'framer-motion';
import { Bot, Layers, Send, Sparkles, Square } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { analyzeCommandInput } from '../../lib/commandUtils';

const CommandInput = () => {
  const [command, setCommand] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState<number>(-1);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const { sendCommand, agents, activeChains, brainStatus, emergencyStop } = useDashboard();

  const analysis = useMemo(() => analyzeCommandInput(command), [command]);
  const isBusy = Boolean(
    brainStatus?.is_busy ||
      (activeChains &&
        activeChains.some((c) => !['completed', 'failed', 'cancelled'].includes(String(c.status).toLowerCase())))
  );

  // Auto-resize textarea cleanly up to 4 lines
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 104)}px`;
  }, [command]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = command.trim();
    if (!trimmed) return;

    sendCommand(trimmed, selectedAgentId ? { agentId: selectedAgentId } : undefined);
    setHistory((prev) => (prev[0] === trimmed ? prev : [trimmed, ...prev.slice(0, 29)]));
    setHistoryIdx(-1);
    setCommand('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
      return;
    }

    if (e.key === 'ArrowUp' && history.length > 0) {
      const el = e.currentTarget;
      const onFirstLine = !command.slice(0, el.selectionStart || 0).includes('\n');
      if (onFirstLine) {
        e.preventDefault();
        const nextIdx = Math.min(historyIdx + 1, history.length - 1);
        setHistoryIdx(nextIdx);
        setCommand(history[nextIdx]);
      }
    } else if (e.key === 'ArrowDown' && historyIdx >= 0) {
      const el = e.currentTarget;
      const onLastLine = !command.slice(el.selectionEnd || 0).includes('\n');
      if (onLastLine) {
        e.preventDefault();
        const nextIdx = historyIdx - 1;
        setHistoryIdx(nextIdx);
        setCommand(nextIdx >= 0 ? history[nextIdx] : '');
      }
    }
  };

  return (
    <motion.div
      id="command-input"
      className="flex-shrink-0 space-y-1.5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      {/* Multi-Command Preview & Target Agent Selector Bar */}
      {(analysis.isMultiStep || (agents && agents.length > 0)) && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <div className="flex items-center gap-2 min-w-0">
            {analysis.isMultiStep && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#00f3ff]/15 text-[#00f3ff] border border-[#00f3ff]/35">
                <Layers className="w-3 h-3" />
                <span>Multi-Step Chain ({analysis.stepCount} steps)</span>
                {analysis.isParallel && (
                  <span className="ml-1 inline-flex items-center gap-0.5 text-violet-300">
                    <Sparkles className="w-2.5 h-2.5" /> Parallel
                  </span>
                )}
              </span>
            )}
            <span className="text-[10px] text-[#6B7280] hidden sm:inline">
              Shift+Enter for new line · ↑/↓ history
            </span>
          </div>

          {agents && agents.length > 0 && (
            <label className="inline-flex items-center gap-1.5 text-[11px] text-[#9CA3AF]">
              <Bot className="w-3.5 h-3.5 text-violet-300" />
              <select
                aria-label="Target Agent"
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className="bg-[#16181D] border border-[#2A2D35] hover:border-violet-500/40 rounded-md px-2 py-0.5 text-[11px] text-white focus:outline-none"
              >
                <option value="">Auto Route</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.status})
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      <div className="glass-panel rounded-lg p-1.5 flex items-end gap-2 focus-within:border-neon-cyan/50 transition-colors">
        <textarea
          ref={textareaRef}
          rows={1}
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Type a command, question, or chain (e.g. open chrome && search "latest AI news")...'
          className="flex-1 bg-transparent text-white placeholder-gray-400 px-3 py-1.5 text-sm focus:outline-none resize-none leading-5 max-h-[104px]"
        />

        {isBusy && (
          <button
            type="button"
            onClick={() => emergencyStop()}
            title="Emergency Stop Active Chains"
            aria-label="Emergency Stop"
            className="bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 px-2.5 py-2 rounded-md flex items-center gap-1 text-xs font-semibold transition-colors shrink-0"
          >
            <Square className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Stop</span>
          </button>
        )}

        <motion.button
          type="button"
          onClick={() => handleSubmit()}
          disabled={!command.trim()}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="bg-[#3B82F6] text-white px-4 py-2 rounded-md flex items-center gap-1.5 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all touch-manipulation shrink-0"
        >
          <Send className="w-4 h-4" />
          <span className="hidden xs:inline">Send</span>
        </motion.button>
      </div>
    </motion.div>
  );
};

export default CommandInput;
