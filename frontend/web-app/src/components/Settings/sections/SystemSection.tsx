import React, { useState } from 'react';
import {
  Server,
  Activity,
  Cpu,
  HardDrive,
  Database,
  Bell,
  Eye,
  AlertOctagon,
  RotateCcw,
  Trash2,
  Sparkles,
  CheckCircle2,
  Loader2,
  Play,
} from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { useDashboard } from '../../../contexts/DashboardContext';
import { apiUrl } from '../../../lib/api';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch } from '../shared';

const LOG_LEVELS = [
  { value: 'DEBUG', label: 'DEBUG (Detailed traces & diagnostics)' },
  { value: 'INFO', label: 'INFO (Normal operational messages)' },
  { value: 'WARNING', label: 'WARNING (Potential issues only)' },
  { value: 'ERROR', label: 'ERROR (Critical failures only)' },
];

const ORB_SIZES = [
  { value: 'small', label: 'Small (100px - Discreet mini orb)' },
  { value: 'medium', label: 'Medium (136px - Recommended default)' },
  { value: 'large', label: 'Large (180px - High visibility)' },
];

export const SystemSection: React.FC = () => {
  const { settings, updateSetting, resetAll } = useSettings();
  const { systemStats } = useDashboard();

  const [cleaningState, setCleaningState] = useState<{ [key: string]: boolean }>({});
  const [cleanFeedback, setCleanFeedback] = useState<{ [key: string]: string }>({});

  if (!settings) return null;
  const sys = settings.system;

  const comp = sys.companion || {
    alwaysOnTop: true,
    size: 'medium',
    opacity: 90,
    autoHide: true,
  };

  const performClean = async (key: string, endpoint: string) => {
    try {
      setCleaningState((prev) => ({ ...prev, [key]: true }));
      setCleanFeedback((prev) => ({ ...prev, [key]: '' }));
      const res = await fetch(apiUrl(endpoint), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setCleanFeedback((prev) => ({
          ...prev,
          [key]: `✓ Freed ${data.freed_mb ?? 0} MB (${data.files_removed ?? data.files_cleaned ?? 0} items cleaned)`,
        }));
      } else {
        setCleanFeedback((prev) => ({ ...prev, [key]: `✕ ${data.error || 'Cleanup failed'}` }));
      }
    } catch (err: any) {
      setCleanFeedback((prev) => ({ ...prev, [key]: `✕ ${err.message || 'Network error'}` }));
    } finally {
      setCleaningState((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleSpawnOrb = async () => {
    try {
      await fetch(apiUrl('/api/desktop/companion/spawn'), { method: 'POST' });
    } catch (err) {
      console.warn('Spawn orb error:', err);
    }
  };

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
          label="Screen Share Stealth Mode"
          description="Make the glowing orb 100% invisible in Zoom, Google Meet, Microsoft Teams, Discord, and screen recordings (WDA_EXCLUDEFROMCAPTURE like Parakeet AI)"
          badge="Parakeet AI"
        >
          <ToggleSwitch
            checked={sys.screenShareStealth !== false}
            onChange={(val) => updateSetting('system', ['screenShareStealth'], val)}
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

      {/* 3. Floating 4D Glowing Orb (Desktop Companion) */}
      <SectionCard
        title="Floating 4D Glowing Orb (Desktop Companion)"
        description="Configure size, transparency, and behavior for the desktop ambient glowing orb"
        icon={Sparkles}
      >
        <SettingRow
          label="Orb Size"
          description="Diameter and screen footprint of the floating glowing orb"
        >
          <SelectDropdown
            value={comp.size || 'medium'}
            options={ORB_SIZES}
            onChange={(val) => updateSetting('system', ['companion', 'size'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Transparency / Opacity"
          description="Adjust see-through level against desktop background and open apps"
        >
          <RangeSlider
            value={comp.opacity ?? 90}
            min={50}
            max={100}
            step={5}
            unit="%"
            onChange={(val) => updateSetting('system', ['companion', 'opacity'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Always-on-Top"
          description="Keep the floating companion visible above other active Windows windows"
        >
          <ToggleSwitch
            checked={Boolean(comp.alwaysOnTop)}
            onChange={(val) => updateSetting('system', ['companion', 'alwaysOnTop'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Auto-Hide on Dashboard Focus"
          description="Automatically hide companion when the main full-screen Pulsar dashboard is opened"
        >
          <ToggleSwitch
            checked={Boolean(comp.autoHide)}
            onChange={(val) => updateSetting('system', ['companion', 'autoHide'], val)}
          />
        </SettingRow>

        <div className="pt-2 flex items-center justify-between border-t border-[#2A2D35]/50">
          <div>
            <p className="text-xs font-semibold text-white">Preview Glowing Orb</p>
            <p className="text-[11px] text-[#9CA3AF]">
              Spawn or toggle the ambient 4D glowing orb overlay on your desktop now
            </p>
          </div>
          <button
            type="button"
            onClick={handleSpawnOrb}
            className="px-3.5 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2 cursor-pointer shrink-0"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Launch Glowing Orb</span>
          </button>
        </div>
      </SectionCard>

      {/* 4. Storage & Cache Cleaner */}
      <SectionCard
        title="Storage & Cache Cleaner"
        description="One-click maintenance to free disk space by clearing audio caches, chat logs, and diagnostics"
        icon={Trash2}
      >
        {/* Voice Audio Cache */}
        <div className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2A2D35]/50">
          <div>
            <p className="text-sm font-semibold text-white">Voice Audio Cache</p>
            <p className="text-xs text-[#9CA3AF] mt-0.5">
              Cached speech synthesis audio previews and temporary Edge-TTS sound files
            </p>
            {cleanFeedback['voice'] && (
              <p className="text-xs text-[#10B981] mt-1 font-medium">{cleanFeedback['voice']}</p>
            )}
          </div>
          <button
            type="button"
            disabled={cleaningState['voice']}
            onClick={() => performClean('voice', '/api/settings/clean_voice_cache')}
            className="px-3.5 py-2 bg-[#2A2D35] hover:bg-[#3A3D45] disabled:opacity-50 text-white text-xs font-medium rounded-lg border border-[#3A3D45] flex items-center gap-2 transition-colors shrink-0 self-start sm:self-center cursor-pointer"
          >
            {cleaningState['voice'] ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#3B82F6]" />
            ) : (
              <Trash2 className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>Clean Voice Cache</span>
          </button>
        </div>

        {/* Chat & Session History */}
        <div className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2A2D35]/50">
          <div>
            <p className="text-sm font-semibold text-white">Chat & Session History</p>
            <p className="text-xs text-[#9CA3AF] mt-0.5">
              Saved conversation transcripts, session logs, and cached prompt context files
            </p>
            {cleanFeedback['chat'] && (
              <p className="text-xs text-[#10B981] mt-1 font-medium">{cleanFeedback['chat']}</p>
            )}
          </div>
          <button
            type="button"
            disabled={cleaningState['chat']}
            onClick={() => {
              if (window.confirm('Clear all chat session history and context files?')) {
                performClean('chat', '/api/settings/clean_chat_history');
              }
            }}
            className="px-3.5 py-2 bg-[#2A2D35] hover:bg-[#3A3D45] disabled:opacity-50 text-white text-xs font-medium rounded-lg border border-[#3A3D45] flex items-center gap-2 transition-colors shrink-0 self-start sm:self-center cursor-pointer"
          >
            {cleaningState['chat'] ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#3B82F6]" />
            ) : (
              <Trash2 className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>Clear Chat History</span>
          </button>
        </div>

        {/* Application Logs */}
        <div className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Application Diagnostic Logs</p>
            <p className="text-xs text-[#9CA3AF] mt-0.5">
              Archived and active background log files in the logs directory
            </p>
            {cleanFeedback['logs'] && (
              <p className="text-xs text-[#10B981] mt-1 font-medium">{cleanFeedback['logs']}</p>
            )}
          </div>
          <button
            type="button"
            disabled={cleaningState['logs']}
            onClick={() => performClean('logs', '/api/settings/clean_logs')}
            className="px-3.5 py-2 bg-[#2A2D35] hover:bg-[#3A3D45] disabled:opacity-50 text-white text-xs font-medium rounded-lg border border-[#3A3D45] flex items-center gap-2 transition-colors shrink-0 self-start sm:self-center cursor-pointer"
          >
            {cleaningState['logs'] ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#3B82F6]" />
            ) : (
              <Trash2 className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>Clean Log Files</span>
          </button>
        </div>
      </SectionCard>

      {/* 5. Logging & Diagnostics */}
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
