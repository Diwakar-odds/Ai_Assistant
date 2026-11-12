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

      {/* 2. Custom User Instructions / About You */}
      <SectionCard
        title="About You & Personal Instructions"
        description="Tell Pulsar about yourself, your role, and how you want it to format its answers"
        icon={User}
      >
        <div className="py-2 space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-white uppercase tracking-wider">
              Custom Prompt Instructions (Apne Baare Mein Batayein)
            </label>
            <span className="text-[11px] text-[#9CA3AF]">
              {(persona.customInstructions || '').length} / 2000 chars
            </span>
          </div>

          <textarea
            value={persona.customInstructions || ''}
            onChange={(e) =>
              updateSetting('voice', ['persona', 'customInstructions'], e.target.value.slice(0, 2000))
            }
            placeholder="e.g. Main student hoon, computer science padhta hoon. Mere sawalon ke jawab crisp Hinglish mein do. Jab code pucho toh modern TypeScript ya Python use karo aur bullet points do."
            rows={4}
            className="w-full bg-[#13151A] border border-[#2A2D35] focus:border-[#3B82F6] rounded-xl p-3.5 text-sm text-white placeholder-[#6B7280] outline-none transition-colors resize-y leading-relaxed font-sans"
          />

          <p className="text-xs text-[#9CA3AF]">
            These instructions are automatically injected into Pulsar's core system prompt and remembered across Voice, Web Chat, Floating Orb, and Agents.
          </p>
        </div>
      </SectionCard>

      {/* 3. Interactive Feedback & Feedback Loops */}
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
