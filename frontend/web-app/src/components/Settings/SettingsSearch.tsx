import React, { useState, useEffect, useRef } from 'react';
import { Search, X, ArrowRight, CornerDownLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSettings } from './SettingsContext';

interface SearchItem {
  id: string;
  label: string;
  description: string;
  sectionId: string;
  sectionName: string;
  keywords: string[];
}

const SEARCH_REGISTRY: SearchItem[] = [
  // General
  { id: 'gen-lang', label: 'Primary Language', description: 'Default language for assistant speech and UI', sectionId: 'general', sectionName: 'General', keywords: ['language', 'english', 'hindi', 'locale'] },
  { id: 'gen-hinglish', label: 'Hinglish Mode', description: 'Mixed Hindi-English speech & instructions', sectionId: 'general', sectionName: 'General', keywords: ['hinglish', 'hindi', 'bilingual', 'desi'] },
  { id: 'gen-theme', label: 'Theme Appearance', description: 'Dark, Light, or System visual style', sectionId: 'general', sectionName: 'General', keywords: ['theme', 'dark', 'light', 'color', 'ui'] },
  { id: 'gen-boot', label: 'Start on Boot', description: 'Launch Pulsar when Windows starts', sectionId: 'general', sectionName: 'General', keywords: ['boot', 'startup', 'windows', 'autostart'] },
  { id: 'gen-anim', label: 'Smooth Animations', description: 'Fluid transitions and reactor orb pulsing', sectionId: 'general', sectionName: 'General', keywords: ['animations', 'motion', 'orb', 'effects'] },

  // AI & Models
  { id: 'ai-provider', label: 'Active Intelligence Provider', description: 'Local GGUF, Google Gemini, OpenAI, or Ollama', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['provider', 'gemini', 'openai', 'gguf', 'local', 'ollama', 'cloud'] },
  { id: 'ai-model', label: 'Active Model', description: 'Specific LLM checkpoint for inference', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['model', 'gpt-4o', 'gemini-2.5', 'pulsar', 'llama'] },
  { id: 'ai-temp', label: 'Temperature (Creativity)', description: 'Controls randomness of model output', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['temperature', 'creativity', 'hallucination', 'randomness'] },
  { id: 'ai-tokens', label: 'Max Response Tokens', description: 'Upper boundary for generated response length', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['tokens', 'length', 'output', 'size'] },
  { id: 'ai-gpu', label: 'GPU Acceleration', description: 'Hardware acceleration for local GGUF models', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['gpu', 'cuda', 'vulkan', 'acceleration', 'hardware'] },
  { id: 'ai-safety', label: 'Content Safety Settings', description: 'Thresholds for moderation and filtering', sectionId: 'ai', sectionName: 'AI & Models', keywords: ['safety', 'filter', 'hate', 'harassment', 'block'] },

  // Voice
  { id: 'v-stt', label: 'Speech-to-Text (STT)', description: 'Microphone voice recognition engine', sectionId: 'voice', sectionName: 'Voice', keywords: ['stt', 'mic', 'microphone', 'speech', 'listen', 'whisper'] },
  { id: 'v-tts', label: 'Text-to-Speech (TTS)', description: 'Neural speech synthesis and spoken audio', sectionId: 'voice', sectionName: 'Voice', keywords: ['tts', 'voice', 'speech', 'audio', 'sound', 'speak', 'swara', 'aria'] },
  { id: 'v-speed', label: 'Speaking Speed & Pitch', description: 'Pacing and tone of spoken responses', sectionId: 'voice', sectionName: 'Voice', keywords: ['speed', 'pitch', 'rate', 'fast', 'slow'] },
  { id: 'v-wake', label: 'Hands-Free Wake Word', description: 'Voice triggers (e.g., "Hey Pulsar")', sectionId: 'voice', sectionName: 'Voice', keywords: ['wake', 'word', 'hey pulsar', 'trigger', 'hotword'] },

  // Persona
  { id: 'p-style', label: 'Persona Style', description: 'JARVIS, Friendly Companion, or Concise', sectionId: 'persona', sectionName: 'Persona', keywords: ['persona', 'style', 'jarvis', 'character', 'tone'] },
  { id: 'p-name', label: 'Assistant & User Title', description: 'Assistant name and how it addresses you (Boss/Sir)', sectionId: 'persona', sectionName: 'Persona', keywords: ['name', 'title', 'boss', 'sir', 'nickname'] },
  { id: 'p-ack', label: 'Wake Acknowledgment', description: 'Chime or verbal confirmation on wake trigger', sectionId: 'persona', sectionName: 'Persona', keywords: ['ack', 'acknowledgment', 'beep', 'chime'] },

  // Security
  { id: 's-gemini-key', label: 'Google Gemini API Key', description: 'Cloud credentials for Gemini models', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['api', 'key', 'gemini', 'google', 'token'] },
  { id: 's-openai-key', label: 'OpenAI API Key', description: 'Cloud credentials for GPT models', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['api', 'key', 'openai', 'gpt', 'token'] },
  { id: 's-perm-apps', label: 'Allow App Execution', description: 'Permission to open and close PC programs', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['permission', 'apps', 'launch', 'execute'] },
  { id: 's-perm-web', label: 'Allow Web Browsing', description: 'Permission to browse internet and search Google', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['permission', 'web', 'internet', 'browse', 'search'] },
  { id: 's-perm-sys', label: 'Allow Windows Control', description: 'Permission for volume, brightness, and WiFi', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['permission', 'system', 'volume', 'brightness', 'control'] },
  { id: 's-perm-del', label: 'Allow File Deletion', description: 'Permission to remove disk files', sectionId: 'security', sectionName: 'Security & Keys', keywords: ['permission', 'delete', 'files', 'remove', 'danger'] },

  // Automation
  { id: 'a-backup', label: 'Automated Database Backup', description: 'Scheduled snapshots of settings and logs', sectionId: 'automation', sectionName: 'Automation', keywords: ['backup', 'database', 'archive', 'schedule'] },
  { id: 'a-smarthome', label: 'Smart Home Bridge', description: 'Home Assistant or IoT ecosystem link', sectionId: 'automation', sectionName: 'Automation', keywords: ['smart', 'home', 'iot', 'homeassistant', 'lights'] },

  // System
  { id: 'sys-overlay', label: 'Minimized 4D Orb Overlay', description: 'Center-taskbar floating orb when minimized', sectionId: 'system', sectionName: 'System', keywords: ['overlay', 'minimized', 'orb', 'floating', 'taskbar'] },
  { id: 'sys-tray', label: 'Minimize to System Tray', description: 'Run quietly in taskbar tray on close', sectionId: 'system', sectionName: 'System', keywords: ['tray', 'minimize', 'close', 'background'] },
  { id: 'sys-logs', label: 'Logging Level & Rotation', description: 'Trace verbosity and log file sizes', sectionId: 'system', sectionName: 'System', keywords: ['logs', 'debug', 'info', 'diagnostics'] },
  { id: 'sys-reset', label: 'Factory Reset All Settings', description: 'Reset all configuration back to defaults', sectionId: 'system', sectionName: 'System', keywords: ['reset', 'factory', 'default', 'restore'] },
];

