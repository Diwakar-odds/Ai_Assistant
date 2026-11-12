import React, { useState } from 'react';
import { Mic, Volume2, Radio, Play, Square, Loader2 } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch, TextInput, TagInput } from '../shared';
import { apiUrl } from '../../../lib/api';

const STT_ENGINES = [
  { value: 'whisper', label: 'OpenAI Whisper (Offline, Accurate)' },
  { value: 'google', label: 'Google Cloud Speech (Fast)' },
];

const TTS_ENGINES = [
  { value: 'edge_tts', label: 'Microsoft Edge Neural (Online, Natural)' },
  { value: 'kittentts', label: 'KittenTTS (Offline, Lightweight)' },
  { value: 'pyttsx3', label: 'Windows SAPI5 (Offline, System Default)' },
];

const FALLBACK_VOICES = [
  { value: 'hi-IN-SwaraNeural', label: 'Swara (Hindi Neural Online)' },
  { value: 'hi-IN-MadhurNeural', label: 'Madhur (Hindi Neural Online)' },
  { value: 'en-US-AriaNeural', label: 'Aria (English US Neural)' },
  { value: 'en-US-GuyNeural', label: 'Guy (English US Neural)' },
  { value: 'en-IN-NeerjaNeural', label: 'Neerja (Indian English Neural)' },
  { value: 'en-IN-PrabhatNeural', label: 'Prabhat (Indian English Neural)' },
];

const STT_LANGUAGES = [
  { value: 'hi-IN', label: 'Hindi (hi-IN)' },
  { value: 'en-US', label: 'English (US) (en-US)' },
  { value: 'en-IN', label: 'English (India) (en-IN)' },
  { value: 'auto', label: 'Auto Detect' },
];

