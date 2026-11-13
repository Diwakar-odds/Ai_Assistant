import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Activity,
    AlertCircle,
    Ban,
    Bot,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock,
    GitBranch,
    Layers,
    Lock,
    Pause,
    Play,
    RefreshCw,
    ShieldAlert,
    ShieldCheck,
    Square,
    Trash2,
    XCircle,
} from 'lucide-react';
import { useDashboard } from '../contexts/DashboardContext';
import {
    API_ENDPOINTS,
    ChainActionDTO,
    ChainDTO,
    apiFetchJson,
    normalizeChainActionDTO,
    normalizeChainDTO,
    normalizeChainStatus,
} from '../lib/api';

export interface ChainMonitorProps {
    chainId?: string | null;
    chain?: ChainDTO | null;
    onChainUpdated?: (chain: ChainDTO) => void;
    compact?: boolean;
}

const getChainStatusBadge = (status: string) => {
    const s = String(status || 'pending').toLowerCase();
    switch (s) {
        case 'completed':
            return {
                label: 'Completed',
                badgeClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
                barClass: 'bg-emerald-500',
            };
        case 'failed':
            return {
                label: 'Failed',
                badgeClass: 'bg-red-500/15 text-red-300 border-red-500/30',
                barClass: 'bg-red-500',
            };
        case 'cancelled':
            return {
                label: 'Cancelled',
                badgeClass: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
                barClass: 'bg-slate-500',
            };
        case 'paused':
            return {
                label: 'Paused',
                badgeClass: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
                barClass: 'bg-amber-500',
            };
        case 'waiting_confirmation':
            return {
                label: 'Awaiting Confirmation',
                badgeClass: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
                barClass: 'bg-orange-500',
            };
        case 'planning':
            return {
                label: 'Planning',
                badgeClass: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
                barClass: 'bg-violet-500',
            };
        case 'verifying':
            return {
                label: 'Verifying',
                badgeClass: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
                barClass: 'bg-cyan-400',
            };
        case 'executing':
            return {
                label: 'Executing',
                badgeClass: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
                barClass: 'bg-gradient-to-r from-[#3B82F6] to-[#00f3ff]',
            };
        default:
            return {
                label: s.charAt(0).toUpperCase() + s.slice(1),
                badgeClass: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
                barClass: 'bg-[#3B82F6]',
            };
    }
};

const getStepStatusMeta = (status: string) => {
    const s = String(status || 'pending').toLowerCase();
    if (s === 'completed') {
        return {
            Icon: CheckCircle2,
            pill: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
            border: 'border-emerald-500/25',
            iconColor: 'text-emerald-400',
            spin: false,
        };
    }
    if (s === 'failed') {
        return {
            Icon: XCircle,
            pill: 'bg-red-500/15 text-red-300 border-red-500/30',
            border: 'border-red-500/30',
            iconColor: 'text-red-400',
            spin: false,
        };
    }
    if (s === 'cancelled' || s === 'skipped') {
        return {
            Icon: Ban,
            pill: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
            border: 'border-slate-500/20',
            iconColor: 'text-slate-400',
            spin: false,
        };
    }
    if (s === 'running' || s === 'executing' || s === 'verifying') {
        return {
            Icon: Activity,
            pill: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
            border: 'border-[#00f3ff]/40',
            iconColor: 'text-[#00f3ff]',
            spin: true,
        };
    }
    if (s === 'paused' || s === 'waiting_confirmation') {
        return {
            Icon: ShieldAlert,
            pill: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
            border: 'border-amber-500/30',
            iconColor: 'text-amber-400',
            spin: false,
        };
    }
    return {
        Icon: Clock,
        pill: 'bg-white/5 text-[#9CA3AF] border-white/10',
        border: 'border-[#2A2D35]',
        iconColor: 'text-[#6B7280]',
        spin: false,
    };
};

