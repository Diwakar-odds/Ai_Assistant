import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import io, { Socket } from 'socket.io-client';
import {
    apiUrl,
    SOCKET_URL,
    API_ENDPOINTS,
    apiFetchJson,
    ChainDTO,
    ChainActionDTO,
    AgentDTO,
    AgentTaskDTO,
    SystemDetailsDTO,
    normalizeChainDTO,
    normalizeActionStatus,
    normalizeChainStatus,
    normalizeAgentDTO,
    normalizeAgentTaskDTO,
    normalizeSystemDetailsDTO,
} from '../lib/api';

export interface SessionActivity {
    seq?: number;
    id: string;
    kind: string;
    title: string;
    detail?: string;
    source?: string;
    status?: string;
    intent?: string | null;
    provider?: string | null;
    model?: string | null;
    time: string;
    timestamp?: string;
    ts_ms?: number;
}

export interface Message {
    id: number;
    type: 'user' | 'ai';
    text: string;
    time: string;
    message_id?: string;
    source?: string;
    isVoice?: boolean;
    provider?: string | null;
    model?: string | null;
    seq?: number;
    ts_ms?: number;
    chain_id?: string | null;
    agent_id?: string | null;
    agent_name?: string | null;
    orchestrated?: boolean;
    steps_completed?: number;
    total_steps?: number;
    actions?: ChainActionDTO[];
}

export interface VoiceCommand {
    id: number;
    command: string;
    time: string;
    message_id?: string;
    source?: string;
    ts_ms?: number;
}

export interface SystemStats {
    cpu: number;
    memory: number;
    disk: number;
    network: string;
}

export interface LearningStats {
    database: string;
    systems: string;
    conversations: string;
    details?: unknown;
}

export interface SystemLog {
    id: number;
    type: 'info' | 'success' | 'warning' | 'error';
    message: string;
    time: string;
}

export interface ConversationSession {
    id: string;
    boot_id?: string;
    startTime: string;
    startTimestamp?: number;
    endTime?: string;
    endTimestamp?: number;
    date?: string;
    day?: string;
    formattedDate?: string;
    messageCount: number;
    userMessageCount: number;
    aiMessageCount: number;
    voiceCount: number;
    activityCount?: number;
    duration?: string;
    preview?: string;
    messages: Message[];
    voiceCommands: VoiceCommand[];
    activities?: SessionActivity[];
}

export interface ActiveChain {
    chain_id: string;
    id?: string;
    command: string;
    progress: number;
    progress_percentage?: number;
    status: 'pending' | 'planning' | 'executing' | 'verifying' | 'paused' | 'waiting_confirmation' | 'completed' | 'failed' | 'cancelled' | string;
    app_context?: string | null;
    current_action_index?: number;
    current_action?: string | null;
    current_agent?: string | null;
    total_actions?: number;
    actions_completed?: number;
    actions_failed?: number;
    actions?: ChainActionDTO[];
}

export type ViewType =
    | 'dashboard'
    | 'apps'
    | 'chat'
    | 'voice'
    | 'settings'
    | 'ai-learning'
    | 'database'
    | 'systems'
    | 'conversations'
    | 'integrations'
    | 'agents'
    | 'chains'
    | 'orchestrator'
    | null;

export type OrbState = 'idle' | 'listening' | 'speaking' | 'processing' | 'error';

export interface SystemStatsPoint {
    time: string;
    cpu: number;
    memory: number;
    disk: number;
}

interface DashboardContextType {
    socket: Socket | null;
    chatMessages: Message[];
    voiceCommands: VoiceCommand[];
    systemStats: SystemStats;
    systemStatsHistory: SystemStatsPoint[];
    systemDetails: SystemDetailsDTO | null;
    learningStats: LearningStats;
    systemLogs: SystemLog[];
    taskProgress: number;
    activeChains: ChainDTO[];
    chainHistory: ChainDTO[];
    selectedChainId: string | null;
    setSelectedChainId: (chainId: string | null) => void;
    openChainMonitor: (chainId?: string | null) => void;
    agents: AgentDTO[];
    agentTasks: AgentTaskDTO[];
    refreshChains: () => Promise<void>;
    refreshAgents: () => Promise<void>;
    refreshSystemDetails: () => Promise<SystemDetailsDTO | null>;
    createAndRunChain: (command: string, opts?: { autoExecute?: boolean; agentId?: string }) => Promise<ChainDTO | null>;
    pauseChain: (chainId: string) => Promise<boolean>;
    resumeChain: (chainId: string, userInput?: string) => Promise<boolean>;
    cancelChain: (chainId: string) => Promise<boolean>;
    emergencyStop: () => Promise<boolean>;
    loadAgent: (agentId: string) => Promise<AgentDTO | null>;
    dispatchAgentTask: (command: string, opts?: { agentId?: string; asyncRun?: boolean }) => Promise<AgentTaskDTO | null>;
    cancelAgentTask: (taskId: string) => Promise<boolean>;
    isVoiceActive: boolean;
    interimTranscript: string;
    audioLevel: number; // 0-100, real-time microphone audio level
    orbState: OrbState;
    orbAudioLevel: number; // 0-100, live voice (mic or TTS) amplitude driving 4D orb vibration
    isSpeaking: boolean;
    orbError: string | null;
    triggerOrbError: (msg?: string) => void;
    desktopOverlayEnabled: boolean;
    setDesktopOverlayEnabled: (enabled: boolean) => void;
    sendCommand: (command: string, opts?: { agentId?: string }) => void;
    isAITyping: boolean;
    toggleVoice: () => void;
    setVoiceLanguage?: (lang: string) => void;
    alwaysActive: boolean;
    toggleAlwaysActive: () => void;
    toggleWakeWord: () => void;
    requireWakeWord: boolean;
    wakeWordDetected: boolean;

    aiMode: 'online' | 'offline';
    aiProvider: 'gemini' | 'openai' | 'gguf';
    setAIProvider: (provider: 'gemini' | 'openai' | 'gguf') => void;
    toggleAIMode: () => void;
    speak: (text: string, lang?: string) => void;
    selectedView: ViewType;
    setSelectedView: (view: ViewType) => void;
    closeDetailView: () => void;
    currentSession: ConversationSession | null;
    conversationHistory: ConversationSession[];
    sessionActivities: SessionActivity[];
    isViewingHistory?: boolean;
    resumeLiveSession?: () => void;
    loadSession?: (sessionId: string) => void;
    deleteSession?: (sessionId: string) => void;
    clearAllSessions?: () => void;
    startNewSession?: () => void;
    isConnected: boolean;

    hudData: any;
    pendingDangerAction: any;
    authorizeAction: () => void;
    cancelAction: () => void;
    isLeftSidebarOpen: boolean;
    isRightSidebarOpen: boolean;
    toggleLeftSidebar: () => void;
    toggleRightSidebar: () => void;
    setSidebarAutoState: (state: any) => void;
    brainStatus: any;

    lastVisionAnalysis: any;
    presenceData: any;
    analyzeCameraFrame: (base64Image: string, prompt?: string) => void;
    checkPresence: (base64Image: string) => void;