export const SettingsSearch: React.FC = () => {
  const { setActiveSection } = useSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global Ctrl+K / Cmd+K hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Filter matching items
  const filtered = SEARCH_REGISTRY.filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase().trim();
    return (
      item.label.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.sectionName.toLowerCase().includes(q) ||
      item.keywords.some((k) => k.toLowerCase().includes(q))
    );
  }).slice(0, 8);

  const handleSelect = (item: SearchItem) => {
    setActiveSection(item.sectionId);
    setIsOpen(false);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      handleSelect(filtered[selectedIndex]);
    }
  };

  return (
    <>
      {/* Trigger Button inside settings header */}
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 bg-[#1F2228] hover:bg-[#2A2D35] text-[#9CA3AF] hover:text-white border border-[#2A2D35] hover:border-[#3A3D45] rounded-lg text-xs transition-colors cursor-pointer"
      >
        <Search className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Search settings...</span>
        <span className="inline sm:hidden">Search</span>
        <kbd className="hidden sm:inline px-1.5 py-0.5 text-[10px] font-mono bg-[#2A2D35] text-[#9CA3AF] rounded border border-[#3A3D45]">
          Ctrl K
        </kbd>
      </button>

      {/* Modal Overlay */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15 }}
              className="w-full max-w-xl bg-[#16181D] border border-[#2A2D35] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Search Bar */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-[#2A2D35]">
                <Search className="w-4 h-4 text-[#3B82F6]" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setSelectedIndex(0);
                  }}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Type to search all settings, models, or permissions..."
                  className="flex-1 bg-transparent text-sm text-white placeholder-[#9CA3AF] outline-none"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => setQuery('')}
                    className="text-[#9CA3AF] hover:text-white p-1"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-2 py-0.5 text-xs text-[#9CA3AF] hover:text-white bg-[#2A2D35] rounded"
                >
                  ESC
                </button>
              </div>

              {/* Results List */}
              <div className="max-h-80 overflow-y-auto p-2 divide-y divide-[#1F2228]">
                {filtered.length === 0 ? (
                  <div className="py-8 text-center text-xs text-[#9CA3AF]">
                    No settings found matching &quot;{query}&quot;
                  </div>
                ) : (
                  filtered.map((item, idx) => {
                    const isSelected = idx === selectedIndex;
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleSelect(item)}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className={`
                          flex items-center justify-between p-3 rounded-xl cursor-pointer transition-colors
                          ${isSelected ? 'bg-[#3B82F6]/15 text-white' : 'text-[#9CA3AF] hover:bg-[#1F2228] hover:text-white'}
                        `}
                      >
                        <div className="min-w-0 pr-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-white">{item.label}</span>
                            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#2A2D35] text-[#9CA3AF] border border-[#3A3D45]">
                              {item.sectionName}
                            </span>
                          </div>
                          <p className="text-xs text-[#9CA3AF] truncate mt-0.5">
                            {item.description}
                          </p>
                        </div>
                        <div className="shrink-0 flex items-center text-[#3B82F6]">
                          {isSelected ? (
                            <CornerDownLeft className="w-4 h-4" />
                          ) : (
                            <ArrowRight className="w-4 h-4 opacity-40" />
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2 bg-[#121418] border-t border-[#1F2228] flex items-center justify-between text-[11px] text-[#6B7280]">
                <span>Navigate with ↑ ↓ keys</span>
                <span>Press Enter to select</span>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};
