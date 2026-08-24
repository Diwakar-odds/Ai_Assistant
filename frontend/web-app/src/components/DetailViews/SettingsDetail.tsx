import { motion, _AnimatePresence } from 'framer-motion';
import {
  _Bell, _Lock, _Palette, Globe, Database, Brain, Zap, _DollarSign, _Clock,
  Mic, Volume2, Shield, _Download, _Upload, _RotateCcw, Save, Check, _X,
  Cpu, _MessageSquare, _Key, _Terminal, Server, Layers, Speaker, HardDrive, Activity, _Wifi
} from 'lucide-react';
import { useState, useEffect, useReducer } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { apiUrl } from '../../lib/api';

// --- Interfaces matching app_settings.json ---

interface GeneralSettings {
  language: string;
  secondaryLanguage: string;
  enableHinglish: boolean;
  theme: string;
  animations: boolean;
  startOnBoot: boolean;
}

interface SecuritySettings {
  apiKeys: {
    googleGemini: string;
    openAI: string;
    elevenLabs: string;
  };
  permissions: {
    allowFileDeletion: boolean;
    allowAppExecution: boolean;
    allowWebBrowsing: boolean;
    allowSystemControl: boolean;
  };
  encryption: {
    encryptDatabase: boolean;
    enablePinParams: boolean;
  };
}

interface AISettings {
  defaultProvider: string;
  defaultModel: string;
  temperature: number;
  maxTokens: number;
  contextWindow: number;
  safetySettings: {
    harassment: string;
    hateSpeech: string;
    sexuallyExplicit: string;
    dangerousContent: string;
  };
  localLlm: {
    enabled: boolean;
    modelPath: string;
    useGpu: boolean;
  };
}

interface VoiceSettings {
  tts: {
    engine: string;
    voice: string;
    rate: number;
    volume: number;
    useCache: boolean;
  };
  stt: {
    engine: string;
    model: string;
    sensitivity: number;
    language: string;
    continuous: boolean;
  };
  wakeWord: {
    enabled: boolean;
    phrases: string[];
    sensitivity: number;
  };
}

interface AutomationSettings {
  autoUpdate: boolean;
  autoBackup: string;
  maxHistorySize: number;
  smartHome: {
    enabled: boolean;
    provider: string;
  };
}

interface SystemSettings {
  logLevel: string;
  maxLogSizeMb: number;
  minimizeToTray: boolean;
  notifications: {
    desktop: boolean;
    sound: boolean;
  };
}

interface AppSettings {
  general: GeneralSettings;
  security: SecuritySettings;
  ai: AISettings;
  voice: VoiceSettings;
  automation: AutomationSettings;
  system: SystemSettings;
}

const AI_PROVIDERS = [
  { value: 'gemini', label: '🔷 Google Gemini' },
  { value: 'openai', label: '🟢 OpenAI (GPT)' },
  { value: 'ollama', label: '🤖 Ollama (Local)' },
  { value: 'gguf', label: '🧠 Pulsar 4.6GB (Local GGUF)' }
];

const AI_MODELS: Record<string, string[]> = {
  gemini: ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-flash-latest'],
  openai: ['gpt-4o-mini', 'gpt-3.5-turbo', 'gpt-4o'],
  ollama: ['llama3.2', 'qwen2.5-coder:3b', 'mistral', 'gemma2'],
  gguf: ['pulsar-final-q4_k_m']
};

// --- Component ---

