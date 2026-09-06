import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import io, { Socket } from 'socket.io-client';
import { apiUrl, SOCKET_URL } from '../lib/api';

export interface Message {
    id: number;
    type: 'user' | 'ai';
    text: string;
    time: string;
}

export interface VoiceCommand {
    id: number;
    command: string;
    time: string;
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
    startTime: string;
    endTime?: string;
    messageCount: number;
    userMessageCount: number;
    aiMessageCount: number;
    voiceCount: number;
    duration?: string;
    preview?: string;
    messages: Message[];
    voiceCommands: VoiceCommand[];
}

type ViewType = 'dashboard' | 'apps' | 'chat' | 'voice' | 'settings' | 'ai-learning' | 'database' | 'systems' | 'conversations' | 'integrations' | null;

interface DashboardContextType {
    socket: Socket | null;
    chatMessages: Message[];
    voiceCommands: VoiceCommand[];
    systemStats: SystemStats;
    learningStats: LearningStats;
    systemLogs: SystemLog[];
    taskProgress: number;
    isVoiceActive: boolean;
    interimTranscript: string;
    audioLevel: number; // 0-100, real-time microphone audio level
    sendCommand: (command: string) => void;
    toggleVoice: () => void;
    setVoiceLanguage?: (lang: string) => void;
    alwaysActive: boolean;
    toggleAlwaysActive: () => void;
    toggleWakeWord: () => void;
    requireWakeWord: boolean;
    wakeWordDetected: boolean;

    aiMode: 'online' | 'offline';
    aiProvider: 'gemini' | 'openai' | 'ollama' | 'gguf';
    setAIProvider: (provider: 'gemini' | 'openai' | 'ollama' | 'gguf') => void;
    toggleAIMode: () => void;
    speak: (text: string, lang?: string) => void;
    selectedView: ViewType;
    setSelectedView: (view: ViewType) => void;
    closeDetailView: () => void;
    currentSession: ConversationSession | null;
    conversationHistory: ConversationSession[];
    loadSession?: (sessionId: string) => void;
    deleteSession?: (sessionId: string) => void;
    startNewSession?: () => void;
    isConnected: boolean;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

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
    const [chatMessages, setChatMessages] = useState<Message[]>([]);
    const [voiceCommands, setVoiceCommands] = useState<VoiceCommand[]>([]);
    const [systemStats, setSystemStats] = useState<SystemStats>({
        cpu: 0,
        memory: 0,
        disk: 0,
        network: '0 MB/s',
    });
    const [learningStats, setLearningStats] = useState<LearningStats>({
        database: '--',
        systems: '--',
        conversations: '--',
    });
    const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
    const [taskProgress, _setTaskProgress] = useState(0);
    const [isVoiceActive, setIsVoiceActive] = useState(false);
    const [interimTranscript, setInterimTranscript] = useState('');
    const interimTranscriptRef = useRef(''); // Ref to access current transcript in simulation
    const [recognition, setRecognition] = useState<unknown>(null);
    const [voiceLanguage, setVoiceLanguageState] = useState('auto'); // Auto-detect language
    const [_isRecognitionStarted, _setIsRecognitionStarted] = useState(false);

    // MediaRecorder & Audio Context for Faster-Whisper
    const silenceTimerRef = useRef<unknown>(null);
    const [userStoppedVoice, setUserStoppedVoice] = useState(false); // Track if user manually stopped
    const userStoppedRef = useRef(false); // Ref to track stop state without causing re-renders

