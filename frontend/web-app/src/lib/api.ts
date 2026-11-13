// Single source of truth for backend API URL and shared multi-agent / chain contracts
// Automatically adapts to dynamic backend port when served via Flask / PyWebView.

const resolveApiBase = (): string => {
    if (typeof window !== 'undefined' && window.location) {
        const { origin, protocol, port } = window.location;
        // When served directly by the Flask backend (default 5000 or fallback 5001+), reuse exact origin
        if (protocol.startsWith('http') && !['5173', '5174', '3000', '4173'].includes(port)) {
            return origin;
        }
    }
    const envUrl = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL;
    return envUrl || 'http://127.0.0.1:5000';
};

export const API_BASE = resolveApiBase();

export const apiUrl = (path: string): string => {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE}${normalizedPath}`;
};

export const SOCKET_URL = API_BASE;

export const getAuthToken = (): string | null => {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem('authToken') || localStorage.getItem('token');
};

export const getAuthHeaders = (extra?: Record<string, string>): Record<string, string> => {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(extra || {}),
    };
    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
};

export async function apiFetchJson<T = any>(path: string, init: RequestInit = {}): Promise<{ ok: boolean; status: number; data: T | null; error?: string }> {
    try {
        const res = await fetch(apiUrl(path), {
            ...init,
            headers: {
                ...getAuthHeaders(),
                ...((init.headers as Record<string, string>) || {}),
            },
        });
        const contentType = res.headers?.get?.('content-type') || '';
        const isJson = contentType.includes('application/json') || !contentType;
        if (!isJson) {
            const text = await res.text().catch(() => '');
            return {
                ok: res.ok,
                status: res.status,
                data: null,
                error: text ? `Unexpected non-JSON response (${res.status})` : `HTTP ${res.status}`,
            };
        }
        const data = (await res.json().catch(() => null)) as T | null;
        return {
            ok: res.ok,
            status: res.status,
            data,
            error: !res.ok ? ((data as any)?.error || (data as any)?.message || `HTTP ${res.status}`) : undefined,
        };
    } catch (err) {
        return {
            ok: false,
            status: 0,
            data: null,
            error: err instanceof Error ? err.message : 'Network error',
        };
    }
}

export const API_ENDPOINTS = {
    status: '/api/status',
    command: '/api/command',
    chat: '/api/chat',
    settings: {
        all: '/api/settings/all',
        update: '/api/settings/update',
        reset: '/api/settings/reset',
        export: '/api/settings/export',
        import: '/api/settings/import',
        completeOnboarding: '/api/settings/complete_onboarding',
    },
    apps: {
        list: '/api/apps',
        refresh: '/api/apps/refresh',
        launch: '/api/apps/launch',
    },
    voice: {
        speak: '/api/voice/speak',
        status: '/api/voice/status',
        list: '/api/voice/list',
        process: '/api/voice/process',
    },
    integrations: {
        status: '/api/integrations/status',
        mcp: '/api/integrations/mcp',
        connect: '/api/integrations/connect',
        disconnect: '/api/integrations/disconnect',
    },
    learning: {
        stats: '/api/learning/stats',
        all_stats: '/api/learning/stats/all',
        dashboard: '/api/learning/dashboard',
    },
    system: {
        stats: '/api/system/stats',
        details: '/api/system/details',
        logs: '/api/logs/recent',
    },
    chains: {
        create: '/api/chains/create',
        active: '/api/chains/active',
        history: '/api/chains/history',
        detail: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}`,
        execute: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}/execute`,
        pause: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}/pause`,
        resume: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}/resume`,
        cancel: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}/cancel`,
        delete: (chainId: string) => `/api/chains/${encodeURIComponent(chainId)}`,
        clear: '/api/chains/clear',
        optimize: '/api/chains/optimize',
        executiveStop: '/api/executive/stop',
        emergencyStop: '/api/emergency/stop',
    },
    agents: {
        list: '/api/agents',
        capabilities: '/api/agents/capabilities',
        dispatch: '/api/agents/dispatch',
        detail: (agentId: string) => `/api/agents/${encodeURIComponent(agentId)}`,
        load: (agentId: string) => `/api/agents/${encodeURIComponent(agentId)}/load`,
        execute: (agentId: string) => `/api/agents/${encodeURIComponent(agentId)}/execute`,
        tasks: '/api/agents/tasks',
        taskDetail: (taskId: string) => `/api/agents/tasks/${encodeURIComponent(taskId)}`,
        cancelTask: (taskId: string) => `/api/agents/tasks/${encodeURIComponent(taskId)}/cancel`,
        workflows: '/api/agents/workflows',
        synthesizeWorkflow: '/api/agents/workflows/synthesize',
        clearWorkflows: '/api/agents/workflows/clear',
        pendingCheckpoints: '/api/agents/checkpoints/pending',
        respondCheckpoint: '/api/agents/checkpoint/respond',
    },
    auth: {
        login: '/api/auth/login',
        verify: '/api/auth/verify',
    },
    jarvis: {
        hud: '/api/jarvis/hud',
    },
} as const;