const SettingsDetail = () => {
  const { systemStats } = useDashboard();

  // Use reducer for guaranteed state updates
  const [settings, setSettings] = useReducer(
    (state: AppSettings | null, newState: AppSettings | null) => {
      // If newState is null or undefined, return it as-is
      if (!newState) return newState;
      // Always return a completely new object reference
      return JSON.parse(JSON.stringify(newState));
    },
    null
  );

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<keyof AppSettings | 'all'>('general');

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const res = await fetch(apiUrl('/api/settings/all'));
      const data = await res.json();
      if (data.success) {
        setSettings(data.settings);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (_category: string) => {
    if (!settings) return;

    try {
      setSaving(true);
      const response = await fetch(apiUrl('/api/settings/update'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          _category: _category,
          settings: settings[_category as keyof AppSettings]
        })
      });

      const result = await response.json();
      if (result.success) {
        setSettings(result.settings); // Update local state with returned settings
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
      } else {
        alert('❌ Failed to save: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      alert('❌ Error saving: ' + error);
    } finally {
      setSaving(false);
    }
  };

  const _resetSettings = async (_category?: string) => {
    if (!confirm(`Are you sure you want to reset ${_category || 'all'} settings?`)) return;
    try {
      const response = await fetch(apiUrl('/api/settings/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ _category })
      });
      const result = await response.json();
      if (result.success) {
        setSettings(result.settings);
        alert('✅ Settings reset successfully');
      }
    } catch (error) {
      alert('❌ Error resetting: ' + error);
    }
  };

  // Helper to update state deeply
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleSettingChange = (_category: string, path: string[], value: any) => {
    if (!settings) return;

    // Deep clone entire state
    const newState = JSON.parse(JSON.stringify(settings));

    // Navigate to the _category
    let current = newState[_category];

    // If path is empty, replace the whole _category
    if (path.length === 0) {
      newState[_category] = value;
      setSettings(newState);
      return;
    }

    // Navigate down the path
    for (let i = 0; i < path.length - 1; i++) {
      current = current[path[i]];
    }

    // Set the final value
    current[path[path.length - 1]] = value;

    // Special handling for side effects
    // If voice_id changes, also update voice_name
    if (path[path.length - 1] === 'voice_id') {
      const availableVoices = (newState.voice && newState.voice.tts && newState.voice.tts.available_voices) || [];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const selectedVoice = availableVoices.find((v: any) => v.id === value);
      if (selectedVoice) {
        current['voice_name'] = selectedVoice.name;
      }
    }

    // If defaultProvider changes, auto-select first model
    if (_category === 'ai' && path.length === 1 && path[0] === 'defaultProvider') {
      const newProvider = value as string;
      const availableModels = AI_MODELS[newProvider] || [];
      if (availableModels.length > 0) {
        current['defaultModel'] = availableModels[0];
      }
    }

    // Dispatch the new state (useReducer will deep clone it again)
    setSettings(newState);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#3B82F6] border-t-transparent mb-4"></div>
          <p className="text-[#9CA3AF]">Loading settings...</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Globe },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'ai', label: 'AI & Models', icon: Brain },
    { id: 'voice', label: 'Voice', icon: Mic },
    { id: 'automation', label: 'Automation', icon: Zap },
    { id: 'system', label: 'System', icon: Server },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-20">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Settings</h3>
          <p className="text-[#9CA3AF]">Configure your AI assistant preferences</p>
        </div>

        {saveSuccess && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 bg-[#10B981]/20 text-[#10B981] px-4 py-2 rounded-lg border border-[#10B981]/30"
          >
            <Check className="w-5 h-5" />
            <span>Saved successfully!</span>
          </motion.div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            onClick={() => setActiveTab(tab.id as any)}
            className={`
              flex items-center gap-2 px-4 py-3 rounded-lg font-medium transition-all whitespace-nowrap
              ${activeTab === tab.id
                ? 'bg-[#3B82F6] text-white shadow-lg shadow-[#3B82F6]/20'
                : 'bg-[#2A2D35] text-[#9CA3AF] hover:bg-[#3A3D45] hover:text-white'
              }
            `}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <motion.div
        key={activeTab as string}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="space-y-6"
      >
        {activeTab === 'system' && (
          <LiveMetrics stats={systemStats} />
        )}

        {/* Special layout for Voice tab */}
        {activeTab === 'voice' && settings?.voice && (
          <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg">
            <div className="p-6 border-b border-[#2A2D35] flex justify-between items-center">
              <h4 className="text-xl font-semibold text-white">Voice Configuration</h4>
              <button
                onClick={() => saveSettings('voice')}
                disabled={saving}
                className="px-6 py-2 bg-[#3B82F6] text-white rounded-lg hover:bg-[#2563EB] transition-colors font-semibold disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> : <Save className="w-4 h-4" />}
                <span>Save Changes</span>
              </button>
            </div>

            <div className="p-6 grid grid-cols-3 gap-4">
              {/* STT Column */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#10B981] font-medium mb-3 flex items-center gap-2 text-sm">
                  <Mic className="w-4 h-4" />
                  STT (Speech-to-Text)
                </h5>
                <div className="space-y-3">
                  <RecursiveFormRenderer
                    data={settings.voice.stt}
                    onChange={(path, val) => handleSettingChange('voice', path, val)}
                    path={['stt']}
                    rootData={settings.voice}
                    depth={1}
                  />
                </div>
              </div>

              {/* TTS Column */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#3B82F6] font-medium mb-3 flex items-center gap-2 text-sm">
                  <Volume2 className="w-4 h-4" />
                  TTS (Text-to-Speech)
                </h5>
                <div className="space-y-3">
                  <RecursiveFormRenderer
                    data={settings.voice.tts}
                    onChange={(path, val) => handleSettingChange('voice', path, val)}
                    path={['tts']}
                    rootData={settings.voice}
                    depth={1}
                  />
                </div>
              </div>

              {/* Wake Word Column */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#8B5CF6] font-medium mb-3 flex items-center gap-2 text-sm">
                  <Speaker className="w-4 h-4" />
                  Wake Word
                </h5>
                <div className="space-y-3">
                  <RecursiveFormRenderer
                    data={settings.voice.wakeWord}
                    onChange={(path, val) => handleSettingChange('voice', path, val)}
                    path={['wakeWord']}
                    rootData={settings.voice}
                    depth={1}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Special layout for AI tab */}
        {activeTab === 'ai' && settings?.ai && (
          <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg">
            <div className="p-6 border-b border-[#2A2D35] flex justify-between items-center">
              <h4 className="text-xl font-semibold text-white">AI Configuration</h4>
              <button
                onClick={() => saveSettings('ai')}
                disabled={saving}
                className="px-6 py-2 bg-[#3B82F6] text-white rounded-lg hover:bg-[#2563EB] transition-colors font-semibold disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> : <Save className="w-4 h-4" />}
                <span>Save Changes</span>
              </button>
            </div>

            <div className="p-6 grid grid-cols-3 gap-4">
              {/* Column 1: Core Settings */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#3B82F6] font-medium mb-3 flex items-center gap-2 text-sm">
                  <Brain className="w-4 h-4" />
                  Core Settings
                </h5>
                <div className="space-y-3">
                  {/* Manually render top-level fields */}
                  {['defaultProvider', 'defaultModel', 'temperature', 'maxTokens', 'contextWindow'].map(key => {
                    const value = settings.ai[key as keyof AISettings];
                    // Create a mini data object for the renderer to handle just this field
                    const fieldData = { [key]: value };

                    return (
                      <RecursiveFormRenderer
                        key={key}
                        data={fieldData}
                        onChange={(path, val) => handleSettingChange('ai', path, val)}
                        path={[]} // Path is relative to the data passed, so empty here
                        rootData={settings.ai} // Pass full AI settings as root for dependency lookups (like provider->model)
                        depth={1}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Column 2: Safety Settings */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#10B981] font-medium mb-3 flex items-center gap-2 text-sm">
                  <Shield className="w-4 h-4" />
                  Safety Settings
                </h5>
                <div className="space-y-3">
                  <RecursiveFormRenderer
                    data={settings.ai.safetySettings}
                    onChange={(path, val) => handleSettingChange('ai', ['safetySettings', ...path], val)}
                    path={['safetySettings']}
                    rootData={settings.ai}
                    depth={1}
                  />
                </div>
              </div>

              {/* Column 3: Local LLM */}
              <div className="border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
                <h5 className="text-[#8B5CF6] font-medium mb-3 flex items-center gap-2 text-sm">
                  <HardDrive className="w-4 h-4" />
                  Local LLM
                </h5>
                <div className="space-y-3">
                  <RecursiveFormRenderer
                    data={settings.ai.localLlm}
                    onChange={(path, val) => handleSettingChange('ai', ['localLlm', ...path], val)}
                    path={['localLlm']}
                    rootData={settings.ai}
                    depth={1}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Default layout for other tabs */}
        {settings && settings[activeTab as keyof AppSettings] && activeTab !== 'voice' && activeTab !== 'ai' && (
          <EditableSection
            key={activeTab} // Force re-render on tab change to reset path context
            title={tabs.find(t => t.id === activeTab)?.label || ''}
            data={settings[activeTab as keyof AppSettings]}
            _category={activeTab as string}
            onChange={(path, val) => handleSettingChange(activeTab as string, path, val)}
            onSave={() => saveSettings(activeTab as string)}
            saving={saving}
          />
        )}
      </motion.div>
    </div>
  );
};

// --- Sub-components ---

const EditableSection = ({ title, data, _category, onChange, onSave, saving }: {
  title: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any,
  _category: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onChange: (path: string[], val: any) => void,
  onSave: () => void,
  saving: boolean
}) => {
  return (
    <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg flex flex-col h-full">
      <div className="p-6 border-b border-[#2A2D35] flex justify-between items-center sticky top-0 bg-[#1F2228] z-10 rounded-t-lg">
        <h4 className="text-xl font-semibold text-white">{title} Configuration</h4>

        <button
          onClick={onSave}
          disabled={saving}
          className="px-6 py-2 bg-[#3B82F6] text-white rounded-lg hover:bg-[#2563EB] transition-colors font-semibold disabled:opacity-50 flex items-center gap-2"
        >
          {saving ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> : <Save className="w-4 h-4" />}
          <span>Save Changes</span>
        </button>
      </div>

      <div className="p-6">
        <RecursiveFormRenderer data={data} onChange={onChange} path={[]} rootData={data} />
      </div>
    </div>
  );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const RecursiveFormRenderer = ({ data, onChange, path, rootData, depth = 0 }: { data: any, onChange: (path: string[], val: any) => void, path: string[], rootData?: any, depth?: number }) => {
  // Use rootData to look up siblings if needed (like defaultProvider)
  // If rootData is not passed, use data (only works at top level)
  const contextData = rootData || data;

  return (
    <div className="grid grid-cols-1 gap-3">
      {Object.entries(data).map(([key, value]) => {
        const currentPath = [...path, key];
        const label = key.replace(/([A-Z])/g, ' $1').trim();

        // Sub-section (nested object) - SKIP if depth > 0 (we're already inside a voice column)
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          if (depth > 0) {
            // We're inside a voice column, don't create subsections - just skip rendering this as a section
            // This prevents the duplicate blue boxes
            return null;
          }

          return (
            <div key={key} className="col-span-3 border border-[#3A3D45] p-4 rounded-lg bg-[#252830]/50">
              <h5 className="text-[#3B82F6] font-medium mb-3 capitalize flex items-center gap-2 text-sm">
                <Layers className="w-4 h-4" />
                {label}
              </h5>
              {/* Pass rootData down so children can access top-level context if needed (though tricky with recursion) */}
              {/* Actually simpler: just recursively render. Sibling lookups need to be done carefully. */}
              <RecursiveFormRenderer data={value} onChange={onChange} path={currentPath} rootData={contextData} depth={depth + 1} />
            </div>
          );
        }

        // Special Handling: AI Provider Dropdown (Top Level)
        if (key === 'defaultProvider') {
          return (
            <div key={key} className="space-y-1.5">
              <label className="text-white text-xs font-medium capitalize block">{label}</label>
              <div className="relative">
                <select
                  value={String(value)}
                  onChange={(e) => onChange(currentPath, e.target.value)}
                  className="w-full p-2.5 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white text-sm focus:border-[#3B82F6] outline-none appearance-none cursor-pointer hover:border-[#3B82F6]/50 transition-colors"
                >
                  {AI_PROVIDERS.map((provider) => (
                    <option key={provider.value} value={provider.value}>{provider.label}</option>
                  ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#9CA3AF] text-xs">▼</div>
              </div>
            </div>
          );
        }

        // Special Handling: TTS Voice Dropdown
        if (key === 'voice_id') {
          // Check if available_voices exists as a sibling or in contextData
          const availableVoices = data.available_voices || contextData.available_voices || (contextData.tts && contextData.tts.available_voices);

          if (availableVoices && Array.isArray(availableVoices) && availableVoices.length > 0) {
            return (
              <div key={key} className="space-y-1.5">
                <label className="text-white text-xs font-medium capitalize block">TTS Voice</label>
                <div className="relative">
                  <select
                    value={String(value)}
                    onChange={(e) => onChange(currentPath, e.target.value)}
                    className="w-full p-2.5 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white text-sm focus:border-[#3B82F6] outline-none appearance-none cursor-pointer hover:border-[#3B82F6]/50 transition-colors"
                  >
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    {availableVoices.map((voice: any) => (
                      <option key={voice.id} value={voice.id}>
                        {(voice as any).name} ({voice.gender}, {voice.accent})
                      </option>
                    ))}
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#9CA3AF] text-xs">▼</div>
                </div>
              </div>
            );
          }
        }

        // Skip voice_name and available_voices from rendering (handled by voice_id)
        if (key === 'voice_name' || key === 'available_voices') {
          return null;
        }

        if (key === 'engine' && path.includes('stt')) {
          const engines = [
            { value: 'whisper', label: 'Whisper (High Accuracy)' },
            { value: 'google', label: 'Google Cloud STT' }
          ];
          return (
            <div key={key} className="space-y-2">
              <label className="text-white text-sm font-medium capitalize block">STT Engine</label>
              <div className="relative">
                <select
                  value={String(value)}
                  onChange={(e) => onChange(currentPath, e.target.value)}
                  className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none appearance-none cursor-pointer hover:border-[#3B82F6]/50 transition-colors"
                >
                  {engines.map((engine) => (
                    <option key={engine.value} value={engine.value}>{engine.label}</option>
                  ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#9CA3AF]">▼</div>
              </div>
            </div>
          );
        }


        // Special Handling: STT Model - only show for Whisper
        if (key === 'model' && path.includes('stt')) {
          // Check if engine is Google (if so, don't show model field)
          const currentEngine = data['engine'] || 'whisper';
          if (currentEngine === 'google') {
            return null; // Hide model field for Google
          }

          return (
            <div key={key} className="space-y-1.5">
              <label className="text-white text-xs font-medium capitalize block">Model</label>
              <input
                type="text"
                value={String(value)}
                onChange={(e) => onChange(currentPath, e.target.value)}
                className="w-full p-2.5 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white text-sm focus:border-[#3B82F6] outline-none"
                placeholder={currentEngine === 'whisper' ? 'whisper-medium' : 'google-cloud-default'}
              />
              <p className="text-xs text-[#6B7280]">Required for {currentEngine === 'whisper' ? 'Whisper' : 'Google'}</p>
            </div>
          );
        }

        // Special Handling: AI Model Dropdown (Top Level)
        if (key === 'defaultModel') {
          // Look up 'defaultProvider' in the CURRENT data object (siblings) OR rootData
          const currentProvider = data['defaultProvider'] || (rootData && rootData['defaultProvider']) || 'google';
          const availableModels = AI_MODELS[currentProvider] || [];

          return (
            <div key={key} className="space-y-2">
              <label className="text-white text-sm font-medium capitalize block">{label}</label>
              {availableModels.length > 0 ? (
                <div className="relative">
                  <select
                    value={String(value)}
                    onChange={(e) => onChange(currentPath, e.target.value)}
                    className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none appearance-none cursor-pointer hover:border-[#3B82F6]/50 transition-colors"
                  >
                    {availableModels.map((model) => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#9CA3AF]">▼</div>
                </div>
              ) : (
                <input
                  type="text"
                  value={String(value)}
                  onChange={(e) => onChange(currentPath, e.target.value)}
                  className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none"
                  placeholder="Enter model name"
                />
              )}
            </div>
          );
        }

        // Array (Simple comma separated for now)
        if (Array.isArray(value)) {
          // Safely convert array to string
          const arrayValue = value.filter(v => v != null).join(', ');

          return (
            <div key={key} className="space-y-2 col-span-1 md:col-span-2">
              <label className="text-white text-sm font-medium capitalize block">{label}</label>
              <input
                type="text"
                value={arrayValue}
                onChange={(e) => {
                  const newValue = e.target.value
                    .split(',')
                    .map(s => s.trim())
                    .filter(s => s.length > 0);
                  onChange(currentPath, newValue);
                }}
                className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none"
                placeholder="Comma separated values (e.g., hey daddy, hey assistant)"
              />
              <p className="text-xs text-[#6B7280]">Separate multiple values with commas</p>
            </div>
          );
        }

        // Boolean
        if (typeof value === 'boolean') {
          return (
            <label key={key} className="flex items-center gap-2.5 p-3 bg-[#2A2D35] rounded-lg cursor-pointer border border-[#3A3D45] hover:border-[#3B82F6]/50 transition-all group h-full pointer-events-auto">
              <div className="relative flex items-center pointer-events-auto">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => onChange(currentPath, e.target.checked)}
                  className="peer sr-only pointer-events-auto"
                />
                <div className={`w-10 h-6 rounded-full transition-colors relative ${value ? 'bg-[#3B82F6]' : 'bg-[#1F2228]'} border border-[#3A3D45]`}>
                  <div className={`absolute top-[1px] left-[1px] bg-white rounded-full h-5 w-5 transition-transform shadow-sm ${value ? 'translate-x-full border-transparent' : 'border-gray-300'}`}></div>
                </div>
              </div>
              <div className="flex-1">
                <span className="text-white text-sm font-medium capitalize block group-hover:text-[#3B82F6] transition-colors">{label}</span>
                <span className={`text-xs ${value ? 'text-[#3B82F6]' : 'text-[#9CA3AF]'}`}>{value ? 'Enabled' : 'Disabled'}</span>
              </div>
            </label>
          );
        }

        // Number
        if (typeof value === 'number') {
          return (
            <div key={key} className="space-y-2">
              <label className="text-white text-sm font-medium capitalize block">{label}</label>
              <input
                type="number"
                value={value}
                onChange={(e) => onChange(currentPath, parseFloat(e.target.value))}
                className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none"
              />
            </div>
          );
        }

        // String (Default)
        return (
          <div key={key} className="space-y-2">
            <label className="text-white text-sm font-medium capitalize block">{label}</label>
            <input
              type="text"
              value={String(value)}
              onChange={(e) => onChange(currentPath, e.target.value)}
              className="w-full p-3 bg-[#2A2D35] border border-[#3A3D45] rounded-lg text-white focus:border-[#3B82F6] outline-none"
            />
          </div>
        );
      })}
    </div>
  );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const LiveMetrics = ({ stats }: { stats: any }) => {
  if (!stats) return null;

  const metrics = [
    { label: 'CPU Load', value: `${stats.cpu}%`, icon: Cpu, color: '#3B82F6' },
    { label: 'Memory', value: `${stats.memory}%`, icon: HardDrive, color: '#10B981' },
    { label: 'Disk', value: `${stats.disk || 0}%`, icon: Database, color: '#8B5CF6' },
    { label: 'Network', value: stats.network, icon: Activity, color: '#F59E0B' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {metrics.map((m) => (
        <div key={m.label} className="bg-[#1F2228] border border-[#2A2D35] p-4 rounded-lg flex items-center gap-4">
          <div className="p-3 rounded-lg bg-[#2A2D35]" style={{ color: m.color }}>
            <m.icon className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[#9CA3AF] text-xs uppercase font-medium">{m.label}</p>
            <p className="text-white text-xl font-bold">{m.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SettingsDetail;