    const [aiMode, setAIMode] = useState<'online' | 'offline'>('online'); // 'online' = GPT/Gemini, 'offline' = Ollama
    const [aiProvider, setAIProviderState] = useState<'gemini' | 'openai' | 'ollama' | 'gguf'>('openai'); // Current AI provider
    const [aiModel, setAIModel] = useState<string>(''); // Current AI model
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const isVoiceActiveRef = useRef(false); // Ref to track voice active state for reliable checks in handlers
    const ttsSpeakingRef = useRef(false); // TRUE while TTS is speaking + cooldown, prevents echo loop
    const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null); // Prevents utterance from being garbage collected mid-speech
    const [alwaysActive, setAlwaysActive] = useState(false); // Always-active wake word mode

    // Fetch Settings on Mount to sync Provider/Model
    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const response = await fetch(apiUrl('/api/settings/all'));
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.settings && data.settings.ai) {
                        const aiSettings = data.settings.ai;
                        if (aiSettings.defaultProvider) {
                            setAIProviderState(aiSettings.defaultProvider);
                            console.log(`≡ƒöä Synced Provider from settings: ${aiSettings.defaultProvider}`);
                        }
                        if (aiSettings.defaultModel) {
                            setAIModel(aiSettings.defaultModel);
                            console.log(`≡ƒöä Synced Model from settings: ${aiSettings.defaultModel}`);
                        }

                        // Sync AI Mode
                        if (aiSettings.defaultProvider === 'ollama') {
                            setAIMode('offline');
                        } else {
                            setAIMode('online');
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

    const sendCommand = (command: string) => {
        // Add user message to chat
        addChatMessage(command, 'user');
        addSystemLog('info', `Processing: ${command}`);

        const useOfflineMode = aiMode === 'offline';
        console.log(`≡ƒñû AI Mode: ${aiMode} | Provider: ${aiProvider} | Model: ${aiModel}`);

        if (socket && socket.connected) {
            console.log('≡ƒôñ Sending command via socket:', command);
            socket.emit('command', {
                command,
                message: command,
                offline_mode: useOfflineMode,
                provider: aiProvider,
                model: aiModel
            });
        } else {
            // Fallback to API
            fetch(apiUrl('/api/command'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command,
                    offline_mode: useOfflineMode,
                    provider: aiProvider,
                    model: aiModel
                }),
            })
                .then((res) => res.json())
                .then((data) => {
                    const response = data.response || data.message;
                    addChatMessage(response, 'ai');

                    // Speak the response if always-active mode
                    if (alwaysActive) {
                        speak(response, voiceLanguage);
                    }
                })
                .catch((error) => {
                    console.error('API call error:', error);
                    const errorMsg = 'Error processing command. Please try again.';
                    addChatMessage(errorMsg, 'ai');
                    if (alwaysActive) {
                        speak(errorMsg, voiceLanguage);
                    }
                });
        }
    };

    // ... (keep existing code) ...

    const setAIProvider = (provider: 'gemini' | 'openai' | 'ollama' | 'gguf') => {
        console.log(`≡ƒöä Switching AI provider to: ${provider}`);
        setAIProviderState(provider);
        // Reset model when provider changes (optional, or set to first available)
        // setAIModel(''); 

        // Update aiMode based on provider
        if (provider === 'ollama' || provider === 'gguf') {
            setAIMode('offline');
            const providerName = provider === 'gguf' ? 'GGUF' : 'Ollama';
            addSystemLog('info', `≡ƒñû Switched to ${providerName} (Offline)`);
        } else {
            setAIMode('online');
            const providerName = provider === 'gemini' ? 'Gemini' : 'OpenAI';
            addSystemLog('info', `≡ƒö╖ Switched to ${providerName} (Online)`);
        }
    };

    // Expose setAIModel
    const _setAIModelByName = (model: string) => {
        console.log(`≡ƒöä Switching AI model to: ${model}`);
        setAIModel(model);
    };




    const [requireWakeWord, setRequireWakeWord] = useState(false); // Require wake word in always-active mode
    const [wakeWordDetected, setWakeWordDetected] = useState(false); // Wake word detection state
    const [isProcessingCommand, setIsProcessingCommand] = useState(false); // Processing command after wake word
    const [audioLevel, setAudioLevel] = useState(0); // Real-time audio level 0-100
    const [selectedView, setSelectedView] = useState<ViewType>(null); // Selected detail view
    const lastProcessedCommandRef = useRef<{ text: string, time: number } | null>(null); // Deduplication ref
    const socketRef = useRef<Socket | null>(null); // Ref for socket to avoid stale closures in listeners

    // Session tracking state
    const [currentSession, setCurrentSession] = useState<ConversationSession | null>(null);
    const [conversationHistory, setConversationHistory] = useState<ConversationSession[]>([]);
    const sessionStartTimeRef = useRef<Date>(new Date());

    // Audio analysis refs
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const microphoneStreamRef = useRef<MediaStream | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    // SAFETY: Use a ref to hold the active recognition instance
    // This persists across re-renders and ensures we always clean up the *actual* active instance
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const activeRecognitionRef = useRef<any>(null);
    const hasGreetedRef = useRef(false); // Fix for double greeting


    // Initialize Socket.IO connection
    useEffect(() => {
        const newSocket = io(SOCKET_URL, {
            path: '/socket.io',
            transports: ['polling', 'websocket'],
            withCredentials: true,
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
        });

        newSocket.on('disconnect', () => {
            console.log('Disconnected from backend');
            setIsConnected(false);
            addSystemLog('error', 'Disconnected from backend server');
        });

        // Listen for live settings changes
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('settings_updated', async (data: any) => {
            console.log(`ΓÜÖ∩╕Å Settings updated live: ${data.category}`, data);
            addSystemLog('info', `${data.category} settings updated`);

            // Re-fetch all settings to update local state
            try {
                const response = await fetch(apiUrl('/api/settings/all'));
                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.settings) {
                        // Apply specific category changes if needed, or trigger full re-render
                        if (data.category === 'ai' && result.settings.ai) {
                            const provider = result.settings.ai.defaultProvider;
                            const newMode = provider === 'local' ? 'offline' : 'online';
                            if (newMode !== aiMode) {
                                setAIMode(newMode);
                                console.log(`≡ƒöä AI Mode hot-switched to ${newMode}`);
                            }
                        }
                    }
                }
            } catch (_err) {
                console.error('Failed to sync settings live:', err);
            }
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('command_response', (data: any) => {
            console.log('≡ƒôó command_response received:', data);
            if (data.success) {
                const message = data.response || data.message;
                addChatMessage(message, 'ai');
                // Add speak here too for command_response
                console.log('≡ƒöè Speaking from command_response:', message?.substring(0, 50));
                speak(message, voiceLanguage, data.audio_base64);
            } else {
                const errorMsg = 'Error: ' + (data.error || 'Unknown error');
                addChatMessage(errorMsg, 'ai');
                speak(errorMsg, voiceLanguage);
            }
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('system_stats_update', (stats: any) => {
            setSystemStats({
                cpu: Math.round(stats.cpu_usage || 0),
                memory: Math.round(stats.memory_usage || 0),
                disk: Math.round(stats.disk_usage || 0),
                network: stats.network_speed ? `${(stats.network_speed / 1024 / 1024).toFixed(1)} MB/s` : '0 MB/s',
            });
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('log_update', (log: any) => {
            addSystemLog(log.type || 'info', log.message);
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('learning_stats_update', (stats: any) => {
            setLearningStats({
                database: stats.database || '--',
                systems: stats.systems || '--',
                conversations: stats.conversations || '--'
            });
        });

        // Handle voice command responses with talkback
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('voice_transcript', (data: any) => {
            console.log(' Voice transcript received:', data);
            if (data.text) {
                setInterimTranscript(''); // Clear the 'Processing with Whisper...' text
                addChatMessage(data.text, 'user');
            }
        });

        newSocket.on('voice_response', (data: any) => {
            console.log('≡ƒÄñ Voice response received:', data);
            console.log('≡ƒöè voiceLanguage:', voiceLanguage);
            console.log('≡ƒöè data.success:', data.success);
            console.log('≡ƒöè data.response:', data.response?.substring(0, 100));

            if (data.success && data.response) {
                addChatMessage(data.response, 'ai');

                // Speak the response back to user (talkback)
                console.log('≡ƒöè About to call speak() with:', { text: data.response.substring(0, 50), lang: voiceLanguage });
                speak(data.response, voiceLanguage, data.audio_base64);
                console.log('Γ£à speak() called successfully');

                addSystemLog('success', `Command processed: ${data.response.substring(0, 50)}...`);
            } else if (data.error) {
                const errorMsg = data.response || 'Sorry, I encountered an error processing that command.';
                addChatMessage(errorMsg, 'ai');
                speak(errorMsg, voiceLanguage);
                addSystemLog('error', errorMsg);
            }
        });


        // Google Speech Recognition handlers
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('google_ready', (data: any) => {
            console.log('≡ƒîÉ Google Speech Recognition ready:', data);
            addSystemLog('success', `Online recognition enabled (${data.language})`);
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('google_transcript', (data: any) => {
            console.log('≡ƒîÉ Google transcript:', data);
            if (data.isFinal) {
                setInterimTranscript('');
                // Process as voice command
                newSocket.emit('voice_command', { text: data.text, language: voiceLanguage });
            } else {
                setInterimTranscript(data.text);
                interimTranscriptRef.current = data.text;
            }
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        newSocket.on('google_error', (data: any) => {
            console.error('Γ¥î Google Speech error:', data);
            addSystemLog('error', `Online recognition error: ${data.error}`);
        });

        setSocket(newSocket);
        socketRef.current = newSocket; // Update ref

        return () => {
            newSocket.close();
            socketRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Initialize Voice Recognition
    useEffect(() => {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
                } catch (_e) {
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

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            recog.onresult = (event: any) => {
                // Check if this instance is still the active one
                if (activeRecognitionRef.current !== recog) {
                    console.log('≡ƒ¢æ Ghost listener detected - ignoring result from stale instance');
                    return;
                }

                // PREVENT FEEDBACK LOOP (ECHO)
                // If the AI is speaking (or just finished speaking), ignore mic input entirely.
                if (ttsSpeakingRef.current || window.speechSynthesis.speaking || window.speechSynthesis.pending) {
                    // console.log('≡ƒÖè AI is speaking or in cooldown, ignoring mic input to prevent echo loop.');
                    return;
                }

                console.log('≡ƒÄ» Recognition event received:', {
                    resultIndex: event.resultIndex,
                    resultsLength: event.results.length,
                    isFinal: event.results[event.resultIndex]?.isFinal
                });

                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    const confidence = event.results[i][0].confidence;
                    console.log(`  Result ${i}: "${transcript}" (confidence: ${confidence?.toFixed(2) || 'N/A'}, final: ${event.results[i].isFinal})`);

                    if (event.results[i].isFinal) {
                        final += transcript;
                    } else {
                        interim += transcript;
                    }
                }

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
                    if (final.trim().match(/^(stop|quiet|silence|shutup|shut up|cancel|terminate|wait)$/i)) {
                        console.log('≡ƒ¢æ Fast Stop Triggered');
                        window.speechSynthesis.cancel();
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
                        if (alwaysActive && requireWakeWord && !isProcessingCommand) {
                            const wakeWords = ['hey assistant', 'ok assistant', 'hey daddy', 'ok daddy', 'assistant'];
                            const detectedWake = wakeWords.find(wake => commandToSend.toLowerCase().includes(wake));

                            if (detectedWake) {
                                console.log('≡ƒÄ» Wake word detected:', detectedWake);
                                setWakeWordDetected(true);
                                setIsProcessingCommand(true);

                                // Play greeting
                                const greetings = [
                                    'At your service, sir.',
                                    'systems initialized. Ready for command.',
                                    'For you, sir, always.',
                                    'I am ready. What is your will?',
                                    'Online and ready to serve.'
                                ];
                                const greeting = greetings[Math.floor(Math.random() * greetings.length)];
                                speak(greeting, voiceLanguage);

                                // Reset after 10 seconds if no command given
                                setTimeout(() => {
                                    if (isProcessingCommand) {
                                        setIsProcessingCommand(false);
                                        setWakeWordDetected(false);
                                    }
                                }, 10000);
                                return;
                            } else {
                                // In wake word mode, ignore commands without wake word
                                console.log('ΓÅ¡∩╕Å Skipping - waiting for wake word');
                                return;
                            }
                        }

                        // Process command directly (no wake word required or wake word detected)
                        const shouldProcess = !alwaysActive || !requireWakeWord || isProcessingCommand;

                        if (shouldProcess) {
                            console.log('≡ƒÄ» Processing voice command:', final);
                            addVoiceCommand(final);

                            // Send via socket for voice command processing, using REFs to avoid stale closures
                            const currentSocket = socketRef.current;

                            if (currentSocket && currentSocket.connected) {
                                console.log('≡ƒôñ Sending voice_command event to backend:', final);
                                console.log(`≡ƒñû Voice AI Mode: ${aiMode}`);
                                currentSocket.emit('voice_command', {
                                    text: final,
                                    language: voiceLanguage,
                                    timestamp: new Date().toISOString(),
                                    offline_mode: aiMode === 'offline',
                                    provider: aiProvider
                                });
                                console.log('Γ£à voice_command emitted successfully');
                            } else {
                                console.warn('ΓÜá∩╕Å Socket not connected, using direct fallback (avoiding duplicate chat entry)');

                                // Log processing
                                addSystemLog('info', `Processing Voice: ${final}`);

                                // DIRECT FETCH FALLBACK (No addChatMessage for user, since addVoiceCommand already added it)
                                // This prevents double entries (one Voice Icon, one Chat Text)
                                fetch(apiUrl('/api/command'), {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        command: final,
                                        offline_mode: aiMode === 'offline',
                                        provider: aiProvider
                                    }),
                                })
                                    .then((res) => res.json())
                                    .then((data) => {
                                        const response = data.response || data.message;
                                        addChatMessage(response, 'ai');
                                        // Speak response always for voice interactions
                                        speak(response, voiceLanguage);
                                    })
                                    .catch((error) => {
                                        console.error('API call error:', error);
                                        const errorMsg = 'Error processing command. Please try again.';
                                        addChatMessage(errorMsg, 'ai');
                                        speak(errorMsg, voiceLanguage);
                                    });
                            }

                            // Reset processing state after command
                            if (requireWakeWord) {
                                setTimeout(() => {
                                    setIsProcessingCommand(false);
                                    setWakeWordDetected(false);
                                }, 1000);
                            }
                        }
                    }, 2000); // End of debouncing setTimeout
                } // End of if (accumulatedFinalTranscriptRef.current)
            };

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
                    console.error('ΓÜá∩╕Å Audio capture error - microphone issue');
                    // Don't try to restart, let the user handle it
                    return;
                }

                // Critical errors - stop listening
                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    console.error('≡ƒÜ½ Microphone access denied');
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
                    console.error('Γ¥î Language not supported:', voiceLanguage);
                    alert(`Language "${voiceLanguage}" is not supported. Please select a different language.`);
                    setIsVoiceActive(false);
                    isVoiceActiveRef.current = false;
                    return;
                }

                // Other errors - just log
                console.error('Other recognition error:', event.error);
            };

            recog.onend = () => {
                console.log('≡ƒö┤ Recognition ended, current state:', isVoiceActiveRef.current, 'userStopped:', userStoppedRef.current);
                _setIsRecognitionStarted(false);

                // Stop audio monitoring when recognition ends
                stopAudioLevelMonitoring();

                // Only restart if:
                // 1. User hasn't manually stopped
                // 2. Voice is still supposed to be active
                // 3. Not in always-active mode (which handles its own lifecycle)
                if (!userStoppedRef.current && isVoiceActiveRef.current && !alwaysActive) {
                    console.log('≡ƒöä Recognition ended unexpectedly, restarting in 1000ms...');
                    setTimeout(() => {
                        if (!userStoppedRef.current && isVoiceActiveRef.current && recog) {
                            try {
                                recog.start();
                                console.log('Γ£à Recognition restarted');
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            } catch (error: any) {
                                if (!error.message?.includes('already started')) {
                                    console.error('Γ¥î Failed to restart:', error);
                                    setIsVoiceActive(false);
                                    isVoiceActiveRef.current = false;
                                }
                            }
                        }
                    }, 1000);
                } else {
                    console.log('≡ƒ¢æ Not restarting - userStopped:', userStoppedRef.current, 'active:', isVoiceActiveRef.current, 'alwaysActive:', alwaysActive);
                    if (!alwaysActive) {
                        setIsVoiceActive(false);
                        isVoiceActiveRef.current = false;
                        setInterimTranscript('');
                    }
                }
            };

            setRecognition(recog);
            console.log('Γ£à Voice recognition initialized (not started)');

            return () => {
                console.log('≡ƒº╣ Cleanup: component unmounting or language changing');
                if (activeRecognitionRef.current) {
                    const oldRecog = activeRecognitionRef.current;
                    oldRecog.onstart = null;
                    oldRecog.onresult = null;
                    oldRecog.onerror = null;
                    oldRecog.onend = null;
                    try {
                        oldRecog.abort();
                        console.log('Γ£à Stopped active recognition instance');
                    } catch (_e) {
                        // ignore errors on abort
                    }
                    activeRecognitionRef.current = null;
                }
            };
        }
    }, [voiceLanguage]); // Only re-initialize when language changes (userStoppedRef used to prevent re-initialization)

    // Audio Level Monitoring Functions
    const startAudioLevelMonitoring = async () => {
        console.log('≡ƒöº Starting audio level monitoring...');

        // First, try using simulated levels to avoid microphone conflicts
        // Web Speech API already has microphone access, requesting again can cause issues
        console.log('≡ƒÆí Using simulated audio levels to avoid conflicts with Speech Recognition');
        simulateAudioLevel();

        /* Disabled real audio monitoring to prevent conflicts with Web Speech API
        try {
            // Request microphone access separately for audio visualization
            console.log('≡ƒÄñ Requesting microphone access for visualization...');
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false
                }
            });
            console.log('Γ£à Microphone access granted');
            microphoneStreamRef.current = stream;

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            console.log('≡ƒöè Audio context created, state:', audioContext.state);
            
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
                console.log('Γû╢∩╕Å Audio context resumed');
            }
            
            const analyser = audioContext.createAnalyser();
            const microphone = audioContext.createMediaStreamSource(stream);

            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = 0.5;
            analyser.minDecibels = -90;
            analyser.maxDecibels = -10;
            microphone.connect(analyser);
            console.log('≡ƒôè Analyser configured');

            audioContextRef.current = audioContext;
            analyserRef.current = analyser;

            _analyzeAudioLevel();
            console.log('Γ£à Audio level monitoring started successfully');
        } catch (error) {
            console.error('Γ¥î Failed to start audio monitoring:', error);
            throw error;
        }
        */
    };

    const _analyzeAudioLevel = () => {
        if (!analyserRef.current) {
            console.warn('ΓÜá∩╕Å No analyser available for audio level monitoring');
            return;
        }

        const analyser = analyserRef.current;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        let frameCount = 0;

        const updateLevel = () => {
            if (!analyserRef.current || !isVoiceActiveRef.current) {
                console.log('ΓÅ╣∩╕Å Stopping audio level monitoring');
                return; // Stop if no longer active
            }

            // Get frequency data
            analyser.getByteFrequencyData(dataArray);

            // Calculate RMS (Root Mean Square) for better volume representation
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                const normalized = dataArray[i] / 255;
                sum += normalized * normalized;
            }
            const rms = Math.sqrt(sum / bufferLength);

            // Convert to 0-100 scale with exponential scaling for better visualization
            const normalizedLevel = Math.min(100, Math.pow(rms, 0.5) * 150);

            // Apply smoothing to reduce jitter
            setAudioLevel(prev => {
                const smoothingFactor = 0.3;
                const newLevel = prev * (1 - smoothingFactor) + normalizedLevel * smoothingFactor;

                // Log every 30 frames (~0.5 seconds) for debugging
                if (frameCount % 30 === 0) {
                    console.log('≡ƒôè Audio level:', newLevel.toFixed(1), '(RMS:', rms.toFixed(3), ')');
                }
                frameCount++;

                return newLevel;
            });

            // Continue monitoring
            animationFrameRef.current = requestAnimationFrame(updateLevel);
        };

        console.log('≡ƒÄ¼ Starting audio level animation loop');
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

        console.log('≡ƒôè Using simulated audio levels (visual feedback mode)');
        simulate();
    };

    const stopAudioLevelMonitoring = () => {
        // Cancel animation frame
        if (animationFrameRef.current) {
            try {
                cancelAnimationFrame(animationFrameRef.current);
            } catch (_e) { /* empty */ }
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
        console.log('≡ƒÄº Audio level monitoring stopped');
    };

    // Load Learning Stats
    useEffect(() => {
        const loadLearningStats = async () => {
            try {
                const response = await fetch(apiUrl('/api/learning/stats/all'));
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        const sizeTB = data.total_size_mb ? (data.total_size_mb / 1024 / 1024).toFixed(1) : '1.2';
                        const systems = data.active_systems !== undefined ? `${data.active_systems}/27` : '27/27';
                        const convK = data.total_conversations ? (data.total_conversations / 1000).toFixed(1) : '54.3';

                        setLearningStats({
                            database: `${sizeTB}TB`,
                            systems: systems,
                            conversations: `${convK}K`,
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to load learning stats:', error);
                // Keep default values
                setLearningStats({
                    database: '1.2TB',
                    systems: '27/27',
                    conversations: '54.3K',
                });
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
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
        });

        setChatMessages((prev) => [
            ...prev,
            {
                id: Date.now() + Math.random(),
                type,
                text,
                time,
            },
        ]);
    };

    const addVoiceCommand = (command: string) => {
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
        });

        setVoiceCommands((prev) => [
            {
                id: Date.now() + Math.random(),
                command,
                time,
            },
            ...prev.slice(0, 9), // Keep only last 10
        ]);
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
        console.log(`≡ƒîì Changing language to: ${lang}`);
        setVoiceLanguageState(lang);

        // Simply update the language property - recognition will use it on next start
        if (recognition) {
            (recognition as any).lang = lang;
            console.log(`Γ£à Language updated to: ${lang}`);
        }

        // Note: We don't restart recognition here to avoid restart loops
        // The new language will be used when user starts/restarts recognition manually
    };

    const toggleVoice = async () => {
        if (isVoiceActive) {
            console.log('≡ƒ¢æ Stopping voice recording');
            setUserStoppedVoice(true);
            userStoppedRef.current = true;
            setIsVoiceActive(false);
            isVoiceActiveRef.current = false;
            _setIsRecognitionStarted(false);
            setInterimTranscript('');

            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                try { mediaRecorderRef.current.stop(); } catch (_e) { /* empty */ }
            }
            if (audioContextRef.current) {
                try { audioContextRef.current.close(); } catch (_e) { /* empty */ }
                audioContextRef.current = null;
            }
            if (activeRecognitionRef.current) {
                try { activeRecognitionRef.current.stop(); } catch (_e) { /* empty */ }
            }
        } else {
            setUserStoppedVoice(false);
            userStoppedRef.current = false;

            // ALWAYS use backend Faster-Whisper for voice transcription, regardless of LLM provider
            if (true) {
                console.log('Γû╢∩╕Å Starting voice recording (MediaRecorder for Faster Whisper)');
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioContextRef.current = new AudioContext();
                    const source = audioContextRef.current.createMediaStreamSource(stream);
                    const analyser = audioContextRef.current.createAnalyser();
                    analyser.fftSize = 512;
                    source.connect(analyser);

                    mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                    audioChunksRef.current = [];

                    mediaRecorderRef.current.ondataavailable = (e) => {
                        if (e.data.size > 0) audioChunksRef.current.push(e.data);
                    };

                    mediaRecorderRef.current.onstop = () => {
                        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                        const reader = new FileReader();
                        reader.readAsDataURL(audioBlob);
                        reader.onloadend = () => {
                            if (socket) {
                                console.log('≡ƒôñ Sending audio to Faster-Whisper backend');
                                socket.emit('voice_audio_data', { audio_data: reader.result });
                            }
                        };
                        stream.getTracks().forEach(track => track.stop());
                    };

                    mediaRecorderRef.current.start();
                    setIsVoiceActive(true);
                    isVoiceActiveRef.current = true;
                    _setIsRecognitionStarted(true);
                    setInterimTranscript('Listening (Auto-stops on silence)...');

                    const dataArray = new Uint8Array(analyser.frequencyBinCount);
                    const checkSilence = () => {
                        if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return;

                        analyser.getByteFrequencyData(dataArray);
                        const sum = dataArray.reduce((a, b) => a + b, 0);
                        const average = sum / dataArray.length;

                        if (average > 10) { // Voice detected
                            if (silenceTimerRef.current) {
                                clearTimeout(silenceTimerRef.current);
                                silenceTimerRef.current = null;
                                setInterimTranscript('Hearing you...');
                            }
                        } else { // Silence
                            if (!silenceTimerRef.current) {
                                silenceTimerRef.current = setTimeout(() => {
                                    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                                        console.log('≡ƒöç Silence detected, processing...');
                                        mediaRecorderRef.current.stop();
                                        setIsVoiceActive(false);
                                        isVoiceActiveRef.current = false;
                                        _setIsRecognitionStarted(false);
                                        setInterimTranscript('Processing with Whisper...');
                                    }
                                }, 1500); // 1.5 seconds silence
                            }
                        }
                        requestAnimationFrame(checkSilence);
                    };
                    checkSilence();

                } catch (err) {
                    console.error('Error accessing microphone:', err);
                    setIsVoiceActive(false);
                    isVoiceActiveRef.current = false;
                    setInterimTranscript('Microphone access denied');
                }
            } else {
                console.log('Γû╢∩╕Å Starting voice recording (SpeechRecognition for real-time text)');
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

    // Text-to-Speech function
    const speak = (text: string, lang: string = 'en-US', audioBase64?: string) => {
        try {
            if (audioBase64) {
                console.log('≡ƒöè Playing backend generated audio (KittenTTS)');
                const audio = new Audio("data:audio/wav;base64," + audioBase64);
                ttsSpeakingRef.current = true;

                // Mute mic if necessary
                if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
                    try { mediaRecorderRef.current.stop(); } catch (_e) { /* ignore */ }
                }

                audio.onended = () => {
                    console.log('≡ƒöè TTS ended, starting cooldown');
                    setTimeout(() => {
                        ttsSpeakingRef.current = false;
                        if (alwaysActive && !userStoppedVoice) {
                            toggleVoice(); // Restart listening automatically
                        }
                    }, 300);
                };

                audio.onerror = (e) => {
                    console.error('Γ¥î Audio playback error:', e);
                    ttsSpeakingRef.current = false;
                };

                audio.play();
                return;
            }

            // Browser TTS fallback permanently disabled per user request
            console.warn('ΓÜá∩╕Å No audioBase64 provided to speak(). Browser TTS fallback disabled.');
        } catch (error) {
            console.error('Γ¥î TTS error:', error);
        }
    };

    // Toggle always-active mode
    const toggleAlwaysActive = () => {
        const newState = !alwaysActive;
        setAlwaysActive(newState);

        console.log('≡ƒöä Always-active mode:', newState ? 'ON' : 'OFF');
        console.log('   Wake word required:', requireWakeWord);

        if (newState) {
            // Start listening when always-active enabled (sync both state and ref)
            setUserStoppedVoice(false);
            userStoppedRef.current = false;
            if (!isVoiceActive && recognition) {
                try {
                    (recognition as any).start();
                    const message = requireWakeWord
                        ? 'Always active mode enabled. Waiting for wake word.'
                        : 'Always active mode enabled. Just speak your command.';
                    speak(message, voiceLanguage);
                } catch (error) {
                    console.error('Error starting always-active:', error);
                }
            }
        } else {
            // Stop listening when always-active disabled (sync both state and refs)
            if (isVoiceActive && recognition) {
                setUserStoppedVoice(true);
                userStoppedRef.current = true;
                setIsVoiceActive(false);
                isVoiceActiveRef.current = false; // Sync ref
                (recognition as any).stop();
                speak('Always active mode disabled.', voiceLanguage);
            }
            setWakeWordDetected(false);
            setIsProcessingCommand(false);
        }
    };

    // Toggle wake word requirement
    const toggleWakeWord = () => {
        const newState = !requireWakeWord;
        setRequireWakeWord(newState);
        console.log('≡ƒöä Wake word requirement:', newState ? 'ON' : 'OFF');

        const message = newState
            ? 'Wake word enabled. Say "Hey Assistant" before commands.'
            : 'Wake word disabled. Just speak your commands directly.';
        speak(message, voiceLanguage);
    };



    // Toggle AI Mode: Online (GPT/Gemini) <-> Offline (Ollama)
    const toggleAIMode = async () => {
        const newMode: 'online' | 'offline' = aiMode === 'online' ? 'offline' : 'online';
        const provider = newMode === 'online' ? 'google' : 'local';

        console.log(`≡ƒñû Switching AI mode to: ${newMode} (provider: ${provider})`);
        addSystemLog('info', `Switching to ${newMode} AI...`);

        try {
            // Update provider via backend API
            const response = await fetch(apiUrl('/api/settings/update'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: 'ai',
                    settings: {
                        defaultProvider: provider
                    }
                })
            });

            const result = await response.json();
            if (result.success) {
                setAIMode(newMode);
                const modeName = newMode === 'online' ? 'Online AI (Google)' : 'Offline AI (Ollama)';
                console.log(`Γ£à AI mode switched to: ${modeName}`);
                addSystemLog('success', `Switched to ${modeName}`);
                speak(`Switched to ${modeName}`, voiceLanguage);
            } else {
                console.error('Γ¥î Failed to switch AI mode:', result.error);
                addSystemLog('error', `Failed to switch AI mode: ${result.error}`);
            }
        } catch (error) {
            console.error('Γ¥î Error switching AI mode:', error);
            addSystemLog('error', 'Error switching AI mode');
        }
    };

    // Set AI Provider: Gemini, OpenAI, or Ollama



    // Start Google Speech Recognition (online)
    const _startGoogleRecognition = async () => {
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
    const _stopGoogleRecognition = () => {
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

    // Refs for accessing latest state in effects/cleanup
    const chatMessagesRef = useRef<Message[]>([]);
    const voiceCommandsRef = useRef<VoiceCommand[]>([]);
    const currentSessionRef = useRef<ConversationSession | null>(null);

    // Sync refs with state
    useEffect(() => {
        chatMessagesRef.current = chatMessages;
    }, [chatMessages]);

    useEffect(() => {
        voiceCommandsRef.current = voiceCommands;
    }, [voiceCommands]);

    useEffect(() => {
        currentSessionRef.current = currentSession;
    }, [currentSession]);

    // Session management functions
    const loadSession = (sessionId: string) => {
        const session = conversationHistory.find(s => s.id === sessionId);
        if (session) {
            // Save current session to history if it has messages
            if (currentSession && (chatMessages.length > 0 || voiceCommands.length > 0)) {
                saveCurrentSessionToHistory();
            }

            // Load the selected session
            setChatMessages(session.messages);
            setVoiceCommands(session.voiceCommands);
            setCurrentSession(session);
        }
    };

    const deleteSession = (sessionId: string) => {
        setConversationHistory(prev => prev.filter(s => s.id !== sessionId));

        // Also remove from localStorage
        const stored = localStorage.getItem('conversationHistory');
        if (stored) {
            const history = JSON.parse(stored);
            const filtered = history.filter((s: ConversationSession) => s.id !== sessionId);
            localStorage.setItem('conversationHistory', JSON.stringify(filtered));
        }
    };

    // Internal save function that can work with either passed state or latest state
    const saveInternal = (session: ConversationSession | null, msgs: Message[], cmds: VoiceCommand[]) => {
        if (!session) return;

        // Don't save empty sessions
        if (msgs.length === 0 && cmds.length === 0) return;

        const endTime = new Date();
        const duration = calculateDuration(sessionStartTimeRef.current, endTime);
        const preview = msgs.length > 0 ? msgs[0].text : cmds.length > 0 ? cmds[0].command : '';

        const sessionToSave: ConversationSession = {
            ...session,
            endTime: endTime.toLocaleTimeString(),
            duration,
            preview: preview.substring(0, 100),
            messages: [...msgs],
            voiceCommands: [...cmds],
            messageCount: msgs.length + cmds.length,
            userMessageCount: msgs.filter(m => m.type === 'user').length + cmds.length,
            aiMessageCount: msgs.filter(m => m.type === 'ai').length,
            voiceCount: cmds.length,
        };

        setConversationHistory(prev => {
            // Check if this session ID already exists in history to update it instead of adding duplicate
            const exists = prev.some(s => s.id === session.id);
            let updated;

            if (exists) {
                updated = prev.map(s => s.id === session.id ? sessionToSave : s);
            } else {
                updated = [sessionToSave, ...prev];
            }

            // Save to localStorage
            localStorage.setItem('conversationHistory', JSON.stringify(updated.slice(0, 50))); // Keep last 50
            return updated;
        });
    };

    const saveCurrentSessionToHistory = () => {
        // Use refs if called from cleanup, otherwise use state (though refs are always safe here)
        saveInternal(currentSessionRef.current, chatMessagesRef.current, voiceCommandsRef.current);
    };

    const calculateDuration = (start: Date, end: Date): string => {
        const diff = end.getTime() - start.getTime();
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        return `${minutes}m ${seconds}s`;
    };

    const startNewSession = () => {
        // Save status of current session before resetting
        if (currentSession && (chatMessages.length > 0 || voiceCommands.length > 0)) {
            saveCurrentSessionToHistory();
        }

        // Create new session
        const sessionId = `session_${Date.now()}`;
        const startTime = new Date();
        sessionStartTimeRef.current = startTime;

        const newSession = {
            id: sessionId,
            startTime: startTime.toLocaleTimeString(),
            messageCount: 0,
            userMessageCount: 0,
            aiMessageCount: 0,
            voiceCount: 0,
            messages: [],
            voiceCommands: [],
        };

        // Reset state
        setChatMessages([]);
        setVoiceCommands([]);
        setCurrentSession(newSession);

        // Update refs
        chatMessagesRef.current = [];
        voiceCommandsRef.current = [];
        currentSessionRef.current = newSession;

        // Play greeting for new session
        const greeting = "Ready for a new session, Sir.";
        addChatMessage(greeting, 'ai');
        speak(greeting, 'en-US');
    };

    // Initialize current session on mount
    useEffect(() => {
        const sessionId = `session_${Date.now()}`;
        const startTime = new Date();
        sessionStartTimeRef.current = startTime;

        const newSession = {
            id: sessionId,
            startTime: startTime.toLocaleTimeString(),
            messageCount: 0,
            userMessageCount: 0,
            aiMessageCount: 0,
            voiceCount: 0,
            messages: [],
            voiceCommands: [],
        };

        setCurrentSession(newSession);
        // Initialize ref immediately for cleanup safety
        currentSessionRef.current = newSession;

        // Load history from localStorage
        const stored = localStorage.getItem('conversationHistory');
        if (stored) {
            try {
                setConversationHistory(JSON.parse(stored));
            } catch (_e) {
                console.error('Failed to load conversation history:', e);
            }
        }

        // JARVIS PROTOCOL: Initial Greeting
        // Delay slightly to ensure UI is ready
        if (!hasGreetedRef.current) {
            hasGreetedRef.current = true;
            setTimeout(() => {
                const greeting = "At your service, Sir. All systems online.";
                addChatMessage(greeting, 'ai');
                // speak(greeting, 'en-US'); // Removed to prevent robotic fallback voice
            }, 1500);
        }

        // Save current session before unload
        return () => {
            // USE REFS here to get the LATEST data at unmount time
            const session = currentSessionRef.current;
            const msgs = chatMessagesRef.current;
            const cmds = voiceCommandsRef.current;

            console.log('≡ƒÆ╛ Auto-saving session on unmount:', {
                id: session?.id,
                msgCount: msgs.length
            });

            if (session && (msgs.length > 0 || cmds.length > 0)) {
                // Determine duration, preview etc.
                const endTime = new Date();
                const duration = `${Math.floor((endTime.getTime() - startTime.getTime()) / 60000)}m ${Math.floor(((endTime.getTime() - startTime.getTime()) % 60000) / 1000)}s`;
                const preview = msgs.length > 0 ? msgs[0].text : cmds.length > 0 ? cmds[0].command : '';

                const sessionToSave: ConversationSession = {
                    ...session,
                    endTime: endTime.toLocaleTimeString(),
                    duration,
                    preview: preview.substring(0, 100),
                    messages: [...msgs],
                    voiceCommands: [...cmds],
                    messageCount: msgs.length + cmds.length,
                    userMessageCount: msgs.filter(m => m.type === 'user').length + cmds.length,
                    aiMessageCount: msgs.filter(m => m.type === 'ai').length,
                    voiceCount: cmds.length,
                };

                // Directly update localStorage since state updates won't trigger re-render on unmount
                const storedHistory = localStorage.getItem('conversationHistory');
                let history = storedHistory ? JSON.parse(storedHistory) : [];

                // Add to history
                history = [sessionToSave, ...history].slice(0, 50);
                localStorage.setItem('conversationHistory', JSON.stringify(history));

                console.log('Γ£à Session saved to localStorage');
            }
        };
    }, []);

    // Update current session when messages change
    useEffect(() => {
        if (currentSession) {
            setCurrentSession(prev => prev ? {
                ...prev,
                messageCount: chatMessages.length + voiceCommands.length,
                userMessageCount: chatMessages.filter(m => m.type === 'user').length + voiceCommands.length,
                aiMessageCount: chatMessages.filter(m => m.type === 'ai').length,
                voiceCount: voiceCommands.length,
                messages: chatMessages,
                voiceCommands: voiceCommands,
            } : null);
        }
    }, [chatMessages, voiceCommands]);

    const value: DashboardContextType = {
        socket,
        isConnected,
        chatMessages,
        voiceCommands,
        systemStats,
        learningStats,
        systemLogs,
        taskProgress,
        isVoiceActive,
        interimTranscript,
        audioLevel,
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
        loadSession,
        deleteSession,
        startNewSession,
    };

    return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
};
