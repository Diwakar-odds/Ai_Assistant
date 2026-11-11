import React from 'react';
import { Sparkles, User, Bell, MessageSquare, History } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch, TextInput } from '../shared';

const PERSONA_STYLES = [
  { value: 'jarvis', label: 'JARVIS (Polite, Crisp & Mission-Focused)' },
  { value: 'friendly', label: 'Friendly Companion (Warm & Conversational)' },
  { value: 'bilingual_buddy', label: 'Bilingual Buddy (Natural Desi Hinglish)' },
  { value: 'concise', label: 'Ultra Concise (Minimal Tokens, Direct Answers)' },
];

const LANGUAGE_MODES = [
  { value: 'auto', label: 'Auto (Adapt dynamically to user speech)' },
  { value: 'hinglish', label: 'Always Hinglish (Hindi words in Roman script)' },
  { value: 'hindi', label: 'Pure Hindi (हिंदी)' },
  { value: 'english', label: 'Standard English' },
];

export const PersonaSection: React.FC = () => {
  const { settings, updateSetting } = useSettings();

  if (!settings) return null;
  const persona = settings.voice?.persona || {
    style: 'jarvis',
    assistantName: 'Pulsar',
    userTitle: 'Boss',
    languageMode: 'auto',
    wakeAckEnabled: true,
    preTaskReports: true,
    postTaskReports: true,
    dynamicGeneration: true,
    recentMemorySize: 18,
  };

  return (
    <div className="space-y-6">
      {/* 1. Identity & Tone */}
      <SectionCard
        title="Identity & Tone of Voice"
        description="Customize how Pulsar addresses you and structures its conversations"
        icon={Sparkles}
      >
        <SettingRow
          label="Persona Style"
          description="High-level personality prompt archetype"
        >
          <SelectDropdown
            value={persona.style || 'jarvis'}
            options={PERSONA_STYLES}
            onChange={(val) => updateSetting('voice', ['persona', 'style'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Assistant Display Name"
          description="Name the assistant calls itself in dialogue"
        >
          <TextInput
            value={persona.assistantName || 'Pulsar'}
            placeholder="Pulsar"
            onChange={(val) => updateSetting('voice', ['persona', 'assistantName'], val)}
          />
        </SettingRow>

        <SettingRow
          label="How Assistant Addresses You"
          description="Title or preferred name (e.g., Boss, Sir, Alex)"
        >
          <TextInput
            value={persona.userTitle || 'Boss'}
            placeholder="Boss"
            onChange={(val) => updateSetting('voice', ['persona', 'userTitle'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Dialogue Language Mode"
          description="How the persona blends languages when responding"
        >
          <SelectDropdown
            value={persona.languageMode || 'auto'}
            options={LANGUAGE_MODES}
            onChange={(val) => updateSetting('voice', ['persona', 'languageMode'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 2. Interactive Feedback & Feedback Loops */}
      <SectionCard
        title="Execution Feedback & Acknowledgments"
        description="Verbal announcements before and after carrying out PC actions"
        icon={Bell}
      >
        <SettingRow
          label="Wake Word Acknowledgment"
          description='Speak a quick chime or "Yes Boss?" immediately upon wake word trigger'
        >
          <ToggleSwitch
            checked={Boolean(persona.wakeAckEnabled)}
            onChange={(val) => updateSetting('voice', ['persona', 'wakeAckEnabled'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Pre-Task Intent Announcement"
          description='Announce action before starting (e.g. "Opening Spotify now...")'
        >
          <ToggleSwitch
            checked={Boolean(persona.preTaskReports)}
            onChange={(val) => updateSetting('voice', ['persona', 'preTaskReports'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Post-Task Confirmation"
          description="Confirm completion or state changes after tool executions"
        >
          <ToggleSwitch
            checked={Boolean(persona.postTaskReports)}
            onChange={(val) => updateSetting('voice', ['persona', 'postTaskReports'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 3. Memory & Dynamics */}
      <SectionCard
        title="Context & Adaptive Memory"
        description="Number of recent interactions preserved in short-term active memory"
        icon={History}
      >
        <SettingRow
          label="Dynamic Persona Generation"
          description="Allow real-time prompt adaptation based on time of day and user mood"
        >
          <ToggleSwitch
            checked={Boolean(persona.dynamicGeneration)}
            onChange={(val) => updateSetting('voice', ['persona', 'dynamicGeneration'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Short-Term Memory Window"
          description="Number of past turns retained in immediate prompt context"
        >
          <RangeSlider
            value={persona.recentMemorySize || 18}
            min={1}
            max={50}
            step={1}
            unit="turns"
            onChange={(val) => updateSetting('voice', ['persona', 'recentMemorySize'], val)}
          />
        </SettingRow>
      </SectionCard>
    </div>
  );
};
