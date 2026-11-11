import React, { useRef } from 'react';
import { Globe, Palette, Sparkles, Power, Download, Upload, RotateCcw, Info } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, ToggleSwitch, SelectDropdown } from '../shared';

const LANGUAGE_OPTIONS = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'hi-IN', label: 'Hindi (हिंदी)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'de-DE', label: 'German (Deutsch)' },
  { value: 'fr-FR', label: 'French (Français)' },
  { value: 'es-ES', label: 'Spanish (Español)' },
];

const THEME_OPTIONS = [
  { value: 'dark', label: 'Dark Mode (Default)' },
  { value: 'light', label: 'Light Mode' },
  { value: 'system', label: 'System Theme' },
];

export const GeneralSection: React.FC = () => {
  const { settings, updateSetting, resetCategory, exportSettings, importSettings } = useSettings();
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!settings) return null;
  const general = settings.general;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importSettings(file);
    }
  };

  return (
    <div className="space-y-6">
      {/* Language & Regional */}
      <SectionCard
        title="Language & Regional"
        description="Configure your spoken and display language preferences"
        icon={Globe}
      >
        <SettingRow
          label="Primary Language"
          description="Default language used for assistant responses and core UI"
        >
          <SelectDropdown
            value={general.language || 'en-US'}
            options={LANGUAGE_OPTIONS}
            onChange={(val) => updateSetting('general', ['language'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Secondary Language"
          description="Fallback or secondary recognition language"
        >
          <SelectDropdown
            value={general.secondaryLanguage || 'hi-IN'}
            options={LANGUAGE_OPTIONS}
            onChange={(val) => updateSetting('general', ['secondaryLanguage'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Enable Hinglish Processing"
          description="Seamlessly understand mixed Hindi-English natural language instructions"
          badge="Bilingual"
        >
          <ToggleSwitch
            checked={Boolean(general.enableHinglish)}
            onChange={(val) => updateSetting('general', ['enableHinglish'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* Interface & Experience */}
      <SectionCard
        title="Interface & Experience"
        description="Visual styling, animations, and Windows startup preferences"
        icon={Palette}
      >
        <SettingRow
          label="Theme Appearance"
          description="Select visual color palette and dark mode theme"
        >
          <SelectDropdown
            value={general.theme || 'dark'}
            options={THEME_OPTIONS}
            onChange={(val) => updateSetting('general', ['theme'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Smooth Animations"
          description="Enable glowing orb pulse and fluid 3D / reactive motion"
        >
          <ToggleSwitch
            checked={Boolean(general.animations)}
            onChange={(val) => updateSetting('general', ['animations'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Start on Windows Boot"
          description="Automatically launch Pulsar AI Assistant in the background on startup"
        >
          <ToggleSwitch
            checked={Boolean(general.startOnBoot)}
            onChange={(val) => updateSetting('general', ['startOnBoot'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* Backup, Import & Reset */}
      <SectionCard
        title="Configuration Management"
        description="Export settings as JSON backup or reset to factory defaults"
        icon={Info}
      >
        <div className="flex flex-wrap items-center justify-between gap-4 py-3">
          <div>
            <p className="text-sm font-medium text-white">Application Version</p>
            <p className="text-xs text-[#9CA3AF]">Pulsar AI Desktop Edition v4.0.0</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".json"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-2 bg-[#2A2D35] hover:bg-[#3A3D45] text-white text-xs font-medium rounded-lg border border-[#3A3D45] flex items-center gap-1.5 transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Import JSON</span>
            </button>

            <button
              type="button"
              onClick={exportSettings}
              className="px-3 py-2 bg-[#2A2D35] hover:bg-[#3A3D45] text-white text-xs font-medium rounded-lg border border-[#3A3D45] flex items-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>

            <button
              type="button"
              onClick={() => {
                if (window.confirm('Reset General settings to factory defaults?')) {
                  resetCategory('general');
                }
              }}
              className="px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-medium rounded-lg border border-red-500/20 flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset General</span>
            </button>
          </div>
        </div>
      </SectionCard>
    </div>
  );
};
