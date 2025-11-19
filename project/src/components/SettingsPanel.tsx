import { useState, useEffect } from 'react';
import { Bell, Shield, Palette, Zap, Globe, Users, Save, RefreshCw, Download, Upload } from 'lucide-react';

interface Setting {
  name: string;
  enabled: boolean;
  description?: string;
}

interface SettingsCategory {
  title: string;
  icon: any;
  color: string;
  settings: Setting[];
}

interface SettingsPanelProps {
  theme: string;
  setTheme: (theme: string) => void;
  language?: string;
  setLanguage?: (language: string) => void;
}

const SettingsPanel = ({ theme, setTheme, language = 'hinglish', setLanguage }: SettingsPanelProps) => {
  const [settings, setSettings] = useState<SettingsCategory[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);

  const initialSettings: SettingsCategory[] = [
    {
      title: 'Notifications',
      icon: Bell,
      color: 'from-[#00CEC9] to-[#6C5CE7]',
      settings: [
        { name: 'Desktop Notifications', enabled: true, description: 'Show system notifications for important events' },
        { name: 'Sound Alerts', enabled: false, description: 'Play sound when notifications appear' },
        { name: 'Email Digest', enabled: true, description: 'Receive daily email summaries' },
      ],
    },
    {
      title: 'Security & Privacy',
      icon: Shield,
      color: 'from-[#6C5CE7] to-[#E17055]',
      settings: [
        { name: 'Two-Factor Authentication', enabled: true, description: 'Require 2FA for sensitive operations' },
        { name: 'Biometric Lock', enabled: true, description: 'Use fingerprint or face recognition' },
        { name: 'Data Encryption', enabled: true, description: 'Encrypt all stored data' },
      ],
    },
    {
      title: 'Appearance',
      icon: Palette,
      color: 'from-[#00B894] to-[#00CEC9]',
      settings: [
        { name: 'Dark Mode', enabled: theme === 'dark', description: 'Use dark theme interface' },
        { name: 'High Contrast', enabled: false, description: 'Increase contrast for accessibility' },
        { name: 'Animations', enabled: true, description: 'Enable UI animations and transitions' },
      ],
    },
    {
      title: 'Language & Region',
      icon: Globe,
      color: 'from-[#E84393] to-[#6C5CE7]',
      settings: [
        { name: 'Hindi Support', enabled: language === 'hindi' || language === 'hinglish', description: 'Enable Hindi language support' },
        { name: 'English Support', enabled: language === 'english' || language === 'hinglish', description: 'Enable English language support' },
        { name: 'Hinglish Mode', enabled: language === 'hinglish', description: 'Enable mixed Hindi-English (Hinglish)' },
        { name: 'Auto Language Detection', enabled: true, description: 'Automatically detect input language' },
        { name: 'Voice in Hindi', enabled: language !== 'english', description: 'Use Hindi for voice recognition and TTS' },
        { name: 'Translation Cache', enabled: true, description: 'Cache translations for better performance' },
      ],
    },
    {
      title: 'Performance',
      icon: Zap,
      color: 'from-[#E17055] to-[#00B894]',
      settings: [
        { name: 'Hardware Acceleration', enabled: true, description: 'Use GPU for better performance' },
        { name: 'Background Processing', enabled: true, description: 'Allow processing when minimized' },
        { name: 'Auto Optimization', enabled: false, description: 'Automatically optimize system resources' },
      ],
    },
    {
      title: 'Integrations',
      icon: Users,
      color: 'from-[#00CEC9] to-[#00B894]',
      settings: [
        { name: 'Calendar Sync', enabled: true, description: 'Sync with system calendar' },
        { name: 'Cloud Storage', enabled: true, description: 'Enable cloud backup and sync' },
        { name: 'Smart Home', enabled: false, description: 'Connect to smart home devices' },
      ],
    },
    {
      title: 'AI Behavior',
      icon: Users,
      color: 'from-[#6C5CE7] to-[#00CEC9]',
      settings: [
        { name: 'Personalized Suggestions', enabled: true, description: 'Learn from your usage patterns' },
        { name: 'Usage Analytics', enabled: true, description: 'Collect anonymous usage data' },
        { name: 'Contextual Help', enabled: true, description: 'Show contextual tips and hints' },
      ],
    },
  ];

  useEffect(() => {
    // Load settings from localStorage
    const savedSettings = localStorage.getItem('yourdaddy-settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(parsed);
        setLastSaved(localStorage.getItem('yourdaddy-settings-timestamp'));
      } catch (error) {
        console.error('Failed to load settings:', error);
        setSettings(initialSettings);
      }
    } else {
      setSettings(initialSettings);
    }
  }, []);

  useEffect(() => {
    // Sync Dark Mode setting with theme
    setSettings(prev => prev.map(category => 
      category.title === 'Appearance' 
        ? {
            ...category,
            settings: category.settings.map(setting => 
              setting.name === 'Dark Mode'
                ? { ...setting, enabled: theme === 'dark' }
                : setting
            )
          }
        : category
    ));
  }, [theme]);

  const toggleSetting = (categoryIndex: number, settingIndex: number) => {
    setSettings(prev => {
      const newSettings = [...prev];
      const category = { ...newSettings[categoryIndex] };
      const setting = { ...category.settings[settingIndex] };
      
      setting.enabled = !setting.enabled;
      category.settings = [...category.settings];
      category.settings[settingIndex] = setting;
      newSettings[categoryIndex] = category;
      
      // Special handling for theme setting
      if (category.title === 'Appearance' && setting.name === 'Dark Mode') {
        setTheme(setting.enabled ? 'dark' : 'light');
      }
      
      setHasChanges(true);
      return newSettings;
    });
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      // Save to localStorage
      localStorage.setItem('yourdaddy-settings', JSON.stringify(settings));
      localStorage.setItem('yourdaddy-settings-timestamp', new Date().toISOString());
      
      // Also try to save to backend
      try {
        await fetch('/api/settings/save', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ settings }),
        });
      } catch (error) {
        console.warn('Failed to save to backend, using local storage only:', error);
      }
      
      setHasChanges(false);
      setLastSaved(new Date().toLocaleString());
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const resetSettings = () => {
    setSettings(initialSettings);
    setHasChanges(true);
    localStorage.removeItem('yourdaddy-settings');
    localStorage.removeItem('yourdaddy-settings-timestamp');
  };

  const exportSettings = () => {
    const dataStr = JSON.stringify(settings, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'yourdaddy-settings.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const importSettings = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const imported = JSON.parse(e.target?.result as string);
          setSettings(imported);
          setHasChanges(true);
        } catch (error) {
          console.error('Failed to import settings:', error);
          alert('Invalid settings file format');
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="min-h-screen py-8 animate-fade-in">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-gradient">Settings & Control Panel</h1>
          <p className="text-[#DDDDDD]">Customize your AI assistant experience</p>
          {lastSaved && (
            <p className="text-sm text-green-400 mt-1">Last saved: {lastSaved}</p>
          )}
        </div>
        <div className="flex items-center gap-4">
          {hasChanges && (
            <span className="text-yellow-400 text-sm">● Unsaved changes</span>
          )}
          <button
            onClick={saveSettings}
            disabled={!hasChanges || saving}
            className="px-4 py-2 bg-[#00B894] rounded-lg hover:bg-[#009A7A] transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save Settings
              </>
            )}
          </button>
          <button
            onClick={resetSettings}
            className="px-4 py-2 bg-[#E17055] rounded-lg hover:bg-[#D55A3A] transition-colors flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Reset
          </button>
        </div>
      </div>

      {/* Language Selection Panel */}
      {setLanguage && (
        <div className="glass-strong p-6 rounded-2xl mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold mb-2 flex items-center gap-2">
                <Globe className="text-[#6C5CE7]" size={20} />
                Language & Region
              </h3>
              <p className="text-[#DDDDDD] text-sm mb-4">
                Choose your preferred language for interaction and interface
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setLanguage('english')}
              className={`p-4 rounded-xl border-2 transition-all hover-lift ${
                language === 'english'
                  ? 'border-[#6C5CE7] bg-[#6C5CE7]/20'
                  : 'border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="text-center">
                <div className="text-2xl mb-2">🇺🇸</div>
                <h4 className="font-semibold">English</h4>
                <p className="text-sm text-[#DDDDDD]">Pure English interface</p>
              </div>
            </button>
            
            <button
              onClick={() => setLanguage('hindi')}
              className={`p-4 rounded-xl border-2 transition-all hover-lift ${
                language === 'hindi'
                  ? 'border-[#6C5CE7] bg-[#6C5CE7]/20'
                  : 'border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="text-center">
                <div className="text-2xl mb-2">🇮🇳</div>
                <h4 className="font-semibold">Hindi</h4>
                <p className="text-sm text-[#DDDDDD]">Pure Hindi interface</p>
              </div>
            </button>
            
            <button
              onClick={() => setLanguage('hinglish')}
              className={`p-4 rounded-xl border-2 transition-all hover-lift ${
                language === 'hinglish'
                  ? 'border-[#6C5CE7] bg-[#6C5CE7]/20'
                  : 'border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="text-center">
                <div className="text-2xl mb-2">🇮🇳🇺🇸</div>
                <h4 className="font-semibold">Hinglish</h4>
                <p className="text-sm text-[#DDDDDD]">Mixed Hindi-English</p>
              </div>
            </button>
          </div>
          
          <div className="mt-4 p-3 bg-blue-500/20 rounded-lg">
            <p className="text-sm text-blue-300">
              <strong>Current:</strong> {language === 'english' ? 'English' : language === 'hindi' ? 'Hindi' : 'Hinglish'} 
              {language === 'hinglish' && ' - You can mix Hindi and English naturally!'}
            </p>
          </div>
        </div>
      )}

      {/* Import/Export Section */}
      <div className="glass-strong p-4 rounded-2xl mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-1">Settings Management</h3>
            <p className="text-sm text-[#DDDDDD]">Backup and restore your settings</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={exportSettings}
              className="px-3 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors flex items-center gap-2"
            >
              <Download size={16} />
              Export
            </button>
            <label className="px-3 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors flex items-center gap-2 cursor-pointer">
              <Upload size={16} />
              Import
              <input
                type="file"
                accept=".json"
                onChange={importSettings}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {settings.map((category, categoryIndex) => {
          const Icon = category.icon;
          return (
            <div key={categoryIndex} className="glass-strong p-6 rounded-2xl hover-lift">
              <div className="flex items-center gap-3 mb-6">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${category.color} flex items-center justify-center`}>
                  <Icon size={24} />
                </div>
                <h2 className="text-xl font-bold">{category.title}</h2>
              </div>
              <div className="space-y-4">
                {category.settings.map((setting, settingIndex) => (
                  <div key={settingIndex} className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <span className="text-white font-medium">{setting.name}</span>
                        {setting.description && (
                          <p className="text-sm text-[#DDDDDD]/70 mt-1">{setting.description}</p>
                        )}
                      </div>
                      <button
                        onClick={() => toggleSetting(categoryIndex, settingIndex)}
                        className={`w-12 h-6 rounded-full cursor-pointer relative transition-all duration-300 flex-shrink-0 ml-3 ${
                          setting.enabled
                            ? 'bg-gradient-to-r ' + category.color
                            : 'bg-white/20'
                        }`}
                        title={`Toggle ${setting.name}`}
                      >
                        <div
                          className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all duration-300 ${
                            setting.enabled ? 'right-1' : 'left-1'
                          }`}
                        ></div>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="glass-strong p-6 rounded-2xl mb-8">
        <h2 className="text-2xl font-bold mb-6">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#00CEC9] to-[#6C5CE7] flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl font-bold">98%</span>
            </div>
            <div className="text-sm text-[#DDDDDD]">Uptime</div>
          </div>
          <div className="text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#6C5CE7] to-[#E17055] flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl font-bold">45ms</span>
            </div>
            <div className="text-sm text-[#DDDDDD]">Response Time</div>
          </div>
          <div className="text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#00B894] to-[#00CEC9] flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl font-bold">256</span>
            </div>
            <div className="text-sm text-[#DDDDDD]">Tasks Completed</div>
          </div>
          <div className="text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#E17055] to-[#00B894] flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl font-bold">12</span>
            </div>
            <div className="text-sm text-[#DDDDDD]">Active Services</div>
          </div>
        </div>
      </div>

      <div className="glass-strong p-6 rounded-2xl">
        <h2 className="text-2xl font-bold mb-6">Integration Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['Calendar', 'Weather API', 'Music Service', 'Smart Home', 'Cloud Storage', 'Email'].map((service, index) => (
            <div key={index} className="glass p-4 rounded-xl flex items-center justify-between">
              <span className="text-[#DDDDDD]">{service}</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-[#00B894] rounded-full animate-pulse"></div>
                <span className="text-xs text-[#00B894]">Active</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
