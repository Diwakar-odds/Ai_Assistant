import React from 'react';
import { Server, Activity, Cpu, HardDrive, Database, Bell, Eye, AlertOctagon, RotateCcw } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { useDashboard } from '../../../contexts/DashboardContext';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch } from '../shared';

const LOG_LEVELS = [
  { value: 'DEBUG', label: 'DEBUG (Detailed traces & diagnostics)' },
  { value: 'INFO', label: 'INFO (Normal operational messages)' },
  { value: 'WARNING', label: 'WARNING (Potential issues only)' },
  { value: 'ERROR', label: 'ERROR (Critical failures only)' },
];

export const SystemSection: React.FC = () => {
  const { settings, updateSetting, resetAll } = useSettings();
  const { systemStats } = useDashboard();

  if (!settings) return null;
  const sys = settings.system;

  const metrics = [
    { label: 'CPU Load', value: `${systemStats?.cpu || 0}%`, icon: Cpu, color: '#3B82F6' },
    { label: 'Memory', value: `${systemStats?.memory || 0}%`, icon: HardDrive, color: '#10B981' },
    { label: 'Disk Space', value: `${systemStats?.disk || 0}%`, icon: Database, color: '#8B5CF6' },
    { label: 'Network Speed', value: systemStats?.network || '0 MB/s', icon: Activity, color: '#F59E0B' },
  ];

  return (
    <div className="space-y-6">
      {/* 1. Live Hardware & Performance Telemetry */}
      <div>
        <h4 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
          <Activity className="w-5 h-5 text-[#3B82F6]" />
          <span>Real-time Resource Telemetry</span>
        </h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {metrics.map((m) => (
            <div
              key={m.label}
              className="bg-[#1F2228] border border-[#2A2D35] p-4 rounded-xl flex items-center gap-3.5 shadow-sm"
            >
              <div
                className="p-3 rounded-lg bg-[#2A2D35] shrink-0"
                style={{ color: m.color }}
              >
                <m.icon className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-[#9CA3AF] text-[11px] uppercase font-bold tracking-wider truncate">
                  {m.label}
                </p>
                <p className="text-white text-lg font-bold truncate">{m.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Window & Desktop Integration */}
      <SectionCard
        title="Windows Desktop Integration"
        description="Floating companions, system tray minimization, and overlay behaviors"
        icon={Server}
      >
        <SettingRow
          label="Minimized 4D Orb Desktop Overlay"
          description="Display the glowing 3D Arc-Reactor orb centered on taskbar whenever Pulsar is minimized or in the background"
          badge="Live Sync"
        >
          <ToggleSwitch
            checked={Boolean(sys.desktopOverlay)}
            onChange={(val) => updateSetting('system', ['desktopOverlay'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Minimize to System Tray"
          description="Keep Pulsar running quietly in the Windows taskbar notification tray when window is closed"
        >
          <ToggleSwitch
            checked={Boolean(sys.minimizeToTray)}
            onChange={(val) => updateSetting('system', ['minimizeToTray'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Windows Desktop Toast Notifications"
          description="Send native Windows 10/11 banners when long background tasks finish"
        >
          <ToggleSwitch
            checked={Boolean(sys.notifications?.desktop)}
            onChange={(val) => updateSetting('system', ['notifications', 'desktop'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Audio Notification Chimes"
          description="Play a subtle ping when notifications arrive or actions resolve"
        >
          <ToggleSwitch
            checked={Boolean(sys.notifications?.sound)}
            onChange={(val) => updateSetting('system', ['notifications', 'sound'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 3. Logging & Diagnostics */}
      <SectionCard
        title="Diagnostics & Log Storage"
        description="Configure backend trace verbosity and log file rotation limits"
        icon={Eye}
        collapsible
        defaultExpanded={false}
      >
        <SettingRow
          label="Backend Logging Level"
          description="Controls diagnostic verbosity in logs and terminal"
        >
          <SelectDropdown
            value={sys.logLevel || 'INFO'}
            options={LOG_LEVELS}
            onChange={(val) => updateSetting('system', ['logLevel'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Maximum Log File Size"
          description="Rotate and archive log files when reaching this size threshold"
        >
          <RangeSlider
            value={sys.maxLogSizeMb || 10}
            min={1}
            max={100}
            step={1}
            unit="MB"
            onChange={(val) => updateSetting('system', ['maxLogSizeMb'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 4. Danger Zone */}
      <SectionCard
        title="Factory Reset & Recovery"
        description="Reset all application settings, active AI models, and preferences to original defaults"
        icon={AlertOctagon}
        danger
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2">
          <div>
            <p className="text-sm font-semibold text-red-400">Reset All Settings</p>
            <p className="text-xs text-[#9CA3AF] mt-0.5">
              This will reset all categories (General, AI, Voice, Security, System) back to default. Personal database files and conversation logs will be preserved.
            </p>
          </div>

          <button
            type="button"
            onClick={async () => {
              const confirmed = window.confirm(
                'Are you sure you want to RESET ALL SETTINGS to factory defaults? This action cannot be undone.'
              );
              if (confirmed) {
                await resetAll();
              }
            }}
            className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-md transition-colors flex items-center gap-2 shrink-0 self-start sm:self-center cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset All to Defaults</span>
          </button>
        </div>
      </SectionCard>
    </div>
  );
};