export type ChainStatus =
    | 'pending'
    | 'planning'
    | 'executing'
    | 'verifying'
    | 'paused'
    | 'waiting_confirmation'
    | 'completed'
    | 'failed'
    | 'cancelled';

export type ActionStatus =
    | 'pending'
    | 'running'
    | 'executing'
    | 'verifying'
    | 'completed'
    | 'failed'
    | 'skipped'
    | 'cancelled'
    | 'paused'
    | 'waiting_confirmation';

export interface VerificationResultDTO {
    success?: boolean;
    verified?: boolean;
    confidence?: number;
    details?: string;
    message?: string;
}

export interface ChainActionDTO {
    id: string;
    step_id?: string;
    type: string;
    description: string;
    status: ActionStatus | string;
    agent_id?: string | null;
    agent_name?: string | null;
    capability?: string | null;
    execution_target?: string | null;
    dependencies?: string[];
    parallel_group?: string | null;
    progress?: number;
    params?: Record<string, any>;
    result?: any;
    output?: any;
    error?: string | null;
    verified?: boolean;
    verification_result?: VerificationResultDTO | null;
    requires_confirmation?: boolean;
    healed_by?: string | null;
    critic_review?: CriticReviewDTO | null;
    duration_seconds?: number;
    started_at?: string;
    completed_at?: string;
}

export interface ChainDTO {
    chain_id: string;
    id: string;
    command: string;
    source?: string;
    status: ChainStatus | string;
    progress_percentage: number;
    progress?: number;
    current_action_index: number;
    current_action?: string | null;
    current_agent?: string | null;
    total_actions: number;
    actions_completed: number;
    actions_failed: number;
    app_context?: string | null;
    requires_confirmation?: boolean;
    action_id?: string | null;
    actions: ChainActionDTO[];
    steps?: ChainActionDTO[];
    created_at?: string;
    started_at?: string;
    completed_at?: string;
    duration_seconds?: number | null;
    final_output?: any;
    errors?: string[];
}

export type AgentStatus = 'idle' | 'busy' | 'offline' | 'error';

export interface AgentDTO {
    id: string;
    name: string;
    category: string;
    description: string;
    capabilities: string[];
    status: AgentStatus;
    loaded?: boolean;
    active_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    current_task?: string | null;
    metrics?: Record<string, any>;
}

export interface AgentTaskDTO {
    task_id: string;
    agent_id?: string | null;
    agent_name?: string | null;
    description: string;
    status: string;
    created_at?: string;
    started_at?: string;
    completed_at?: string;
    execution_time?: number;
    result?: any;
    error?: string | null;
    output_path?: string | null;
    artifacts?: string[];
}

export interface WorkflowRecipeDTO {
    id: string;
    normalized_pattern: string;
    workflow_name: string;
    tags?: string;
    success_count: number;
    last_used?: number;
    plan?: any;
}

export interface CheckpointDTO {
    checkpoint_id: string;
    step_id: string;
    agent_id: string;
    description: string;
    params?: Record<string, any>;
    chain_id?: string;
    status: 'pending' | 'confirmed' | 'rejected';
    created_at?: number;
}

export interface CriticReviewDTO {
    step_id: string;
    creator_agent: string;
    critic_agent: string;
    score: number;
    approved: boolean;
    critique?: string;
}

export interface SystemDetailsDTO {
    os: string;
    uptime: string;
    processes: number | null;
    threads: number | null;
    cpu_usage?: number;
    memory_usage?: number;
    disk_usage?: number;
    hostname?: string;
}

export const normalizeChainStatus = (raw: unknown): ChainStatus | string => {
    const val = String(raw || 'pending').trim().toLowerCase();
    if (val === 'running' || val === 'in_progress' || val === 'created' || val === 'decomposed') {
        return val === 'created' ? 'pending' : val === 'decomposed' ? 'planning' : 'executing';
    }
    if (val === 'canceled') return 'cancelled';
    return val;
};

export const normalizeActionStatus = (raw: unknown): ActionStatus | string => {
    const val = String(raw || 'pending').trim().toLowerCase();
    if (val === 'in_progress') return 'executing';
    if (val === 'canceled') return 'cancelled';
    return val;
};

