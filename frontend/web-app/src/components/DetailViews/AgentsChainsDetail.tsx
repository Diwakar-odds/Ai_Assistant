import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Activity,
    Bot,
    CheckCircle2,
    Cpu,
    GitBranch,
    Layers,
    Loader2,
    Play,
    RefreshCw,
    Search,
    Send,
    Sparkles,
    Square,
    XCircle,
    Zap,
} from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';
import { analyzeCommandInput } from '../../lib/commandUtils';
import ChainMonitor from '../ChainMonitor';

const AgentsChainsDetail = () => {
    const {
        activeChains,
        chainHistory,
        selectedChainId,
        setSelectedChainId,
        agents,
        agentTasks,
        refreshChains,
        refreshAgents,
        createAndRunChain,
        emergencyStop,
        loadAgent,
        dispatchAgentTask,
        cancelAgentTask,
    } = useDashboard();

    const [activeTab, setActiveTab] = useState<'chains' | 'agents'>('chains');
    const [refreshing, setRefreshing] = useState(false);

    // Chain launcher state
    const [chainCommand, setChainCommand] = useState('');
    const [launchingChain, setLaunchingChain] = useState(false);

    // Agent filter & direct execution state
    const [agentQuery, setAgentQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<'all' | 'idle' | 'busy' | 'offline'>('all');
    const [targetAgentId, setTargetAgentId] = useState<string | null>(null);
    const [agentTaskPrompt, setAgentTaskPrompt] = useState('');
    const [autoDispatchPrompt, setAutoDispatchPrompt] = useState('');
    const [dispatchingAgent, setDispatchingAgent] = useState(false);
    const [dispatchFeedback, setDispatchFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    useEffect(() => {
        refreshChains();
        refreshAgents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const allChains = useMemo(() => {
        const map = new Map<string, (typeof activeChains)[number]>();
        activeChains.forEach((c) => map.set(c.chain_id, c));
        chainHistory.forEach((c) => {
            if (!map.has(c.chain_id)) map.set(c.chain_id, c);
        });
        return Array.from(map.values());
    }, [activeChains, chainHistory]);

    const effectiveChainId = selectedChainId || allChains[0]?.chain_id || null;
    const effectiveChain = useMemo(
        () => allChains.find((c) => c.chain_id === effectiveChainId) || null,
        [allChains, effectiveChainId]
    );

    const commandAnalysis = useMemo(() => analyzeCommandInput(chainCommand), [chainCommand]);

    const busyAgentsCount = agents.filter((a) => a.status === 'busy').length;
    const totalCompletedTasks =
        agents.reduce((acc, a) => acc + (a.completed_tasks || 0), 0) +
        chainHistory.filter((c) => c.status === 'completed').length;

    const filteredAgents = useMemo(() => {
        const q = agentQuery.trim().toLowerCase();
        return agents.filter((agent) => {
            if (statusFilter !== 'all' && agent.status !== statusFilter) return false;
            if (!q) return true;
            return (
                agent.name.toLowerCase().includes(q) ||
                agent.id.toLowerCase().includes(q) ||
                agent.category.toLowerCase().includes(q) ||
                agent.description.toLowerCase().includes(q) ||
                agent.capabilities.some((cap) => cap.toLowerCase().includes(q))
            );
        });
    }, [agents, agentQuery, statusFilter]);

    const handleRefreshAll = async () => {
        setRefreshing(true);
        await Promise.all([refreshChains(), refreshAgents()]);
        setRefreshing(false);
    };

    const handleLaunchChain = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!chainCommand.trim() || launchingChain) return;
        setLaunchingChain(true);
        const created = await createAndRunChain(chainCommand.trim(), { autoExecute: true });
        setLaunchingChain(false);
        if (created) {
            setChainCommand('');
        }
    };

    const handleRunAgentTask = async (agentId?: string) => {
        const prompt = agentId ? agentTaskPrompt.trim() : autoDispatchPrompt.trim();
        if (!prompt || dispatchingAgent) return;
        setDispatchingAgent(true);
        setDispatchFeedback(null);
        const res = await dispatchAgentTask(prompt, {
            agentId,
            asyncRun: true,
        });
        setDispatchingAgent(false);
        if (res) {
            setDispatchFeedback({
                type: 'success',
                text: `Dispatched task ${res.task_id}${res.agent_id ? ` to ${res.agent_id}` : ''} (${res.status})`,
            });
            if (agentId) {
                setAgentTaskPrompt('');
                setTargetAgentId(null);
            } else {
                setAutoDispatchPrompt('');
            }
        } else {
            setDispatchFeedback({
                type: 'error',
                text: 'Failed to dispatch task. Verify backend agent service is running.',
            });
        }
    };

    return (
        <div className="space-y-6">
            {/* Header & Quick Controls */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h3 className="text-2xl font-bold text-white flex items-center gap-2.5">
                        <WorkflowHeaderIcon />
                        <span>Multi-Agent & Chain Orchestrator</span>
                    </h3>
                    <p className="text-sm text-[#9CA3AF] mt-1">
                        Monitor multi-step execution DAGs, inspect live step telemetry, and dispatch specialized AI agents.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <button
                        type="button"
                        onClick={handleRefreshAll}
                        disabled={refreshing}
                        className="px-3.5 py-2 bg-[#1F2228] hover:bg-[#2A2D35] border border-[#2A2D35] text-white rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                    {(activeChains.length > 0 || busyAgentsCount > 0) && (
                        <button
                            type="button"
                            onClick={() => emergencyStop()}
                            className="px-3.5 py-2 bg-red-500/15 hover:bg-red-500/25 border border-red-500/40 text-red-200 rounded-lg text-xs font-semibold flex items-center gap-2 transition-colors"
                        >
                            <Square className="w-3.5 h-3.5" />
                            Emergency Stop
                        </button>
                    )}
                </div>
            </div>

            {/* KPI Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-[#9CA3AF]">Active Chains</p>
                        <p className="text-2xl font-bold text-white mt-0.5">{activeChains.length}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-[#3B82F6]/15 text-[#60A5FA]">
                        <GitBranch className="w-5 h-5" />
                    </div>
                </div>
                <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-[#9CA3AF]">Registered Agents</p>
                        <p className="text-2xl font-bold text-white mt-0.5">{agents.length}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-violet-500/15 text-violet-300">
                        <Bot className="w-5 h-5" />
                    </div>
                </div>
                <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-[#9CA3AF]">Agents Busy</p>
                        <p className="text-2xl font-bold text-[#00f3ff] mt-0.5">{busyAgentsCount}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-cyan-500/15 text-[#00f3ff]">
                        <Activity className="w-5 h-5" />
                    </div>
                </div>
                <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-[#9CA3AF]">Completed Runs</p>
                        <p className="text-2xl font-bold text-emerald-400 mt-0.5">{totalCompletedTasks}</p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-emerald-500/15 text-emerald-400">
                        <CheckCircle2 className="w-5 h-5" />
                    </div>
                </div>
            </div>

            {/* Primary Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-[#2A2D35] pb-2">
                <button
                    type="button"
                    onClick={() => setActiveTab('chains')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                        activeTab === 'chains'
                            ? 'bg-[#3B82F6]/20 text-white border border-[#3B82F6]/40 shadow-[0_0_12px_rgba(59,130,246,0.2)]'
                            : 'text-[#9CA3AF] hover:text-white hover:bg-[#1F2228]'
                    }`}
                >
                    <Layers className="w-4 h-4 text-[#00f3ff]" />
                    <span>Execution Chains</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-[#0D1017] text-[#9CA3AF]">
                        {allChains.length}
                    </span>
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab('agents')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all ${
                        activeTab === 'agents'
                            ? 'bg-violet-500/20 text-white border border-violet-500/40 shadow-[0_0_12px_rgba(139,92,246,0.2)]'
                            : 'text-[#9CA3AF] hover:text-white hover:bg-[#1F2228]'
                    }`}
                >
                    <Cpu className="w-4 h-4 text-violet-300" />
                    <span>Specialized Agents</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-[#0D1017] text-[#9CA3AF]">
                        {agents.length}
                    </span>
                </button>
            </div>

            {activeTab === 'chains' ? (
                <div className="space-y-5">
                    {/* Multi-Command Chain Launcher */}
                    <form
                        onSubmit={handleLaunchChain}
                        className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 space-y-2.5"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <label htmlFor="chain-launcher-input" className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF]">
                                Launch Multi-Step Command Chain
                            </label>
                            {commandAnalysis.isMultiStep && (
                                <span className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-full bg-cyan-500/15 text-[#00f3ff] border border-cyan-500/30">
                                    <Sparkles className="w-3 h-3" />
                                    {commandAnalysis.stepCount} steps detected
                                    {commandAnalysis.isParallel ? ' (Parallel DAG)' : ''}
                                </span>
                            )}
                        </div>
                        <div className="flex flex-col sm:flex-row gap-2">
                            <input
                                id="chain-launcher-input"
                                type="text"
                                value={chainCommand}
                                onChange={(e) => setChainCommand(e.target.value)}
                                placeholder='e.g. open chrome && search "AI trends" -> summarize top 3 results'
                                className="flex-1 bg-[#0D1017] border border-[#2A2D35] focus:border-[#00f3ff]/50 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-[#6B7280] focus:outline-none"
                            />
                            <button
                                type="submit"
                                disabled={!chainCommand.trim() || launchingChain}
                                className="px-4 py-2.5 rounded-lg bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors shrink-0"
                            >
                                {launchingChain ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                <span>Run Chain</span>
                            </button>
                        </div>
                    </form>

                    {/* Chains Master-Detail */}
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                        <div className="lg:col-span-5 space-y-3">
                            <div className="flex items-center justify-between">
                                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#9CA3AF]">
                                    Active & Recent Chains
                                </h4>
                            </div>

                            {allChains.length === 0 ? (
                                <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-6 text-center text-xs text-[#9CA3AF]">
                                    No chains executed yet. Run a single or multi-step command above or from the main prompt.
                                </div>
                            ) : (
                                <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
                                    {allChains.map((c) => {
                                        const isSelected = c.chain_id === effectiveChainId;
                                        const isActive = !['completed', 'failed', 'cancelled'].includes(c.status);
                                        return (
                                            <button
                                                key={c.chain_id}
                                                type="button"
                                                onClick={() => setSelectedChainId(c.chain_id)}
                                                className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                                                    isSelected
                                                        ? 'bg-[#1F2228] border-[#00f3ff]/60 shadow-[0_0_15px_rgba(0,243,255,0.12)]'
                                                        : 'bg-[#16181D] border-[#2A2D35] hover:border-[#3B82F6]/40'
                                                }`}
                                            >
                                                <div className="flex items-center justify-between gap-2 mb-1.5">
                                                    <span className="text-[10px] font-mono text-[#6B7280] truncate">
                                                        {c.chain_id}
                                                    </span>
                                                    <span
                                                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                                                            c.status === 'completed'
                                                                ? 'bg-emerald-500/15 text-emerald-300'
                                                                : c.status === 'failed'
                                                                ? 'bg-red-500/15 text-red-300'
                                                                : c.status === 'cancelled'
                                                                ? 'bg-slate-500/15 text-slate-300'
                                                                : c.status === 'paused'
                                                                ? 'bg-amber-500/15 text-amber-300'
                                                                : 'bg-cyan-500/15 text-cyan-300'
                                                        }`}
                                                    >
                                                        {isActive && '● '}
                                                        {c.status}
                                                    </span>
                                                </div>
                                                <p className="text-sm font-medium text-white line-clamp-2 mb-2">
                                                    {c.command || 'Orchestrated Command'}
                                                </p>
                                                <div className="flex items-center justify-between text-[11px] text-[#9CA3AF] mb-1.5">
                                                    <span>
                                                        {c.actions_completed}/{c.total_actions || c.actions.length} steps
                                                    </span>
                                                    <span className="font-mono text-[#00f3ff]">{c.progress_percentage}%</span>
                                                </div>
                                                <div className="h-1.5 w-full bg-[#0D1017] rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full transition-all ${
                                                            c.status === 'completed'
                                                                ? 'bg-emerald-500'
                                                                : c.status === 'failed'
                                                                ? 'bg-red-500'
                                                                : 'bg-[#00f3ff]'
                                                        }`}
                                                        style={{ width: `${c.progress_percentage}%` }}
                                                    />
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="lg:col-span-7">
                            <ChainMonitor chainId={effectiveChainId} chain={effectiveChain} />
                        </div>
                    </div>
                </div>
            ) : (
                <div className="space-y-5">
                    {/* Auto-Dispatch & Filter Controls */}
                    <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 space-y-3">
                        <div className="flex flex-col sm:flex-row gap-2">
                            <input
                                type="text"
                                value={autoDispatchPrompt}
                                onChange={(e) => setAutoDispatchPrompt(e.target.value)}
                                placeholder="Smart Auto-Dispatch: describe any task (research, write report, analyze data, organize files)..."
                                className="flex-1 bg-[#0D1017] border border-[#2A2D35] focus:border-violet-500/50 rounded-lg px-3.5 py-2 text-sm text-white placeholder-[#6B7280] focus:outline-none"
                            />
                            <button
                                type="button"
                                onClick={() => handleRunAgentTask(undefined)}
                                disabled={!autoDispatchPrompt.trim() || dispatchingAgent}
                                className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-medium flex items-center justify-center gap-2 transition-colors shrink-0"
                            >
                                <Zap className="w-4 h-4" />
                                <span>Auto Dispatch</span>
                            </button>
                        </div>

                        {dispatchFeedback && (
                            <div
                                className={`text-xs px-3 py-2 rounded-lg border ${
                                    dispatchFeedback.type === 'success'
                                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                                        : 'bg-red-500/10 border-red-500/30 text-red-300'
                                }`}
                            >
                                {dispatchFeedback.text}
                            </div>
                        )}

                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                            <div className="relative flex-1 max-w-sm">
                                <Search className="w-4 h-4 text-[#6B7280] absolute left-3 top-1/2 -translate-y-1/2" />
                                <input
                                    type="text"
                                    value={agentQuery}
                                    onChange={(e) => setAgentQuery(e.target.value)}
                                    placeholder="Filter agents by name, category, or capability..."
                                    className="w-full bg-[#0D1017] border border-[#2A2D35] rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-[#6B7280] focus:outline-none focus:border-[#00f3ff]/40"
                                />
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap">
                                {(['all', 'idle', 'busy', 'offline'] as const).map((status) => (
                                    <button
                                        key={status}
                                        type="button"
                                        onClick={() => setStatusFilter(status)}
                                        className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-colors ${
                                            statusFilter === status
                                                ? 'bg-white text-black'
                                                : 'bg-[#0D1017] text-[#9CA3AF] hover:text-white border border-[#2A2D35]'
                                        }`}
                                    >
                                        {status}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Agents Grid */}
                    {filteredAgents.length === 0 ? (
                        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-8 text-center">
                            <Bot className="w-10 h-10 text-violet-400/50 mx-auto mb-3" />
                            <p className="text-sm font-medium text-white">No agents match your filter</p>
                            <p className="text-xs text-[#6B7280] mt-1">
                                Try clearing the search filter or click Refresh to query the backend registry.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {filteredAgents.map((agent) => {
                                const isTarget = targetAgentId === agent.id;
                                const statusColors =
                                    agent.status === 'busy'
                                        ? 'bg-cyan-500/15 text-[#00f3ff] border-cyan-500/30'
                                        : agent.status === 'error'
                                        ? 'bg-red-500/15 text-red-300 border-red-500/30'
                                        : agent.status === 'offline'
                                        ? 'bg-slate-500/15 text-slate-300 border-slate-500/30'
                                        : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';

                                return (
                                    <motion.div
                                        key={agent.id}
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="bg-[#1F2228] border border-[#2A2D35] hover:border-violet-500/40 rounded-xl p-4 flex flex-col justify-between gap-3 transition-colors"
                                    >
                                        <div>
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div className="flex items-center gap-2.5 min-w-0">
                                                    <div className="p-2 rounded-lg bg-violet-500/15 text-violet-300 shrink-0">
                                                        <Bot className="w-4 h-4" />
                                                    </div>
                                                    <div className="min-w-0">
                                                        <h5 className="text-sm font-semibold text-white truncate">
                                                            {agent.name}
                                                        </h5>
                                                        <span className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">
                                                            {agent.category}
                                                        </span>
                                                    </div>
                                                </div>
                                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase shrink-0 ${statusColors}`}>
                                                    {agent.status}
                                                </span>
                                            </div>

                                            <p className="text-xs text-[#9CA3AF] line-clamp-2 min-h-[2rem] mb-2.5">
                                                {agent.description || `Specialized ${agent.category} agent`}
                                            </p>

                                            {agent.current_task && (
                                                <div className="mb-2.5 px-2.5 py-1.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-[11px] text-cyan-200 truncate">
                                                    Running: {agent.current_task}
                                                </div>
                                            )}

                                            <div className="flex flex-wrap gap-1 mb-3">
                                                {agent.capabilities.slice(0, 5).map((cap) => (
                                                    <span
                                                        key={cap}
                                                        className="text-[10px] px-1.5 py-0.5 rounded bg-[#0D1017] border border-[#2A2D35] text-[#9CA3AF]"
                                                    >
                                                        {cap}
                                                    </span>
                                                ))}
                                                {agent.capabilities.length > 5 && (
                                                    <span className="text-[10px] text-[#6B7280]">
                                                        +{agent.capabilities.length - 5}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="pt-2.5 border-t border-[#2A2D35] space-y-2">
                                            <div className="flex items-center justify-between text-[11px] text-[#6B7280]">
                                                <span>Done: {agent.completed_tasks} · Err: {agent.failed_tasks}</span>
                                                <div className="flex items-center gap-1.5">
                                                    {(agent.loaded === false || agent.status === 'offline') && (
                                                        <button
                                                            type="button"
                                                            onClick={() => loadAgent(agent.id)}
                                                            className="px-2 py-1 rounded bg-[#2A2D35] hover:bg-[#3A3D45] text-white text-[11px] font-medium transition-colors"
                                                        >
                                                            Load
                                                        </button>
                                                    )}
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            setTargetAgentId(isTarget ? null : agent.id);
                                                            setAgentTaskPrompt('');
                                                        }}
                                                        className="px-2.5 py-1 rounded bg-[#3B82F6]/20 hover:bg-[#3B82F6]/30 text-[#60A5FA] border border-[#3B82F6]/30 text-[11px] font-medium transition-colors"
                                                    >
                                                        {isTarget ? 'Close' : 'Run Task'}
                                                    </button>
                                                </div>
                                            </div>

                                            {isTarget && (
                                                <div className="flex gap-1.5 pt-1">
                                                    <input
                                                        type="text"
                                                        value={agentTaskPrompt}
                                                        onChange={(e) => setAgentTaskPrompt(e.target.value)}
                                                        placeholder={`Task for ${agent.name}...`}
                                                        className="flex-1 bg-[#0D1017] border border-[#2A2D35] rounded px-2.5 py-1.5 text-xs text-white placeholder-[#6B7280] focus:outline-none"
                                                    />
                                                    <button
                                                        type="button"
                                                        onClick={() => handleRunAgentTask(agent.id)}
                                                        disabled={!agentTaskPrompt.trim() || dispatchingAgent}
                                                        className="px-2.5 py-1.5 rounded bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white text-xs flex items-center gap-1"
                                                    >
                                                        <Send className="w-3 h-3" />
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}

                    {/* Recent Agent Task Executions */}
                    {agentTasks.length > 0 && (
                        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 space-y-3">
                            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                                <Activity className="w-4 h-4 text-[#00f3ff]" />
                                <span>Recent Agent Tasks ({agentTasks.length})</span>
                            </h4>
                            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                                {agentTasks.map((task) => {
                                    const isTaskActive = ['pending', 'running', 'executing'].includes(task.status);
                                    return (
                                        <div
                                            key={task.task_id}
                                            className="flex items-start justify-between gap-3 bg-[#16181D] border border-[#2A2D35] rounded-lg px-3 py-2.5 text-xs"
                                        >
                                            <div className="min-w-0 flex-1">
                                                <div className="flex flex-wrap items-center gap-2 mb-1">
                                                    <span className="font-mono text-[10px] text-[#6B7280]">{task.task_id}</span>
                                                    {(task.agent_name || task.agent_id) && (
                                                        <span className="px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 text-[10px] font-medium">
                                                            {task.agent_name || task.agent_id}
                                                        </span>
                                                    )}
                                                    <span
                                                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                                            task.status === 'completed'
                                                                ? 'bg-emerald-500/15 text-emerald-300'
                                                                : task.status === 'failed'
                                                                ? 'bg-red-500/15 text-red-300'
                                                                : task.status === 'cancelled'
                                                                ? 'bg-slate-500/15 text-slate-300'
                                                                : 'bg-cyan-500/15 text-cyan-300'
                                                        }`}
                                                    >
                                                        {task.status}
                                                    </span>
                                                </div>
                                                <p className="text-white break-words">{task.description}</p>
                                                {task.error && <p className="text-red-300 mt-1 font-mono">{task.error}</p>}
                                            </div>
                                            {isTaskActive && (
                                                <button
                                                    type="button"
                                                    onClick={() => cancelAgentTask(task.task_id)}
                                                    className="px-2 py-1 rounded bg-red-500/15 hover:bg-red-500/25 text-red-300 text-[11px] flex items-center gap-1 shrink-0"
                                                >
                                                    <XCircle className="w-3 h-3" />
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

const WorkflowHeaderIcon = () => (
    <span className="p-2 rounded-lg bg-[#00f3ff]/10 border border-[#00f3ff]/30 text-[#00f3ff]">
        <Layers className="w-5 h-5" />
    </span>
);

export default AgentsChainsDetail;
