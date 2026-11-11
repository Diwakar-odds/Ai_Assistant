import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import SettingsPanel from '../Settings/SettingsPanel';
import { DashboardProvider } from '../../contexts/DashboardContext';

describe('SettingsPanel Component', () => {
  it('renders settings navigation sidebar correctly', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/settings/all')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              settings: {
                onboarded: true,
                general: { language: 'en-US', secondaryLanguage: 'hi-IN', enableHinglish: true, theme: 'dark', animations: true, startOnBoot: true },
                security: { apiKeys: { googleGemini: '', openAI: '' }, permissions: { allowFileDeletion: false, allowAppExecution: true, allowWebBrowsing: true, allowSystemControl: true }, encryption: { encryptDatabase: true, enablePinParams: false } },
                ai: { defaultProvider: 'gemini', defaultModel: 'gemini-2.5-flash', temperature: 0.7, maxTokens: 2048, contextWindow: 4096, safetySettings: { dangerousContent: 'block_none', harassment: 'block_none', hateSpeech: 'block_none', sexuallyExplicit: 'block_none' }, localLlm: { enabled: true, modelPath: 'models/pulsar.gguf', useGpu: false } },
                voice: { tts: { enabled: true, engine: 'edge_tts', voice_id: 'hi-IN-SwaraNeural', voice_name: 'Swara', speed: 1.0, pitch: 1.0, volume: 0.9, useCache: true }, stt: { enabled: true, engine: 'whisper', model: 'whisper-small', sensitivity: 0.5, language: 'hi-IN', continuous: true }, wakeWord: { enabled: true, phrases: ['hey pulsar'], sensitivity: 0.6 }, persona: { style: 'jarvis', assistantName: 'Pulsar', userTitle: 'Boss', languageMode: 'auto', wakeAckEnabled: true, preTaskReports: true, postTaskReports: true, dynamicGeneration: true, recentMemorySize: 18 } },
                automation: { autoUpdate: true, autoBackup: 'weekly', maxHistorySize: 1000, smartHome: { enabled: false, provider: 'none' } },
                system: { logLevel: 'INFO', maxLogSizeMb: 10, minimizeToTray: true, desktopOverlay: true, notifications: { desktop: true, sound: true } },
              },
            }),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      } as Response);
    });

    render(
      <DashboardProvider>
        <SettingsPanel />
      </DashboardProvider>
    );

    await waitFor(() => {
      expect(screen.queryByText(/Loading your preferences/i)).not.toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText('AI & Models')).toBeInTheDocument();
    expect(screen.getByText('Voice')).toBeInTheDocument();
    expect(screen.getByText('Persona')).toBeInTheDocument();
    expect(screen.getByText('Security & Keys')).toBeInTheDocument();
    expect(screen.getByText('Automation')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });
});
