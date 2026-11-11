import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Globe,
  Brain,
  Mic,
  Sparkles,
  Shield,
  Zap,
  Server,
  Check,
  Loader2,
  AlertCircle,
  LucideIcon,
} from 'lucide-react';
import { SettingsProvider, useSettings } from './SettingsContext';
import { SettingsSearch } from './SettingsSearch';
import {
  GeneralSection,
  AIProviderSection,
  VoiceSection,
  PersonaSection,
  SecuritySection,
  AutomationSection,
  SystemSection,
} from './sections';

interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'general', label: 'General', icon: Globe },
  { id: 'ai', label: 'AI & Models', icon: Brain },
  { id: 'voice', label: 'Voice', icon: Mic },
  { id: 'persona', label: 'Persona', icon: Sparkles },
  { id: 'security', label: 'Security & Keys', icon: Shield },
  { id: 'automation', label: 'Automation', icon: Zap },
  { id: 'system', label: 'System', icon: Server },
];

const SettingsInner: React.FC = () => {
  const { activeSection, setActiveSection, saveStatus, loading, errorMessage } = useSettings();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 py-12">
        <Loader2 className="w-10 h-10 text-[#3B82F6] animate-spin mb-3" />
        <p className="text-sm text-[#9CA3AF]">Loading your preferences...</p>
      </div>
    );
  }

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'general':
        return <GeneralSection />;
      case 'ai':
        return <AIProviderSection />;
      case 'voice':
        return <VoiceSection />;
      case 'persona':
        return <PersonaSection />;
      case 'security':
        return <SecuritySection />;
      case 'automation':
        return <AutomationSection />;
      case 'system':
        return <SystemSection />;
      default:
        return <GeneralSection />;
    }
  };

  return (
    <div className="flex flex-col h-[78vh] max-h-[850px] overflow-hidden -mx-6 -my-4">
      {/* Header bar with auto-save badge and search */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-[#2A2D35] bg-[#16181D] shrink-0">
        <div className="flex items-center gap-3">
          <div>
            <h3 className="text-lg font-bold text-white leading-tight">Settings</h3>
            <p className="text-xs text-[#9CA3AF]">Customise intelligence, voice, and system behavior</p>
          </div>

          {/* Auto-save status indicator */}
          <div className="hidden sm:flex items-center pl-3">
            {saveStatus === 'saving' && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-full animate-pulse">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Saving...</span>
              </span>
            )}
            {saveStatus === 'saved' && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                <Check className="w-3 h-3" />
                <span>All changes saved</span>
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-full">
                <AlertCircle className="w-3 h-3" />
                <span>{errorMessage || 'Failed to save'}</span>
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <SettingsSearch />
        </div>
      </div>

      {/* Main split: sidebar + content pane */}
      <div className="flex flex-col md:flex-row flex-1 overflow-hidden bg-[#16181D]">
        {/* Sidebar Nav */}
        <div className="w-full md:w-56 lg:w-64 bg-[#14161B] border-b md:border-b-0 md:border-r border-[#2A2D35] p-2 md:p-3 shrink-0 flex md:flex-col gap-1 overflow-x-auto md:overflow-y-auto no-scrollbar">
          {NAV_ITEMS.map((item) => {
            const isActive = activeSection === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveSection(item.id)}
                className={`
                  flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 whitespace-nowrap cursor-pointer text-left
                  ${isActive
                    ? 'bg-[#3B82F6] text-white shadow-lg shadow-[#3B82F6]/20 font-semibold'
                    : 'text-[#9CA3AF] hover:text-white hover:bg-[#1F2228]'
                  }
                `}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-[#9CA3AF]'}`} />
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="px-1.5 py-0.5 text-[9px] uppercase font-bold rounded bg-white/20 text-white">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content View Pane */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#0F1115] custom-scrollbar">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
              className="max-w-4xl mx-auto pb-12"
            >
              {renderActiveSection()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export const SettingsPanel: React.FC = () => {
  return (
    <SettingsProvider>
      <SettingsInner />
    </SettingsProvider>
  );
};

export default SettingsPanel;
