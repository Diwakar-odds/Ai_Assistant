import React from 'react';
import { Brain, Cpu, ShieldAlert, Sliders, HardDrive, Check, Zap } from 'lucide-react';
import { useSettings } from '../SettingsContext';
import { SectionCard, SettingRow, RangeSlider, SelectDropdown, ToggleSwitch, TextInput } from '../shared';

interface ProviderCardInfo {
  id: string;
  name: string;
  badge: string;
  tagline: string;
  icon: string;
}

const PROVIDERS: ProviderCardInfo[] = [
  {
    id: 'gguf',
    name: 'Local GGUF',
    badge: 'Offline',
    tagline: '100% Private, on-device AI. Zero API fees or internet required.',
    icon: '🧠',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    badge: 'Recommended',
    tagline: 'Lightning fast, multimodal, 1M+ context window cloud intelligence.',
    icon: '🔷',
  },
  {
    id: 'openai',
    name: 'OpenAI GPT',
    badge: 'Cloud',
    tagline: 'Industry-standard GPT-4o & reasoning models for complex tasks.',
    icon: '🟢',
  },
  {
    id: 'ollama',
    name: 'Ollama API',
    badge: 'Self-Hosted',
    tagline: 'Connect to your local Ollama server instance on port 11434.',
    icon: '🦙',
  },
];

const STATIC_MODELS: Record<string, string[]> = {
  gemini: ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash'],
  openai: ['gpt-4o-mini', 'gpt-4o', 'o3-mini', 'gpt-4-turbo'],
  ollama: ['llama3.2', 'mistral', 'qwen2.5', 'deepseek-r1:8b'],
};

const SAFETY_LEVELS = [
  { value: 'block_none', label: 'Allow All (Unrestricted)' },
  { value: 'block_low_and_above', label: 'Strict (Block Low & Above)' },
  { value: 'block_medium_and_above', label: 'Standard (Block Medium & Above)' },
  { value: 'block_high_only', label: 'Lenient (Block High Only)' },
];

