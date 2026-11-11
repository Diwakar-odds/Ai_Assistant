import React from 'react';
import { Zap, RefreshCw, Archive, Home, History } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch } from '../shared';

const BACKUP_FREQUENCIES = [
  { value: 'daily', label: 'Daily Backup' },
  { value: 'weekly', label: 'Weekly Backup (Recommended)' },
  { value: 'monthly', label: 'Monthly Backup' },
  { value: 'never', label: 'Never' },
];

const SMART_HOME_PROVIDERS = [
  { value: 'none', label: 'None (Disabled)' },
  { value: 'homeassistant', label: 'Home Assistant' },
  { value: 'googlehome', label: 'Google Home / Nest' },
  { value: 'mqtt', label: 'Generic MQTT Broker' },
];

export const AutomationSection: React.FC = () => {
  const { settings, updateSetting } = useSettings();

  if (!settings) return null;
  const auto = settings.automation;

  return (
    <div className="space-y-6">
      {/* 1. Maintenance & Backups */}
      <SectionCard
        title="Background Maintenance & Backups"
        description="Automated system upkeep and history retention routines"
        icon={RefreshCw}
      >
        <SettingRow
          label="Automatic Software Updates"
          description="Check for new Pulsar releases and security patches automatically"
        >
          <ToggleSwitch
            checked={Boolean(auto.autoUpdate)}
            onChange={(val) => updateSetting('automation', ['autoUpdate'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Automated Database Backup"
          description="Create automated snapshots of your preferences and chat logs"
        >
          <SelectDropdown
            value={auto.autoBackup || 'weekly'}
            options={BACKUP_FREQUENCIES}
            onChange={(val) => updateSetting('automation', ['autoBackup'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Max Conversation History Limit"
          description="Number of past session records to preserve before archiving old entries"
        >
          <RangeSlider
            value={auto.maxHistorySize || 1000}
            min={100}
            max={10000}
            step={100}
            unit="records"
            onChange={(val) => updateSetting('automation', ['maxHistorySize'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 2. Smart Home & IoT Automation */}
      <SectionCard
        title="Smart Home Integration"
        description="Connect Pulsar to Home Assistant or IoT ecosystems for ambient voice control"
        icon={Home}
      >
        <SettingRow
          label="Enable Smart Home Bridge"
          description="Allow voice commands to control IoT lights, plugs, and sensors"
        >
          <ToggleSwitch
            checked={Boolean(auto.smartHome?.enabled)}
            onChange={(val) => updateSetting('automation', ['smartHome', 'enabled'], val)}
          />
        </SettingRow>

        {auto.smartHome?.enabled && (
          <SettingRow
            label="Integration Ecosystem"
            description="Target protocol or smart home hub"
          >
            <SelectDropdown
              value={auto.smartHome?.provider || 'none'}
              options={SMART_HOME_PROVIDERS}
              onChange={(val) => updateSetting('automation', ['smartHome', 'provider'], val)}
            />
          </SettingRow>
        )}
      </SectionCard>
    </div>
  );
};