export const normalizeAgentStatus = (raw: unknown): AgentStatus => {
    const val = String(raw || 'idle').trim().toLowerCase();
    if (val === 'working' || val === 'busy' || val === 'active' || val === 'executing') return 'busy';
    if (val === 'offline' || val === 'unloaded' || val === 'disabled') return 'offline';
    if (val === 'error' || val === 'failed') return 'error';
    return 'idle';
};

export const normalizeChainActionDTO = (raw: any, index = 0): ChainActionDTO => {
    const verificationRaw = raw?.verification_result ?? raw?.verification ?? null;
    const verificationObj: VerificationResultDTO | null =
        verificationRaw && typeof verificationRaw === 'object'
            ? {
                  success:
                      typeof verificationRaw.success === 'boolean'
                          ? verificationRaw.success
                          : typeof verificationRaw.verified === 'boolean'
                          ? verificationRaw.verified
                          : undefined,
                  verified:
                      typeof verificationRaw.verified === 'boolean'
                          ? verificationRaw.verified
                          : verificationRaw.success,
                  confidence:
                      typeof verificationRaw.confidence === 'number'
                          ? verificationRaw.confidence
                          : undefined,
                  details: verificationRaw.details || verificationRaw.message || undefined,
              }
            : null;

    const verifiedFlag =
        typeof raw?.verified === 'boolean'
            ? raw.verified
            : typeof verificationObj?.verified === 'boolean'
            ? verificationObj.verified
            : undefined;

    const id = String(raw?.id || raw?.action_id || raw?.step_id || `action_${index + 1}`);
    const status = normalizeActionStatus(raw?.status);
    const result = raw?.result !== undefined ? raw.result : raw?.output;
    const output = raw?.output !== undefined ? raw.output : raw?.result;

    return {
        id,
        step_id: raw?.step_id ? String(raw.step_id) : id,
        type: String(raw?.type || raw?.action_type || raw?.intent || 'task'),
        description: String(raw?.description || raw?.title || raw?.command || `Step ${index + 1}`),
        status,
        agent_id: raw?.agent_id ?? raw?.assigned_agent ?? raw?.params?.agent_id ?? null,
        agent_name: raw?.agent_name ?? null,
        capability: raw?.capability ?? null,
        execution_target: raw?.execution_target ?? null,
        dependencies: Array.isArray(raw?.dependencies) ? raw.dependencies.map(String) : [],
        parallel_group: raw?.parallel_group ?? null,
        progress: typeof raw?.progress === 'number' ? raw.progress : undefined,
        params: raw?.params && typeof raw.params === 'object' ? raw.params : undefined,
        result,
        output,
        error: raw?.error ? String(raw.error) : null,
        verified: verifiedFlag,
        verification_result: verificationObj,
        requires_confirmation: Boolean(raw?.requires_confirmation),
        healed_by: raw?.healed_by ?? raw?.params?.healed_by ?? null,
        critic_review: raw?.critic_review ?? raw?.params?.critic_review ?? null,
        duration_seconds: typeof raw?.duration_seconds === 'number' ? raw.duration_seconds : undefined,
        started_at: raw?.started_at,
        completed_at: raw?.completed_at,
    };
};