export const VoiceSection: React.FC = () => {
  const { settings, updateSetting } = useSettings();
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  if (!settings) return null;
  const voice = settings.voice;
  const tts = voice.tts;
  const stt = voice.stt;
  const wakeWord = voice.wakeWord;

  // Build voice options from available_voices or fallback
  const availableVoices = tts.available_voices;
  const voiceOptions = Array.isArray(availableVoices) && availableVoices.length > 0
    ? availableVoices.map((v) => ({
        value: v.id,
        label: `${v.name} (${v.gender || 'Neural'}, ${v.accent || 'Default'})`,
      }))
    : FALLBACK_VOICES;

  const handleVoicePreview = async () => {
    if (isPlayingPreview) return;
    setIsPlayingPreview(true);
    setPreviewError(null);

    try {
      const response = await fetch(apiUrl('/api/voice/preview'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voice_id: tts.voice_id || 'hi-IN-SwaraNeural',
          text: 'Namaste! Main Pulsar AI Assistant hoon. Main aapki kya madad kar sakti hoon?',
        }),
      });

      const data = await response.json();
      if (response.ok && data.success && data.audio_data) {
        const audio = new Audio(data.audio_data);
        audio.onended = () => setIsPlayingPreview(false);
        audio.onerror = () => {
          setIsPlayingPreview(false);
          setPreviewError('Failed to play audio');
        };
        await audio.play();
      } else {
        setIsPlayingPreview(false);
        setPreviewError(data.error || 'Preview unavailable');
      }
    } catch (err: any) {
      console.error('Preview error:', err);
      setIsPlayingPreview(false);
      setPreviewError(err.message || 'Error triggering preview');
    }
  };

  const handleVoiceChange = (voiceId: string) => {
    updateSetting('voice', ['tts', 'voice_id'], voiceId);
    // Find voice name
    const found = availableVoices?.find((v) => v.id === voiceId);
    if (found?.name) {
      updateSetting('voice', ['tts', 'voice_name'], found.name);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Speech-to-Text (STT) */}
      <SectionCard
        title="Speech Recognition (STT)"
        description="Configure microphone input processing, model sensitivity, and noise reduction"
        icon={Mic}
      >
        <SettingRow
          label="Enable Voice Recognition"
          description="Allow Pulsar to listen to spoken microphone audio"
        >
          <ToggleSwitch
            checked={Boolean(stt.enabled)}
            onChange={(val) => updateSetting('voice', ['stt', 'enabled'], val)}
          />
        </SettingRow>

        <SettingRow
          label="STT Engine"
          description="Recognition model provider"
        >
          <SelectDropdown
            value={stt.engine || 'whisper'}
            options={STT_ENGINES}
            onChange={(val) => updateSetting('voice', ['stt', 'engine'], val)}
          />
        </SettingRow>

        {stt.engine === 'whisper' && (
          <SettingRow
            label="Whisper Model Size"
            description="whisper-tiny, whisper-base, whisper-small, or whisper-medium"
          >
            <TextInput
              value={stt.model || 'whisper-small'}
              placeholder="whisper-small"
              onChange={(val) => updateSetting('voice', ['stt', 'model'], val)}
            />
          </SettingRow>
        )}

        <SettingRow
          label="Recognition Language"
          description="Spoken dialect to optimize transcription accuracy for"
        >
          <SelectDropdown
            value={stt.language || 'hi-IN'}
            options={STT_LANGUAGES}
            onChange={(val) => updateSetting('voice', ['stt', 'language'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Microphone Sensitivity"
          description="VAD (Voice Activity Detection) threshold for speech onset"
        >
          <RangeSlider
            value={typeof stt.sensitivity === 'number' ? stt.sensitivity : 0.5}
            min={0.1}
            max={1.0}
            step={0.05}
            onChange={(val) => updateSetting('voice', ['stt', 'sensitivity'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Continuous Listening"
          description="Keep microphone active without requiring push-to-talk button press"
        >
          <ToggleSwitch
            checked={Boolean(stt.continuous)}
            onChange={(val) => updateSetting('voice', ['stt', 'continuous'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Background Noise Reduction"
          description="Filter fan noise, keyboard clicks, and environmental hum"
        >
          <ToggleSwitch
            checked={Boolean(stt.noise_reduction)}
            onChange={(val) => updateSetting('voice', ['stt', 'noise_reduction'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 2. Text-to-Speech (TTS) */}
      <SectionCard
        title="Speech Synthesis (TTS)"
        description="Choose voice identity, speaking pace, pitch, and output audio volume"
        icon={Volume2}
      >
        <SettingRow
          label="Enable Voice Speech Output"
          description="Speak assistant answers aloud through speakers"
        >
          <ToggleSwitch
            checked={Boolean(tts.enabled)}
            onChange={(val) => updateSetting('voice', ['tts', 'enabled'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Synthesis Engine"
          description="Underlying neural speech generation backend"
        >
          <SelectDropdown
            value={tts.engine || 'edge_tts'}
            options={TTS_ENGINES}
            onChange={(val) => updateSetting('voice', ['tts', 'engine'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Voice Persona"
          description="Active neural voice profile for responses"
          error={previewError || undefined}
        >
          <div className="flex items-center gap-2">
            <SelectDropdown
              value={tts.voice_id || voiceOptions[0]?.value}
              options={voiceOptions}
              onChange={handleVoiceChange}
            />
            <button
              type="button"
              onClick={handleVoicePreview}
              disabled={isPlayingPreview || !tts.enabled}
              className={`
                px-3 py-2 text-xs font-medium rounded-lg border transition-all flex items-center gap-1.5 shrink-0
                ${isPlayingPreview
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                  : 'bg-[#3B82F6] hover:bg-[#2563EB] text-white border-transparent'
                } disabled:opacity-50 disabled:cursor-not-allowed
              `}
              title="Preview selected voice"
            >
              {isPlayingPreview ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span className="hidden sm:inline">Playing...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span className="hidden sm:inline">Preview</span>
                </>
              )}
            </button>
          </div>
        </SettingRow>

        <SettingRow
          label="Speaking Speed"
          description="Speech rate factor (1.0 is normal human pace)"
        >
          <RangeSlider
            value={typeof tts.speed === 'number' ? tts.speed : 1.0}
            min={0.5}
            max={2.0}
            step={0.1}
            unit="x"
            onChange={(val) => updateSetting('voice', ['tts', 'speed'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Voice Pitch"
          description="Higher or lower tone frequency"
        >
          <RangeSlider
            value={typeof tts.pitch === 'number' ? tts.pitch : 1.0}
            min={0.5}
            max={2.0}
            step={0.1}
            unit="x"
            onChange={(val) => updateSetting('voice', ['tts', 'pitch'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Speech Volume"
          description="Assistant audio loudness level"
        >
          <RangeSlider
            value={typeof tts.volume === 'number' ? tts.volume : 0.9}
            min={0.0}
            max={1.0}
            step={0.05}
            onChange={(val) => updateSetting('voice', ['tts', 'volume'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Cache Generated Audio"
          description="Save synthesized audio on disk to instantly replay common greetings"
        >
          <ToggleSwitch
            checked={Boolean(tts.useCache)}
            onChange={(val) => updateSetting('voice', ['tts', 'useCache'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 3. Wake Word Detection */}
      <SectionCard
        title="Hands-Free Wake Word"
        description="Listen for trigger keywords to activate Pulsar without clicking"
        icon={Radio}
      >
        <SettingRow
          label="Enable Wake Word Detection"
          description="Pulsar awakens upon hearing your configured phrases"
        >
          <ToggleSwitch
            checked={Boolean(wakeWord.enabled)}
            onChange={(val) => updateSetting('voice', ['wakeWord', 'enabled'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Wake Phrases"
          description="Keywords that trigger listening mode (type phrase and press Enter)"
        >
          <div className="w-full sm:w-80">
            <TagInput
              values={Array.isArray(wakeWord.phrases) ? wakeWord.phrases : ['hey pulsar', 'pulsar', 'ok pulsar']}
              onChange={(phrases) => updateSetting('voice', ['wakeWord', 'phrases'], phrases)}
              placeholder="e.g. hey pulsar..."
            />
          </div>
        </SettingRow>

        <SettingRow
          label="Detection Sensitivity"
          description="Higher sensitivity reacts quicker but may trigger on background sounds"
        >
          <RangeSlider
            value={typeof wakeWord.sensitivity === 'number' ? wakeWord.sensitivity : 0.6}
            min={0.1}
            max={1.0}
            step={0.05}
            onChange={(val) => updateSetting('voice', ['wakeWord', 'sensitivity'], val)}
          />
        </SettingRow>
      </SectionCard>
    </div>
  );
};
