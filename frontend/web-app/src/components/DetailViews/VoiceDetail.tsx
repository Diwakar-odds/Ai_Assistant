import { motion } from 'framer-motion';
import { Mic, Volume2, Clock, Loader2, Play, Check } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';
import { useState, useEffect } from 'react';

interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  accent: string;
  language: string;
  description: string;
}

const VoiceDetail = () => {
  const { voiceCommands, isVoiceActive, toggleVoice, alwaysActive, toggleAlwaysActive } = useDashboard();

   
  const [settings, setSettings] = useState<any>(null);
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState('');

  // Load settings and voices on mount
  useEffect(() => {
    loadSettings();
    loadVoices();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/voice/settings');
      const data = await response.json();
      if (data.success) {
        setSettings(data.settings);
        setSelectedVoice(data.settings?.tts?.voice_id || 'en-US-AriaNeural');
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadVoices = async () => {
    try {
      const response = await fetch('/api/voice/list');
      const data = await response.json();
      if (data.success) {
        setVoices(data.voices);
      }
    } catch (error) {
      console.error('Failed to load voices:', error);
    }
  };

  const saveSettings = async () => {
    if (!settings) return;

    setSaving(true);
    try {
      const response = await fetch('/api/voice/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      const data = await response.json();
      if (data.success) {
        console.log('Settings saved successfully');
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleVoiceChange = async (voiceId: string) => {
    const voice = voices.find(v => v.id === voiceId);
    if (!voice) return;

    setSelectedVoice(voiceId);
    setSettings({
      ...settings,
      tts: {
        ...settings.tts,
        voice_id: voiceId,
        voice_name: voice.name
      }
    });

    // Auto-save
    setTimeout(() => saveSettings(), 100);
  };

  const playVoicePreview = async () => {
    setPreviewPlaying(true);
    try {
      const response = await fetch('/api/voice/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voice_id: selectedVoice,
          text: "Hello! This is a preview of my voice. I'm here to assist you."
        })
      });
      const data = await response.json();

      if (data.success && data.audio_data) {
        const audio = new Audio(data.audio_data);
        audio.play();
        audio.onended = () => setPreviewPlaying(false);
      }
    } catch (error) {
      console.error('Preview failed:', error);
      setPreviewPlaying(false);
    }
  };

  const toggleTTS = () => {
    setSettings({
      ...settings,
      tts: { ...settings.tts, enabled: !settings.tts?.enabled }
    });
    setTimeout(() => saveSettings(), 100);
  };

  const toggleSTT = () => {
    setSettings({
      ...settings,
      stt: { ...settings.stt, enabled: !settings.stt?.enabled }
    });
    setTimeout(() => saveSettings(), 100);
  };

  const toggleNoiseReduction = () => {
    setSettings({
      ...settings,
      stt: { ...settings.stt, noise_reduction: !settings.stt?.noise_reduction }
    });
    setTimeout(() => saveSettings(), 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-[#3B82F6] animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Voice Control</h3>
          <p className="text-[#9CA3AF]">Manage voice commands and settings</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={toggleVoice}
            className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${isVoiceActive
              ? 'bg-[#EF4444]/20 text-[#EF4444] hover:bg-[#EF4444]/30'
              : 'bg-[#10B981]/20 text-[#10B981] hover:bg-[#10B981]/30'
              }`}
          >
            <Mic className="w-4 h-4" />
            {isVoiceActive ? 'Stop Listening' : 'Start Listening'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* TTS Settings */}
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-[#3B82F6]" />
            Text-to-Speech (TTS)
          </h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-white">Enabled</span>
              <button
                onClick={toggleTTS}
                className={`px-4 py-2 rounded-lg transition-all ${settings?.tts?.enabled
                  ? 'bg-[#10B981]/20 text-[#10B981]'
                  : 'bg-[#6B7280]/20 text-[#9CA3AF]'
                  }`}
              >
                {settings?.tts?.enabled ? 'ON' : 'OFF'}
              </button>
            </div>

            <div>
              <label className="text-white text-sm mb-2 block">Select Voice</label>
              <select
                value={selectedVoice}
                onChange={(e) => handleVoiceChange(e.target.value)}
                className="w-full bg-[#2A2D35] text-white px-4 py-2 rounded-lg border border-[#3A3D45] focus:border-[#3B82F6] focus:outline-none"
                disabled={!settings?.tts?.enabled}
              >
                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name} ({voice.gender}, {voice.accent}) - {voice.description}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={playVoicePreview}
              disabled={previewPlaying || !settings?.tts?.enabled}
              className="w-full bg-[#3B82F6] hover:bg-[#2563EB] text-white px-4 py-2 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {previewPlaying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Playing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Preview Voice
                </>
              )}
            </button>
          </div>
        </div>

        {/* STT Settings */}
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Mic className="w-5 h-5 text-[#10B981]" />
            Speech-to-Text (STT)
          </h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-white">Enabled</span>
              <button
                onClick={toggleSTT}
                className={`px-4 py-2 rounded-lg transition-all ${settings?.stt?.enabled
                  ? 'bg-[#10B981]/20 text-[#10B981]'
                  : 'bg-[#6B7280]/20 text-[#9CA3AF]'
                  }`}
              >
                {settings?.stt?.enabled ? 'ON' : 'OFF'}
              </button>
            </div>

            <div>
              <label className="text-white text-sm mb-2 block">Recognition Engine</label>
              <select
                value={settings?.stt?.engine || 'whisper'}
                onChange={(e) => {
                  setSettings({
                    ...settings,
                    stt: { ...settings.stt, engine: e.target.value }
                  });
                  setTimeout(() => saveSettings(), 100);
                }}
                className="w-full bg-[#2A2D35] text-white px-4 py-2 rounded-lg border border-[#3A3D45] focus:border-[#3B82F6] focus:outline-none"
                disabled={!settings?.stt?.enabled}
              >

                <option value="whisper">Whisper (High Accuracy)</option>
                <option value="google">Google (Cloud)</option>
              </select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white">Noise Reduction</p>
                <p className="text-xs text-[#9CA3AF]">Filter background noise</p>
              </div>
              <button
                onClick={toggleNoiseReduction}
                disabled={!settings?.stt?.enabled}
                className={`px-4 py-2 rounded-lg transition-all ${settings?.stt?.noise_reduction
                  ? 'bg-[#10B981]/20 text-[#10B981]'
                  : 'bg-[#6B7280]/20 text-[#9CA3AF]'
                  } disabled:opacity-50`}
              >
                {settings?.stt?.noise_reduction ? 'ON' : 'OFF'}
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white">Language</p>
                <p className="text-xs text-[#9CA3AF]">{settings?.stt?.language || 'en-US'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Voice Statistics */}
      <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Voice Statistics</h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-[#9CA3AF]">Commands Today</span>
              <span className="text-white font-semibold">{voiceCommands.length}</span>
            </div>
            <div className="h-2 bg-[#2A2D35] rounded-full overflow-hidden">
              <div className="h-full bg-[#3B82F6]" style={{ width: '70%' }} />
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-2">
              <span className="text-[#9CA3AF]">Recognition Accuracy</span>
              <span className="text-white font-semibold">94%</span>
            </div>
            <div className="h-2 bg-[#2A2D35] rounded-full overflow-hidden">
              <div className="h-full bg-[#10B981]" style={{ width: '94%' }} />
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-2">
              <span className="text-[#9CA3AF]">Response Time</span>
              <span className="text-white font-semibold">0.8s avg</span>
            </div>
            <div className="h-2 bg-[#2A2D35] rounded-full overflow-hidden">
              <div className="h-full bg-[#F59E0B]" style={{ width: '85%' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Commands */}
      <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Recent Voice Commands</h4>
        <div className="space-y-2 max-h-[300px] overflow-y-auto">
          {voiceCommands.length === 0 ? (
            <div className="text-center py-8">
              <Mic className="w-12 h-12 text-[#3B82F6] mx-auto mb-3 opacity-50" />
              <p className="text-[#9CA3AF]">No voice commands yet</p>
            </div>
          ) : (
            voiceCommands.map((command, index) => (
              <motion.div
                key={command.id}
                className="flex items-center gap-3 p-3 bg-[#2A2D35] rounded-lg hover:bg-[#3A3D45] transition-colors"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <Mic className="w-4 h-4 text-[#3B82F6]" />
                <p className="flex-1 text-white">{command.command}</p>
                <span className="text-xs text-[#6B7280] flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {command.time}
                </span>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {saving && (
        <div className="fixed bottom-4 right-4 bg-[#10B981] text-white px-4 py-2 rounded-lg flex items-center gap-2 shadow-lg">
          <Check className="w-4 h-4" />
          Settings saved
        </div>
      )}
    </div>
  );
};

export default VoiceDetail;