export const AIProviderSection: React.FC = () => {
  const { settings, updateSetting, dynamicGgufModels } = useSettings();

  if (!settings) return null;
  const ai = settings.ai;
  const currentProvider = (ai.defaultProvider || 'gemini').toLowerCase();

  // Resolve models for the current provider
  const availableModelOptions: { value: string; label: string }[] = (() => {
    let list: string[] = [];
    if (currentProvider === 'gguf') {
      list = dynamicGgufModels.length > 0 ? dynamicGgufModels : ['pulsar-final-q4_k_m'];
    } else {
      list = STATIC_MODELS[currentProvider] || ['default'];
    }
    // Ensure current model is selectable even if custom
    if (ai.defaultModel && !list.includes(ai.defaultModel)) {
      list = [ai.defaultModel, ...list];
    }
    return list.map((m) => ({ value: m, label: m }));
  })();

  const handleProviderSelect = (providerId: string) => {
    updateSetting('ai', ['defaultProvider'], providerId);
    // Pick the first available model for that provider
    let firstModel = 'gemini-2.5-flash';
    if (providerId === 'gguf') {
      firstModel = dynamicGgufModels[0] || 'pulsar-final-q4_k_m';
      updateSetting('ai', ['localLlm', 'modelPath'], `models/${firstModel}.gguf`);
    } else if (STATIC_MODELS[providerId]?.length) {
      firstModel = STATIC_MODELS[providerId][0];
    }
    updateSetting('ai', ['defaultModel'], firstModel);
  };

  const handleModelChange = (modelName: string) => {
    updateSetting('ai', ['defaultModel'], modelName);
    if (currentProvider === 'gguf') {
      const sanitized = modelName.endsWith('.gguf') ? modelName : `${modelName}.gguf`;
      updateSetting('ai', ['localLlm', 'modelPath'], `models/${sanitized}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Visual Provider Selection Grid */}
      <div>
        <h4 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
          <Brain className="w-5 h-5 text-[#3B82F6]" />
          <span>Active Intelligence Provider</span>
        </h4>
        <p className="text-xs text-[#9CA3AF] mb-4">
          Choose whether your commands and chat queries are processed locally on your machine or routed through cloud frontier models.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {PROVIDERS.map((p) => {
            const isSelected = currentProvider === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handleProviderSelect(p.id)}
                className={`
                  relative flex flex-col text-left p-4 rounded-xl border-2 transition-all duration-200 cursor-pointer
                  ${isSelected
                    ? 'border-[#3B82F6] bg-[#3B82F6]/10 shadow-lg shadow-[#3B82F6]/15'
                    : 'border-[#2A2D35] bg-[#1F2228] hover:border-[#3A3D45] hover:bg-[#252830]'
                  }
                `}
              >
                {isSelected && (
                  <span className="absolute top-3 right-3 flex items-center justify-center w-5 h-5 rounded-full bg-[#3B82F6] text-white">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </span>
                )}

                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{p.icon}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-[#2A2D35] text-[#9CA3AF] border border-[#3A3D45]">
                    {p.badge}
                  </span>
                </div>

                <p className="text-sm font-semibold text-white mb-1">{p.name}</p>
                <p className="text-xs text-[#9CA3AF] leading-relaxed flex-1">{p.tagline}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Model & Generation Parameters */}
      <SectionCard
        title="Model & Hyperparameters"
        description="Fine-tune inference randomness, response tokens, and context window"
        icon={Sliders}
      >
        <SettingRow
          label="Active Model"
          description={`Selected model for ${currentProvider.toUpperCase()} operations`}
        >
          <SelectDropdown
            value={ai.defaultModel || availableModelOptions[0]?.value}
            options={availableModelOptions}
            onChange={handleModelChange}
          />
        </SettingRow>

        <SettingRow
          label="Temperature (Creativity)"
          description="0.0 is deterministic and precise, 1.0 is balanced, 2.0 is highly creative"
        >
          <RangeSlider
            value={typeof ai.temperature === 'number' ? ai.temperature : 0.7}
            min={0}
            max={2}
            step={0.1}
            onChange={(val) => updateSetting('ai', ['temperature'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Maximum Response Tokens"
          description="Upper limit on length of generated responses"
        >
          <RangeSlider
            value={ai.maxTokens || 2048}
            min={256}
            max={8192}
            step={256}
            unit="tokens"
            onChange={(val) => updateSetting('ai', ['maxTokens'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Context Window Limit"
          description="Size of conversation history and memory fed into LLM prompts"
        >
          <RangeSlider
            value={ai.contextWindow || 4096}
            min={1024}
            max={32768}
            step={1024}
            unit="tokens"
            onChange={(val) => updateSetting('ai', ['contextWindow'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 3. Local GGUF Runtime Options */}
      <SectionCard
        title="Local Engine Settings"
        description="Configuration for on-device GGUF / LLaMA runtime engines"
        icon={HardDrive}
        collapsible
        defaultExpanded={currentProvider === 'gguf'}
      >
        <SettingRow
          label="Enable Local LLM Engine"
          description="Activate the local embedded inference server"
        >
          <ToggleSwitch
            checked={Boolean(ai.localLlm?.enabled)}
            onChange={(val) => updateSetting('ai', ['localLlm', 'enabled'], val)}
          />
        </SettingRow>

        <SettingRow
          label="GGUF Model File Path"
          description="Relative or absolute path to your quantised .gguf model weights"
        >
          <TextInput
            value={ai.localLlm?.modelPath || 'models/pulsar-final-q4_k_m.gguf'}
            onChange={(val) => updateSetting('ai', ['localLlm', 'modelPath'], val)}
            placeholder="models/my-model.gguf"
          />
        </SettingRow>

        <SettingRow
          label="GPU Acceleration (cuBLAS / Vulkan)"
          description="Offload model layers to dedicated NVIDIA or AMD GPU if available"
          badge="Hardware"
        >
          <ToggleSwitch
            checked={Boolean(ai.localLlm?.useGpu)}
            onChange={(val) => updateSetting('ai', ['localLlm', 'useGpu'], val)}
          />
        </SettingRow>
      </SectionCard>

      {/* 4. Safety Guardrails */}
      <SectionCard
        title="Safety & Content Moderation"
        description="Thresholds for cloud API content safety filters"
        icon={ShieldAlert}
        collapsible
        defaultExpanded={false}
      >
        <SettingRow
          label="Harassment Filter"
          description="Block content that targets individuals with derogatory language"
        >
          <SelectDropdown
            value={ai.safetySettings?.harassment || 'block_none'}
            options={SAFETY_LEVELS}
            onChange={(val) => updateSetting('ai', ['safetySettings', 'harassment'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Hate Speech Filter"
          description="Filter language promoting hatred against identity groups"
        >
          <SelectDropdown
            value={ai.safetySettings?.hateSpeech || 'block_none'}
            options={SAFETY_LEVELS}
            onChange={(val) => updateSetting('ai', ['safetySettings', 'hateSpeech'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Dangerous Content"
          description="Prevent generation of instructions for dangerous activities"
        >
          <SelectDropdown
            value={ai.safetySettings?.dangerousContent || 'block_none'}
            options={SAFETY_LEVELS}
            onChange={(val) => updateSetting('ai', ['safetySettings', 'dangerousContent'], val)}
          />
        </SettingRow>

        <SettingRow
          label="Sexually Explicit"
          description="Filter adult and explicit content"
        >
          <SelectDropdown
            value={ai.safetySettings?.sexuallyExplicit || 'block_none'}
            options={SAFETY_LEVELS}
            onChange={(val) => updateSetting('ai', ['safetySettings', 'sexuallyExplicit'], val)}
          />
        </SettingRow>
      </SectionCard>
    </div>
  );
};