export const normalizeChainDTO = (rawInput: any): ChainDTO | null => {
    const raw = rawInput?.chain && typeof rawInput.chain === 'object' ? rawInput.chain : rawInput;
    if (!raw || typeof raw !== 'object') return null;

    const chainId = String(raw.chain_id || raw.id || '').trim();
    if (!chainId) return null;

    const rawActions = Array.isArray(raw.actions)
        ? raw.actions
        : Array.isArray(raw.steps)
        ? raw.steps
        : [];
    const actions: ChainActionDTO[] = rawActions.map((a: any, idx: number) =>
        normalizeChainActionDTO(a, idx)
    );

    const totalActions =
        typeof raw.total_actions === 'number'
            ? raw.total_actions
            : typeof raw.total_steps === 'number'
            ? raw.total_steps
            : actions.length;

    const actionsCompleted =
        typeof raw.actions_completed === 'number'
            ? raw.actions_completed
            : typeof raw.steps_completed === 'number'
            ? raw.steps_completed
            : actions.filter((a) => a.status === 'completed').length;

    const actionsFailed =
        typeof raw.actions_failed === 'number'
            ? raw.actions_failed
            : actions.filter((a) => a.status === 'failed').length;

    const status = normalizeChainStatus(raw.status);
    let progressPct =
        typeof raw.progress_percentage === 'number'
            ? raw.progress_percentage
            : typeof raw.progress === 'number'
            ? raw.progress
            : totalActions > 0
            ? Math.round((actionsCompleted / totalActions) * 100)
            : status === 'completed'
            ? 100
            : 0;
    progressPct = Math.max(0, Math.min(100, Math.round(progressPct)));

    const currentIdx =
        typeof raw.current_action_index === 'number'
            ? raw.current_action_index
            : Math.max(
                  0,
                  actions.findIndex((a) => a.status === 'running' || a.status === 'executing' || a.status === 'verifying')
              );

    const activeStep = actions[currentIdx];

    return {
        chain_id: chainId,
        id: chainId,
        command: String(raw.command || raw.goal || raw.description || ''),
        source: raw.source ? String(raw.source) : undefined,
        status,
        progress_percentage: progressPct,
        progress: progressPct,
        current_action_index: currentIdx,
        current_action:
            raw.current_action ?? activeStep?.description ?? null,
        current_agent:
            raw.current_agent ?? activeStep?.agent_name ?? activeStep?.agent_id ?? null,
        total_actions: totalActions,
        actions_completed: actionsCompleted,
        actions_failed: actionsFailed,
        app_context: raw.app_context ?? null,
        requires_confirmation: Boolean(raw.requires_confirmation),
        action_id: raw.action_id ?? null,
        actions,
        steps: actions,
        created_at: raw.created_at,
        started_at: raw.started_at,
        completed_at: raw.completed_at,
        duration_seconds: typeof raw.duration_seconds === 'number' ? raw.duration_seconds : null,
        final_output: raw.final_output ?? raw.output ?? null,
        errors: Array.isArray(raw.errors) ? raw.errors.map(String) : [],
    };
};

export const normalizeAgentDTO = (raw: any): AgentDTO | null => {
    if (!raw || typeof raw !== 'object') return null;
    const id = String(raw.id || raw.agent_id || '').trim();
    if (!id) return null;
    return {
        id,
        name: String(raw.name || id),
        category: String(raw.category || 'general'),
        description: String(raw.description || ''),
        capabilities: Array.isArray(raw.capabilities) ? raw.capabilities.map(String) : [],
        status: normalizeAgentStatus(raw.status),
        loaded: typeof raw.loaded === 'boolean' ? raw.loaded : undefined,
        active_tasks: Number(raw.active_tasks || 0),
        completed_tasks: Number(raw.completed_tasks || 0),
        failed_tasks: Number(raw.failed_tasks || 0),
        current_task: raw.current_task ? String(raw.current_task) : null,
        metrics: raw.metrics && typeof raw.metrics === 'object' ? raw.metrics : undefined,
    };
};

export const normalizeAgentTaskDTO = (raw: any): AgentTaskDTO | null => {
    if (!raw || typeof raw !== 'object') return null;
    const taskId = String(raw.task_id || raw.id || '').trim();
    if (!taskId) return null;
    return {
        task_id: taskId,
        agent_id: raw.agent_id ? String(raw.agent_id) : null,
        agent_name: raw.agent_name ? String(raw.agent_name) : null,
        description: String(raw.description || raw.command || ''),
        status: String(raw.status || 'pending').toLowerCase(),
        created_at: raw.created_at,
        started_at: raw.started_at,
        completed_at: raw.completed_at,
        execution_time: typeof raw.execution_time === 'number' ? raw.execution_time : undefined,
        result: raw.result ?? null,
        error: raw.error ? String(raw.error) : null,
        output_path: raw.output_path ? String(raw.output_path) : null,
        artifacts: Array.isArray(raw.artifacts) ? raw.artifacts.map(String) : [],
    };
};

export const normalizeSystemDetailsDTO = (raw: any): SystemDetailsDTO => ({
    os: String(raw?.os || raw?.operating_system || raw?.platform || 'Unknown'),
    uptime: String(raw?.uptime || '--'),
    processes: typeof raw?.processes === 'number' ? raw.processes : (typeof raw?.process_count === 'number' ? raw.process_count : null),
    threads: typeof raw?.threads === 'number' ? raw.threads : (typeof raw?.thread_count === 'number' ? raw.thread_count : null),
    cpu_usage: typeof raw?.cpu_usage === 'number' ? raw.cpu_usage : undefined,
    memory_usage: typeof raw?.memory_usage === 'number' ? raw.memory_usage : undefined,
    disk_usage: typeof raw?.disk_usage === 'number' ? raw.disk_usage : undefined,
    hostname: raw?.hostname ? String(raw.hostname) : undefined,
});