const formatOutputValue = (val: unknown): string => {
    if (val === null || val === undefined) return '';
    if (typeof val === 'string') return val;
    try {
        return JSON.stringify(val, null, 2);
    } catch {
        return String(val);
    }
};

const ChainMonitor: React.FC<ChainMonitorProps> = ({
    chainId: propChainId,
    chain: propChain,
    onChainUpdated,
    compact = false,
}) => {
    const {
        socket,
        isConnected,
        activeChains,
        chainHistory,
        pauseChain,
        resumeChain,
        cancelChain,
        deleteChain,
        emergencyStop,
    } = useDashboard();

    const targetChainId = propChain?.chain_id || propChainId || null;

    const [fetchedChain, setFetchedChain] = useState<ChainDTO | null>(null);
    const [loading, setLoading] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [busyAction, setBusyAction] = useState<string | null>(null);
    const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

    const contextChain = useMemo(() => {
        if (!targetChainId) return null;
        return (
            activeChains?.find((c) => c.chain_id === targetChainId) ||
            chainHistory?.find((c) => c.chain_id === targetChainId) ||
            null
        );
    }, [targetChainId, activeChains, chainHistory]);

    const scopedFetchedChain = useMemo(
        () => (fetchedChain && fetchedChain.chain_id === targetChainId ? fetchedChain : null),
        [fetchedChain, targetChainId]
    );

    const chain: ChainDTO | null = useMemo(() => {
        if (contextChain && scopedFetchedChain) {
            return contextChain.actions.length >= scopedFetchedChain.actions.length
                ? contextChain
                : { ...scopedFetchedChain, ...contextChain, actions: scopedFetchedChain.actions };
        }
        return contextChain || scopedFetchedChain || propChain || null;
    }, [contextChain, scopedFetchedChain, propChain]);

    const latestChainRef = useRef<ChainDTO | null>(chain);
    useEffect(() => {
        latestChainRef.current = chain;
    }, [chain]);

    const loadChainDetail = async (id: string) => {
        setLoading(true);
        setFetchError(null);
        const res = await apiFetchJson<any>(API_ENDPOINTS.chains.detail(id));
        setLoading(false);
        if (res.ok && res.data) {
            const parsed = normalizeChainDTO(res.data);
            if (parsed) {
                setFetchedChain(parsed);
                onChainUpdated?.(parsed);
            }
        } else if (!latestChainRef.current && !propChain) {
            setFetchError(res.error || 'Failed to load chain details');
        }
    };

    useEffect(() => {
        setFetchedChain(null);
        if (!targetChainId) return;
        loadChainDetail(targetChainId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [targetChainId]);

    useEffect(() => {
        if (!socket || !isConnected || !targetChainId) return;

        socket.emit('subscribe_chain', { chain_id: targetChainId });

        const handleEvent = (eventType: string) => (payload: any) => {
            if (!payload || typeof payload !== 'object') return;
            const inner = payload.data && typeof payload.data === 'object' ? { ...payload, ...payload.data } : payload;
            const evtChainId = String(inner.chain_id || inner.id || inner.chain?.chain_id || '').trim();
            if (evtChainId && evtChainId !== targetChainId) return;

            if (inner.chain || Array.isArray(inner.actions) || Array.isArray(inner.steps)) {
                const parsed = normalizeChainDTO(inner.chain || inner);
                if (parsed) {
                    setFetchedChain(parsed);
                    onChainUpdated?.(parsed);
                }
                return;
            }

            setFetchedChain((prev) => {
                const base = (prev && prev.chain_id === targetChainId ? prev : null) || latestChainRef.current;
                if (!base) return prev;
                const nextStatus =
                    eventType === 'chain.started' || eventType === 'chain.resumed'
                        ? 'executing'
                        : eventType === 'chain.paused'
                        ? 'paused'
                        : eventType === 'chain.cancelled'
                        ? 'cancelled'
                        : eventType === 'chain.completed'
                        ? 'completed'
                        : eventType === 'chain.failed'
                        ? 'failed'
                        : inner.status
                        ? normalizeChainStatus(inner.status)
                        : base.status;

                const stepId = String(inner.action_id || inner.step_id || '').trim();
                let nextActions = base.actions;
                if (stepId) {
                    nextActions = base.actions.map((a) => {
                        if (a.id !== stepId) return a;
                        return normalizeChainActionDTO({
                            ...a,
                            status:
                                eventType === 'chain.step_completed'
                                    ? 'completed'
                                    : eventType === 'chain.step_failed'
                                    ? 'failed'
                                    : eventType === 'chain.step_started'
                                    ? 'running'
                                    : inner.step_status || a.status,
                            agent_id: inner.agent_id ?? a.agent_id,
                            agent_name: inner.agent_name ?? a.agent_name,
                            result: inner.result !== undefined ? inner.result : a.result,
                            output: inner.output !== undefined ? inner.output : a.output,
                            error: inner.error !== undefined ? inner.error : a.error,
                            verified:
                                eventType === 'chain.verification_completed'
                                    ? Boolean(inner.verified ?? inner.success ?? true)
                                    : a.verified,
                            verification_result: inner.verification_result ?? inner.verification ?? a.verification_result,
                        });
                    });
                }

                return normalizeChainDTO({
                    ...base,
                    status: nextStatus,
                    progress_percentage:
                        typeof inner.progress_percentage === 'number'
                            ? inner.progress_percentage
                            : typeof inner.progress === 'number'
                            ? inner.progress
                            : base.progress_percentage,
                    actions: nextActions,
                    final_output: inner.final_output !== undefined ? inner.final_output : base.final_output,
                });
            });
        };

        const events = [
            'chain_progress',
            'chain.started',
            'chain.planned',
            'chain.step_started',
            'chain.step_completed',
            'chain.step_failed',
            'chain.verification_completed',
            'chain.paused',
            'chain.resumed',
            'chain.cancelled',
            'chain.completed',
            'chain.failed',
        ] as const;

        const listeners = events.map((evt) => {
            const fn = handleEvent(evt);
            socket.on(evt, fn);
            return { evt, fn };
        });

        return () => {
            socket.emit('unsubscribe_chain', { chain_id: targetChainId });
            listeners.forEach(({ evt, fn }) => socket.off(evt, fn));
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [socket, isConnected, targetChainId]);

    if (!targetChainId && !chain) {
        return (
            <div className="bg-[#16181D] border border-[#2A2D35] rounded-xl p-8 text-center text-[#9CA3AF]">
                <Layers className="w-10 h-10 text-[#3B82F6]/50 mx-auto mb-3" />
                <p className="text-sm font-medium text-white">No Chain Selected</p>
                <p className="text-xs text-[#6B7280] mt-1">
                    Select an active or historical chain to inspect step-by-step execution and assigned agents.
                </p>
            </div>
        );
    }

    if (loading && !chain) {
        return (
            <div className="bg-[#16181D] border border-[#2A2D35] rounded-xl p-8 flex items-center justify-center gap-3 text-[#9CA3AF]">
                <RefreshCw className="w-4 h-4 animate-spin text-[#00f3ff]" />
                <span className="text-sm">Loading chain {targetChainId}...</span>
            </div>
        );
    }

    if (!chain) {
        return (
            <div className="bg-[#16181D] border border-red-500/30 rounded-xl p-6 text-center">
                <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-white">Unable to load chain {targetChainId}</p>
                {fetchError && <p className="text-xs text-red-300 mt-1">{fetchError}</p>}
                {targetChainId && (
                    <button
                        type="button"
                        onClick={() => loadChainDetail(targetChainId)}
                        className="mt-3 px-3 py-1.5 text-xs bg-[#2A2D35] hover:bg-[#3A3D45] text-white rounded-lg transition-colors"
                    >
                        Retry
                    </button>
                )}
            </div>
        );
    }

    const statusMeta = getChainStatusBadge(chain.status);
    const isRunning = ['executing', 'planning', 'verifying'].includes(String(chain.status).toLowerCase());
    const isPaused = String(chain.status).toLowerCase() === 'paused';
    const isWaitingConfirm = String(chain.status).toLowerCase() === 'waiting_confirmation';
    const isPending = String(chain.status).toLowerCase() === 'pending';
    const isTerminal = ['completed', 'failed', 'cancelled'].includes(String(chain.status).toLowerCase());

    const handleControl = async (action: 'pause' | 'resume' | 'cancel' | 'execute' | 'authorize' | 'stop_all' | 'delete') => {
        setBusyAction(action);
        try {
            if (action === 'pause') {
                await pauseChain(chain.chain_id);
            } else if (action === 'resume') {
                await resumeChain(chain.chain_id);
            } else if (action === 'authorize') {
                await resumeChain(chain.chain_id, 'yes');
            } else if (action === 'cancel') {
                await cancelChain(chain.chain_id);
            } else if (action === 'delete') {
                await deleteChain(chain.chain_id);
                setFetchedChain(null);
                return;
            } else if (action === 'execute') {
                const res = await apiFetchJson<any>(API_ENDPOINTS.chains.execute(chain.chain_id), {
                    method: 'POST',
                    body: '{}',
                });
                if (res.ok && res.data) {
                    const updated = normalizeChainDTO(res.data);
                    if (updated) setFetchedChain(updated);
                }
            } else if (action === 'stop_all') {
                await emergencyStop();
            }
            await loadChainDetail(chain.chain_id);
        } finally {
            setBusyAction(null);
        }
    };

    const toggleExpand = (stepId: string) => {
        setExpandedSteps((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
    };

    return (
        <div className={`bg-[#16181D] border border-[#2A2D35] rounded-xl ${compact ? 'p-4' : 'p-5'} space-y-4`}>
            {/* Header */}
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0D1017] border border-[#2A2D35] text-[#9CA3AF]">
                            {chain.chain_id}
                        </span>
                        <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${statusMeta.badgeClass}`}>
                            {statusMeta.label}
                        </span>
                        {chain.app_context && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                                {chain.app_context}
                            </span>
                        )}
                        {typeof chain.duration_seconds === 'number' && chain.duration_seconds > 0 && (
                            <span className="text-[10px] text-[#9CA3AF] font-mono">
                                {chain.duration_seconds.toFixed(1)}s
                            </span>
                        )}
                    </div>
                    <h4 className="text-base font-semibold text-white break-words">{chain.command || 'Orchestrated Chain'}</h4>
                </div>

                {/* Controls */}
                <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                    <button
                        type="button"
                        onClick={() => loadChainDetail(chain.chain_id)}
                        disabled={loading}
                        title="Refresh Chain Status"
                        className="p-2 rounded-lg bg-[#1F2228] hover:bg-[#2A2D35] border border-[#2A2D35] text-[#9CA3AF] hover:text-white transition-colors"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    </button>

                    {isPending && (
                        <button
                            type="button"
                            onClick={() => handleControl('execute')}
                            disabled={busyAction !== null}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#3B82F6]/20 hover:bg-[#3B82F6]/30 text-[#60A5FA] border border-[#3B82F6]/30 flex items-center gap-1.5 transition-colors"
                        >
                            <Play className="w-3.5 h-3.5" />
                            Execute
                        </button>
                    )}

                    {isRunning && (
                        <button
                            type="button"
                            onClick={() => handleControl('pause')}
                            disabled={busyAction !== null}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 transition-colors"
                        >
                            <Pause className="w-3.5 h-3.5" />
                            Pause
                        </button>
                    )}

                    {isPaused && (
                        <button
                            type="button"
                            onClick={() => handleControl('resume')}
                            disabled={busyAction !== null}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 transition-colors"
                        >
                            <Play className="w-3.5 h-3.5" />
                            Resume
                        </button>
                    )}

                    {isWaitingConfirm && (
                        <button
                            type="button"
                            onClick={() => handleControl('authorize')}
                            disabled={busyAction !== null}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-orange-500/20 hover:bg-orange-500/30 text-orange-200 border border-orange-500/40 flex items-center gap-1.5 transition-colors"
                        >
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Authorize
                        </button>
                    )}

                    {!isTerminal && (
                        <>
                            <button
                                type="button"
                                onClick={() => handleControl('cancel')}
                                disabled={busyAction !== null}
                                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 flex items-center gap-1.5 transition-colors"
                            >
                                <XCircle className="w-3.5 h-3.5" />
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={() => handleControl('stop_all')}
                                disabled={busyAction !== null}
                                title="Emergency Stop All Active Chains"
                                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-red-600/20 hover:bg-red-600/30 text-red-200 border border-red-500/40 flex items-center gap-1 transition-colors"
                            >
                                <Square className="w-3 h-3" />
                                Stop All
                            </button>
                        </>
                    )}

                    <button
                        type="button"
                        onClick={() => handleControl('delete')}
                        disabled={busyAction !== null}
                        title="Delete Chain Record"
                        className="px-2 py-1.5 rounded-lg text-xs font-medium bg-[#1F2228] hover:bg-red-500/20 text-[#9CA3AF] hover:text-red-300 border border-[#2A2D35] hover:border-red-500/30 flex items-center gap-1 transition-colors"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Overall Progress Bar */}
            <div className="bg-[#0D1017] border border-[#1F2228] rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                    <span className="text-[#9CA3AF]">
                        Progress:{' '}
                        <span className="text-white font-semibold">
                            {chain.actions_completed} / {chain.total_actions || chain.actions.length}
                        </span>{' '}
                        steps completed
                        {chain.actions_failed > 0 && (
                            <span className="text-red-400 ml-2">({chain.actions_failed} failed)</span>
                        )}
                    </span>
                    <span className="font-mono font-bold text-[#00f3ff]">{chain.progress_percentage}%</span>
                </div>
                <div className="h-2 w-full bg-[#1F2228] rounded-full overflow-hidden">
                    <motion.div
                        className={`h-full rounded-full ${statusMeta.barClass}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${chain.progress_percentage}%` }}
                        transition={{ duration: 0.4, ease: 'easeOut' }}
                    />
                </div>
            </div>

            {/* Checkpoint Gate Confirmation Banner */}
            {isWaitingConfirm && (
                <div className="p-4 rounded-xl bg-gradient-to-r from-orange-500/15 to-amber-500/10 border border-orange-500/40 space-y-2.5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-orange-300">
                            <ShieldAlert className="w-5 h-5 text-orange-400 shrink-0" />
                            <h5 className="text-sm font-semibold">Human-in-the-Loop Checkpoint Gate</h5>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-200 border border-orange-500/30">
                            Action Paused for Confirmation
                        </span>
                    </div>
                    <p className="text-xs text-orange-200/90 leading-relaxed">
                        A sensitive multi-agent action (such as sending an external email, altering files, or executing system control) requires your explicit authorization.
                    </p>
                    <div className="flex items-center gap-2 pt-1">
                        <button
                            type="button"
                            onClick={() => handleControl('authorize')}
                            disabled={busyAction !== null}
                            className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-[0_0_12px_rgba(16,185,129,0.3)] transition-colors"
                        >
                            <ShieldCheck className="w-4 h-4" />
                            Approve & Execute
                        </button>
                        <button
                            type="button"
                            onClick={() => handleControl('cancel')}
                            disabled={busyAction !== null}
                            className="px-4 py-2 rounded-lg text-xs font-semibold bg-red-600/80 hover:bg-red-600 text-white flex items-center gap-1.5 transition-colors"
                        >
                            <XCircle className="w-4 h-4" />
                            Reject & Abort
                        </button>
                    </div>
                </div>
            )}

            {/* Step / Action Timeline */}
            <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                    <h5 className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF] flex items-center gap-1.5">
                        <GitBranch className="w-3.5 h-3.5 text-[#00f3ff]" />
                        <span>Execution Steps ({chain.actions.length})</span>
                    </h5>
                </div>

                {chain.actions.length === 0 ? (
                    <div className="p-4 rounded-lg bg-[#0D1017] border border-[#1F2228] text-xs text-[#6B7280] text-center">
                        {isRunning ? 'Decomposing command into execution steps...' : 'No step breakdown recorded for this chain.'}
                    </div>
                ) : (
                    <div className="space-y-2">
                        {chain.actions.map((step: ChainActionDTO, idx: number) => {
                            const meta = getStepStatusMeta(step.status);
                            const StepIcon = meta.Icon;
                            const hasDetails = Boolean(
                                step.result !== undefined && step.result !== null
                                    ? true
                                    : step.output !== undefined && step.output !== null
                                    ? true
                                    : step.error || step.verification_result || step.critic_review
                            );
                            const isExpanded = Boolean(expandedSteps[step.id] ?? (step.status === 'failed'));

                            return (
                                <motion.div
                                    key={step.id || idx}
                                    initial={{ opacity: 0, y: 6 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={`bg-[#1F2228] border ${meta.border} rounded-lg p-3 transition-colors`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-start gap-2.5 min-w-0 flex-1">
                                            <StepIcon
                                                className={`w-4 h-4 mt-0.5 shrink-0 ${meta.iconColor} ${meta.spin ? 'animate-pulse' : ''}`}
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="flex flex-wrap items-center gap-1.5 mb-1">
                                                    <span className="text-xs font-mono text-[#6B7280]">#{idx + 1}</span>
                                                    <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-[#16181D] border border-[#2A2D35] text-slate-200">
                                                        {step.type}
                                                    </span>
                                                    {(step.agent_name || step.agent_id) && (
                                                        <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">
                                                            <Bot className="w-2.5 h-2.5" />
                                                            {step.agent_name || step.agent_id}
                                                        </span>
                                                    )}
                                                    {step.parallel_group && (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                                                            parallel: {step.parallel_group}
                                                        </span>
                                                    )}
                                                    {step.healed_by && (
                                                        <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                                            <span>🩹</span>
                                                            Auto-Recovered ({step.healed_by})
                                                        </span>
                                                    )}
                                                    {step.critic_review && (
                                                        <span
                                                            className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${
                                                                step.critic_review.approved
                                                                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                                                    : 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30'
                                                            }`}
                                                        >
                                                            <span>🧐</span>
                                                            Critic: {step.critic_review.score}/10
                                                        </span>
                                                    )}
                                                    {step.requires_confirmation && (
                                                        <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">
                                                            <Lock className="w-2.5 h-2.5" />
                                                            Checkpoint Gate
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-sm text-white break-words">{step.description}</p>

                                                {step.dependencies && step.dependencies.length > 0 && (
                                                    <div className="flex flex-wrap items-center gap-1 mt-1.5">
                                                        <span className="text-[10px] text-[#6B7280]">Depends on:</span>
                                                        {step.dependencies.map((dep) => (
                                                            <span
                                                                key={dep}
                                                                className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#0D1017] text-[#9CA3AF] border border-[#2A2D35]"
                                                            >
                                                                {dep}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2 shrink-0">
                                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${meta.pill}`}>
                                                {step.status}
                                            </span>
                                            {hasDetails && (
                                                <button
                                                    type="button"
                                                    onClick={() => toggleExpand(step.id)}
                                                    aria-label={isExpanded ? 'Collapse step details' : 'Expand step details'}
                                                    className="p-1 rounded hover:bg-white/5 text-[#9CA3AF] hover:text-white"
                                                >
                                                    {isExpanded ? (
                                                        <ChevronDown className="w-3.5 h-3.5" />
                                                    ) : (
                                                        <ChevronRight className="w-3.5 h-3.5" />
                                                    )}
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Creator-Critic Peer Review Summary */}
                                    {step.critic_review && (
                                        <div className="mt-2 pt-2 border-t border-[#2A2D35] flex flex-col gap-1 text-xs">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                                                    <span>🧐</span>
                                                    Critic Peer Review ({step.critic_review.critic_agent})
                                                </span>
                                                <span
                                                    className={`text-[11px] font-mono font-medium ${
                                                        step.critic_review.approved ? 'text-emerald-400' : 'text-amber-400'
                                                    }`}
                                                >
                                                    Score: {step.critic_review.score}/10 ({step.critic_review.approved ? 'Approved' : 'Revised'})
                                                </span>
                                            </div>
                                            {step.critic_review.critique && (
                                                <p className="text-[11px] text-slate-400 italic bg-[#0D1017] p-2 rounded border border-[#2A2D35]/50 break-words">
                                                    "{step.critic_review.critique}"
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {/* Verification Badge */}
                                    {(typeof step.verified === 'boolean' || step.verification_result) && (
                                        <div className="mt-2 pt-2 border-t border-[#2A2D35] flex flex-wrap items-center gap-2 text-xs">
                                            {step.verified ?? step.verification_result?.verified ?? step.verification_result?.success ? (
                                                <span className="inline-flex items-center gap-1 text-emerald-300 font-medium">
                                                    <ShieldCheck className="w-3.5 h-3.5" />
                                                    Verified
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 text-red-300 font-medium">
                                                    <ShieldAlert className="w-3.5 h-3.5" />
                                                    Verification Failed
                                                </span>
                                            )}
                                            {typeof step.verification_result?.confidence === 'number' && (
                                                <span className="text-[11px] font-mono text-[#9CA3AF]">
                                                    ({Math.round(step.verification_result.confidence * (step.verification_result.confidence <= 1 ? 100 : 1))}% confidence)
                                                </span>
                                            )}
                                            {step.verification_result?.details && (
                                                <span className="text-[#9CA3AF] truncate">{step.verification_result.details}</span>
                                            )}
                                        </div>
                                    )}

                                    {/* Expandable Output / Error */}
                                    {isExpanded && (step.error || step.output !== undefined || step.result !== undefined) && (
                                        <div className="mt-2 pt-2 border-t border-[#2A2D35] space-y-1.5 text-xs">
                                            {step.error && (
                                                <div className="p-2 rounded bg-red-500/10 border border-red-500/25 text-red-200 font-mono whitespace-pre-wrap break-words">
                                                    {step.error}
                                                </div>
                                            )}
                                            {(step.output !== undefined && step.output !== null) ||
                                            (step.result !== undefined && step.result !== null) ? (
                                                <pre className="p-2 rounded bg-[#0D1017] border border-[#2A2D35] text-slate-300 font-mono text-[11px] overflow-x-auto max-h-40">
                                                    {formatOutputValue(step.output ?? step.result)}
                                                </pre>
                                            ) : null}
                                        </div>
                                    )}
                                </motion.div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Final Output / Chain Errors */}
            {chain.errors && chain.errors.length > 0 && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 space-y-1">
                    <p className="text-xs font-semibold text-red-300">Chain Errors</p>
                    {chain.errors.map((err, i) => (
                        <p key={i} className="text-xs text-red-200 font-mono break-words">
                            • {err}
                        </p>
                    ))}
                </div>
            )}

            {chain.final_output !== null && chain.final_output !== undefined && chain.final_output !== '' && (
                <div className="p-3 rounded-lg bg-[#0D1017] border border-emerald-500/25 space-y-1">
                    <p className="text-xs font-semibold text-emerald-300">Final Output</p>
                    <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                        {formatOutputValue(chain.final_output)}
                    </pre>
                </div>
            )}
        </div>
    );
};

export default ChainMonitor;
