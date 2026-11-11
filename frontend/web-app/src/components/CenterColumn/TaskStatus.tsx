import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useMemo } from 'react';
import { Bot, ExternalLink, Pause, Play, Square, X } from 'lucide-react';
import { useDashboard, ActiveChain } from '../../contexts/DashboardContext';
import { ChainDTO, normalizeChainDTO } from '../../lib/api';

const SingleChainCard = ({
  chain,
  onInspect,
  onPause,
  onResume,
  onCancel,
}: {
  chain: ChainDTO;
  onInspect: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
}) => {
  const progress = useMotionValue(0);
  const progressPercent = useTransform(progress, (value) => Math.round(value));
  const pct = chain.progress_percentage ?? chain.progress ?? 0;

  useEffect(() => {
    const controls = animate(progress, pct, {
      duration: 0.6,
      ease: 'easeOut',
    });
    return controls.stop;
  }, [progress, pct]);

  const circumference = 2 * Math.PI * 9;
  const strokeDashoffset = useTransform(progress, [0, 100], [circumference, 0]);

  const statusLower = String(chain.status || 'executing').toLowerCase();
  const isComplete = statusLower === 'completed';
  const isFailed = statusLower === 'failed';
  const isCancelled = statusLower === 'cancelled';
  const isPaused = statusLower === 'paused';
  const isTerminal = isComplete || isFailed || isCancelled;

  let color = '#00f3ff';
  if (isComplete) color = '#10B981';
  else if (isFailed) color = '#EF4444';
  else if (isCancelled) color = '#6B7280';
  else if (isPaused) color = '#F59E0B';

  const currentStepText =
    chain.current_action ||
    chain.actions?.[chain.current_action_index]?.description ||
    null;
  const currentAgent =
    chain.current_agent ||
    chain.actions?.[chain.current_action_index]?.agent_name ||
    chain.actions?.[chain.current_action_index]?.agent_id ||
    null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onInspect(chain.chain_id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onInspect(chain.chain_id);
        }
      }}
      className="flex items-center gap-2.5 bg-[#0D1017]/90 hover:bg-[#141824] border border-[#242938] hover:border-[#00f3ff]/40 rounded-lg px-2.5 py-2 min-w-[210px] max-w-[270px] cursor-pointer transition-all shrink-0 text-left"
      title="Click to inspect full chain execution"
    >
      {/* Circular Progress Ring */}
      <div className="relative shrink-0">
        <svg className="w-[28px] h-[28px] -rotate-90" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="9" fill="none" stroke="#1F2228" strokeWidth="2.5" />
          <motion.circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ filter: `drop-shadow(0 0 5px ${color}66)` }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-[8px] font-bold text-white leading-none">
            <motion.span>{progressPercent}</motion.span>
          </div>
        </div>
      </div>

      {/* Chain Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span
            className="text-[9px] font-semibold uppercase px-1.5 py-0.2 rounded"
            style={{ backgroundColor: `${color}1A`, color }}
          >
            {statusLower}
          </span>
          {(chain.total_actions > 0 || chain.actions.length > 0) && (
            <span className="text-[9px] font-mono text-[#9CA3AF]">
              {chain.actions_completed}/{chain.total_actions || chain.actions.length}
            </span>
          )}
          {currentAgent && (
            <span className="inline-flex items-center gap-0.5 text-[9px] text-violet-300 bg-violet-500/15 px-1 rounded truncate max-w-[80px]">
              <Bot className="w-2.5 h-2.5 shrink-0" />
              <span className="truncate">{currentAgent}</span>
            </span>
          )}
        </div>

        <p className="text-[11px] font-medium text-white truncate">
          {chain.app_context ? `[${chain.app_context}] ` : ''}
          {chain.command}
        </p>

        {currentStepText && !isTerminal && (
          <p className="text-[10px] text-[#9CA3AF] truncate">{currentStepText}</p>
        )}
      </div>

      {/* Per-Chain Quick Actions */}
      {!isTerminal && (
        <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
          {isPaused ? (
            <button
              type="button"
              onClick={() => onResume(chain.chain_id)}
              title="Resume chain"
              aria-label={`Resume ${chain.chain_id}`}
              className="p-1 rounded bg-emerald-500/15 hover:bg-emerald-500/30 text-emerald-300 transition-colors"
            >
              <Play className="w-3 h-3" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onPause(chain.chain_id)}
              title="Pause chain"
              aria-label={`Pause ${chain.chain_id}`}
              className="p-1 rounded bg-amber-500/15 hover:bg-amber-500/30 text-amber-300 transition-colors"
            >
              <Pause className="w-3 h-3" />
            </button>
          )}
          <button
            type="button"
            onClick={() => onCancel(chain.chain_id)}
            title="Cancel chain"
            aria-label={`Cancel ${chain.chain_id}`}
            className="p-1 rounded bg-red-500/15 hover:bg-red-500/30 text-red-300 transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};

const TaskStatus = () => {
  const {
    brainStatus,
    activeChains,
    openChainMonitor,
    pauseChain,
    resumeChain,
    cancelChain,
    emergencyStop,
  } = useDashboard();

  const mergedChains = useMemo(() => {
    const map = new Map<string, ChainDTO>();
    (activeChains || []).forEach((c) => {
      map.set(c.chain_id, c);
    });
    if (Array.isArray(brainStatus?.active_chains)) {
      brainStatus.active_chains.forEach((raw: ActiveChain) => {
        if (!raw?.chain_id) return;
        const normalized = normalizeChainDTO(raw);
        if (normalized && !map.has(normalized.chain_id)) {
          map.set(normalized.chain_id, normalized);
        }
      });
    }
    return Array.from(map.values());
  }, [activeChains, brainStatus]);

  const isBusy = Boolean(
    brainStatus?.is_busy ||
      mergedChains.some((c) => !['completed', 'failed', 'cancelled'].includes(String(c.status).toLowerCase()))
  );

  if (!isBusy && mergedChains.length === 0) {
    return null;
  }

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg p-2.5 flex flex-col flex-shrink-0 w-full"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
    >
      <div className="flex justify-between items-center w-full mb-2 px-0.5 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full ${isBusy ? 'bg-[#00f3ff] animate-pulse' : 'bg-emerald-400'}`} />
          <h3 className="text-[11px] font-bold text-white truncate">
            {isBusy ? 'Orchestrator Active' : 'Recent Execution'} ({mergedChains.length})
          </h3>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => openChainMonitor(mergedChains[0]?.chain_id || null)}
            className="text-[10px] bg-[#1F2228] hover:bg-[#2A2D35] text-[#00f3ff] border border-[#00f3ff]/25 px-2 py-0.5 rounded flex items-center gap-1 transition-colors"
          >
            <ExternalLink className="w-2.5 h-2.5" />
            Inspect
          </button>
          {isBusy && (
            <button
              type="button"
              onClick={() => emergencyStop()}
              className="text-[10px] font-semibold bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25 px-2 py-0.5 rounded flex items-center gap-1 transition-colors"
            >
              <Square className="w-2.5 h-2.5" />
              STOP
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-row gap-2 overflow-x-auto pb-0.5">
        {mergedChains.map((chain) => (
          <SingleChainCard
            key={chain.chain_id}
            chain={chain}
            onInspect={(id) => openChainMonitor(id)}
            onPause={(id) => pauseChain(id)}
            onResume={(id) => resumeChain(id)}
            onCancel={(id) => cancelChain(id)}
          />
        ))}
      </div>
    </motion.div>
  );
};

export default TaskStatus;
