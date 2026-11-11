import React from 'react';
import { KeyRound, Shield, Lock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, ToggleSwitch, PasswordInput } from '../shared';
import { apiUrl } from '../../../lib/api';

export const SecuritySection: React.FC = () => {
  const { settings, updateSetting } = useSettings();

  if (!settings) return null;
  const security = settings.security;
  const apiKeys = security.apiKeys || { googleGemini: '', openAI: '', anthropic: '', elevenLabs: '' };
  const permissions = security.permissions || {
    allowAppExecution: true,
    allowWebBrowsing: true,
    allowSystemControl: true,
    allowFileDeletion: false,
  };
  const encryption = security.encryption || { encryptDatabase: true, enablePinParams: false };

  // Verification helper for cloud API keys
  const verifyApiKey = async (provider: string, keyVal: string): Promise<boolean> => {
    if (!keyVal || keyVal.startsWith('***')) return true;
    try {
      // Test provider via command or providers endpoint
      const res = await fetch(apiUrl('/api/settings/update'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: 'security',
          settings: {
            apiKeys: { [provider]: keyVal },
          },
        }),
      });
      const data = await res.json();
      return Boolean(data.success);
    } catch {
      return false;
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Cloud Provider API Keys */}
      <SectionCard
        title="AI Cloud Credentials & API Keys"
        description="Keys are encrypted and stored securely in Windows Credential Manager"
        icon={KeyRound}
        badge="Encrypted"
      >
        <SettingRow
          label="Google Gemini API Key"
          description="Powers Gemini 2.5 Flash & Pro models"
        >
          <PasswordInput
            value={apiKeys.googleGemini || ''}
            placeholder="AIzaSy..."
            onChange={(val) => updateSetting('security', ['apiKeys', 'googleGemini'], val)}
            onVerify={() => verifyApiKey('googleGemini', apiKeys.googleGemini)}
          />
        </SettingRow>

        <SettingRow
          label="OpenAI API Key"
          description="Powers GPT-4o, GPT-4o-mini and o3-mini models"
        >
          <PasswordInput
            value={apiKeys.openAI || ''}
            placeholder="sk-proj-..."
            onChange={(val) => updateSetting('security', ['apiKeys', 'openAI'], val)}
            onVerify={() => verifyApiKey('openAI', apiKeys.openAI)}
          />
        </SettingRow>

        <SettingRow
          label="Anthropic Claude API Key"
          description="Optional key for Anthropic Claude 3.5 Sonnet / Haiku integrations"
        >
          <PasswordInput
            value={apiKeys.anthropic || ''}
            placeholder="sk-ant-..."
            onChange={(val) => updateSetting('security', ['apiKeys', 'anthropic'], val)}
          />
        </SettingRow>

        <SettingRow
          label="ElevenLabs Neural Voice API Key"
          description="Optional key for hyper-realistic cloned voice TTS output"
        >
          <PasswordInput
            value={apiKeys.elevenLabs || ''}
            placeholder="xi-..."
            onChange={(val) => updateSetting('security', ['apiKeys', 'elevenLabs'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 2. Runtime System Permissions */}
      <SectionCard
        title="Execution Permissions & Guardrails"
        description="Explicit authorization boundaries for automated assistant actions"
        icon={Shield}
      >
        <SettingRow
          label="Allow Application Execution"
          description="Let Pulsar launch, focus, and close desktop applications on your PC"
        >
          <ToggleSwitch
            checked={Boolean(permissions.allowAppExecution)}
            onChange={(val) => updateSetting('security', ['permissions', 'allowAppExecution'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Allow Web Browsing"
          description="Allow web searches, URL fetching, and online fact retrieval"
        >
          <ToggleSwitch
            checked={Boolean(permissions.allowWebBrowsing)}
            onChange={(val) => updateSetting('security', ['permissions', 'allowWebBrowsing'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Allow Windows System Control"
          description="Permit hardware toggles (volume, screen brightness, WiFi, power states)"
        >
          <ToggleSwitch
            checked={Boolean(permissions.allowSystemControl)}
            onChange={(val) => updateSetting('security', ['permissions', 'allowSystemControl'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Allow File Deletion (High Risk)"
          description="Permit removing files and folders from disk during cleanup workflows"
          danger
          badge="Danger"
        >
          <ToggleSwitch
            checked={Boolean(permissions.allowFileDeletion)}
            onChange={(val) => updateSetting('security', ['permissions', 'allowFileDeletion'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 3. Data Protection & Encryption */}
      <SectionCard
        title="Local Storage & Encryption"
        description="At-rest cryptographic protection for your personal conversations and database"
        icon={Lock}
      >
        <SettingRow
          label="Encrypt Local Database"
          description="Encrypt SQLite activity logs and vector knowledge embeddings on disk"
        >
          <ToggleSwitch
            checked={Boolean(encryption.encryptDatabase)}
            onChange={(val) => updateSetting('security', ['encryption', 'encryptDatabase'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Require Confirmation for Critical Tasks"
          description="Prompt for explicit confirmation before running irreversible system commands"
        >
          <ToggleSwitch
            checked={Boolean(encryption.enablePinParams)}
            onChange={(val) => updateSetting('security', ['encryption', 'enablePinParams'], val)}
          />
        </SettingRow>
      </SectionCard>
    </div>
  );
};