    lastGesture: any;
    checkGesture: (base64Image: string) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

// Unified default wake phrases (English + Hinglish/Devanagari)
const DEFAULT_WAKE_PHRASES: string[] = [
    'hey pulsar',
    'pulsar',
    'ok pulsar',
    'hey assistant',
    'ok assistant',
    'पल्सर',
    'पलसर',
    'हे पल्सर',
    'हे पलसर',
    'ओके पल्सर',
    'सुनो पल्सर',
];

const BARGE_IN_STOP_REGEX =
    /^(?:(?:hey|ok)\s+pulsar|pulsar|हे\s*पल्सर|ओके\s*पल्सर|पल्सर)?[\s,.:;!?।-]*(?:stop|stop\s+speaking|stop\s+talking|stop\s+it|quiet|be\s+quiet|silence|shutup|shut\s+up|cancel|never\s*mind|enough|wait|hold\s+on|chup|chup\s+ho|chup\s+ho\s+ja|chup\s+ho\s+jao|chup\s+raho|chup\s+kar|chup\s+karo|bas|bas\s+kar|bas\s+karo|ruk|ruk\s+ja|ruk\s+jao|ruko|roko|band\s+kar|band\s+karo|bolna\s+band(?:\s+karo?)?|aawaz\s+band(?:\s+karo?)?|awaaz\s+band(?:\s+karo?)?|चुप(?:\s+हो(?:\s+जाओ?)?|\s+रहो|\s+करो?)?|बस(?:\s+करो?)?|रुक(?:\s+जाओ?)?|रुको|रोको|बोलना\s+बंद(?:\s+करो?)?|बंद\s+करो?|स्टॉप)(?:[\s,.:;!?।-]+(?:please|plz|yaar|bhai|ab|abhi|na|zara|boss|प्लीज|यार|अभी|ना))?[\s,.:;!?।-]*$/iu;

const BARGE_IN_SILENCE_HEADS = [
    'chup ho jao', 'chup ho ja', 'chup raho', 'chup karo', 'chup kar', 'chup ho', 'chup',
    'shut up', 'shutup', 'be quiet', 'stop speaking', 'stop talking', 'stop it', 'mute yourself',
    'bolna band karo', 'bolna band kar', 'bolna band', 'awaaz band karo', 'aawaz band karo',
    'shant ho jao', 'चुप हो जाओ', 'चुप हो जा', 'चुप रहो', 'चुप करो', 'चुप कर', 'चुप', 'बोलना बंद करो', 'बोलना बंद', 'शांत',
];

const BARGE_IN_DISQUALIFIER_RE =
    /\b(?:spotify|chrome|notepad|whatsapp|youtube|music|song|video|gaana|wifi|bluetooth|app|download|recording|settings|task|what|why|how|when|where|who|open|kholo|play|search)\b/i;

const isBargeInStopPhrase = (raw: string): boolean => {
    const cleaned = (raw || '').trim();
    if (!cleaned) return false;
    if (BARGE_IN_STOP_REGEX.test(cleaned)) return true;

    const noWake = cleaned
        .replace(/^(?:(?:hey|ok)\s+pulsar|pulsar|हे\s*पल्सर|ओके\s*पल्सर|पल्सर)[\s,.:;!?।-]*/iu, '')
        .replace(/[\s,.:;!?।-]+(?:(?:hey|ok)\s+pulsar|pulsar|हे\s*पल्सर|ओके\s*पल्सर|पल्सर)$/iu, '')
        .replace(/[,.:;!?।-]+/g, ' ')
        .trim()
        .toLowerCase();

    if (!noWake) return false;
    const words = noWake.split(/\s+/).filter(Boolean);
    if (words.length <= 6 && !BARGE_IN_DISQUALIFIER_RE.test(noWake)) {
        for (const head of BARGE_IN_SILENCE_HEADS) {
            if (noWake === head || noWake.startsWith(`${head} `)) {
                return true;
            }
        }
    }
    return false;
};

// GLOBAL DEDUPLICATION VARIABLE (Outside component to persist across re-renders/instances)
let globalLastCommandInfo = { text: '', time: 0 };

export const useDashboard = () => {
    const context = useContext(DashboardContext);
    if (!context) {
        throw new Error('useDashboard must be used within DashboardProvider');
    }
    return context;
};

interface DashboardProviderProps {
    children: ReactNode;
}

export const DashboardProvider: React.FC<DashboardProviderProps> = ({ children }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    
    // Restored Uncommitted IDE States
    const [hudData, setHudData] = useState<any>({ mood: 'neutral', projectProgress: 0, projectName: '', systemHealth: 100 });
    const [pendingDangerAction, setPendingDangerAction] = useState<any>(null);
    const [brainStatus, setBrainStatus] = useState<any>(null);
    const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
    const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
    const toggleLeftSidebar = () => setIsLeftSidebarOpen(!isLeftSidebarOpen);
    const toggleRightSidebar = () => setIsRightSidebarOpen(!isRightSidebarOpen);
    
    // Camera Vision States
    const [lastVisionAnalysis, setLastVisionAnalysis] = useState<any>(null);
    const [presenceData, setPresenceData] = useState<any>(null);

    const analyzeCameraFrame = (base64Image: string, prompt: string = "What do you see in this image?") => {
        if (socket && isConnected) {
            console.log('Sending frame for analysis...');
            socket.emit('analyze_image', { image: base64Image, prompt });
        }
    };

    const checkPresence = (base64Image: string) => {
        if (socket && isConnected) {
            socket.emit('analyze_presence', { image: base64Image });
        }
    };

    const [lastGesture, setLastGesture] = useState<any>(null);

    const checkGesture = (base64Image: string) => {
        if (socket && isConnected) {
            socket.emit('analyze_gesture', { image: base64Image });
        }
    };

    const setSidebarAutoState = (_state: any) => {}; // Placeholder if needed
    const [chatMessages, setChatMessages] = useState<Message[]>([]);
    const [isAITyping, setIsAITyping] = useState(false);
    const [voiceCommands, setVoiceCommands] = useState<VoiceCommand[]>([]);
    const [systemStats, setSystemStats] = useState<SystemStats>({
        cpu: 0,
        memory: 0,
        disk: 0,
        network: '0 MB/s',
    });
    const [systemStatsHistory, setSystemStatsHistory] = useState<SystemStatsPoint[]>([]);
    const [systemDetails, setSystemDetails] = useState<SystemDetailsDTO | null>(null);
    const [learningStats, setLearningStats] = useState<LearningStats>({
        database: '--',
        systems: '--',
        conversations: '--',
    });
    const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
    const [taskProgress, setTaskProgress] = useState(0);
    const [activeChains, setActiveChains] = useState<ChainDTO[]>([]);
    const activeChainsRef = useRef<ChainDTO[]>([]);
    const [chainHistory, setChainHistory] = useState<ChainDTO[]>([]);
    const chainHistoryRef = useRef<ChainDTO[]>([]);
    const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
    const selectedChainIdRef = useRef<string | null>(null);
    const [agents, setAgents] = useState<AgentDTO[]>([]);
    const [agentTasks, setAgentTasks] = useState<AgentTaskDTO[]>([]);
    const lastStreamChunkKeyRef = useRef<string>('');
    const [isVoiceActive, setIsVoiceActive] = useState(false);
    const [interimTranscript, setInterimTranscript] = useState('');
    const interimTranscriptRef = useRef(''); // Ref to access current transcript in simulation
    const [recognition, setRecognition] = useState<unknown>(null);
    const [voiceLanguage, setVoiceLanguageState] = useState(() => {
        return localStorage.getItem('voice_language') || 'hi-IN';
    });
    const [_isRecognitionStarted, _setIsRecognitionStarted] = useState(false);
    const accumulatedFinalTranscriptRef = useRef('');
    const transcriptTimeoutRef = useRef<any>(null);

    // MediaRecorder & Audio Context for Faster-Whisper
    const silenceTimerRef = useRef<any>(null);
    const [_userStoppedVoice, setUserStoppedVoice] = useState(false); // Track if user manually stopped
    const userStoppedRef = useRef(false); // Ref to track stop state without causing re-renders

    const [aiMode, setAIMode] = useState<'online' | 'offline'>('offline');
    const [aiProvider, setAIProviderState] = useState<'gemini' | 'openai' | 'gguf'>('gguf');
    const [aiModel, setAIModel] = useState<string>('pulsar-final-q4_k_m');
    const aiModeRef = useRef<'online' | 'offline'>('offline');
    const aiProviderRef = useRef<'gemini' | 'openai' | 'gguf'>('gguf');
    const aiModelRef = useRef<string>('pulsar-final-q4_k_m');

    const updateAIRefs = (
        provider: 'gemini' | 'openai' | 'gguf',
        model: string,
        mode?: 'online' | 'offline'
    ) => {
        const resolvedMode: 'online' | 'offline' =
            mode || (provider === 'gguf' ? 'offline' : 'online');
        aiProviderRef.current = provider;
        aiModelRef.current = model;
        aiModeRef.current = resolvedMode;
        setAIProviderState(provider);
        setAIModel(model);
        setAIMode(resolvedMode);
    };
    
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const isVoiceActiveRef = useRef(false); // Ref to track voice active state for reliable checks in handlers
    const ttsSpeakingRef = useRef(false); // TRUE while TTS is speaking + cooldown, prevents echo loop
    const [ttsEnabled, setTtsEnabled] = useState(true);
    const ttsEnabledRef = useRef(true);
    const [alwaysActive, setAlwaysActive] = useState(true); // Always-wake mode ON by default ("Hey Pulsar")
    const alwaysActiveRef = useRef(true);
    const requireWakeWordRef = useRef(true);
    const wakePhrasesRef = useRef<string[]>(DEFAULT_WAKE_PHRASES);
    const isProcessingCommandRef = useRef(false);
    const [remoteTtsSpeaking, setRemoteTtsSpeaking] = useState(false);
    const remoteTtsSpeakingRef = useRef(false);
    const wasRemoteTtsSpeakingRef = useRef(false);
    const isSpeaking = remoteTtsSpeaking;
    const [speakingLevel, setSpeakingLevel] = useState(0);
    const [orbError, setOrbError] = useState<string | null>(null);
    const [desktopOverlayEnabled, setDesktopOverlayEnabledState] = useState(true);
    const [isTranscribingVoice, setIsTranscribingVoice] = useState(false);
    const [wakePhrases, setWakePhrases] = useState<string[]>(DEFAULT_WAKE_PHRASES);
    const [appMinimized, setAppMinimized] = useState<boolean>(() =>
        typeof document !== 'undefined' ? document.visibilityState === 'hidden' : false
    );

    const orbErrorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const transcribeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const ttsCooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const lastOrbEmitTimeRef = useRef<number>(0);
    const lastEmittedOrbStateRef = useRef<OrbState>('idle');
    const seenFailedChainsRef = useRef<Set<string>>(new Set());

    const clearOrbError = () => {
        if (orbErrorTimerRef.current) {
            clearTimeout(orbErrorTimerRef.current);
            orbErrorTimerRef.current = null;
        }
        setOrbError(null);
    };

    const triggerOrbError = (msg?: string) => {
        if (orbErrorTimerRef.current) {
            clearTimeout(orbErrorTimerRef.current);
        }
        setOrbError(msg || 'Action failed');
        orbErrorTimerRef.current = setTimeout(() => {
            setOrbError(null);
            orbErrorTimerRef.current = null;
        }, 3600);
    };

    const setDesktopOverlayEnabled = (enabled: boolean) => {
        setDesktopOverlayEnabledState(enabled);
    };

    // Fetch Settings on Mount to sync Provider/Model, WakeWord, TTS, Language & Desktop Overlay
    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const response = await fetch(apiUrl('/api/settings/all'));
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.settings) {
                        const aiSettings = data.settings.ai;
                        if (aiSettings) {
                            const rawProv = String(aiSettings.defaultProvider || 'gguf').toLowerCase();
                            const normProv: 'gemini' | 'openai' | 'gguf' =
                                (rawProv === 'gemini' || rawProv === 'openai' || rawProv === 'gguf')
                                    ? rawProv
                                    : 'gguf';
                            const resolvedModel = String(
                                aiSettings.defaultModel || (normProv === 'gguf' ? 'pulsar-final-q4_k_m' : 'gemini-2.5-flash')
                            );
                            const newMode: 'online' | 'offline' =
                                normProv === 'gguf' ? 'offline' : 'online';
                            updateAIRefs(normProv, resolvedModel, newMode);
                            console.log(`🔄 Synced AI from settings: ${normProv} (${resolvedModel}) [${newMode}]`);
                        }

                        const sttCfg = data.settings.voice?.stt;
                        if (sttCfg) {
                            if (typeof sttCfg.continuous === 'boolean') {
                                setAlwaysActive(sttCfg.continuous);
                                alwaysActiveRef.current = sttCfg.continuous;
                            }
                            if (typeof sttCfg.language === 'string' && sttCfg.language.trim()) {
                                setVoiceLanguageState(sttCfg.language);
                                localStorage.setItem('voice_language', sttCfg.language);
                            }
                        }

                        const ttsCfg = data.settings.voice?.tts;
                        if (ttsCfg && typeof ttsCfg.enabled === 'boolean') {
                            setTtsEnabled(ttsCfg.enabled);
                            ttsEnabledRef.current = ttsCfg.enabled;
                        }

                        const wakeCfg = data.settings.voice?.wakeWord;
                        if (wakeCfg) {
                            if (typeof wakeCfg.enabled === 'boolean') {
                                setRequireWakeWord(wakeCfg.enabled);
                                requireWakeWordRef.current = wakeCfg.enabled;
                            }
                            if (Array.isArray(wakeCfg.phrases)) {
                                const merged = Array.from(
                                    new Set([
                                        ...wakeCfg.phrases.map((p: string) => String(p).trim().toLowerCase()).filter(Boolean),
                                        ...DEFAULT_WAKE_PHRASES,
                                    ])
                                );
                                setWakePhrases(merged);
                                wakePhrasesRef.current = merged;
                            }
                        }

                        if (typeof data.settings.system?.desktopOverlay === 'boolean') {
                            setDesktopOverlayEnabledState(data.settings.system.desktopOverlay);
                        }
                    }
                }
            } catch (error) {
                console.error("Failed to sync AI settings:", error);
            }
        };
        fetchSettings();
    }, []);

    // ... (keep existing code) ...

    // Unified Session & Activity Sync State + Refs
    const [currentSession, setCurrentSession] = useState<ConversationSession | null>(null);
    const [conversationHistory, setConversationHistory] = useState<ConversationSession[]>([]);
    const [sessionActivities, setSessionActivities] = useState<SessionActivity[]>([]);
    const sessionStartTimeRef = useRef<Date>(new Date());
    const chatMessagesRef = useRef<Message[]>([]);
    const voiceCommandsRef = useRef<VoiceCommand[]>([]);
    const sessionActivitiesRef = useRef<SessionActivity[]>([]);
    const currentSessionRef = useRef<ConversationSession | null>(null);
    const hasGreetedRef = useRef(false);

    const streamingMessageIdRef = useRef<string | null>(null);
    const lastBootIdRef = useRef<string | null>(
        typeof window !== 'undefined' ? localStorage.getItem('pulsar_last_boot_id') : null
    );
    const backendActiveSessionIdRef = useRef<string | null>(null);
    const seenMessageIdsRef = useRef<Set<string>>(new Set());
    const seenActivityIdsRef = useRef<Set<string>>(new Set());
    const [isViewingHistory, setIsViewingHistory] = useState<boolean>(false);
    const isViewingHistoryRef = useRef<boolean>(false);
    const nextLocalNumericIdRef = useRef<number>(Date.now());
    const syncInFlightRef = useRef<Promise<void> | null>(null);

    const setViewingHistory = (val: boolean) => {
        isViewingHistoryRef.current = val;
        setIsViewingHistory(val);
    };

    const makeClientMessageId = (prefix: string = 'cli'): string =>
        `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    const getNextNumericId = (): number => {
        const next = Math.max(Date.now(), nextLocalNumericIdRef.current + 1);
        nextLocalNumericIdRef.current = next;
        return next;
    };

    const formatClock12h = (d: Date = new Date()): string =>
        d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });

    const formatSessionDuration = (startTimestamp: number, endTimestamp: number): string => {
        const diff = Math.max(0, endTimestamp - startTimestamp);
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        if (hours > 0) {
            return `${hours}h ${minutes}m ${seconds}s`;
        }
        return `${minutes}m ${seconds}s`;
    };

    const extractMeaningfulPreview = (
        msgs: Message[],
        cmds: VoiceCommand[],
        acts: SessionActivity[] = []
    ): string => {
        const firstUserMsg = msgs.find(m => m.type === 'user' && m.text && m.text.trim().length > 0);
        if (firstUserMsg) return firstUserMsg.text.trim();
        if (cmds && cmds.length > 0 && cmds[0].command) {
            return cmds[0].command.trim();
        }
        const meaningfulAi = msgs.find(m => m.type === 'ai' && m.text &&
            !m.text.toLowerCase().includes('at your service') &&
            !m.text.toLowerCase().includes('all systems online') &&
            !m.text.toLowerCase().includes('ready for a new session')
        );
        if (meaningfulAi) return meaningfulAi.text.trim();
        const meaningfulAct = acts.find(
            a => a.kind !== 'session' && a.kind !== 'startup' && (a.detail || a.title)
        );
        if (meaningfulAct) return String(meaningfulAct.detail || meaningfulAct.title).trim();
        if (msgs.length > 0 && msgs[0].text) return msgs[0].text.trim();
        return 'Interactive Session';
    };

    const normalizeAndSortSessions = (rawSessions: any[]): ConversationSession[] => {
        if (!Array.isArray(rawSessions)) return [];
        return rawSessions.map(session => {
            let startTimestamp = session.startTimestamp;
            if (!startTimestamp && session.id && String(session.id).startsWith('session_')) {
                const parsed = parseInt(String(session.id).replace('session_', ''), 10);
                if (!isNaN(parsed) && parsed > 1000000000000) {
                    startTimestamp = parsed;
                }
            }
            if (!startTimestamp) {
                startTimestamp = Date.now();
            }

            const startDate = new Date(startTimestamp);
            const day = session.day || startDate.toLocaleDateString(undefined, { weekday: 'long' });
            const date = session.date || startDate.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
            const formattedDate = session.formattedDate || `${day}, ${date}`;
            const msgs = Array.isArray(session.messages) ? session.messages : [];
            const cmds = Array.isArray(session.voiceCommands) ? session.voiceCommands : [];
            const acts = Array.isArray(session.activities) ? session.activities : [];

            let preview = session.preview;
            if (!preview || preview.includes('At your service, Sir') || preview.includes('Ready for a new session')) {
                preview = extractMeaningfulPreview(msgs, cmds, acts);
            }

            let duration = session.duration;
            let endTimestamp = session.endTimestamp;
            if (session.endTimestamp && startTimestamp) {
                duration = formatSessionDuration(startTimestamp, session.endTimestamp);
            } else if (!duration || duration === 'Active' || duration === '0m 0s') {
                if (session.endTime && startTimestamp) {
                    try {
                        const parsedEnd = new Date(`${startDate.toDateString()} ${session.endTime}`);
                        if (!isNaN(parsedEnd.getTime()) && parsedEnd.getTime() >= startTimestamp) {
                            endTimestamp = parsedEnd.getTime();
                            duration = formatSessionDuration(startTimestamp, endTimestamp);
                        }
                    } catch { /* ignore invalid date */ }
                }
            }

            return {
                ...session,
                startTimestamp,
                endTimestamp: endTimestamp || session.endTimestamp,
                day,
                date,
                formattedDate,
                messages: msgs,
                voiceCommands: cmds,
                activities: acts,
                activityCount: session.activityCount ?? acts.length,
                preview: preview || 'Interactive Session',
                duration: duration || '0m 0s'
            };
        }).sort((a, b) => (b.startTimestamp || 0) - (a.startTimestamp || 0));
    };

    const upsertChatMessage = (incoming: {
        id?: number;
        message_id?: string;
        target_fallback_id?: string;
        type: 'user' | 'ai';
        text: string;
        time?: string;
        source?: string;
        isVoice?: boolean;
        provider?: string | null;
        model?: string | null;
        seq?: number;
        ts_ms?: number;
        chain_id?: string | null;
        agent_id?: string | null;
        agent_name?: string | null;
        orchestrated?: boolean;
        steps_completed?: number;
        total_steps?: number;
        actions?: ChainActionDTO[];
    }) => {
        const cleanText = String(incoming.text ?? '');
        const msgUid = incoming.message_id ? String(incoming.message_id).trim() : '';
        if (msgUid) {
            seenMessageIdsRef.current.add(msgUid);
        }
        const nowMs = incoming.ts_ms || Date.now();
        const nowTime = incoming.time || formatClock12h();

        setChatMessages(prev => {
            let matchIdx = -1;
            if (msgUid) {
                matchIdx = prev.findIndex(m => m.message_id === msgUid);
            }
            if (matchIdx < 0 && incoming.target_fallback_id) {
                matchIdx = prev.findIndex(m => m.message_id === incoming.target_fallback_id);
            }
            if (matchIdx >= 0) {
                const updated = [...prev];
                const cur = updated[matchIdx];
                updated[matchIdx] = {
                    ...cur,
                    message_id: msgUid || cur.message_id,
                    text: cleanText !== '' ? cleanText : cur.text,
                    time: incoming.time || cur.time,
                    source: incoming.source ?? cur.source,
                    isVoice: typeof incoming.isVoice === 'boolean' ? incoming.isVoice : cur.isVoice,
                    provider: incoming.provider ?? cur.provider,
                    model: incoming.model ?? cur.model,
                    seq: incoming.seq ?? cur.seq,
                    ts_ms: incoming.ts_ms ?? cur.ts_ms,
                    chain_id: incoming.chain_id ?? cur.chain_id,
                    agent_id: incoming.agent_id ?? cur.agent_id,
                    agent_name: incoming.agent_name ?? cur.agent_name,
                    orchestrated: incoming.orchestrated ?? cur.orchestrated,
                    steps_completed: incoming.steps_completed ?? cur.steps_completed,
                    total_steps: incoming.total_steps ?? cur.total_steps,
                    actions: incoming.actions ?? cur.actions,
                };
                return updated;
            }

            if (!msgUid && cleanText.trim()) {
                const trimmed = cleanText.trim();
                for (let i = prev.length - 1; i >= Math.max(0, prev.length - 3); i--) {
                    const candidate = prev[i];
                    if (
                        candidate.type === incoming.type &&
                        candidate.text.trim() === trimmed &&
                        Math.abs((candidate.ts_ms || nowMs) - nowMs) < 5000
                    ) {
                        const updated = [...prev];
                        updated[i] = {
                            ...candidate,
                            source: incoming.source ?? candidate.source,
                            isVoice: typeof incoming.isVoice === 'boolean' ? incoming.isVoice : candidate.isVoice,
                            chain_id: incoming.chain_id ?? candidate.chain_id,
                            agent_id: incoming.agent_id ?? candidate.agent_id,
                            agent_name: incoming.agent_name ?? candidate.agent_name,
                            orchestrated: incoming.orchestrated ?? candidate.orchestrated,
                            steps_completed: incoming.steps_completed ?? candidate.steps_completed,
                            total_steps: incoming.total_steps ?? candidate.total_steps,
                            actions: incoming.actions ?? candidate.actions,
                        };
                        return updated;
                    }
                }
            }

            return [
                ...prev,
                {
                    id: typeof incoming.id === 'number' ? incoming.id : getNextNumericId(),
                    type: incoming.type,
                    text: cleanText,
                    time: nowTime,
                    message_id: msgUid || undefined,
                    source: incoming.source,
                    isVoice: incoming.isVoice,
                    provider: incoming.provider,
                    model: incoming.model,
                    seq: incoming.seq,
                    ts_ms: nowMs,
                    chain_id: incoming.chain_id,
                    agent_id: incoming.agent_id,
                    agent_name: incoming.agent_name,
                    orchestrated: incoming.orchestrated,
                    steps_completed: incoming.steps_completed,
                    total_steps: incoming.total_steps,
                    actions: incoming.actions,
                },
            ];
        });
    };

    const appendVoiceCommandUnique = (incoming: {
        id?: number;
        message_id?: string;
        command: string;
        time?: string;
        source?: string;
        ts_ms?: number;
    }) => {
        const cleanCmd = String(incoming.command || '').trim();
        if (!cleanCmd) return;
        const msgUid = incoming.message_id ? String(incoming.message_id).trim() : '';
        const nowMs = incoming.ts_ms || Date.now();
        const nowTime = incoming.time || formatClock12h();

        setVoiceCommands(prev => {
            if (msgUid) {
                const idx = prev.findIndex(v => v.message_id === msgUid);
                if (idx >= 0) {
                    const updated = [...prev];
                    updated[idx] = {
                        ...updated[idx],
                        command: cleanCmd,
                        time: incoming.time || updated[idx].time,
                        source: incoming.source ?? updated[idx].source,
                    };
                    return updated;
                }
            }
            const dupRecent = prev.slice(0, 3).some(
                v => v.command.trim() === cleanCmd && Math.abs((v.ts_ms || nowMs) - nowMs) < 5000
            );
            if (dupRecent) return prev;
            return [
                {
                    id: typeof incoming.id === 'number' ? incoming.id : getNextNumericId(),
                    command: cleanCmd,
                    time: nowTime,
                    message_id: msgUid || undefined,
                    source: incoming.source,
                    ts_ms: nowMs,
                },
                ...prev.slice(0, 49),
            ];
        });
    };

    const appendActivityUnique = (act: SessionActivity) => {
        if (!act || !act.id) return;
        seenActivityIdsRef.current.add(act.id);
        setSessionActivities(prev => {
            const idx = prev.findIndex(a => a.id === act.id);
            if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...act };
                return updated;
            }
            return [...prev, act].slice(-500);
        });
    };

    const hydrateActiveSession = (rawSession: any) => {
        if (!rawSession) return;
        const baseMsgs: Message[] = Array.isArray(rawSession.messages) ? rawSession.messages : [];
        const baseMsgIds = new Set(baseMsgs.map(m => m.message_id).filter(Boolean));
        const nowMs = Date.now();
        const optimisticMsgs =
            rawSession.id === backendActiveSessionIdRef.current
                ? chatMessagesRef.current.filter(
                      m =>
                          m.message_id &&
                          /^(chat_user|recog_voice|google_voice|voice_user)_/.test(m.message_id) &&
                          (m.ts_ms || 0) >= nowMs - 15000 &&
                          !baseMsgIds.has(m.message_id)
                  )
                : [];
        const msgs: Message[] = optimisticMsgs.length > 0 ? [...baseMsgs, ...optimisticMsgs] : baseMsgs;

        const baseCmds: VoiceCommand[] = Array.isArray(rawSession.voiceCommands) ? rawSession.voiceCommands : [];
        const baseCmdIds = new Set(baseCmds.map(c => c.message_id).filter(Boolean));
        const optimisticCmds =
            rawSession.id === backendActiveSessionIdRef.current
                ? voiceCommandsRef.current.filter(
                      c =>
                          c.message_id &&
                          /^(recog_voice|google_voice|voice_user)_/.test(c.message_id) &&
                          (c.ts_ms || 0) >= nowMs - 15000 &&
                          !baseCmdIds.has(c.message_id)
                  )
                : [];
        const rawCmds: VoiceCommand[] = optimisticCmds.length > 0 ? [...baseCmds, ...optimisticCmds] : baseCmds;
        const acts: SessionActivity[] = Array.isArray(rawSession.activities) ? rawSession.activities : [];

        const cmdListNewestFirst = [...rawCmds].sort((a, b) => (b.ts_ms || b.id || 0) - (a.ts_ms || a.id || 0));

        seenMessageIdsRef.current.clear();
        for (const m of msgs) {
            if (m.message_id) seenMessageIdsRef.current.add(m.message_id);
        }
        seenActivityIdsRef.current.clear();
        for (const a of acts) {
            if (a.id) seenActivityIdsRef.current.add(a.id);
        }

        const normalizedSess: ConversationSession = {
            ...rawSession,
            messages: msgs,
            voiceCommands: cmdListNewestFirst,
            activities: acts,
            messageCount: rawSession.messageCount ?? msgs.length,
            userMessageCount: rawSession.userMessageCount ?? msgs.filter(m => m.type === 'user').length,
            aiMessageCount: rawSession.aiMessageCount ?? msgs.filter(m => m.type === 'ai').length,
            voiceCount: rawSession.voiceCount ?? cmdListNewestFirst.length,
            activityCount: rawSession.activityCount ?? acts.length,
        };

        setCurrentSession(normalizedSess);
        currentSessionRef.current = normalizedSess;
        setChatMessages(msgs);
        chatMessagesRef.current = msgs;
        setVoiceCommands(cmdListNewestFirst);
        voiceCommandsRef.current = cmdListNewestFirst;
        setSessionActivities(acts);
        sessionActivitiesRef.current = acts;
    };

    const syncWithBackendSession = (opts?: { triggerStartupGreetingIfEmpty?: boolean; force?: boolean }): Promise<void> => {
        const triggerGreeting = opts?.triggerStartupGreetingIfEmpty !== false;
        const force = Boolean(opts?.force);
        if (syncInFlightRef.current) {
            return syncInFlightRef.current.then(() => {
                if (force) {
                    return syncWithBackendSession({ triggerStartupGreetingIfEmpty: triggerGreeting, force: false });
                }
            });
        }

        const runSync = async () => {
            try {
                const [curRes, histRes] = await Promise.all([
                    fetch(apiUrl('/api/sessions/current')),
                    fetch(apiUrl('/api/sessions/history?limit=50')),
                ]);

                if (curRes.ok) {
                    const curJson = await curRes.json();
                    if (curJson?.success && curJson.session) {
                        const backendBootId = String(curJson.boot_id || curJson.session.boot_id || '').trim();
                        const prevSavedBootId = localStorage.getItem('pulsar_last_boot_id');
                        const isNewBoot = Boolean(backendBootId && prevSavedBootId !== backendBootId);

                        if (isNewBoot) {
                            localStorage.setItem('pulsar_last_boot_id', backendBootId);
                            lastBootIdRef.current = backendBootId;
                            setViewingHistory(false);
                            hasGreetedRef.current = false;
                            streamingMessageIdRef.current = null;
                            seenMessageIdsRef.current.clear();
                            seenActivityIdsRef.current.clear();
                        } else if (backendBootId) {
                            lastBootIdRef.current = backendBootId;
                        }

                        backendActiveSessionIdRef.current = curJson.session.id;

                        if (!isViewingHistoryRef.current || isNewBoot) {
                            hydrateActiveSession(curJson.session);
                        }

                        const existingMsgs = Array.isArray(curJson.session.messages) ? curJson.session.messages : [];
                        if (existingMsgs.length > 0) {
                            hasGreetedRef.current = true;
                        } else if (!hasGreetedRef.current && triggerGreeting) {
                            hasGreetedRef.current = true;
                            const fallbackBoot = [
                                'Online hoon Boss — sab systems ready hain, batayein kya karein?',
                                'All systems green, Boss. What is on the agenda?',
                                'Main Pulsar hoon, Boss — command dene ke liye ready.',
                            ];
                            const fallbackMsg = fallbackBoot[Math.floor(Math.random() * fallbackBoot.length)];
                            fetch(apiUrl('/api/voice/wake-ack'), {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    kind: 'startup',
                                    speak: false,
                                    source: 'webui_startup',
                                }),
                            })
                                .then((res) => (res.ok ? res.json() : null))
                                .then((ackData) => {
                                    const greeting = (ackData?.text || '').trim() || fallbackMsg;
                                    const targetSid = ackData?.session_id || curJson.session.id;
                                    if (!isViewingHistoryRef.current && backendActiveSessionIdRef.current === targetSid) {
                                        upsertChatMessage({
                                            text: greeting,
                                            type: 'ai',
                                            message_id: ackData?.message_id || `startup_${targetSid}`,
                                            source: 'webui_startup',
                                            isVoice: false,
                                        });
                                    }
                                })
                                .catch(() => {
                                    if (!isViewingHistoryRef.current) {
                                        upsertChatMessage({
                                            text: fallbackMsg,
                                            type: 'ai',
                                            message_id: `startup_${curJson.session.id}`,
                                            source: 'webui_startup',
                                            isVoice: false,
                                        });
                                    }
                                });
                        }
                    }
                }

                if (histRes.ok) {
                    const histJson = await histRes.json();
                    if (histJson?.success && Array.isArray(histJson.sessions)) {
                        const activeId = backendActiveSessionIdRef.current;
                        const filteredRaw = activeId
                            ? histJson.sessions.filter((s: any) => s.id !== activeId)
                            : histJson.sessions;
                        const normalized = normalizeAndSortSessions(filteredRaw);
                        setConversationHistory(normalized);
                        localStorage.setItem('conversationHistory', JSON.stringify(normalized.slice(0, 50)));
                    }
                }
            } catch (err) {
                console.warn('Could not sync sessions with backend:', err);
                if (!hasGreetedRef.current && chatMessagesRef.current.length === 0 && triggerGreeting) {
                    hasGreetedRef.current = true;
                    upsertChatMessage({
                        text: 'Online hoon Boss — sab systems ready hain, batayein kya karein?',
                        type: 'ai',
                        source: 'webui_startup_offline',
                        isVoice: false,
                    });
                }
            }
        };

        const p = runSync().finally(() => {
            syncInFlightRef.current = null;
        });
        syncInFlightRef.current = p;
        return p;
    };

    const upsertChainState = (rawChain: any) => {
        const normalized = normalizeChainDTO(rawChain);
        if (!normalized) return null;

        const isTerminal = ['completed', 'failed', 'cancelled'].includes(normalized.status);
        if (isTerminal) {
            const nextActive = activeChainsRef.current.filter(c => c.chain_id !== normalized.chain_id);
            activeChainsRef.current = nextActive;
            setActiveChains(nextActive);
            const avg = nextActive.length > 0
                ? Math.round(nextActive.reduce((acc, c) => acc + c.progress_percentage, 0) / nextActive.length)
                : normalized.progress_percentage;
            setTaskProgress(avg);

            const filteredHist = chainHistoryRef.current.filter(c => c.chain_id !== normalized.chain_id);
            const existingHist = chainHistoryRef.current.find(c => c.chain_id === normalized.chain_id)
                || activeChainsRef.current.find(c => c.chain_id === normalized.chain_id);
            const finalChain: ChainDTO = {
                ...normalized,
                actions: normalized.actions.length > 0 ? normalized.actions : (existingHist?.actions || []),
            };
            const nextHist = [finalChain, ...filteredHist].slice(0, 50);
            chainHistoryRef.current = nextHist;
            setChainHistory(nextHist);
        } else {
            const prevActive = activeChainsRef.current;
            const idx = prevActive.findIndex(c => c.chain_id === normalized.chain_id);
            const nextActive = idx >= 0
                ? prevActive.map((c, i) => (i === idx ? { ...c, ...normalized, actions: normalized.actions.length > 0 ? normalized.actions : c.actions } : c))
                : [normalized, ...prevActive];
            activeChainsRef.current = nextActive;
            setActiveChains(nextActive);
            const avg = nextActive.length > 0
                ? Math.round(nextActive.reduce((acc, c) => acc + c.progress_percentage, 0) / nextActive.length)
                : 0;
            setTaskProgress(avg);
        }

        if (normalized.requires_confirmation && normalized.action_id) {
            setPendingDangerAction({
                id: normalized.action_id,
                description: normalized.current_action || normalized.command || 'Action requires confirmation',
                chain_id: normalized.chain_id,
                source: 'chain',
            });
        }

        return normalized;
    };

    const applyChainEventDelta = (eventType: string, payload: any) => {
        if (!payload || typeof payload !== 'object') return;
        const inner = payload.data && typeof payload.data === 'object' ? { ...payload, ...payload.data } : payload;

        if (inner.chain || Array.isArray(inner.actions) || Array.isArray(inner.steps)) {
            const updated = upsertChainState(inner.chain || inner);
            if (updated) return;
        }

        const chainId = String(inner.chain_id || inner.id || '').trim();
        if (!chainId) return;

        const stepPayload = inner.action || inner.step;
        const stepId = String(inner.action_id || inner.step_id || stepPayload?.id || stepPayload?.action_id || '').trim();
        const stepIndex = typeof inner.step_index === 'number'
            ? inner.step_index
            : typeof inner.current_action_index === 'number'
            ? inner.current_action_index
            : undefined;

        const nextChainStatus =
            eventType === 'chain.started' || eventType === 'chain.resumed'
                ? 'executing'
                : eventType === 'chain.planned' || eventType === 'chain.decomposed'
                ? 'planning'
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
                : undefined;

        const applyUpdate = (existing?: ChainDTO): ChainDTO => {
            const base: ChainDTO = existing || {
                chain_id: chainId,
                id: chainId,
                command: String(inner.command || chainId),
                source: inner.source,
                status: nextChainStatus || 'executing',
                progress_percentage: typeof inner.progress_percentage === 'number'
                    ? inner.progress_percentage
                    : typeof inner.progress === 'number'
                    ? inner.progress
                    : 0,
                current_action_index: stepIndex ?? 0,
                current_action: inner.description || inner.current_action || null,
                current_agent: inner.agent_name || inner.agent_id || inner.current_agent || null,
                total_actions: Number(inner.total_actions || inner.total_steps || 0),
                actions_completed: Number(inner.actions_completed || inner.steps_completed || 0),
                actions_failed: Number(inner.actions_failed || 0),
                app_context: inner.app_context ?? null,
                actions: [],
                errors: [],
            };

            let updatedActions = [...base.actions];
            if (stepId || stepPayload || typeof stepIndex === 'number') {
                const targetIdx = updatedActions.findIndex(
                    (a, idx) => (stepId && a.id === stepId) || (typeof stepIndex === 'number' && idx === stepIndex)
                );
                const inferredStepStatus =
                    eventType === 'chain.step_started'
                        ? 'running'
                        : eventType === 'chain.step_completed'
                        ? 'completed'
                        : eventType === 'chain.step_failed'
                        ? 'failed'
                        : inner.step_status || stepPayload?.status
                        ? normalizeActionStatus(inner.step_status || stepPayload?.status)
                        : undefined;

                if (targetIdx >= 0) {
                    const prevStep = updatedActions[targetIdx];
                    updatedActions[targetIdx] = {
                        ...prevStep,
                        ...(stepPayload && typeof stepPayload === 'object' ? stepPayload : {}),
                        status: inferredStepStatus || prevStep.status,
                        agent_id: inner.agent_id ?? stepPayload?.agent_id ?? prevStep.agent_id,
                        agent_name: inner.agent_name ?? stepPayload?.agent_name ?? prevStep.agent_name,
                        result: inner.result !== undefined ? inner.result : prevStep.result,
                        output: inner.output !== undefined ? inner.output : prevStep.output,
                        error: inner.error !== undefined ? inner.error : prevStep.error,
                        verified:
                            eventType === 'chain.verification_completed'
                                ? Boolean(inner.verified ?? inner.success ?? true)
                                : prevStep.verified,
                        verification_result:
                            inner.verification_result ?? inner.verification ?? prevStep.verification_result,
                    };
                } else if (stepPayload) {
                    updatedActions = [
                        ...updatedActions,
                        {
                            id: stepId || `action_${updatedActions.length + 1}`,
                            type: String(stepPayload.type || inner.type || 'task'),
                            description: String(stepPayload.description || inner.description || 'Step'),
                            status: inferredStepStatus || 'running',
                            agent_id: inner.agent_id ?? stepPayload.agent_id ?? null,
                            agent_name: inner.agent_name ?? stepPayload.agent_name ?? null,
                        },
                    ];
                }
            }

            const merged = normalizeChainDTO({
                ...base,
                command: inner.command || base.command,
                status: nextChainStatus || base.status,
                progress_percentage:
                    typeof inner.progress_percentage === 'number'
                        ? inner.progress_percentage
                        : typeof inner.progress === 'number'
                        ? inner.progress
                        : base.progress_percentage,
                current_action_index: stepIndex ?? base.current_action_index,
                current_action: inner.description || inner.current_action || base.current_action,
                current_agent: inner.agent_name || inner.agent_id || inner.current_agent || base.current_agent,
                total_actions: inner.total_actions ?? inner.total_steps ?? Math.max(base.total_actions, updatedActions.length),
                actions_completed: inner.actions_completed ?? inner.steps_completed ?? base.actions_completed,
                actions_failed: inner.actions_failed ?? base.actions_failed,
                final_output: inner.final_output !== undefined ? inner.final_output : base.final_output,
                errors: Array.isArray(inner.errors) ? inner.errors : base.errors,
                actions: updatedActions,
            });
            return merged || base;
        };

        const existing =
            activeChainsRef.current.find(c => c.chain_id === chainId) ||
            chainHistoryRef.current.find(c => c.chain_id === chainId);
        const merged = applyUpdate(existing);
        upsertChainState(merged);

        if (merged.actions.length === 0 && eventType === 'chain.started') {
            apiFetchJson(API_ENDPOINTS.chains.detail(chainId)).then(res => {
                if (res.ok && res.data) {
                    upsertChainState(res.data);
                }
            });
        }
    };

    const refreshChains = useCallback(async () => {
        const [activeRes, historyRes] = await Promise.all([
            apiFetchJson<any>(API_ENDPOINTS.chains.active),
            apiFetchJson<any>(`${API_ENDPOINTS.chains.history}?limit=25`),
        ]);

        if (activeRes.ok && activeRes.data) {
            const rawList = Array.isArray(activeRes.data)
                ? activeRes.data
                : activeRes.data.chains || activeRes.data.active_chains || [];
            const normalized = rawList.map(normalizeChainDTO).filter((c: ChainDTO | null): c is ChainDTO => Boolean(c));
            activeChainsRef.current = normalized;
            setActiveChains(normalized);
            const avg = normalized.length > 0
                ? Math.round(normalized.reduce((acc: number, c: ChainDTO) => acc + c.progress_percentage, 0) / normalized.length)
                : 0;
            setTaskProgress(avg);
        }

        if (historyRes.ok && historyRes.data) {
            const rawHist = Array.isArray(historyRes.data)
                ? historyRes.data
                : historyRes.data.chains || historyRes.data.history || [];
            const normalizedHist = rawHist.map(normalizeChainDTO).filter((c: ChainDTO | null): c is ChainDTO => Boolean(c));
            chainHistoryRef.current = normalizedHist;
            setChainHistory(normalizedHist);
        }
    }, []);

    const refreshAgents = useCallback(async () => {
        const [agentsRes, tasksRes] = await Promise.all([
            apiFetchJson<any>(API_ENDPOINTS.agents.list),
            apiFetchJson<any>(API_ENDPOINTS.agents.tasks),
        ]);

        if (agentsRes.ok && agentsRes.data) {
            const rawAgents = Array.isArray(agentsRes.data)
                ? agentsRes.data
                : agentsRes.data.agents || [];
            setAgents(rawAgents.map(normalizeAgentDTO).filter((a: AgentDTO | null): a is AgentDTO => Boolean(a)));
        }

        if (tasksRes.ok && tasksRes.data) {
            const rawTasks = Array.isArray(tasksRes.data)
                ? tasksRes.data
                : tasksRes.data.tasks || [];
            setAgentTasks(rawTasks.map(normalizeAgentTaskDTO).filter((t: AgentTaskDTO | null): t is AgentTaskDTO => Boolean(t)));
        }
    }, []);

    const refreshSystemDetails = useCallback(async (): Promise<SystemDetailsDTO | null> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.system.details);
        if (res.ok && res.data) {
            const parsed = normalizeSystemDetailsDTO(res.data.details || res.data);
            setSystemDetails(parsed);
            return parsed;
        }
        return null;
    }, []);

    const openChainMonitor = (chainId?: string | null) => {
        if (chainId) {
            setSelectedChainId(chainId);
            selectedChainIdRef.current = chainId;
        }
        setSelectedView('agents');
    };

    const createAndRunChain = async (
        command: string,
        opts?: { autoExecute?: boolean; agentId?: string }
    ): Promise<ChainDTO | null> => {
        if (!command.trim()) return null;
        const curProvider = aiProviderRef.current;
        const curModel = aiModelRef.current;
        const curMode = aiModeRef.current;
        const useOfflineMode = curMode === 'offline' || curProvider === 'gguf';

        const res = await apiFetchJson<any>(API_ENDPOINTS.chains.create, {
            method: 'POST',
            body: JSON.stringify({
                command,
                source: 'webui_orchestrator',
                auto_execute: opts?.autoExecute !== false,
                agent_id: opts?.agentId || undefined,
                offline_mode: useOfflineMode,
                provider: curProvider,
                model: curModel,
            }),
        });

        if (res.ok && res.data) {
            const normalized = upsertChainState(res.data.chain || res.data);
            if (normalized) {
                setSelectedChainId(normalized.chain_id);
                selectedChainIdRef.current = normalized.chain_id;
                addSystemLog('info', `Chain started: ${normalized.chain_id}`);
                return normalized;
            }
        }
        addSystemLog('error', `Failed to start chain: ${res.error || 'Unknown error'}`);
        return null;
    };

    const pauseChain = async (chainId: string): Promise<boolean> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.chains.pause(chainId), { method: 'POST', body: '{}' });
        if (res.ok) {
            applyChainEventDelta('chain.paused', res.data?.chain || { chain_id: chainId, status: 'paused' });
            addSystemLog('info', `Paused chain ${chainId}`);
            return true;
        }
        return false;
    };

    const resumeChain = async (chainId: string, userInput?: string): Promise<boolean> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.chains.resume(chainId), {
            method: 'POST',
            body: JSON.stringify(userInput ? { user_input: userInput } : {}),
        });
        if (res.ok) {
            applyChainEventDelta('chain.resumed', res.data?.chain || { chain_id: chainId, status: 'executing' });
            addSystemLog('info', `Resumed chain ${chainId}`);
            return true;
        }
        return false;
    };

    const cancelChain = async (chainId: string): Promise<boolean> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.chains.cancel(chainId), { method: 'POST', body: '{}' });
        if (res.ok) {
            applyChainEventDelta('chain.cancelled', res.data?.chain || { chain_id: chainId, status: 'cancelled' });
            addSystemLog('warning', `Cancelled chain ${chainId}`);
            return true;
        }
        return false;
    };

    const emergencyStop = async (): Promise<boolean> => {
        if (socket && socket.connected) {
            socket.emit('emergency_stop', { source: 'webui' });
        }
        const [execRes, emergRes] = await Promise.all([
            apiFetchJson<any>(API_ENDPOINTS.chains.executiveStop, { method: 'POST', body: '{}' }),
            apiFetchJson<any>(API_ENDPOINTS.chains.emergencyStop, { method: 'POST', body: '{}' }),
        ]);
        const ok = execRes.ok || emergRes.ok || Boolean(socket?.connected);
        if (ok) {
            const stoppedChains = activeChainsRef.current.map(c => ({ ...c, status: 'cancelled' as const }));
            activeChainsRef.current = [];
            setActiveChains([]);
            if (stoppedChains.length > 0) {
                const stoppedIds = new Set(stoppedChains.map(c => c.chain_id));
                const nextHist = [
                    ...stoppedChains,
                    ...chainHistoryRef.current.filter(x => !stoppedIds.has(x.chain_id)),
                ].slice(0, 50);
                chainHistoryRef.current = nextHist;
                setChainHistory(nextHist);
            }
            setBrainStatus((prev: any) => (prev ? { ...prev, is_busy: false, active_chains: [] } : prev));
            setIsAITyping(false);
            setTaskProgress(0);
            addSystemLog('warning', 'Emergency stop triggered');
        }
        return ok;
    };

    const loadAgent = async (agentId: string): Promise<AgentDTO | null> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.agents.load(agentId), { method: 'POST', body: '{}' });
        if (res.ok && res.data) {
            const parsed = normalizeAgentDTO(res.data.agent || res.data);
            if (parsed) {
                setAgents(prev => {
                    const idx = prev.findIndex(a => a.id === parsed.id);
                    return idx >= 0 ? prev.map((a, i) => (i === idx ? parsed : a)) : [...prev, parsed];
                });
                addSystemLog('success', `Loaded agent ${parsed.name}`);
                return parsed;
            }
        }
        return null;
    };

    const dispatchAgentTask = async (
        command: string,
        opts?: { agentId?: string; asyncRun?: boolean }
    ): Promise<AgentTaskDTO | null> => {
        if (!command.trim()) return null;
        const curProvider = aiProviderRef.current;
        const curModel = aiModelRef.current;
        const useOfflineMode = aiModeRef.current === 'offline' || curProvider === 'gguf';

        const endpoint = opts?.agentId
            ? API_ENDPOINTS.agents.execute(opts.agentId)
            : API_ENDPOINTS.agents.dispatch;

        const res = await apiFetchJson<any>(endpoint, {
            method: 'POST',
            body: JSON.stringify({
                command,
                description: command,
                async: Boolean(opts?.asyncRun),
                offline_mode: useOfflineMode,
                provider: curProvider,
                model: curModel,
            }),
        });

        if (res.ok && res.data) {
            const parsed = normalizeAgentTaskDTO(res.data.task || res.data);
            if (parsed) {
                setAgentTasks(prev => [parsed, ...prev.filter(t => t.task_id !== parsed.task_id)].slice(0, 50));
            }
            if (res.data.requires_confirmation && res.data.action_id) {
                setPendingDangerAction({
                    id: res.data.action_id,
                    description: res.data.message || command,
                    source: 'agent',
                });
            }
            refreshAgents();
            return parsed;
        }
        addSystemLog('error', `Agent dispatch failed: ${res.error || 'Unknown error'}`);
        return null;
    };

    const cancelAgentTask = async (taskId: string): Promise<boolean> => {
        const res = await apiFetchJson<any>(API_ENDPOINTS.agents.cancelTask(taskId), { method: 'POST', body: '{}' });
        if (res.ok) {
            setAgentTasks(prev => prev.map(t => (t.task_id === taskId ? { ...t, status: 'cancelled' } : t)));
            addSystemLog('warning', `Cancelled agent task ${taskId}`);
            return true;
        }
        return false;
    };

    const sendCommand = (command: string, opts?: { agentId?: string }) => {
        if (!command.trim()) return;
        if (isViewingHistoryRef.current) {
            setViewingHistory(false);
            setChatMessages([]);
            chatMessagesRef.current = [];
            setVoiceCommands([]);
            voiceCommandsRef.current = [];
            setSessionActivities([]);
            sessionActivitiesRef.current = [];
            syncWithBackendSession({ triggerStartupGreetingIfEmpty: false });
        }

        const isStopCmd = isBargeInStopPhrase(command);
        if (isStopCmd) {
            stopBackendSpeech('chat_barge_in');
        }

        const clientMsgId = makeClientMessageId('chat_user');
        clearOrbError();
        streamingMessageIdRef.current = null;
        upsertChatMessage({
            text: command,
            type: 'user',
            message_id: clientMsgId,
            source: 'webui_chat',
            isVoice: false,
            agent_id: opts?.agentId || null,
        });
        setIsAITyping(!isStopCmd);
        addSystemLog('info', `Processing${opts?.agentId ? ` [${opts.agentId}]` : ''}: ${command}`);

        const curProvider = aiProviderRef.current;
        const curModel = aiModelRef.current;
        const curMode = aiModeRef.current;
        const useOfflineMode = curMode === 'offline' || curProvider === 'gguf';
        console.log(`🤖 AI Mode: ${curMode} | Provider: ${curProvider} | Model: ${curModel}`);

        if (opts?.agentId) {
            dispatchAgentTask(command, { agentId: opts.agentId })
                .then((task) => {
                    setIsAITyping(false);
                    if (!task) {
                        triggerOrbError('Agent task failed');
                        return;
                    }
                    const text =
                        typeof task.result === 'string'
                            ? task.result
                            : task.result?.output || task.result?.summary || task.result?.message || task.error || `Agent ${opts.agentId} finished task (${task.status}).`;
                    upsertChatMessage({
                        text: String(text),
                        type: 'ai',
                        source: 'agent_execute',
                        isVoice: false,
                        agent_id: opts.agentId,
                        agent_name: task.agent_name || undefined,
                    });
                })
                .catch(() => {
                    setIsAITyping(false);
                    triggerOrbError('Agent dispatch failed');
                });
            return;
        }

        if (socket && socket.connected) {
            console.log('📤 Sending command via socket:', command);
            socket.emit('command', {
                command,
                message: command,
                source: 'webui_chat',
                client_message_id: clientMsgId,
                offline_mode: useOfflineMode,
                provider: curProvider,
                model: curModel,
            });
        } else {
            // Fallback to API
            fetch(apiUrl('/api/command'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command,
                    source: 'webui_chat',
                    client_message_id: clientMsgId,
                    offline_mode: useOfflineMode,
                    provider: curProvider,
                    model: curModel,
                    speak: Boolean(ttsEnabledRef.current && alwaysActiveRef.current),
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    setIsAITyping(false);
                    if (data.success === false) {
                        triggerOrbError(data.error || data.response || 'Command failed');
                    }
                    if (data.chain) {
                        upsertChainState(data.chain);
                    } else if (data.chain_id) {
                        applyChainEventDelta('chain.started', data);
                    }
                    if (data.requires_confirmation && data.action_id) {
                        setPendingDangerAction({
                            id: data.action_id,
                            description: data.confirmation_description || data.response || command,
                            chain_id: data.chain_id,
                            source: 'http',
                        });
                    }
                    const response = data.response || data.message;
                    if (response) {
                        upsertChatMessage({
                            text: response,
                            type: 'ai',
                            message_id: data.message_id,
                            source: 'http_command',
                            isVoice: false,
                            provider: data.provider,
                            model: data.model,
                            chain_id: data.chain_id ?? null,
                            agent_id: data.agent_id ?? null,
                            agent_name: data.agent_name ?? null,
                            orchestrated: Boolean(data.orchestrated || data.chain_id),
                            steps_completed: data.steps_completed,
                            total_steps: data.total_steps,
                            actions: Array.isArray(data.actions) ? data.actions : undefined,
                        });
                    }

                    // Speak via unified backend TTS only if backend didn't already speak
                    if (response && ttsEnabledRef.current && alwaysActiveRef.current && !data.skip_tts) {
                        speak(response, voiceLanguage);
                    }
                })
                .catch((error) => {
                    setIsAITyping(false);
                    triggerOrbError('Error processing command');
                    console.error('API call error:', error);
                    const errorMsg = 'Error processing command. Please try again.';
                    upsertChatMessage({
                        text: errorMsg,
                        type: 'ai',
                        source: 'http_error',
                        isVoice: false,
                    });
                    if (ttsEnabledRef.current && alwaysActiveRef.current) {
                        speak(errorMsg, voiceLanguage);
                    }
                });
        }
    };

    // ... (keep existing code) ...

    const setAIProvider = (provider: 'gemini' | 'openai' | 'gguf') => {
        // Ensure aiModel matches the newly selected provider
        let targetModel = '';
        if (provider === 'gguf') targetModel = 'pulsar-final-q4_k_m';
        else if (provider === 'gemini') targetModel = 'gemini-2.5-flash';
        else if (provider === 'openai') targetModel = 'gpt-4o-mini';

        const newMode: 'online' | 'offline' =
            provider === 'gguf' ? 'offline' : 'online';
        updateAIRefs(provider, targetModel, newMode);

        if (newMode === 'offline') {
            addSystemLog('info', `🤖 Switched to GGUF (Offline)`);
        } else {
            const providerName = provider === 'gemini' ? 'Gemini' : 'OpenAI';
            addSystemLog('info', `🔷 Switched to ${providerName} (Online)`);
        }

        // Persist synchronously to backend settings so REST/SSE/Companion/voice stay 100% synced
        fetch(apiUrl('/api/settings/update'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: 'ai',
                settings: {
                    defaultProvider: provider,
                    defaultModel: targetModel,
                },
            }),
        }).catch((err) => {
            console.warn('Could not persist AI provider change:', err);
        });
    };

    // Expose setAIModel
    const setAIModelByName = (model: string) => {
        console.log(`🔄 Switching AI model to: ${model}`);
        aiModelRef.current = model;
        setAIModel(model);
        fetch(apiUrl('/api/settings/update'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: 'ai',
                settings: {
                    defaultProvider: aiProviderRef.current,
                    defaultModel: model,
                },
            }),
        }).catch((err) => {
            console.warn('Could not persist AI model change:', err);
        });
    };




    const [requireWakeWord, setRequireWakeWord] = useState(true); // Require wake word in always-active mode
    const [wakeWordDetected, setWakeWordDetected] = useState(false); // Wake word detection state
    const [isProcessingCommand, setIsProcessingCommand] = useState(false); // Processing command after wake word
    const [audioLevel, setAudioLevel] = useState(0); // Real-time audio level 0-100
    const [selectedView, setSelectedView] = useState<ViewType>(null); // Selected detail view
    const lastProcessedCommandRef = useRef<{ text: string, time: number } | null>(null); // Deduplication ref
    const socketRef = useRef<Socket | null>(null); // Ref for socket to avoid stale closures in listeners

    // Audio analysis refs
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const microphoneStreamRef = useRef<MediaStream | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    // SAFETY: Use a ref to hold the active recognition instance
    // This persists across re-renders and ensures we always clean up the *actual* active instance
     
    const activeRecognitionRef = useRef<any>(null);


    const [remoteOrbState, setRemoteOrbState] = useState<OrbState>('idle');
    const [remoteOrbAudioLevel, setRemoteOrbAudioLevel] = useState<number>(0);

    // Initialize Socket.IO connection
    useEffect(() => {
        const savedToken = localStorage.getItem('authToken') || localStorage.getItem('token');
        const initiallyHidden = typeof document !== 'undefined' ? document.visibilityState === 'hidden' : false;
        const newSocket = io(SOCKET_URL, {
            path: '/socket.io',
            query: { role: 'webui', minimized: initiallyHidden ? '1' : '0' },
            transports: ['polling', 'websocket'],
            withCredentials: true,
            auth: savedToken ? { token: savedToken } : {},
            autoConnect: true,
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
        });

        newSocket.on('connect', () => {
            console.log('Connected to backend');
            setIsConnected(true);
            addSystemLog('success', 'Connected to backend server');
            const isHidden = typeof document !== 'undefined' ? document.visibilityState === 'hidden' : false;
            setAppMinimized(isHidden);
            newSocket.emit('app_visibility', { minimized: isHidden });
            if (selectedChainIdRef.current) {
                newSocket.emit('subscribe_chain', { chain_id: selectedChainIdRef.current });
            }
            refreshChains();
            refreshAgents();
            refreshSystemDetails();
        });

        newSocket.on('connection_established', (data: any) => {
            const incomingBootId = String(data?.boot_id || '').trim();
            if (!lastBootIdRef.current || (incomingBootId && incomingBootId !== lastBootIdRef.current)) {
                syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
            } else if (data?.active_session_id && backendActiveSessionIdRef.current && data.active_session_id !== backendActiveSessionIdRef.current) {
                syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
            }
        });

        newSocket.on('session_started', (data: any) => {
            if (!data?.session) return;
            const incomingBootId = String(data.boot_id || data.session.boot_id || '').trim();
            if (incomingBootId) {
                localStorage.setItem('pulsar_last_boot_id', incomingBootId);
                lastBootIdRef.current = incomingBootId;
            }
            setViewingHistory(false);
            setIsAITyping(false);
            setIsTranscribingVoice(false);
            setInterimTranscript('');
            setWakeWordDetected(false);
            clearOrbError();
            streamingMessageIdRef.current = null;
            seenMessageIdsRef.current.clear();
            seenActivityIdsRef.current.clear();
            backendActiveSessionIdRef.current = data.session.id;
            hasGreetedRef.current = Boolean(data.session.messages?.length);
            hydrateActiveSession(data.session);
            fetch(apiUrl('/api/sessions/history?limit=50'))
                .then((res) => (res.ok ? res.json() : null))
                .then((histJson) => {
                    if (histJson?.success && Array.isArray(histJson.sessions)) {
                        const filtered = histJson.sessions.filter((s: any) => s.id !== data.session.id);
                        const normalized = normalizeAndSortSessions(filtered);
                        setConversationHistory(normalized);
                        localStorage.setItem('conversationHistory', JSON.stringify(normalized.slice(0, 50)));
                    }
                })
                .catch(() => {});
        });

        newSocket.on('session_event', (data: any) => {
            if (!data) return;
            if (data.boot_id && lastBootIdRef.current && data.boot_id !== lastBootIdRef.current) {
                syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
                return;
            }
            if (isViewingHistoryRef.current) {
                return;
            }
            if (data.session_id && backendActiveSessionIdRef.current && data.session_id !== backendActiveSessionIdRef.current) {
                return;
            }
            if (data.message) {
                const msg = data.message;
                const isAi = msg.type !== 'user';
                const targetFallback = isAi && streamingMessageIdRef.current ? streamingMessageIdRef.current : undefined;
                if (msg.source === 'webui_startup') {
                    hasGreetedRef.current = true;
                }
                upsertChatMessage({
                    id: typeof msg.id === 'number' ? msg.id : undefined,
                    message_id: msg.message_id || targetFallback,
                    target_fallback_id: targetFallback,
                    type: isAi ? 'ai' : 'user',
                    text: String(msg.text || ''),
                    time: msg.time,
                    source: msg.source,
                    isVoice: msg.isVoice,
                    provider: msg.provider,
                    model: msg.model,
                    seq: msg.seq,
                    ts_ms: msg.ts_ms,
                });
            }
            if (data.voice_command) {
                appendVoiceCommandUnique(data.voice_command);
            }
            if (data.activity) {
                appendActivityUnique(data.activity);
            }
            if (data.stats) {
                setCurrentSession(prev => prev ? {
                    ...prev,
                    messageCount: data.stats.messageCount ?? prev.messageCount,
                    userMessageCount: data.stats.userMessageCount ?? prev.userMessageCount,
                    aiMessageCount: data.stats.aiMessageCount ?? prev.aiMessageCount,
                    voiceCount: data.stats.voiceCount ?? prev.voiceCount,
                    activityCount: data.stats.activityCount ?? prev.activityCount,
                    endTime: data.stats.endTime ?? prev.endTime,
                    endTimestamp: data.stats.endTimestamp ?? prev.endTimestamp,
                    duration: data.stats.duration ?? prev.duration,
                    preview: data.stats.preview ?? prev.preview,
                } : prev);
            }
        });

        newSocket.on('connect_error', (err) => {
            console.warn('Socket.IO connection error:', err?.message || err);
        });

        newSocket.on('disconnect', () => {
            console.log('Disconnected from backend');
            setIsConnected(false);
            addSystemLog('error', 'Disconnected from backend server');
        });

        newSocket.on('overlay_config_updated', (data: any) => {
            if (typeof data?.enabled === 'boolean') {
                setDesktopOverlayEnabledState(data.enabled);
            }
        });

        newSocket.on('orb_state_sync', (data: any) => {
            if (!data || data.source === 'webui' || data.source === 'visibility') return;
            const nextState = data.state as OrbState;
            if (nextState && ['idle', 'listening', 'speaking', 'processing', 'error'].includes(nextState)) {
                setRemoteOrbState(nextState);
                if (nextState === 'idle') {
                    setRemoteOrbAudioLevel(0);
                    setIsTranscribingVoice(false);
                }
            }
            if (typeof data.audio_level === 'number') {
                setRemoteOrbAudioLevel(Math.max(0, Math.min(100, data.audio_level)));
            }
            if (typeof data.overlay_enabled === 'boolean') {
                setDesktopOverlayEnabledState(data.overlay_enabled);
            }
            if (typeof data.tts_speaking === 'boolean') {
                const ttsActive = data.tts_speaking;
                remoteTtsSpeakingRef.current = ttsActive;
                setRemoteTtsSpeaking(ttsActive);

                if (ttsActive) {
                    if (ttsCooldownTimerRef.current) {
                        clearTimeout(ttsCooldownTimerRef.current);
                        ttsCooldownTimerRef.current = null;
                    }
                    wasRemoteTtsSpeakingRef.current = true;
                    ttsSpeakingRef.current = true;
                    if (typeof data.audio_level === 'number') {
                        setSpeakingLevel(Math.max(0, Math.min(100, data.audio_level)));
                    }
                    // Pause Faster-Whisper MediaRecorder during backend TTS (SpeechRecognition stays open strictly for barge-in stop)
                    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                        try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
                    }
                } else {
                    setSpeakingLevel(0);
                    if (wasRemoteTtsSpeakingRef.current) {
                        wasRemoteTtsSpeakingRef.current = false;
                        if (ttsCooldownTimerRef.current) {
                            clearTimeout(ttsCooldownTimerRef.current);
                        }
                        ttsCooldownTimerRef.current = setTimeout(() => {
                            ttsCooldownTimerRef.current = null;
                            ttsSpeakingRef.current = false;
                            if (
                                alwaysActiveRef.current &&
                                !requireWakeWordRef.current &&
                                !userStoppedRef.current &&
                                !isVoiceActiveRef.current &&
                                typeof document !== 'undefined' &&
                                document.visibilityState !== 'hidden'
                            ) {
                                toggleVoice().catch((err) => {
                                    console.error('Error resuming continuous listening after backend TTS:', err);
                                });
                            }
                        }, 900);
                    }
                }
            }
        });

        newSocket.on('wake_word_status', (data: any) => {
            setIsTranscribingVoice(false);
            if (transcribeTimeoutRef.current) {
                clearTimeout(transcribeTimeoutRef.current);
                transcribeTimeoutRef.current = null;
            }
            if (data?.detected) {
                clearOrbError();
                setWakeWordDetected(true);
                setTimeout(() => setWakeWordDetected(false), 6000);
            }
        });

        newSocket.on('wake_word_detected', (data: any) => {
            clearOrbError();
            setWakeWordDetected(true);
            if (data?.wake_word) {
                addSystemLog('info', `Wake word heard: "${data.wake_word}"`);
            }
            setTimeout(() => setWakeWordDetected(false), 7000);
        });

        // Listen for live settings changes
        newSocket.on('settings_updated', async (data: any) => {
            console.log(`⚙️ Settings updated live: ${data.category}`, data);
            addSystemLog('info', `${data.category} settings updated`);

            const applySettingsSnapshot = (allSettings: any) => {
                if (!allSettings) return;
                if (allSettings.ai) {
                    const rawProv = String(allSettings.ai.defaultProvider || aiProviderRef.current || 'gguf').toLowerCase();
                    const provider: 'gemini' | 'openai' | 'gguf' =
                        (rawProv === 'gemini' || rawProv === 'openai' || rawProv === 'gguf')
                            ? rawProv
                            : 'gguf';
                    const newMode: 'online' | 'offline' =
                        provider === 'gguf' ? 'offline' : 'online';
                    const model = String(allSettings.ai.defaultModel || aiModelRef.current);
                    updateAIRefs(provider, model, newMode);
                }
                const sttCfg = allSettings.voice?.stt;
                if (sttCfg) {
                    if (typeof sttCfg.continuous === 'boolean') {
                        setAlwaysActive(sttCfg.continuous);
                        alwaysActiveRef.current = sttCfg.continuous;
                    }
                    if (typeof sttCfg.language === 'string' && sttCfg.language.trim()) {
                        setVoiceLanguageState(sttCfg.language);
                        localStorage.setItem('voice_language', sttCfg.language);
                    }
                }
                const ttsCfg = allSettings.voice?.tts;
                if (ttsCfg && typeof ttsCfg.enabled === 'boolean') {
                    setTtsEnabled(ttsCfg.enabled);
                    ttsEnabledRef.current = ttsCfg.enabled;
                }
                const wakeCfg = allSettings.voice?.wakeWord;
                if (wakeCfg) {
                    if (typeof wakeCfg.enabled === 'boolean') {
                        setRequireWakeWord(wakeCfg.enabled);
                        requireWakeWordRef.current = wakeCfg.enabled;
                    }
                    if (Array.isArray(wakeCfg.phrases)) {
                        const merged = Array.from(new Set([
                            ...wakeCfg.phrases.map((p: string) => String(p).trim().toLowerCase()).filter(Boolean),
                            ...DEFAULT_WAKE_PHRASES,
                        ]));
                        setWakePhrases(merged);
                        wakePhrasesRef.current = merged;
                    }
                }
                if (typeof allSettings.system?.desktopOverlay === 'boolean') {
                    setDesktopOverlayEnabledState(allSettings.system.desktopOverlay);
                }
            };

            if (data?.all_settings) {
                applySettingsSnapshot(data.all_settings);
                return;
            }
            if (data?.category === 'system' && typeof data?.settings?.desktopOverlay === 'boolean') {
                setDesktopOverlayEnabledState(data.settings.desktopOverlay);
            }
            if (data?.category === 'voice' && data?.settings?.tts && typeof data.settings.tts.enabled === 'boolean') {
                setTtsEnabled(data.settings.tts.enabled);
                ttsEnabledRef.current = data.settings.tts.enabled;
            }

            // Fallback: Re-fetch all settings to update local state
            try {
                const response = await fetch(apiUrl('/api/settings/all'));
                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.settings) {
                        applySettingsSnapshot(result.settings);
                    }
                }
            } catch (err) {
                console.error('Failed to sync settings live:', err);
            }
        });

        newSocket.on('navigate_view', (data: any) => {
            const targetView = data?.view as ViewType;
            const validViews: ViewType[] = [
                'dashboard', 'apps', 'chat', 'voice', 'settings',
                'ai-learning', 'database', 'systems', 'conversations', 'integrations',
                'agents', 'chains', 'orchestrator'
            ];
            if (targetView && validViews.includes(targetView)) {
                setSelectedView(targetView);
                addSystemLog('info', `Navigated to ${targetView} view via voice`);
            }
        });

         
        newSocket.on('command_response', (data: any) => {
            console.log('🔄 command_response received:', data);
            if (!data) return;
            if (data.session_id && backendActiveSessionIdRef.current && data.session_id !== backendActiveSessionIdRef.current) {
                return;
            }

            if (data.chain) {
                upsertChainState(data.chain);
            } else if (data.chain_id) {
                applyChainEventDelta(
                    data.success === false ? 'chain.failed' : 'chain.started',
                    data
                );
            }

            if (data.requires_confirmation && data.action_id) {
                setPendingDangerAction({
                    id: data.action_id,
                    description: data.confirmation_description || data.response || data.message || 'Confirm action',
                    chain_id: data.chain_id,
                    source: 'command',
                });
            }

            if (data.success && ['executing', 'running', 'queued'].includes(String(data.brain_action || ''))) {
                setIsAITyping(true);
                if (data.pre_report || data.response) {
                    setInterimTranscript(String(data.pre_report || data.response));
                }
                return;
            }

            if (data.is_wake_ack) {
                setIsAITyping(false);
                setIsTranscribingVoice(false);
                if (transcribeTimeoutRef.current) {
                    clearTimeout(transcribeTimeoutRef.current);
                    transcribeTimeoutRef.current = null;
                }
                if (data.response) {
                    const ackTxt = String(data.response);
                    setInterimTranscript(ackTxt);
                    setTimeout(() => {
                        setInterimTranscript(prev => (prev === ackTxt ? '' : prev));
                    }, 2500);
                } else {
                    setInterimTranscript('');
                }
                return;
            }

            setIsAITyping(false);
            setIsTranscribingVoice(false);
            setWakeWordDetected(false);
            if (transcribeTimeoutRef.current) {
                clearTimeout(transcribeTimeoutRef.current);
                transcribeTimeoutRef.current = null;
            }
            setInterimTranscript('');

            const targetStreamId = streamingMessageIdRef.current;
            streamingMessageIdRef.current = null;

            if (data.success) {
                clearOrbError();
                const message = String(data.response || data.message || '').trim();
                if (message && !isViewingHistoryRef.current) {
                    upsertChatMessage({
                        text: message,
                        type: 'ai',
                        message_id: data.message_id || targetStreamId || undefined,
                        target_fallback_id: targetStreamId || undefined,
                        source: data.source || 'command_response',
                        isVoice: false,
                        provider: data.provider,
                        model: data.model,
                        chain_id: data.chain_id ?? null,
                        agent_id: data.agent_id ?? null,
                        agent_name: data.agent_name ?? null,
                        orchestrated: Boolean(data.orchestrated || data.chain_id),
                        steps_completed: data.steps_completed,
                        total_steps: data.total_steps,
                        actions: Array.isArray(data.actions) ? data.actions : undefined,
                    });
                }

                // Backend owns all voice output; only speak via /api/voice/speak when skip_tts isn't already set
                if (message && ttsEnabledRef.current && data.source !== 'companion_voice' && !data.skip_tts) {
                    speak(message, voiceLanguage);
                }
            } else {
                const rawErr = String(data.error || data.response || 'Unknown error');
                const errorMsg = rawErr.startsWith('Error:') ? rawErr : 'Error: ' + rawErr;
                triggerOrbError(rawErr);
                if (!isViewingHistoryRef.current) {
                    upsertChatMessage({
                        text: errorMsg,
                        type: 'ai',
                        message_id: data.message_id || targetStreamId || undefined,
                        target_fallback_id: targetStreamId || undefined,
                        source: data.source || 'error',
                        isVoice: false,
                        provider: data.provider,
                        model: data.model,
                        chain_id: data.chain_id ?? null,
                        agent_id: data.agent_id ?? null,
                        agent_name: data.agent_name ?? null,
                    });
                }
                if (ttsEnabledRef.current && !data.skip_tts) {
                    speak(errorMsg, voiceLanguage);
                }
            }
        });

        newSocket.on('command_status', (data: any) => {
            if (!data) return;
            const phase = String(data.phase || '');
            const statusText = String(data.status || '').trim();
            if (phase === 'pre_report' && statusText) {
                setInterimTranscript(statusText);
                addSystemLog('info', statusText);
            } else if (phase === 'proactive_update' && statusText) {
                addSystemLog('success', statusText);
            } else if (phase === 'completed' || phase === 'failed' || phase === 'cancelled') {
                setInterimTranscript('');
            }
        });

        newSocket.on('hud_update', (data: any) => {
            if (!data || typeof data !== 'object') return;
            setHudData({
                mood: data.mood ?? 'neutral',
                projectName: data.projectName ?? data.project_name ?? '',
                projectProgress: Number(data.projectProgress ?? data.project_progress ?? 0),
                systemHealth: Number(data.systemHealth ?? data.system_health ?? 100),
                pendingTask: data.pendingTask ?? data.pending_task ?? '',
                activeModel: data.activeModel ?? data.active_model ?? '',
                ...data,
            });
        });

        newSocket.on('brain_status', (data: any) => {
            setBrainStatus(data);
            if (Array.isArray(data?.active_chains)) {
                for (const chain of data.active_chains) {
                    if (chain?.chain_id) {
                        const existing = activeChainsRef.current.find(c => c.chain_id === chain.chain_id);
                        upsertChainState({
                            ...existing,
                            ...chain,
                            actions: existing?.actions?.length ? existing.actions : chain.actions,
                        });
                    }
                    if (chain?.status === 'failed' && chain?.chain_id && !seenFailedChainsRef.current.has(chain.chain_id)) {
                        seenFailedChainsRef.current.add(chain.chain_id);
                        triggerOrbError(`Task failed: ${chain.command || chain.chain_id}`);
                    }
                }
            }
        });

        // Chain Orchestration Real-time Events
        const chainEventNames = [
            'chain_progress',
            'chain.started',
            'chain.planned',
            'chain.decomposed',
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
        chainEventNames.forEach((evtName) => {
            newSocket.on(evtName, (payload: any) => {
                const resolvedType = payload?.event_type || evtName;
                applyChainEventDelta(resolvedType, payload);
                if (resolvedType === 'chain.failed' && payload?.chain_id) {
                    triggerOrbError(`Chain failed: ${payload.error || payload.chain_id}`);
                    addSystemLog('error', `Chain failed (${payload.chain_id})`);
                } else if (resolvedType === 'chain.completed' && payload?.chain_id) {
                    addSystemLog('success', `Chain completed (${payload.chain_id})`);
                }
            });
        });

        // Multi-Agent Lifecycle Events
        newSocket.on('agents_snapshot', (payload: any) => {
            const rawAgents = Array.isArray(payload) ? payload : payload?.agents || [];
            if (Array.isArray(rawAgents)) {
                setAgents(rawAgents.map(normalizeAgentDTO).filter((a: AgentDTO | null): a is AgentDTO => Boolean(a)));
            }
        });

        newSocket.on('agent.status_changed', (payload: any) => {
            if (!payload || typeof payload !== 'object') return;
            const agentId = String(payload.agent_id || payload.id || '').trim();
            if (!agentId) return;
            const parsed = normalizeAgentDTO({ id: agentId, ...payload });
            if (!parsed) return;
            setAgents(prev => {
                const idx = prev.findIndex(a => a.id === agentId);
                if (idx >= 0) {
                    return prev.map((a, i) => (i === idx ? { ...a, ...parsed, capabilities: parsed.capabilities.length ? parsed.capabilities : a.capabilities, description: parsed.description || a.description } : a));
                }
                return [...prev, parsed];
            });
        });

        ['agent.task_started', 'agent.task_completed', 'agent.task_failed'].forEach((evtName) => {
            newSocket.on(evtName, (payload: any) => {
                if (!payload || typeof payload !== 'object') return;
                const status =
                    evtName === 'agent.task_started'
                        ? 'running'
                        : evtName === 'agent.task_completed'
                        ? 'completed'
                        : 'failed';
                const taskDto = normalizeAgentTaskDTO({
                    task_id: payload.task_id || payload.id || `task_${Date.now()}`,
                    status,
                    ...payload,
                });
                if (taskDto) {
                    setAgentTasks(prev => [taskDto, ...prev.filter(t => t.task_id !== taskDto.task_id)].slice(0, 50));
                }
                if (payload.agent_id) {
                    setAgents(prev => prev.map(a => {
                        if (a.id !== payload.agent_id) return a;
                        const isStart = evtName === 'agent.task_started';
                        return {
                            ...a,
                            status: isStart ? 'busy' : 'idle',
                            active_tasks: isStart ? a.active_tasks + 1 : Math.max(0, a.active_tasks - 1),
                            completed_tasks: evtName === 'agent.task_completed' ? a.completed_tasks + 1 : a.completed_tasks,
                            failed_tasks: evtName === 'agent.task_failed' ? a.failed_tasks + 1 : a.failed_tasks,
                            current_task: isStart ? (payload.description || taskDto?.description || null) : null,
                        };
                    }));
                }
            });
        });

        newSocket.on('danger_action_pending', (data: any) => setPendingDangerAction(data));
        newSocket.on('danger_action_resolved', () => setPendingDangerAction(null));
        
        newSocket.on('system_stats_update', (stats: any) => {
            const cpuVal = Math.round(stats.cpu_usage || 0);
            const memVal = Math.round(stats.memory_usage || 0);
            const diskVal = Math.round(stats.disk_usage || 0);
            setSystemStats({
                cpu: cpuVal,
                memory: memVal,
                disk: diskVal,
                network: stats.network_speed ? `${(stats.network_speed / 1024 / 1024).toFixed(1)} MB/s` : '0 MB/s',
            });
            setSystemStatsHistory(prev => [
                ...prev.slice(-23),
                {
                    time: formatClock12h(),
                    cpu: cpuVal,
                    memory: memVal,
                    disk: diskVal,
                },
            ]);
        });

         
        newSocket.on('log_update', (log: any) => {
            addSystemLog(log.type || 'info', log.message);
        });

         
        newSocket.on('learning_stats_update', (stats: any) => {
            setLearningStats(prev => ({
                database: stats.database || '--',
                systems: stats.systems || '--',
                conversations: stats.conversations || '--',
                details: stats.details ?? prev.details,
            }));
        });

        // Vision Analysis Handlers
        newSocket.on('image_analysis_response', (data: any) => {
            console.log('Vision analysis received:', data);
            setLastVisionAnalysis(data);
            if (data.analysis && data.analysis.description) {
                addChatMessage(`I see: ${data.analysis.description}`, 'ai');
            }
        });

        newSocket.on('image_analysis_error', (data: any) => {
            console.error('Vision analysis error:', data);
            addSystemLog('error', `Vision error: ${data.error}`);
        });

        newSocket.on('presence_update', (data: any) => {
            console.log('Presence update:', data);
            setPresenceData(data);
        });

        newSocket.on('gesture_detected', (data: any) => {
            console.log('Gesture detected:', data.gesture);
            setLastGesture(data);
            
            // Map gestures to actions
            if (data.gesture === 'STOP') {
                stopBackendSpeech('gesture_stop');
            } else if (data.gesture === 'MUTE_MIC') {
                setIsVoiceActive(false);
            } else if (data.gesture === 'SWIPE_LEFT' || data.gesture === 'SWIPE_RIGHT') {
                setSelectedView((prev: ViewType) => {
                    const views: ViewType[] = ['chat', 'systems', 'conversations', 'settings'];
                    const safePrev = prev === 'dashboard' || prev === null ? 'chat' : prev;
                    const currentIndex = views.indexOf(safePrev);
                    if (currentIndex === -1) return 'chat';
                    
                    if (data.gesture === 'SWIPE_LEFT') {
                        return views[(currentIndex + 1) % views.length];
                    } else {
                        return views[(currentIndex - 1 + views.length) % views.length];
                    }
                });
            } else if (data.gesture === 'THUMBS_UP') {
                setPendingDangerAction((prev: any) => {
                    if (prev && newSocket) {
                        newSocket.emit('authorize_action', { id: prev.id });
                    }
                    return null;
                });
            } else if (data.gesture === 'THUMBS_DOWN') {
                setPendingDangerAction((prev: any) => {
                    if (prev && newSocket) {
                        newSocket.emit('cancel_action', { id: prev.id });
                    }
                    return null;
                });
            }
        });

        // Handle voice command responses with talkback
         
        newSocket.on('voice_transcript', (data: any) => {
            console.log(' Voice transcript received:', data);
            setIsTranscribingVoice(false);
            if (transcribeTimeoutRef.current) {
                clearTimeout(transcribeTimeoutRef.current);
                transcribeTimeoutRef.current = null;
            }
            if (data?.text && !isViewingHistoryRef.current) {
                setInterimTranscript(''); // Clear the 'Processing with Whisper...' text
                const msgId = data.message_id ? String(data.message_id) : undefined;
                const src = String(data.source || 'webui_voice');
                upsertChatMessage({
                    text: data.text,
                    type: 'user',
                    message_id: msgId,
                    source: src,
                    isVoice: true,
                });
                appendVoiceCommandUnique({
                    command: data.text,
                    message_id: msgId,
                    source: src,
                });
                setIsAITyping(true);
            }
        });
        newSocket.on('voice_response', (data: any) => {
            console.log('🎤 Voice response received:', data);
            setIsAITyping(false);
            setIsTranscribingVoice(false);
            setWakeWordDetected(false);
            if (transcribeTimeoutRef.current) {
                clearTimeout(transcribeTimeoutRef.current);
                transcribeTimeoutRef.current = null;
            }
            setInterimTranscript('');
            streamingMessageIdRef.current = null;

            if (data.success && data.response) {
                clearOrbError();
                if (!isViewingHistoryRef.current) {
                    upsertChatMessage({
                        text: data.response,
                        type: 'ai',
                        message_id: data.message_id,
                        source: data.source || 'voice_response',
                        isVoice: false,
                    });
                }

                // Backend owns TTS playback unless caller didn't trigger it yet
                if (!data.skip_tts) {
                    speak(data.response, voiceLanguage);
                }

                addSystemLog('success', `Command processed: ${data.response.substring(0, 50)}...`);
            } else if (data.error) {
                const errorMsg = data.response || 'Sorry, I encountered an error processing that command.';
                triggerOrbError(errorMsg);
                if (!isViewingHistoryRef.current) {
                    upsertChatMessage({
                        text: errorMsg,
                        type: 'ai',
                        message_id: data.message_id,
                        source: 'voice_error',
                        isVoice: false,
                    });
                }
                if (!data.skip_tts) {
                    speak(errorMsg, voiceLanguage);
                }
                addSystemLog('error', errorMsg);
            }
        });

        const handleStreamChunk = (data: any) => {
            if (!data || isViewingHistoryRef.current) return;
            if (data.session_id && backendActiveSessionIdRef.current && data.session_id !== backendActiveSessionIdRef.current) return;
            const streamId = String(data.stream_id || '').trim() || streamingMessageIdRef.current || makeClientMessageId('stream_ai');
            if (data.chunk_index !== undefined) {
                const chunkKey = `${streamId}:${data.chunk_index}`;
                if (lastStreamChunkKeyRef.current === chunkKey) return;
                lastStreamChunkKeyRef.current = chunkKey;
            }
            if (data.is_start) {
                setIsAITyping(false);
                streamingMessageIdRef.current = streamId;
                upsertChatMessage({
                    text: String(data.token || ''),
                    type: 'ai',
                    message_id: streamId,
                    source: 'stream',
                    isVoice: false,
                    provider: data.provider,
                    model: data.model,
                });
            } else {
                const token = String(data.token || '');
                const targetId = streamingMessageIdRef.current || streamId;
                streamingMessageIdRef.current = targetId;
                setChatMessages(prev => {
                    const idx = prev.findIndex(m => m.message_id === targetId);
                    if (idx >= 0) {
                        const updated = [...prev];
                        updated[idx] = {
                            ...updated[idx],
                            text: updated[idx].text + token,
                        };
                        return updated;
                    }
                    return [
                        ...prev,
                        {
                            id: getNextNumericId(),
                            type: 'ai',
                            text: token,
                            time: formatClock12h(),
                            message_id: targetId,
                            source: 'stream',
                            isVoice: false,
                            provider: data.provider,
                            model: data.model,
                            ts_ms: Date.now(),
                        },
                    ];
                });
            }
        };

        newSocket.on('chat_stream_chunk', handleStreamChunk);
        newSocket.on('chat_token', handleStreamChunk);
        newSocket.on('chat_complete', (data: any) => {
            setIsAITyping(false);
            if (data?.response && !isViewingHistoryRef.current) {
                const targetId = streamingMessageIdRef.current || data.stream_id || data.message_id;
                upsertChatMessage({
                    text: String(data.response),
                    type: 'ai',
                    message_id: data.message_id || targetId || undefined,
                    target_fallback_id: targetId || undefined,
                    source: 'stream',
                    isVoice: false,
                    provider: data.provider,
                    model: data.model,
                    chain_id: data.chain_id ?? null,
                    agent_id: data.agent_id ?? null,
                    agent_name: data.agent_name ?? null,
                });
            }
            streamingMessageIdRef.current = null;
        });

        newSocket.on('chat_stream_end', (data: any) => {
            if (data?.session_id && backendActiveSessionIdRef.current && data.session_id !== backendActiveSessionIdRef.current) {
                return;
            }
            setIsAITyping(false);
            streamingMessageIdRef.current = null;
        });


        // Google Speech Recognition handlers
         
        newSocket.on('google_ready', (data: any) => {
            console.log('≡ƒîÉ Google Speech Recognition ready:', data);
            addSystemLog('success', `Online recognition enabled (${data.language})`);
        });

         
        newSocket.on('google_transcript', (data: any) => {
            console.log('🌐 Google transcript:', data);
            if (data.isFinal && data.text) {
                setInterimTranscript('');
                if (isViewingHistoryRef.current) {
                    setViewingHistory(false);
                    setChatMessages([]);
                    chatMessagesRef.current = [];
                    setVoiceCommands([]);
                    voiceCommandsRef.current = [];
                    setSessionActivities([]);
                    sessionActivitiesRef.current = [];
                    syncWithBackendSession({ triggerStartupGreetingIfEmpty: false });
                }
                const clientMsgId = makeClientMessageId('google_voice');
                streamingMessageIdRef.current = null;
                upsertChatMessage({
                    text: data.text,
                    type: 'user',
                    message_id: clientMsgId,
                    source: 'google_voice',
                    isVoice: true,
                });
                appendVoiceCommandUnique({
                    command: data.text,
                    message_id: clientMsgId,
                    source: 'google_voice',
                });
                setIsAITyping(true);
                // Process as voice command using latest refs so provider/model switches always take effect
                const curProvider = aiProviderRef.current;
                const curModel = aiModelRef.current;
                const curOffline = aiModeRef.current === 'offline' || curProvider === 'gguf';
                newSocket.emit('voice_command', {
                    text: data.text,
                    source: 'google_voice',
                    client_message_id: clientMsgId,
                    language: voiceLanguage,
                    offline_mode: curOffline,
                    provider: curProvider,
                    model: curModel,
                });
            } else {
                setInterimTranscript(data.text);
                interimTranscriptRef.current = data.text;
            }
        });

         
        newSocket.on('google_error', (data: any) => {
            console.error('❌ Google Speech error:', data);
            triggerOrbError(`Online recognition error: ${data?.error || 'Failed'}`);
            addSystemLog('error', `Online recognition error: ${data.error}`);
        });

        setSocket(newSocket);
        socketRef.current = newSocket; // Update ref

        return () => {
            if (ttsCooldownTimerRef.current) {
                clearTimeout(ttsCooldownTimerRef.current);
                ttsCooldownTimerRef.current = null;
            }
            newSocket.close();
            socketRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Initialize Voice Recognition
    useEffect(() => {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
             
            const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            const recog = new SpeechRecognition();
            recog.continuous = true;  // Keep listening continuously
            recog.interimResults = true; // Enable interim results for real-time transcription

            // Handle language selection - browser doesn't support "auto" as language code
            if (voiceLanguage === 'auto') {
                // Use browser's default language or Hindi as fallback
                recog.lang = navigator.language || 'hi-IN';
                console.log(`≡ƒîÉ Auto-detect: Using language ${recog.lang}`);
            } else {
                recog.lang = voiceLanguage;
                console.log(`≡ƒîÉ Using selected language: ${recog.lang}`);
            }
            // Cleanup previous instance if it exists
            if (activeRecognitionRef.current) {
                console.log('≡ƒº╣ Aborting previous recognition instance');
                try {
                    activeRecognitionRef.current.abort();
                    activeRecognitionRef.current.onend = null; // Prevent restart loops from old instance
                } catch (e) {
                    console.warn('Error aborting previous recognition:', e);
                }
            }

            // Set as active instance
            activeRecognitionRef.current = recog;

            recog.onstart = () => {
                console.log('≡ƒÄñ Voice recognition started');
                console.log('   Language:', recog.lang);
                console.log('   Continuous:', recog.continuous);
                console.log('   Interim Results:', recog.interimResults);
                console.log('   Max Alternatives:', recog.maxAlternatives);

                // Only set active if user didn't manually stop (use ref to avoid stale state)
                if (!userStoppedRef.current) {
                    setIsVoiceActive(true);
                    isVoiceActiveRef.current = true; // Sync ref
                    setInterimTranscript('');
                    _setIsRecognitionStarted(true);

                    // Start audio level monitoring immediately
                    console.log('≡ƒÄº Initiating audio level monitoring...');
                    startAudioLevelMonitoring().catch(err => {
                        console.error('Γ¥î Audio monitoring failed:', err);
                        console.log('≡ƒôè Falling back to simulated audio levels');
                        simulateAudioLevel();
                    });
                } else {
                    console.log('ΓÜá∩╕Å Recognition started but user stopped - stopping immediately');
                    _setIsRecognitionStarted(false);
                    recog.stop();
                }
            };

             
            recog.onresult = (event: any) => {
                // Check if this instance is still the active one
                if (activeRecognitionRef.current !== recog) {
                    console.log('≡ƒ¢æ Ghost listener detected - ignoring result from stale instance');
                    return;
                }

                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        final += transcript;
                    } else {
                        interim += transcript;
                    }
                }

                // PREVENT FEEDBACK LOOP (ECHO) WHILE ALLOWING EXPLICIT BARGE-IN STOP PHRASES
                const candidateStopText = (final || interim).trim();
                if (ttsSpeakingRef.current || remoteTtsSpeakingRef.current) {
                    if (isBargeInStopPhrase(candidateStopText)) {
                        console.log('Voice Barge-In Stop Triggered during TTS:', candidateStopText);
                        stopBackendSpeech('voice_fast_stop');
                        setInterimTranscript('');
                        interimTranscriptRef.current = '';
                        accumulatedFinalTranscriptRef.current = '';
                        if (transcriptTimeoutRef.current) clearTimeout(transcriptTimeoutRef.current);
                    }
                    return;
                }

                console.log('≡ƒÄ» Recognition event received:', {
                    resultIndex: event.resultIndex,
                    resultsLength: event.results.length,
                    isFinal: event.results[event.resultIndex]?.isFinal
                });

                // Combine accumulated final with new interim
                const fullInterim = accumulatedFinalTranscriptRef.current
                    ? accumulatedFinalTranscriptRef.current + (interim ? ' ' + interim : '')
                    : interim;

                if (fullInterim) {
                    console.log('≡ƒÆ¼ Setting interim transcript:', fullInterim);
                    setInterimTranscript(fullInterim);
                    interimTranscriptRef.current = fullInterim; // Update ref for simulation
                } else {
                    console.log('ΓÜá∩╕Å No interim text');
                }

                // Reset timer whenever there is speech (interim or final)
                if (transcriptTimeoutRef.current) {
                    clearTimeout(transcriptTimeoutRef.current);
                }

                // Process final result
                if (final) {
                    // FAST STOP: Intercept stop commands client-side for zero latency
                    if (isBargeInStopPhrase(final)) {
                        console.log('Fast Stop Triggered:', final);
                        stopBackendSpeech('voice_fast_stop');
                        setInterimTranscript('');
                        interimTranscriptRef.current = '';
                        accumulatedFinalTranscriptRef.current = '';
                        if (transcriptTimeoutRef.current) clearTimeout(transcriptTimeoutRef.current);
                        return;
                    }

                    if (accumulatedFinalTranscriptRef.current) {
                        accumulatedFinalTranscriptRef.current += ' ' + final;
                    } else {
                        accumulatedFinalTranscriptRef.current = final;
                    }

                    // Update UI to show the accumulated text as interim until it's sent
                    setInterimTranscript(accumulatedFinalTranscriptRef.current);
                    interimTranscriptRef.current = accumulatedFinalTranscriptRef.current;
                }

                if (accumulatedFinalTranscriptRef.current) {
                    transcriptTimeoutRef.current = setTimeout(() => {
                        const commandToSend = accumulatedFinalTranscriptRef.current.trim();
                        accumulatedFinalTranscriptRef.current = '';

                        console.log('Γ£à Final transcript (accumulated):', commandToSend);
                        setInterimTranscript('');
                        interimTranscriptRef.current = ''; // Clear ref

                        // Deduplication check
                        const now = Date.now();

                        // Check Global Variable (protects against duplicate listeners/instances)
                        if (globalLastCommandInfo.text === commandToSend && (now - globalLastCommandInfo.time) < 2000) {
                            console.log('≡ƒÜ½ Global duplicate command ignored:', commandToSend);
                            return;
                        }

                        // Check Local Ref (standard check)
                        if (lastProcessedCommandRef.current &&
                            lastProcessedCommandRef.current.text === commandToSend &&
                            (now - lastProcessedCommandRef.current.time) < 2000) {
                            console.log('≡ƒÜ½ Local duplicate command ignored:', commandToSend);
                            return;
                        }

                        // Update both
                        lastProcessedCommandRef.current = { text: commandToSend, time: now };
                        globalLastCommandInfo = { text: commandToSend, time: now };

                        // Always-active mode with wake word requirement
                        const isAlwaysOn = alwaysActiveRef.current;
                        const needWake = requireWakeWordRef.current;
                        const isProcCmd = isProcessingCommandRef.current;
                        let finalVoiceCommand = commandToSend;

                        if (isAlwaysOn && needWake && !isProcCmd) {
                            const activeWakeWords = wakePhrasesRef.current;
                            const escapedWakes = [...activeWakeWords]
                                .filter(Boolean)
                                .sort((a, b) => b.length - a.length)
                                .map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
                            const prefixWakeRegex = escapedWakes.length > 0
                                ? new RegExp(
                                    `^\\s*(?:${escapedWakes.join('|')})(?=$|[\\s,.:;!?।\\-])(?:[\\s,.:;!?।-]+)?(.*)$`,
                                    'iu'
                                )
                                : null;
                            const anywhereWakeRegex = escapedWakes.length > 0
                                ? new RegExp(
                                    `^.*?(?:^|[\\s,.:;!?।\\-])(${escapedWakes.join('|')})(?=$|[\\s,.:;!?।\\-])[\\s,.:;!?।-]*(.*)$`,
                                    'iu'
                                )
                                : null;
                            const prefixMatch = prefixWakeRegex ? commandToSend.match(prefixWakeRegex) : null;
                            const anyMatch = !prefixMatch && anywhereWakeRegex ? commandToSend.match(anywhereWakeRegex) : null;
                            const detectedWake = prefixMatch
                                ? prefixMatch[0].trim()
                                : (anyMatch ? anyMatch[1].trim() : null);

                            if (detectedWake) {
                                console.log('Wake word detected:', detectedWake);
                                clearOrbError();
                                setWakeWordDetected(true);

                                const strippedInline = ((prefixMatch ? prefixMatch[1] : anyMatch?.[2]) || '').trim();

                                if (strippedInline) {
                                    // Execute inline command spoken right after wake word (e.g. "Hey Pulsar open YouTube")
                                    finalVoiceCommand = strippedInline;
                                } else {
                                    setIsProcessingCommand(true);
                                    isProcessingCommandRef.current = true;

                                    // Request a dynamic non-repeating wake acknowledgment from backend persona
                                    const fallbackAcks = [
                                        'Haan Boss, sun rahi hoon — bolo.',
                                        'Ji Boss, batayein?',
                                        'Ready hoon Boss, kya kaam hai?',
                                        'Listening, Boss.',
                                        'Bolo Boss, kya karwana hai?',
                                    ];
                                    const offlineAck = fallbackAcks[Math.floor(Math.random() * fallbackAcks.length)];
                                    fetch(apiUrl('/api/voice/wake-ack'), {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                            wake_word: detectedWake,
                                            raw_transcript: commandToSend,
                                            kind: 'wake',
                                            speak: Boolean(ttsEnabledRef.current),
                                            wait: false,
                                            source: 'webui_wake',
                                        }),
                                    })
                                        .then((res) => (res.ok ? res.json() : null))
                                        .then((data) => {
                                            const reply = (data?.text || '').trim() || offlineAck;
                                            if (!(data?.queued || data?.spoken) && ttsEnabledRef.current) {
                                                speak(reply, voiceLanguage);
                                            }
                                        })
                                        .catch(() => {
                                            if (ttsEnabledRef.current) {
                                                speak(offlineAck, voiceLanguage);
                                            }
                                        });

                                    // Reset after 10 seconds if no command given
                                    setTimeout(() => {
                                        if (isProcessingCommandRef.current) {
                                            setIsProcessingCommand(false);
                                            isProcessingCommandRef.current = false;
                                            setWakeWordDetected(false);
                                        }
                                    }, 10000);
                                    return;
                                }
                            } else {
                                // In wake word mode, ignore commands without wake word
                                console.log('Skipping - waiting for wake word');
                                return;
                            }
                        }

                        // Process command directly (no wake word required or wake word detected)
                        const shouldProcess = !isAlwaysOn || !needWake || isProcCmd || finalVoiceCommand !== commandToSend;

                        if (shouldProcess) {
                            const dispatchedCommand = finalVoiceCommand;
                            console.log('Processing voice command:', dispatchedCommand);
                            clearOrbError();
                            if (isViewingHistoryRef.current) {
                                setViewingHistory(false);
                                setChatMessages([]);
                                chatMessagesRef.current = [];
                                setVoiceCommands([]);
                                voiceCommandsRef.current = [];
                                setSessionActivities([]);
                                sessionActivitiesRef.current = [];
                                syncWithBackendSession({ triggerStartupGreetingIfEmpty: false });
                            }
                            const clientMsgId = makeClientMessageId('recog_voice');
                            streamingMessageIdRef.current = null;
                            upsertChatMessage({
                                text: dispatchedCommand,
                                type: 'user',
                                message_id: clientMsgId,
                                source: 'webui_voice',
                                isVoice: true,
                            });
                            appendVoiceCommandUnique({
                                command: dispatchedCommand,
                                message_id: clientMsgId,
                                source: 'webui_voice',
                            });
                            setIsAITyping(true);

                            // Send via socket for voice command processing, using REFs to avoid stale closures
                            const currentSocket = socketRef.current;
                            const curProvider = aiProviderRef.current;
                            const curModel = aiModelRef.current;
                            const curMode = aiModeRef.current;
                            const curOffline = curMode === 'offline' || curProvider === 'gguf';

                            if (currentSocket && currentSocket.connected) {
                                console.log('Sending voice_command event to backend:', dispatchedCommand);
                                console.log(`Voice AI Mode: ${curMode} | Provider: ${curProvider} | Model: ${curModel}`);
                                currentSocket.emit('voice_command', {
                                    text: dispatchedCommand,
                                    source: 'webui_voice',
                                    client_message_id: clientMsgId,
                                    language: voiceLanguage,
                                    timestamp: new Date().toISOString(),
                                    offline_mode: curOffline,
                                    provider: curProvider,
                                    model: curModel
                                });
                                console.log('voice_command emitted successfully');
                            } else {
                                console.warn('Socket not connected, using direct fallback');

                                // Log processing
                                addSystemLog('info', `Processing Voice: ${dispatchedCommand}`);

                                fetch(apiUrl('/api/command'), {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        command: dispatchedCommand,
                                        source: 'webui_voice',
                                        client_message_id: clientMsgId,
                                        speak: Boolean(ttsEnabledRef.current),
                                        offline_mode: curOffline,
                                        provider: curProvider,
                                        model: curModel
                                    }),
                                })
                                    .then((res) => res.json())
                                    .then((data) => {
                                        setIsAITyping(false);
                                        if (data.success === false) {
                                            triggerOrbError(data.error || data.response || 'Voice command failed');
                                        }
                                        const response = data.response || data.message;
                                        if (response) {
                                            upsertChatMessage({
                                                text: response,
                                                type: 'ai',
                                                message_id: data.message_id,
                                                source: 'http_voice_command',
                                                isVoice: false,
                                                provider: data.provider,
                                                model: data.model,
                                            });
                                        }
                                        if (response && !data.skip_tts) {
                                            speak(response, voiceLanguage);
                                        }
                                    })
                                    .catch((error) => {
                                        setIsAITyping(false);
                                        triggerOrbError('Error processing voice command');
                                        console.error('API call error:', error);
                                        const errorMsg = 'Error processing command. Please try again.';
                                        upsertChatMessage({
                                            text: errorMsg,
                                            type: 'ai',
                                            source: 'http_voice_error',
                                            isVoice: false,
                                        });
                                        speak(errorMsg, voiceLanguage);
                                    });
                            }

                            // Reset processing state after command
                            if (needWake) {
                                setTimeout(() => {
                                    setIsProcessingCommand(false);
                                    isProcessingCommandRef.current = false;
                                    setWakeWordDetected(false);
                                }, 1000);
                            }
                        }
                    }, 2000); // End of debouncing setTimeout
                } // End of if (accumulatedFinalTranscriptRef.current)
            };

             
            recog.onerror = (event: any) => {
                console.error('≡ƒÜ¿ Speech recognition error:', event.error);

                // Ignore 'aborted' errors during normal stop
                if (event.error === 'aborted') {
                    console.log('Recognition aborted (normal during stop)');
                    return;
                }

                // Temporary errors - just log, continuous mode will handle it
                if (event.error === 'no-speech') {
                    // console.log('ΓÜá∩╕Å No speech detected, continuous mode will continue...');
                    return;
                }

                if (event.error === 'audio-capture') {
                    console.error('Audio capture error - microphone issue');
                    triggerOrbError('Microphone audio capture error');
                    // Don't try to restart, let the user handle it
                    return;
                }

                // Critical errors - stop listening
                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    console.error('Microphone access denied');
                    triggerOrbError('Microphone access denied');
                    alert('Microphone access denied. Please allow microphone access in your browser settings.');
                    setIsVoiceActive(false);
                    isVoiceActiveRef.current = false;
                    setInterimTranscript('');
                    setUserStoppedVoice(true);
                    userStoppedRef.current = true;
                    return;
                }

                // Network errors
                if (event.error === 'network') {
                    console.error('≡ƒîÉ Network error during recognition');
                    return;
                }

                // Language not supported
                if (event.error === 'language-not-supported') {
                    console.error('Language not supported:', voiceLanguage);
                    triggerOrbError(`Language "${voiceLanguage}" is not supported`);
                    alert(`Language "${voiceLanguage}" is not supported. Please select a different language.`);
                    setIsVoiceActive(false);
                    isVoiceActiveRef.current = false;
                    return;
                }

                // Other errors - just log
                console.error('Other recognition error:', event.error);
            };

            recog.onend = () => {
                console.log('⏳ Recognition ended, current state:', isVoiceActiveRef.current, 'userStopped:', userStoppedRef.current);
                _setIsRecognitionStarted(false);

                // Stop audio monitoring when recognition ends
                stopAudioLevelMonitoring();

                // Only restart if:
                // 1. User hasn't manually stopped
                // 2. Voice is still supposed to be active
                // 3. Not in always-active mode (which handles its own lifecycle)
                if (!userStoppedRef.current && isVoiceActiveRef.current && !alwaysActiveRef.current) {
                    console.log('🔄 Recognition ended unexpectedly, restarting in 1000ms...');
                    setTimeout(() => {
                        // Echo prevention: don't restart mic while TTS is speaking or in cooldown
                        if (ttsSpeakingRef.current) {
                            console.log('🔇 Skipping recognition restart — TTS still speaking/cooling down');
                            return;
                        }
                        if (!userStoppedRef.current && isVoiceActiveRef.current && recog) {
                            try {
                                recog.start();
                                console.log('✅ Recognition restarted');
                                 
                            } catch (error: any) {
                                if (!error.message?.includes('already started')) {
                                    console.error('❌ Failed to restart:', error);
                                    setIsVoiceActive(false);
                                    isVoiceActiveRef.current = false;
                                }
                            }
                        }
                    }, 1000);
                } else {
                    console.log('🚫 Not restarting - userStopped:', userStoppedRef.current, 'active:', isVoiceActiveRef.current, 'alwaysActive:', alwaysActiveRef.current);
                    if (!alwaysActiveRef.current) {
                        setIsVoiceActive(false);
                        isVoiceActiveRef.current = false;
                        setInterimTranscript('');
                    }
                }
            };

            setRecognition(recog);
            console.log('✅ Voice recognition initialized (not started)');

            return () => {
                console.log('🧹 Cleanup: component unmounting or language changing');
                if (activeRecognitionRef.current) {
                    const oldRecog = activeRecognitionRef.current;
                    oldRecog.onstart = null;
                    oldRecog.onresult = null;
                    oldRecog.onerror = null;
                    oldRecog.onend = null;
                    try {
                        oldRecog.abort();
                        console.log('✅ Stopped active recognition instance');
                    } catch (e) {
                        // ignore errors on abort
                    }
                    activeRecognitionRef.current = null;
                }
            };
        }
    }, [voiceLanguage]); // Only re-initialize when language changes (userStoppedRef used to prevent re-initialization)

    // Audio Level Monitoring Functions
    const startAudioLevelMonitoring = async () => {
        console.log('Starting real-time audio level monitoring...');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            microphoneStreamRef.current = stream;

            const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            const audioContext = new AudioCtx();

            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            const analyser = audioContext.createAnalyser();
            const microphone = audioContext.createMediaStreamSource(stream);

            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = 0.45;
            analyser.minDecibels = -90;
            analyser.maxDecibels = -10;
            microphone.connect(analyser);

            audioContextRef.current = audioContext;
            analyserRef.current = analyser;

            analyzeAudioLevel();
        } catch (error) {
            console.warn('Microphone analyser unavailable, falling back to simulated audio levels:', error);
            simulateAudioLevel();
        }
    };

    const analyzeAudioLevel = () => {
        if (!analyserRef.current) {
            console.warn('No analyser available for audio level monitoring');
            return;
        }

        const analyser = analyserRef.current;
        const bufferLength = analyser.frequencyBinCount;
        const freqArray = new Uint8Array(bufferLength);
        const timeArray = new Uint8Array(analyser.fftSize);
        let smoothedLevel = 0;
        let lastUiUpdate = 0;

        const updateLevel = () => {
            if (!analyserRef.current || !isVoiceActiveRef.current) {
                console.log('Stopping audio level monitoring');
                return;
            }

            analyser.getByteFrequencyData(freqArray);
            analyser.getByteTimeDomainData(timeArray);

            // Time-domain RMS tracks speech dynamics directly with zero lag
            let tdSum = 0;
            for (let i = 0; i < timeArray.length; i++) {
                const v = (timeArray[i] - 128) / 128;
                tdSum += v * v;
            }
            const tdRms = Math.sqrt(tdSum / timeArray.length);

            let freqSum = 0;
            for (let i = 0; i < bufferLength; i++) {
                const normalized = freqArray[i] / 255;
                freqSum += normalized * normalized;
            }
            const freqRms = Math.sqrt(freqSum / bufferLength);

            const tdLevel = Math.max(0, (tdRms - 0.012) * 340);
            const freqLevel = Math.max(0, (freqRms - 0.03) * 190);
            const instantLevel = Math.min(100, Math.max(tdLevel, freqLevel));

            // Fast attack, smooth decay
            const alpha = instantLevel > smoothedLevel ? 0.48 : 0.22;
            smoothedLevel = smoothedLevel * (1 - alpha) + instantLevel * alpha;

            const now = performance.now();
            if (now - lastUiUpdate >= 30) {
                lastUiUpdate = now;
                setAudioLevel(Math.round(smoothedLevel));
            }

            animationFrameRef.current = requestAnimationFrame(updateLevel);
        };

        console.log('Starting audio level animation loop');
        updateLevel();
    };

    const simulateAudioLevel = () => {
        // Simulate realistic audio level when real monitoring unavailable
        let isSpeaking = false;
        let speakingStartTime = 0;

        const simulate = () => {
            if (!isVoiceActiveRef.current) {
                return;
            }

            const now = Date.now();

            // Check if there's actual speech (transcript is being generated)
            const hasTranscript = interimTranscriptRef.current.length > 0;

            // Random speaking bursts every 2-4 seconds when no transcript
            if (!hasTranscript && !isSpeaking && Math.random() > 0.98) {
                isSpeaking = true;
                speakingStartTime = now;
            }

            // Speaking duration: 1-3 seconds
            if (isSpeaking && (now - speakingStartTime) > (1000 + Math.random() * 2000)) {
                isSpeaking = false;
            }

            let level;
            if (hasTranscript || isSpeaking) {
                // Simulate speech with varying amplitude
                const baseLevel = 45;
                const variation = 25;
                const frequency = 0.015; // Faster oscillation for speech
                const noise = (Math.random() - 0.5) * 15; // Add randomness
                level = baseLevel + Math.sin(now * frequency) * variation + noise;
            } else {
                // Low ambient level when silent
                const baseLevel = 12;
                const variation = 8;
                const frequency = 0.005; // Slower oscillation
                level = baseLevel + Math.sin(now * frequency) * variation;
            }

            setAudioLevel(Math.max(0, Math.min(100, level)));

            animationFrameRef.current = requestAnimationFrame(simulate);
        };

        console.log('🎧 Using simulated audio levels (visual feedback mode)');
        simulate();
    };

    const stopAudioLevelMonitoring = () => {
        // Cancel animation frame
        if (animationFrameRef.current) {
            try {
                cancelAnimationFrame(animationFrameRef.current);
            } catch (e) { /* empty */ }
            animationFrameRef.current = null;
        }

        // Stop microphone stream
        if (microphoneStreamRef.current) {
            microphoneStreamRef.current.getTracks().forEach(track => track.stop());
            microphoneStreamRef.current = null;
        }

        // Close audio context
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        analyserRef.current = null;
        setAudioLevel(0);
        console.log('🛑 Audio level monitoring stopped');
    };

    // Load Learning Stats
    useEffect(() => {
        const loadLearningStats = async () => {
            try {
                const response = await fetch(apiUrl(API_ENDPOINTS.learning.all_stats));
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        const sizeDisplay =
                            typeof data.total_size_mb === 'number'
                                ? data.total_size_mb >= 1024 * 1024
                                    ? `${(data.total_size_mb / 1024 / 1024).toFixed(1)}TB`
                                    : data.total_size_mb >= 1024
                                    ? `${(data.total_size_mb / 1024).toFixed(1)}GB`
                                    : `${data.total_size_mb.toFixed(1)}MB`
                                : '--';
                        const totalSystems = data.total_systems ?? 27;
                        const systems =
                            data.active_systems !== undefined
                                ? `${data.active_systems}/${totalSystems}`
                                : '--';
                        const convs =
                            typeof data.total_conversations === 'number'
                                ? data.total_conversations >= 1000
                                    ? `${(data.total_conversations / 1000).toFixed(1)}K`
                                    : String(data.total_conversations)
                                : '--';

                        setLearningStats({
                            database: sizeDisplay,
                            systems,
                            conversations: convs,
                            details: data.details,
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to load learning stats:', error);
            }
        };

        loadLearningStats();
    }, []);

    // Stats simulation removed - show real data only when connected
    // When disconnected, stats will just not update (last known values shown)
    useEffect(() => {
        // intentionally empty - fake stats removed
    }, [socket]);

    const addChatMessage = (text: string, type: 'user' | 'ai') => {
        upsertChatMessage({
            text,
            type,
            source: 'local',
            isVoice: false,
        });
    };

    const addVoiceCommand = (command: string) => {
        appendVoiceCommandUnique({
            command,
            source: 'local_voice',
        });
    };

    const addSystemLog = (type: 'info' | 'success' | 'warning' | 'error', message: string) => {
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });

        setSystemLogs((prev) => [
            {
                id: Date.now() + Math.random(),
                type,
                message,
                time,
            },
            ...prev.slice(0, 49), // Keep only last 50
        ]);
    };



    const setVoiceLanguage = (lang: string) => {
        console.log(`🌐 Changing language to: ${lang}`);
        setVoiceLanguageState(lang);

        // Simply update the language property - recognition will use it on next start
        if (recognition) {
            (recognition as any).lang = lang;
            console.log(`✅ Language updated to: ${lang}`);
        }

        // Note: We don't restart recognition here to avoid restart loops
        // The new language will be used when user starts/restarts recognition manually
    };

    const toggleVoice = async () => {
        if (isVoiceActive) {
            console.log('🚫 Stopping voice recording');
            setUserStoppedVoice(true);
            userStoppedRef.current = true;
            setIsVoiceActive(false);
            isVoiceActiveRef.current = false;
            _setIsRecognitionStarted(false);
            setInterimTranscript('');
            setAudioLevel(0);

            if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = null;
            }
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                try { mediaRecorderRef.current.stop(); } catch { /* empty */ }
            }
            if (microphoneStreamRef.current) {
                try {
                    microphoneStreamRef.current.getTracks().forEach(track => track.stop());
                } catch { /* empty */ }
                microphoneStreamRef.current = null;
            }
            if (audioContextRef.current) {
                try { audioContextRef.current.close(); } catch { /* empty */ }
                audioContextRef.current = null;
            }
            analyserRef.current = null;
            if (activeRecognitionRef.current) {
                try { activeRecognitionRef.current.stop(); } catch { /* empty */ }
            }
        } else {
            // User explicitly requested recording — unlock mic and cancel any ongoing backend speech (barge-in)
            clearOrbError();
            stopBackendSpeech('mic_toggle_start');

            setUserStoppedVoice(false);
            userStoppedRef.current = false;

            if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = null;
            }

            // ALWAYS use backend Faster-Whisper for voice transcription, regardless of LLM provider
            // eslint-disable-next-line no-constant-condition
            if (true) {
                console.log('▶️ Starting voice recording (MediaRecorder for Faster Whisper)');
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    microphoneStreamRef.current = stream;

                    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
                    const audioCtx = new AudioCtx();
                    if (audioCtx.state === 'suspended') {
                        await audioCtx.resume();
                    }
                    audioContextRef.current = audioCtx;

                    const source = audioCtx.createMediaStreamSource(stream);
                    const analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 512;
                    analyser.smoothingTimeConstant = 0.4;
                    source.connect(analyser);
                    analyserRef.current = analyser;

                    mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                    audioChunksRef.current = [];
                    let autoStoppedSilent = false;

                    mediaRecorderRef.current.ondataavailable = (e) => {
                        if (e.data.size > 0) audioChunksRef.current.push(e.data);
                    };

                    mediaRecorderRef.current.onstop = () => {
                        setAudioLevel(0);
                        stream.getTracks().forEach(track => track.stop());
                        if (microphoneStreamRef.current === stream) {
                            microphoneStreamRef.current = null;
                        }

                        // Don't send audio if TTS started playing while we were recording (echo prevention)
                        if (ttsSpeakingRef.current || autoStoppedSilent) {
                            console.log('🔇 Discarding recorded audio (TTS active or silent timeout)');
                            return;
                        }

                        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                        const reader = new FileReader();
                        reader.readAsDataURL(audioBlob);
                        reader.onloadend = () => {
                            if (socket && socket.connected) {
                                console.log('📡 Sending audio to Faster-Whisper backend');
                                setIsTranscribingVoice(true);
                                if (transcribeTimeoutRef.current) {
                                    clearTimeout(transcribeTimeoutRef.current);
                                }
                                transcribeTimeoutRef.current = setTimeout(() => {
                                    setIsTranscribingVoice(false);
                                    transcribeTimeoutRef.current = null;
                                }, 12000);
                                if (isViewingHistoryRef.current) {
                                    setViewingHistory(false);
                                    setChatMessages([]);
                                    chatMessagesRef.current = [];
                                    setVoiceCommands([]);
                                    voiceCommandsRef.current = [];
                                    setSessionActivities([]);
                                    sessionActivitiesRef.current = [];
                                    syncWithBackendSession({ triggerStartupGreetingIfEmpty: false });
                                }
                                streamingMessageIdRef.current = null;
                                socket.emit('voice_audio_data', {
                                    audio_data: reader.result,
                                    client_message_id: makeClientMessageId('voice_user'),
                                    language: voiceLanguage,
                                    require_wake_word: requireWakeWordRef.current,
                                    provider: aiProviderRef.current,
                                    model: aiModelRef.current,
                                    offline_mode: aiModeRef.current === 'offline' || aiProviderRef.current === 'gguf',
                                });
                            }
                        };
                    };

                    mediaRecorderRef.current.start();
                    setIsVoiceActive(true);
                    isVoiceActiveRef.current = true;
                    _setIsRecognitionStarted(true);
                    setInterimTranscript('Listening (Auto-stops on silence)...');

                    const dataArray = new Uint8Array(analyser.frequencyBinCount);
                    const timeArray = new Uint8Array(analyser.fftSize);
                    let hasSpoken = false;
                    let smoothedLevel = 0;
                    let lastLevelCommit = 0;

                    const checkSilence = () => {
                        if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
                            setAudioLevel(0);
                            return;
                        }

                        analyser.getByteFrequencyData(dataArray);
                        analyser.getByteTimeDomainData(timeArray);

                        const sum = dataArray.reduce((a, b) => a + b, 0);
                        const average = sum / dataArray.length;

                        let tdSum = 0;
                        for (let i = 0; i < timeArray.length; i++) {
                            const v = (timeArray[i] - 128) / 128;
                            tdSum += v * v;
                        }
                        const tdRms = Math.sqrt(tdSum / timeArray.length);

                        const rawLevel = Math.min(
                            100,
                            Math.max(0, Math.max((tdRms - 0.012) * 340, (average - 6) * 2.1))
                        );
                        const alpha = rawLevel > smoothedLevel ? 0.5 : 0.22;
                        smoothedLevel = smoothedLevel * (1 - alpha) + rawLevel * alpha;

                        const now = performance.now();
                        if (now - lastLevelCommit >= 30) {
                            lastLevelCommit = now;
                            setAudioLevel(Math.round(smoothedLevel));
                        }

                        if (average > 12 || tdRms > 0.032) { // Voice detected
                            hasSpoken = true;
                            if (silenceTimerRef.current) {
                                clearTimeout(silenceTimerRef.current);
                                silenceTimerRef.current = null;
                            }
                            setInterimTranscript('Hearing you...');
                        } else { // Silence
                            const timeoutMs = hasSpoken ? 1800 : 7000;
                            if (!silenceTimerRef.current) {
                                silenceTimerRef.current = setTimeout(() => {
                                    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                                        console.log(hasSpoken ? '⏳ Speech pause detected, processing...' : '⏳ Max wait time reached with no speech, stopping...');
                                        autoStoppedSilent = !hasSpoken;
                                        mediaRecorderRef.current.stop();
                                        setIsVoiceActive(false);
                                        isVoiceActiveRef.current = false;
                                        _setIsRecognitionStarted(false);
                                        setAudioLevel(0);
                                        setInterimTranscript(hasSpoken ? 'Processing with Whisper...' : '');
                                    }
                                    silenceTimerRef.current = null;
                                }, timeoutMs);
                            }
                        }
                        requestAnimationFrame(checkSilence);
                    };
                    checkSilence();

                } catch (err) {
                    console.error('Error accessing microphone:', err);
                    setIsVoiceActive(false);
                    isVoiceActiveRef.current = false;
                    setAudioLevel(0);
                    setInterimTranscript('Microphone access denied');
                    triggerOrbError('Microphone access denied');
                }
            } else {
                console.log('⚠️ Starting voice recording (SpeechRecognition for real-time text)');
                if (activeRecognitionRef.current) {
                    try {
                        activeRecognitionRef.current.start();
                    } catch (err) {
                        console.error('Error starting recognition:', err);
                    }
                } else {
                    console.error('Voice recognition not initialized');
                    setInterimTranscript('Voice recognition not supported or not initialized.');
                }
            }
        }
    };

    const stopBackendSpeech = (reason: string = 'webui_stop') => {
        if (ttsCooldownTimerRef.current) {
            clearTimeout(ttsCooldownTimerRef.current);
            ttsCooldownTimerRef.current = null;
        }
        wasRemoteTtsSpeakingRef.current = false;
        remoteTtsSpeakingRef.current = false;
        ttsSpeakingRef.current = false;
        setRemoteTtsSpeaking(false);
        setSpeakingLevel(0);
        setRemoteOrbState('idle');
        setRemoteOrbAudioLevel(0);

        if (socketRef.current && socketRef.current.connected) {
            try {
                socketRef.current.emit('voice_stop', { reason });
            } catch { /* empty */ }
        }
        fetch(apiUrl('/api/voice/stop'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason }),
        }).catch(() => {});
    };

    // Unified single-speaker Text-to-Speech (routes all notices & responses to backend TTSOutputService)
    const speak = (text: string, _lang: string = voiceLanguage) => {
        try {
            if (!ttsEnabledRef.current) {
                ttsSpeakingRef.current = false;
                setRemoteTtsSpeaking(false);
                setSpeakingLevel(0);
                return;
            }
            const cleanText = (text || '').trim();
            if (!cleanText) {
                return;
            }

            // Keep SpeechRecognition open for barge-in stop phrases; pause only MediaRecorder capture
            ttsSpeakingRef.current = true;
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
            }

            fetch(apiUrl('/api/voice/speak'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: cleanText,
                    interrupt: true,
                    wait: false,
                    source: 'webui_notice',
                }),
            })
                .then((res) => (res.ok ? res.json() : null))
                .then((data) => {
                    if (!data || !data.queued) {
                        ttsSpeakingRef.current = false;
                        setRemoteTtsSpeaking(false);
                    }
                })
                .catch(() => {
                    ttsSpeakingRef.current = false;
                    setRemoteTtsSpeaking(false);
                });
        } catch (error) {
            console.error('TTS error:', error);
            ttsSpeakingRef.current = false;
            setRemoteTtsSpeaking(false);
            setSpeakingLevel(0);
        }
    };

    // Toggle always-active wake mode (synced across WebUI & Companion background listener)
    const toggleAlwaysActive = async () => {
        const newState = !alwaysActive;
        setAlwaysActive(newState);
        alwaysActiveRef.current = newState;

        console.log('🔄 Always-active wake mode:', newState ? 'ON' : 'OFF');
        console.log('   Wake word required:', requireWakeWord);

        // Persist to backend settings so companion voice listener enables/pauses live
        try {
            await fetch(apiUrl('/api/settings/update'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: 'voice',
                    settings: { stt: { continuous: newState } },
                }),
            });
        } catch (err) {
            console.warn('Could not persist continuous wake setting:', err);
        }

        if (newState) {
            setUserStoppedVoice(false);
            userStoppedRef.current = false;
            const message = requireWakeWord
                ? 'Always wake mode enabled. Say "Hey Pulsar" anytime.'
                : 'Always active mode enabled.';
            speak(message, voiceLanguage);
        } else {
            if (isVoiceActive) {
                try {
                    await toggleVoice();
                } catch (error) {
                    console.error('❌ Error stopping active voice capture:', error);
                }
            }
            speak('Always wake mode disabled.', voiceLanguage);
            setWakeWordDetected(false);
            setIsProcessingCommand(false);
            isProcessingCommandRef.current = false;
        }
    };

    // Toggle wake word requirement (persisted to backend)
    const toggleWakeWord = async () => {
        const newState = !requireWakeWord;
        setRequireWakeWord(newState);
        requireWakeWordRef.current = newState;
        console.log('Wake word requirement:', newState ? 'ON' : 'OFF');

        try {
            await fetch(apiUrl('/api/settings/update'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: 'voice',
                    settings: { wakeWord: { enabled: newState } },
                }),
            });
        } catch (err) {
            console.warn('Could not persist wakeWord setting:', err);
        }

        const message = newState
            ? 'Wake word enabled. Say "Hey Pulsar" before commands.'
            : 'Wake word disabled. Just speak your commands directly.';
        speak(message, voiceLanguage);
    };



    // Toggle AI Mode: Online (Gemini) <-> Offline (Local GGUF)
    const toggleAIMode = async () => {
        const newMode: 'online' | 'offline' = aiModeRef.current === 'online' ? 'offline' : 'online';
        const provider: 'gemini' | 'gguf' = newMode === 'online' ? 'gemini' : 'gguf';
        const targetModel = newMode === 'online' ? 'gemini-2.5-flash' : 'pulsar-final-q4_k_m';

        console.log(`🤖 Switching AI mode to: ${newMode} (provider: ${provider}, model: ${targetModel})`);
        addSystemLog('info', `Switching to ${newMode} AI...`);

        try {
            // Update provider & matching defaultModel via backend API
            const response = await fetch(apiUrl('/api/settings/update'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: 'ai',
                    settings: {
                        defaultProvider: provider,
                        defaultModel: targetModel,
                    }
                })
            });

            const result = await response.json();
            if (result.success) {
                updateAIRefs(provider, targetModel, newMode);
                const modeName = newMode === 'online' ? 'Online AI (Gemini)' : 'Offline AI (Local GGUF)';
                console.log(`✅ AI mode switched to: ${modeName}`);
                addSystemLog('success', `Switched to ${modeName}`);
                speak(`Switched to ${modeName}`, voiceLanguage);
            } else {
                console.error('❌ Failed to switch AI mode:', result.error);
                addSystemLog('error', `Failed to switch AI mode: ${result.error}`);
            }
        } catch (error) {
            console.error('❌ Error switching AI mode:', error);
            addSystemLog('error', 'Error switching AI mode');
        }
    };

    // Set AI Provider: Gemini, OpenAI, or GGUF



    // Start Google Speech Recognition (online)
    const startGoogleRecognition = async () => {
        if (!socket) {
            addSystemLog('error', 'Not connected to server');
            return;
        }

        try {
            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create MediaRecorder for audio capture
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            // Start Google Speech session on backend
            socket.emit('google_start_recognition', {
                language: voiceLanguage,
                sampleRate: 16000
            });

            // Send audio chunks to backend
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    // Convert blob to array buffer and send
                    event.data.arrayBuffer().then(buffer => {
                        socket.emit('google_audio_chunk', {
                            audio: Array.from(new Uint8Array(buffer))
                        });
                    });
                }
            };

            mediaRecorder.start(100); // Capture in 100ms chunks for real-time processing
            setIsVoiceActive(true);
            _setIsRecognitionStarted(true);
            console.log('≡ƒîÉ Google Speech Recognition started');

        } catch (error) {
            console.error('Γ¥î Microphone access denied:', error);
            addSystemLog('error', 'Microphone access denied');
        }
    };

    // Stop Google Speech Recognition
    const stopGoogleRecognition = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }

        if (socket) {
            socket.emit('google_stop_recognition');
        }

        setIsVoiceActive(false);
        _setIsRecognitionStarted(false);
        setInterimTranscript('');
        console.log('≡ƒÜ½ Google Speech Recognition stopped');
    };

    const closeDetailView = () => {
        setSelectedView(null);
    };

    // Sync refs with state
    useEffect(() => {
        chatMessagesRef.current = chatMessages;
    }, [chatMessages]);

    useEffect(() => {
        voiceCommandsRef.current = voiceCommands;
    }, [voiceCommands]);

    useEffect(() => {
        sessionActivitiesRef.current = sessionActivities;
    }, [sessionActivities]);

    useEffect(() => {
        currentSessionRef.current = currentSession;
    }, [currentSession]);

    // Session management functions
    const loadSession = (sessionId: string) => {
        const session = conversationHistory.find(s => s.id === sessionId);
        const isHistorical = sessionId !== backendActiveSessionIdRef.current;
        setViewingHistory(isHistorical);

        if (session) {
            hydrateActiveSession(session);
        }

        fetch(apiUrl(`/api/sessions/${encodeURIComponent(sessionId)}`))
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.success && data.session && data.session.id === sessionId) {
                    hydrateActiveSession(data.session);
                }
            })
            .catch(() => {});
    };

    const resumeLiveSession = () => {
        setViewingHistory(false);
        syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
    };

    const deleteSession = (sessionId: string) => {
        setConversationHistory(prev => prev.filter(s => s.id !== sessionId));

        const stored = localStorage.getItem('conversationHistory');
        if (stored) {
            try {
                const history = JSON.parse(stored);
                const filtered = history.filter((s: ConversationSession) => s.id !== sessionId);
                localStorage.setItem('conversationHistory', JSON.stringify(filtered));
            } catch (e) {
                console.error('Failed to delete session from storage:', e);
            }
        }

        fetch(apiUrl(`/api/sessions/${encodeURIComponent(sessionId)}`), {
            method: 'DELETE',
        })
            .then((res) => {
                if (res.ok && currentSessionRef.current?.id === sessionId) {
                    setViewingHistory(false);
                    syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
                }
            })
            .catch(() => {});
    };

    const clearAllSessions = () => {
        setConversationHistory([]);
        localStorage.removeItem('conversationHistory');
        if (isViewingHistoryRef.current) {
            setViewingHistory(false);
            syncWithBackendSession({ triggerStartupGreetingIfEmpty: true, force: true });
        }
        fetch(apiUrl('/api/sessions/clear'), { method: 'POST' }).catch(() => {});
    };

    const isSessionMeaningful = (msgs: Message[], cmds: VoiceCommand[], acts: SessionActivity[] = []): boolean => {
        if (cmds.length > 0) return true;
        if (
            msgs.some(
                m =>
                    m.type === 'user' ||
                    !['webui_startup', 'startup_greeting', 'new_session', 'webui_new_session', 'backend_startup', 'webui_startup_offline', 'webui_new_session_offline'].includes(
                        m.source || ''
                    )
            )
        ) {
            return true;
        }
        if (acts.some(a => a.kind !== 'session' && a.kind !== 'startup')) {
            return true;
        }
        return false;
    };

    // Internal save function for offline fallback archival (connected mode persists via backend ChatSessionStore)
    const saveInternal = (
        session: ConversationSession | null,
        msgs: Message[],
        cmds: VoiceCommand[],
        acts: SessionActivity[] = [],
        forceArchive: boolean = false
    ) => {
        if (!session) return;
        if (!isSessionMeaningful(msgs, cmds, acts)) return;
        if (!forceArchive && backendActiveSessionIdRef.current && session.id === backendActiveSessionIdRef.current) {
            return;
        }

        const endTime = new Date();
        const endTimestamp = endTime.getTime();

        let startTimestamp = session.startTimestamp;
        if (!startTimestamp && session.id && session.id.startsWith('session_')) {
            const parsed = parseInt(session.id.replace('session_', ''), 10);
            if (!isNaN(parsed) && parsed > 1000000000000) {
                startTimestamp = parsed;
            }
        }
        if (!startTimestamp) {
            startTimestamp = sessionStartTimeRef.current ? sessionStartTimeRef.current.getTime() : (endTimestamp - 60000);
        }

        const startDate = new Date(startTimestamp);
        const day = session.day || startDate.toLocaleDateString(undefined, { weekday: 'long' });
        const date = session.date || startDate.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
        const formattedDate = `${day}, ${date}`;
        const duration = formatSessionDuration(startTimestamp, endTimestamp);
        const preview = extractMeaningfulPreview(msgs, cmds, acts);

        const sessionToSave: ConversationSession = {
            ...session,
            startTimestamp,
            endTimestamp,
            startTime: session.startTime || startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            endTime: endTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            date,
            day,
            formattedDate,
            duration,
            preview: preview.substring(0, 150),
            messages: [...msgs],
            voiceCommands: [...cmds],
            activities: [...acts],
            messageCount: msgs.length,
            userMessageCount: msgs.filter(m => m.type === 'user').length,
            aiMessageCount: msgs.filter(m => m.type === 'ai').length,
            voiceCount: cmds.length,
            activityCount: acts.length,
        };

        setConversationHistory(prev => {
            const filtered = prev.filter(s => s.id !== session.id);
            const updated = [sessionToSave, ...filtered].sort((a, b) => (b.startTimestamp || 0) - (a.startTimestamp || 0));
            localStorage.setItem('conversationHistory', JSON.stringify(updated.slice(0, 50)));
            return updated;
        });
    };

    const saveCurrentSessionToHistory = (forceArchive: boolean = false) => {
        saveInternal(
            currentSessionRef.current,
            chatMessagesRef.current,
            voiceCommandsRef.current,
            sessionActivitiesRef.current,
            forceArchive
        );
    };

    const startNewSession = () => {
        stopBackendSpeech('new_session');
        setViewingHistory(false);
        setIsAITyping(false);
        setIsTranscribingVoice(false);
        setInterimTranscript('');
        setWakeWordDetected(false);
        clearOrbError();
        streamingMessageIdRef.current = null;
        backendActiveSessionIdRef.current = null;
        hasGreetedRef.current = false;
        seenMessageIdsRef.current.clear();
        seenActivityIdsRef.current.clear();
        setChatMessages([]);
        chatMessagesRef.current = [];
        setVoiceCommands([]);
        voiceCommandsRef.current = [];
        setSessionActivities([]);
        sessionActivitiesRef.current = [];

        const offlineSessionAcks = [
            'Naya session ready hai Boss — batayein kis cheez pe kaam karein?',
            'Fresh start lete hain Boss, bolo kya task hai?',
            'Fresh session initialized, Boss. What are we tackling?',
        ];
        const fallbackGreeting = offlineSessionAcks[Math.floor(Math.random() * offlineSessionAcks.length)];

        fetch(apiUrl('/api/sessions/new'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reason: 'manual',
                speak: Boolean(ttsEnabledRef.current),
                source: 'webui_new_session',
            }),
        })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.success && data.session) {
                    if (data.boot_id) {
                        localStorage.setItem('pulsar_last_boot_id', String(data.boot_id));
                        lastBootIdRef.current = String(data.boot_id);
                    }
                    backendActiveSessionIdRef.current = data.session.id;
                    hasGreetedRef.current = Boolean(data.session.messages?.length);
                    hydrateActiveSession(data.session);
                    if (!(data?.queued || data?.spoken) && data.greeting && ttsEnabledRef.current) {
                        speak(data.greeting, voiceLanguage);
                    }
                    fetch(apiUrl('/api/sessions/history?limit=50'))
                        .then((r) => (r.ok ? r.json() : null))
                        .then((histJson) => {
                            if (histJson?.success && Array.isArray(histJson.sessions)) {
                                const filtered = histJson.sessions.filter((s: any) => s.id !== data.session.id);
                                const normalized = normalizeAndSortSessions(filtered);
                                setConversationHistory(normalized);
                                localStorage.setItem('conversationHistory', JSON.stringify(normalized.slice(0, 50)));
                            }
                        })
                        .catch(() => {});
                } else {
                    throw new Error('Failed to create new session');
                }
            })
            .catch(() => {
                saveCurrentSessionToHistory(true);

                const now = new Date();
                const startTimestamp = now.getTime();
                const sessionId = `session_${startTimestamp}`;
                sessionStartTimeRef.current = now;
                const day = now.toLocaleDateString(undefined, { weekday: 'long' });
                const date = now.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

                const offlineSession: ConversationSession = {
                    id: sessionId,
                    startTimestamp,
                    startTime: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    date,
                    day,
                    formattedDate: `${day}, ${date}`,
                    messageCount: 0,
                    userMessageCount: 0,
                    aiMessageCount: 0,
                    voiceCount: 0,
                    activityCount: 0,
                    messages: [],
                    voiceCommands: [],
                    activities: [],
                };

                hydrateActiveSession(offlineSession);
                hasGreetedRef.current = true;
                upsertChatMessage({
                    text: fallbackGreeting,
                    type: 'ai',
                    source: 'webui_new_session_offline',
                    isVoice: false,
                });
                if (ttsEnabledRef.current) {
                    speak(fallbackGreeting, voiceLanguage);
                }
            });
    };

    // Initialize current session on mount using backend BOOT_ID as source of truth
    useEffect(() => {
        const now = new Date();
        const startTimestamp = now.getTime();
        const sessionId = `session_${startTimestamp}`;
        sessionStartTimeRef.current = now;

        const day = now.toLocaleDateString(undefined, { weekday: 'long' });
        const date = now.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

        const blankPlaceholder: ConversationSession = {
            id: sessionId,
            startTimestamp,
            startTime: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            date,
            day,
            formattedDate: `${day}, ${date}`,
            messageCount: 0,
            userMessageCount: 0,
            aiMessageCount: 0,
            voiceCount: 0,
            activityCount: 0,
            messages: [],
            voiceCommands: [],
            activities: [],
        };

        setCurrentSession(blankPlaceholder);
        currentSessionRef.current = blankPlaceholder;

        // Seed history list temporarily from localStorage until backend responds (never auto-restore old active chat)
        const stored = localStorage.getItem('conversationHistory');
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                const normalized = normalizeAndSortSessions(parsed);
                setConversationHistory(normalized);
            } catch (e) {
                console.error('Failed to load conversation history:', e);
            }
        }

        // Sync active session & history with backend (fresh session on new boot, preserved on same-boot F5)
        syncWithBackendSession({ triggerStartupGreetingIfEmpty: true });

        // Persist offline-only active session on unmount if backend wasn't managing it
        return () => {
            const session = currentSessionRef.current;
            const msgs = chatMessagesRef.current;
            const cmds = voiceCommandsRef.current;
            const acts = sessionActivitiesRef.current;

            if (
                session &&
                !isViewingHistoryRef.current &&
                (!backendActiveSessionIdRef.current || session.id !== backendActiveSessionIdRef.current) &&
                isSessionMeaningful(msgs, cmds, acts)
            ) {
                const endTime = new Date();
                const endTimestamp = endTime.getTime();
                const sTs = session.startTimestamp || endTimestamp - 60000;
                const sDate = new Date(sTs);
                const sDay = session.day || sDate.toLocaleDateString(undefined, { weekday: 'long' });
                const sDateStr = session.date || sDate.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

                const sessionToSave: ConversationSession = {
                    ...session,
                    startTimestamp: sTs,
                    endTimestamp,
                    startTime: session.startTime || sDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    endTime: endTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    date: sDateStr,
                    day: sDay,
                    formattedDate: `${sDay}, ${sDateStr}`,
                    duration: formatSessionDuration(sTs, endTimestamp),
                    preview: extractMeaningfulPreview(msgs, cmds, acts).substring(0, 150),
                    messages: [...msgs],
                    voiceCommands: [...cmds],
                    activities: [...acts],
                    messageCount: msgs.length,
                    userMessageCount: msgs.filter(m => m.type === 'user').length,
                    aiMessageCount: msgs.filter(m => m.type === 'ai').length,
                    voiceCount: cmds.length,
                    activityCount: acts.length,
                };

                try {
                    const storedHistory = localStorage.getItem('conversationHistory');
                    let history = storedHistory ? JSON.parse(storedHistory) : [];
                    const filtered = history.filter((s: any) => s.id !== session.id);
                    history = [sessionToSave, ...filtered].sort((a: any, b: any) => (b.startTimestamp || 0) - (a.startTimestamp || 0)).slice(0, 50);
                    localStorage.setItem('conversationHistory', JSON.stringify(history));
                } catch {
                    // ignore storage quota errors on teardown
                }
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Keep currentSession stats synchronized with local state updates
    useEffect(() => {
        if (currentSession && !isViewingHistoryRef.current) {
            setCurrentSession(prev => prev ? {
                ...prev,
                messageCount: chatMessages.length,
                userMessageCount: chatMessages.filter(m => m.type === 'user').length,
                aiMessageCount: chatMessages.filter(m => m.type === 'ai').length,
                voiceCount: voiceCommands.length,
                activityCount: sessionActivities.length,
                messages: chatMessages,
                voiceCommands: voiceCommands,
                activities: sessionActivities,
            } : null);
        }
        if (!isViewingHistoryRef.current && (chatMessages.length > 0 || voiceCommands.length > 0 || sessionActivities.length > 0)) {
            saveInternal(currentSessionRef.current, chatMessages, voiceCommands, sessionActivities);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [chatMessages, voiceCommands, sessionActivities]);

    // Keep voice & wake-word refs synchronized across async callbacks
    useEffect(() => {
        alwaysActiveRef.current = alwaysActive;
    }, [alwaysActive]);

    useEffect(() => {
        requireWakeWordRef.current = requireWakeWord;
    }, [requireWakeWord]);

    useEffect(() => {
        wakePhrasesRef.current = wakePhrases;
    }, [wakePhrases]);

    useEffect(() => {
        isProcessingCommandRef.current = isProcessingCommand;
    }, [isProcessingCommand]);

    // Track browser/desktop app visibility, focus & close state for taskbar-adjacent orb overlay
    useEffect(() => {
        const updateVisibility = (forceMinimized?: boolean) => {
            const hidden = typeof forceMinimized === 'boolean'
                ? forceMinimized
                : (typeof document !== 'undefined' ? document.visibilityState === 'hidden' : false);
            setAppMinimized(hidden);
            if (socket && isConnected) {
                socket.emit('app_visibility', { minimized: hidden });
            }
        };

        const handleVisibilityChange = () => updateVisibility();
        const handleWindowFocus = () => {
            if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                updateVisibility(false);
            }
        };
        const handleUnload = () => {
            setAppMinimized(true);
            if (socket && socket.connected) {
                socket.emit('app_visibility', { minimized: true, unloading: true, source: 'webui_unload' });
            }
            try {
                if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
                    const blob = new Blob(
                        [JSON.stringify({ app_minimized: true, source: 'webui_unload' })],
                        { type: 'application/json' }
                    );
                    navigator.sendBeacon(apiUrl('/api/desktop/overlay/state'), blob);
                }
            } catch {
                // ignore beacon errors during teardown
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        window.addEventListener('focus', handleWindowFocus);
        window.addEventListener('pagehide', handleUnload);
        window.addEventListener('beforeunload', handleUnload);

        let tauriInterval: ReturnType<typeof setInterval> | null = null;
        if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
            let prevMin: boolean | null = null;
            tauriInterval = setInterval(async () => {
                try {
                    const { getCurrentWindow } = await import('@tauri-apps/api/window');
                    const minState = await getCurrentWindow().isMinimized();
                    const hidden = minState || document.visibilityState === 'hidden';
                    if (prevMin !== hidden) {
                        prevMin = hidden;
                        updateVisibility(hidden);
                    }
                } catch {
                    // ignore if not inside Tauri window
                }
            }, 600);
        }

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            window.removeEventListener('focus', handleWindowFocus);
            window.removeEventListener('pagehide', handleUnload);
            window.removeEventListener('beforeunload', handleUnload);
            if (tauriInterval) clearInterval(tauriInterval);
        };
    }, [socket, isConnected]);

    // Subscribe Socket.IO room for active selected chain
    useEffect(() => {
        selectedChainIdRef.current = selectedChainId;
        if (!socket || !isConnected || !selectedChainId) return;
        socket.emit('subscribe_chain', { chain_id: selectedChainId });
        return () => {
            socket.emit('unsubscribe_chain', { chain_id: selectedChainId });
        };
    }, [selectedChainId, socket, isConnected]);

    // Initial HTTP hydration for agents, chains & system details
    useEffect(() => {
        refreshChains();
        refreshAgents();
        refreshSystemDetails();
    }, [refreshChains, refreshAgents, refreshSystemDetails]);

    // Derive unified 5-state 4D Orb state & real-time vibration amplitude
    const hasActiveBrainChain =
        (Array.isArray(brainStatus?.active_chains) &&
            brainStatus.active_chains.some((c: ActiveChain) => ['executing', 'running', 'planning', 'verifying'].includes(String(c.status).toLowerCase()))) ||
        activeChains.some((c) => ['executing', 'planning', 'verifying'].includes(String(c.status).toLowerCase()));

    // Note: passive Always-Wake standby stays 'idle' until wake word or mic button activates listening.
    // Backend TTS speaking state (remoteTtsSpeaking) is intentionally excluded from localOrbState so
    // orb_state_sync updates do not echo back via orb_state_update.
    const localOrbState: OrbState =
        (orbError || pendingDangerAction) ? 'error' :
        (isAITyping || isTranscribingVoice || hasActiveBrainChain) ? 'processing' :
        (isVoiceActive || wakeWordDetected) ? 'listening' :
        'idle';

    const localOrbAudioLevel: number =
        localOrbState === 'listening' ? audioLevel :
        0;

    const orbState: OrbState =
        localOrbState !== 'idle'
            ? localOrbState
            : (remoteTtsSpeaking ? 'speaking' : remoteOrbState);

    const orbAudioLevel: number =
        orbState === 'speaking'
            ? Math.max(14, remoteOrbAudioLevel || speakingLevel)
            : orbState === 'listening'
                ? (isVoiceActive ? audioLevel : Math.max(audioLevel, remoteOrbAudioLevel))
                : 0;

    // Broadcast local WebUI orb state & voice level to backend / desktop overlay (throttled for 60fps mic/TTS)
    useEffect(() => {
        if (!socket || !isConnected) return;

        // Avoid emitting local 'idle' repeatedly when remote companion owns an active state
        const stateChanged = lastEmittedOrbStateRef.current !== localOrbState;
        if (localOrbState === 'idle' && !stateChanged) {
            return;
        }

        const now = performance.now();
        if (!stateChanged && now - lastOrbEmitTimeRef.current < 65) {
            return;
        }

        lastOrbEmitTimeRef.current = now;
        lastEmittedOrbStateRef.current = localOrbState;

        socket.emit('orb_state_update', {
            state: localOrbState,
            audio_level: localOrbAudioLevel,
            webui_mic_active: isVoiceActive,
            app_minimized: appMinimized,
            error_message: orbError || '',
            source: 'webui',
        });
    }, [localOrbState, localOrbAudioLevel, isVoiceActive, appMinimized, orbError, socket, isConnected]);

    const value: DashboardContextType = {
        socket,
        isConnected,
        chatMessages,
        isAITyping,
        voiceCommands,
        systemStats,
        systemStatsHistory,
        systemDetails,
        learningStats,
        systemLogs,
        taskProgress,
        activeChains,
        chainHistory,
        selectedChainId,
        setSelectedChainId,
        openChainMonitor,
        agents,
        agentTasks,
        refreshChains,
        refreshAgents,
        refreshSystemDetails,
        createAndRunChain,
        pauseChain,
        resumeChain,
        cancelChain,
        emergencyStop,
        loadAgent,
        dispatchAgentTask,
        cancelAgentTask,
        isVoiceActive,
        interimTranscript,
        audioLevel,
        orbState,
        orbAudioLevel,
        isSpeaking,
        orbError,
        triggerOrbError,
        desktopOverlayEnabled,
        setDesktopOverlayEnabled,
        sendCommand,
        toggleVoice,
        setVoiceLanguage,
        alwaysActive,
        requireWakeWord,
        toggleAlwaysActive,
        toggleWakeWord,
        wakeWordDetected,

        aiMode,
        aiProvider,
        setAIProvider,
        toggleAIMode,
        speak,
        selectedView,
        setSelectedView,
        closeDetailView,
        currentSession,
        conversationHistory,
        sessionActivities,
        isViewingHistory,
        resumeLiveSession,
        loadSession,
        deleteSession,
        clearAllSessions,
        startNewSession,
        
        // Arc Reactor HUD
        hudData,
        pendingDangerAction,
        authorizeAction: () => {
            if (!pendingDangerAction) return;
            const cur = pendingDangerAction;
            setPendingDangerAction(null);
            if (socket && socket.connected) {
                socket.emit('authorize_action', { id: cur.id });
            }
            if (cur.chain_id) {
                resumeChain(cur.chain_id, 'yes');
            } else if (cur.source === 'http' || cur.source === 'command' || cur.source === 'agent' || !socket?.connected) {
                apiFetchJson('/api/agent/confirm', {
                    method: 'POST',
                    body: JSON.stringify({ action_id: cur.id, confirmed: true }),
                });
            }
        },
        cancelAction: () => {
            if (!pendingDangerAction) return;
            const cur = pendingDangerAction;
            setPendingDangerAction(null);
            if (socket && socket.connected) {
                socket.emit('cancel_action', { id: cur.id });
            }
            if (cur.chain_id) {
                cancelChain(cur.chain_id);
            } else if (cur.source === 'http' || cur.source === 'command' || cur.source === 'agent' || !socket?.connected) {
                apiFetchJson('/api/agent/confirm', {
                    method: 'POST',
                    body: JSON.stringify({ action_id: cur.id, confirmed: false }),
                });
            }
        },
        
        // Sidebar State
        isLeftSidebarOpen,
        isRightSidebarOpen,
        toggleLeftSidebar,
        toggleRightSidebar,
        setSidebarAutoState,
        
        // Executive Brain State
        brainStatus,

        // Vision Analysis
        lastVisionAnalysis,
        presenceData,
        analyzeCameraFrame,
        checkPresence,
        lastGesture,
        checkGesture
    };

    return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
};
