import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { apiUrl } from '../../lib/api';
import { useDashboard } from '../../contexts/DashboardContext';

export interface GeneralSettings {
  language: string;
  secondaryLanguage: string;
  enableHinglish: boolean;
  theme: string;
  animations: boolean;
  startOnBoot: boolean;
  hotkey?: string;
  hotkeyEnabled?: boolean;
}

export interface SecuritySettings {
  apiKeys: {
    googleGemini: string;
    openAI: string;
    anthropic?: string;
    elevenLabs: string;
    [key: string]: string | undefined;
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

export interface AISettings {
  defaultProvider: string;
  defaultModel: string;
  temperature: number;
  maxTokens: number;
  contextWindow: number;
  safetySettings: {
    dangerousContent: string;
    harassment: string;
    hateSpeech: string;
    sexuallyExplicit: string;
  };
  localLlm: {
    enabled: boolean;
    modelPath: string;
    useGpu: boolean;
  };
}

export interface VoiceSettings {
  tts: {
    enabled: boolean;
    engine: string;
    voice_id: string;
    voice_name: string;
    speed: number;
    pitch: number;
    volume: number;
    useCache: boolean;
    available_voices?: Array<{
      id: string;
      name: string;
      gender?: string;
      accent?: string;
      engine?: string;
    }>;
  };
  stt: {
    enabled: boolean;
    engine: string;
    model: string;
    sensitivity: number;
    language: string;
    continuous: boolean;
    noise_reduction?: boolean;
  };
  wakeWord: {
    enabled: boolean;
    phrases: string[];
    sensitivity: number;
  };
  persona?: {
    style: string;
    assistantName: string;
    userTitle: string;
    languageMode: string;
    wakeAckEnabled: boolean;
    preTaskReports: boolean;
    postTaskReports: boolean;
    dynamicGeneration: boolean;
    recentMemorySize: number;
    customInstructions?: string;
  };
}

export interface AutomationSettings {
  autoUpdate: boolean;
  autoBackup: string;
  maxHistorySize: number;
  smartHome: {
    enabled: boolean;
    provider: string;
  };
}

export interface SystemSettings {
  logLevel: string;
  maxLogSizeMb: number;
  minimizeToTray: boolean;
  desktopOverlay: boolean;
  screenShareStealth?: boolean;
  companion?: {
    alwaysOnTop: boolean;
    size: 'small' | 'medium' | 'large';
    opacity: number;
    autoHide: boolean;
  };
  notifications: {
    desktop: boolean;
    sound: boolean;
  };
}

export interface AppSettings {
  onboarded?: boolean;
  general: GeneralSettings;
  security: SecuritySettings;
  ai: AISettings;
  voice: VoiceSettings;
  automation: AutomationSettings;
  system: SystemSettings;
}

export interface SettingsContextType {
  settings: AppSettings | null;
  loading: boolean;
  dirtyCategories: Set<string>;
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  errorMessage: string | null;
  activeSection: string;
  setActiveSection: (sec: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  dynamicGgufModels: string[];
  updateSetting: (category: string, path: string[], value: any) => void;
  resetCategory: (category: string) => Promise<boolean>;
  resetAll: () => Promise<boolean>;
  exportSettings: () => void;
  importSettings: (file: File) => Promise<boolean>;
}

const SettingsContext = createContext<SettingsContextType | null>(null);

export const DEFAULT_GGUF_MODELS = [
  'pulsar-final-q4_k_m',
  'pulsar-v2-checkpoint-23000-Q3_K_M',
];

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { setDesktopOverlayEnabled, socket } = useDashboard();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [dirtyCategories, setDirtyCategories] = useState<Set<string>>(new Set());
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('general');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [dynamicGgufModels, setDynamicGgufModels] = useState<string[]>(DEFAULT_GGUF_MODELS);

  const overlayRef = useRef(setDesktopOverlayEnabled);
  overlayRef.current = setDesktopOverlayEnabled;

  // References for debouncing
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const latestSettingsRef = useRef<AppSettings | null>(null);
  latestSettingsRef.current = settings;
  const dirtyCategoriesRef = useRef<Set<string>>(dirtyCategories);
  dirtyCategoriesRef.current = dirtyCategories;

  // 1. Initial Load - stable callback
  const fetchInitialSettings = useCallback(async () => {
    try {
      setLoading(true);
      const [allRes, localRes] = await Promise.all([
        fetch(apiUrl('/api/settings/all')).then((r) => r.json()).catch(() => null),
        fetch(apiUrl('/api/local_ai/status')).then((r) => r.json()).catch(() => null),
      ]);

      if (allRes?.success && allRes.settings) {
        const loaded = allRes.settings as AppSettings;
        if (loaded.system && typeof loaded.system.desktopOverlay !== 'boolean') {
          loaded.system.desktopOverlay = true;
        }
        if (loaded.system && typeof loaded.system.screenShareStealth !== 'boolean') {
          loaded.system.screenShareStealth = true;
        }
        setSettings(loaded);
        if (typeof loaded.system?.desktopOverlay === 'boolean') {
          overlayRef.current?.(loaded.system.desktopOverlay);
        }
      }

      if (localRes) {
        const discovered = localRes.available_gguf_models || localRes.gguf?.available_models;
        if (Array.isArray(discovered) && discovered.length > 0) {
          setDynamicGgufModels(Array.from(new Set([...discovered, ...DEFAULT_GGUF_MODELS])));
        }
      }
    } catch (err) {
      console.error('[SettingsContext] Failed to load settings:', err);
      setErrorMessage('Failed to load settings from server');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialSettings();
  }, [fetchInitialSettings]);

  // 2. Real-time WebSocket settings synchronization
  useEffect(() => {
    if (!socket) return;

    const handleSettingsUpdated = (data: any) => {
      if (!data) return;
      if (data.all_settings) {
        setSettings((prev) => {
          if (!prev) return data.all_settings;
          const next = { ...data.all_settings };
          dirtyCategoriesRef.current.forEach((dirtyCat) => {
            if ((prev as any)[dirtyCat]) {
              next[dirtyCat] = (prev as any)[dirtyCat];
            }
          });
          return next;
        });
      }
    };

    socket.on('settings_updated', handleSettingsUpdated);
    return () => {
      socket.off('settings_updated', handleSettingsUpdated);
    };
  }, [socket]);

  // 3. Save function for dirty categories
  const saveDirtyCategories = useCallback(async () => {
    const categoriesToSave = Array.from(dirtyCategoriesRef.current);
    if (categoriesToSave.length === 0 || !latestSettingsRef.current) return;

    setSaveStatus('saving');
    try {
      for (const cat of categoriesToSave) {
        const catPayload = (latestSettingsRef.current as any)[cat];
        if (!catPayload) continue;

        const res = await fetch(apiUrl('/api/settings/update'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            category: cat,
            settings: catPayload,
          }),
        });

        const result = await res.json();
        if (!result.success) {
          throw new Error(result.error || `Failed to update ${cat}`);
        }
      }

      setDirtyCategories(new Set());
      setSaveStatus('saved');
      setTimeout(() => {
        setSaveStatus((curr) => (curr === 'saved' ? 'idle' : curr));
      }, 2000);
    } catch (err: any) {
      console.error('[SettingsContext] Auto-save error:', err);
      setSaveStatus('error');
      setErrorMessage(err.message || 'Auto-save failed');
    }
  }, []);

  // 4. Update Setting Mutator
  const updateSetting = useCallback(
    (category: string, path: string[], value: any) => {
      setSettings((prev) => {
        if (!prev) return prev;
        const next: AppSettings = JSON.parse(JSON.stringify(prev));
        let curr: any = (next as any)[category];
        if (!curr) return prev;

        if (path.length === 0) {
          (next as any)[category] = value;
        } else {
          for (let i = 0; i < path.length - 1; i++) {
            curr = curr[path[i]];
          }
          curr[path[path.length - 1]] = value;
        }

        // Special side-effect: instant sync for Minimized Desktop Overlay
        if (category === 'system' && path.length === 1 && path[0] === 'desktopOverlay') {
          const enabled = Boolean(value);
          overlayRef.current?.(enabled);
          fetch(apiUrl('/api/settings/update'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              category: 'system',
              settings: { desktopOverlay: enabled },
            }),
          }).catch((e) => console.error('Failed instant overlay sync:', e));
        }

        return next;
      });

      setDirtyCategories((prev) => {
        const next = new Set(prev);
        next.add(category);
        return next;
      });

      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        saveDirtyCategories();
      }, 800);
    },
    [saveDirtyCategories]
  );

  // 5. Reset Category
  const resetCategory = useCallback(
    async (category: string): Promise<boolean> => {
      try {
        setSaveStatus('saving');
        const res = await fetch(apiUrl('/api/settings/reset'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category }),
        });
        const result = await res.json();
        if (result.success && result.settings) {
          setSettings(result.settings);
          setDirtyCategories((prev) => {
            const next = new Set(prev);
            next.delete(category);
            return next;
          });
          setSaveStatus('saved');
          setTimeout(() => setSaveStatus('idle'), 2000);
          return true;
        }
        return false;
      } catch (err) {
        console.error('Reset error:', err);
        setSaveStatus('error');
        return false;
      }
    },
    []
  );

  // 6. Reset All
  const resetAll = useCallback(async (): Promise<boolean> => {
    try {
      setSaveStatus('saving');
      const res = await fetch(apiUrl('/api/settings/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const result = await res.json();
      if (result.success && result.settings) {
        setSettings(result.settings);
        setDirtyCategories(new Set());
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 2000);
        return true;
      }
      return false;
    } catch (err) {
      console.error('Reset all error:', err);
      setSaveStatus('error');
      return false;
    }
  }, []);

  // 7. Export Settings JSON
  const exportSettings = useCallback(() => {
    if (!settings) return;
    const blob = new Blob([JSON.stringify(settings, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pulsar_settings_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [settings]);

  // 8. Import Settings JSON
  const importSettings = useCallback(
    async (file: File): Promise<boolean> => {
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        setSaveStatus('saving');
        const res = await fetch(apiUrl('/api/settings/save'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed),
        });
        const result = await res.json();
        if (result.success) {
          await fetchInitialSettings();
          setSaveStatus('saved');
          setTimeout(() => setSaveStatus('idle'), 2000);
          return true;
        }
        return false;
      } catch (err) {
        console.error('Import error:', err);
        setSaveStatus('error');
        return false;
      }
    },
    [fetchInitialSettings]
  );

  return (
    <SettingsContext.Provider
      value={{
        settings,
        loading,
        dirtyCategories,
        saveStatus,
        errorMessage,
        activeSection,
        setActiveSection,
        searchQuery,
        setSearchQuery,
        dynamicGgufModels,
        updateSetting,
        resetCategory,
        resetAll,
        exportSettings,
        importSettings,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = (): SettingsContextType => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};
