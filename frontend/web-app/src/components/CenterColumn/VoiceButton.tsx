import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Globe, Zap, AlertTriangle, Loader2, Volume2 } from 'lucide-react';
import { useDashboard, OrbState } from '../../contexts/DashboardContext';
import { useState } from 'react';
import ArcReactorRings from './ArcReactorRings';
import DangerBanner from './DangerBanner';

const STATE_UI_META: Record<OrbState, { label: string; color: string }> = {
  idle: { label: 'Standing still · Tap or say "Pulsar"', color: '#818cf8' },
  listening: { label: 'Listening...', color: '#00f3ff' },
  speaking: { label: 'Speaking...', color: '#ec4899' },
  processing: { label: 'Processing...', color: '#f59e0b' },
  error: { label: 'Action failed — check attention', color: '#ef4444' },
};

const VoiceButton = () => {
  const {
    isVoiceActive,
    interimTranscript,
    orbState,
    orbAudioLevel,
    orbError,
    toggleVoice,
    setVoiceLanguage,
    alwaysActive,
    toggleAlwaysActive,
    requireWakeWord,
    wakeWordDetected,
    toggleWakeWord,
    aiProvider,
    setAIProvider,
    hudData,
    pendingDangerAction,
    authorizeAction,
    cancelAction,
  } = useDashboard();

  const [showLangSelector, setShowLangSelector] = useState(false);
  const [showProviderSelector, setShowProviderSelector] = useState(false);
  const [selectedLang, setSelectedLang] = useState(() => {
    // Persist language selection across reloads — default to Hindi
    return localStorage.getItem('voice_language') || 'hi-IN';
  });

  const languages = [
    { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
    { code: 'en-IN', name: 'English (India)', flag: '🇮🇳' },
    { code: 'hi-IN', name: 'हिंदी (Hindi)', flag: '🇮🇳' },
    { code: 'auto', name: 'Auto Detect', flag: '🌐' },
  ];

  const aiProviders = [
    { id: 'gguf' as const, name: 'GGUF (Local)', icon: '🧠', color: 'yellow' },
    { id: 'openai' as const, name: 'OpenAI', icon: '🟢', color: 'green' },
    { id: 'gemini' as const, name: 'Gemini', icon: '🔷', color: 'blue' },
  ];

  const currentProvider = aiProviders.find(p => p.id === aiProvider) || aiProviders[0];

  const handleLanguageChange = (langCode: string) => {
    setSelectedLang(langCode);
    localStorage.setItem('voice_language', langCode);
    setVoiceLanguage?.(langCode);
    setShowLangSelector(false);
  };

  const handleProviderChange = (providerId: 'gemini' | 'openai' | 'gguf') => {
    setAIProvider(providerId);
    setShowProviderSelector(false);
  };

  const isListening = orbState === 'listening' || isVoiceActive || wakeWordDetected;
  const activeMeta = STATE_UI_META[orbState] || STATE_UI_META.idle;
  const statusLabel =
    orbState === 'error' && orbError
      ? orbError
      : orbState === 'idle'
        ? (alwaysActive ? 'Always Wake ON · Say "Hey Pulsar"' : 'Standing still · Tap or say "Hey Pulsar"')
        : activeMeta.label;

  return (
    <motion.div
      className="flex flex-col items-center gap-2 sm:gap-3 w-full max-w-sm mx-auto"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      {/* 4D Glowing Particle Orb */}
      <div
        id="ai-orb"
        onClick={toggleVoice}
        className="relative w-[84%] max-w-[300px] aspect-square overflow-visible cursor-pointer select-none"
      >
        <ArcReactorRings
          mood={hudData.mood}
          projectProgress={hudData.projectProgress}
          projectName={hudData.projectName}
          systemHealth={hudData.systemHealth}
          dangerMode={!!pendingDangerAction}
          orbState={orbState}
          audioLevel={orbAudioLevel}
        />

        {/* Minimal translucent frosted center mic pill so the 4D core shines through */}
        <motion.button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            toggleVoice();
          }}
          aria-label={isListening ? 'Stop listening' : 'Start voice listening'}
          className="absolute inset-0 m-auto w-11 h-11 rounded-full bg-slate-950/35 backdrop-blur-sm flex items-center justify-center cursor-pointer z-10 transition-colors"
          style={{
            border: `1px solid ${activeMeta.color}44`,
            boxShadow: `0 0 18px ${activeMeta.color}33`,
          }}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.94 }}
        >
          {orbState === 'error' ? (
            <AlertTriangle className="w-5 h-5" style={{ color: activeMeta.color }} strokeWidth={2} />
          ) : orbState === 'processing' ? (
            <Loader2 className="w-5 h-5 animate-spin" style={{ color: activeMeta.color }} strokeWidth={2} />
          ) : orbState === 'speaking' ? (
            <Volume2 className="w-5 h-5" style={{ color: activeMeta.color }} strokeWidth={2} />
          ) : isListening ? (
            <motion.div
              animate={{ scale: [1, 1.18, 1] }}
              transition={{ duration: 1.3, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Mic className="w-5 h-5" style={{ color: activeMeta.color }} strokeWidth={2} />
            </motion.div>
          ) : (
            <MicOff className="w-5 h-5 text-indigo-200/75 hover:text-cyan-300 transition-colors" strokeWidth={1.8} />
          )}
        </motion.button>
      </div>

      {/* Status text */}
      <motion.div
        className="text-center"
        animate={{
          opacity: orbState !== 'idle' ? [0.78, 1, 0.78] : 0.75,
        }}
        transition={{
          duration: orbState === 'error' ? 0.9 : 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <p
          className="text-sm sm:text-base md:text-lg font-light tracking-wide transition-colors duration-300"
          style={{ color: activeMeta.color }}
        >
          {statusLabel}
        </p>
        {interimTranscript && orbState !== 'idle' && (
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-white/70 text-xs sm:text-sm mt-2 max-w-md px-4"
          >
            {interimTranscript}
          </motion.p>
        )}
      </motion.div>

      {/* Danger Authorization Banner */}
      <DangerBanner
        pendingAction={pendingDangerAction}
        onAuthorize={authorizeAction}
        onCancel={cancelAction}
      />

      {/* Compact controls */}
      <div className="flex gap-2 sm:gap-3 items-center flex-wrap justify-center">
        <motion.button
          onClick={toggleAlwaysActive}
          className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${alwaysActive
            ? 'bg-[#00f3ff]/20 text-[#00f3ff] border border-[#00f3ff]/40'
            : 'bg-[#1a1f2e] text-[#00f3ff]/50 border border-[#00f3ff]/20 hover:border-[#00f3ff]/40'
            }`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          title={alwaysActive ? 'Always listening enabled' : 'Click to enable continuous listening'}
        >
          <Zap className="w-2.5 h-2.5 sm:w-3 sm:h-3 inline mr-1" />
          Always On: {alwaysActive ? 'ON' : 'OFF'}
        </motion.button>

        <motion.button
          onClick={toggleWakeWord}
          className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${requireWakeWord
            ? 'bg-amber-500/20 text-amber-400 border border-amber-400/40'
            : 'bg-[#1a1f2e] text-amber-400/50 border border-amber-400/20 hover:border-amber-400/40'
            }`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          title={requireWakeWord ? 'Wake word active ("Hey Pulsar", "Pulsar", "Hey Assistant")' : 'Wake word off (executes directly)'}
        >
          <Mic className="w-2.5 h-2.5 sm:w-3 sm:h-3 inline mr-1" />
          Wake Word: {requireWakeWord ? 'ON' : 'OFF'}
        </motion.button>

        {/* AI Provider Selector */}
        <div className="relative">
          <motion.button
            onClick={() => setShowProviderSelector(!showProviderSelector)}
            className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${aiProvider === 'gguf'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40'
              : aiProvider === 'openai'
                ? 'bg-green-500/20 text-green-400 border border-green-400/40'
                : 'bg-blue-500/20 text-blue-400 border border-blue-400/40'
              }`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title={`AI Provider: ${currentProvider.name}`}
          >
            {currentProvider.icon} {currentProvider.name}
          </motion.button>

          {/* Provider dropdown */}
          <AnimatePresence>
            {showProviderSelector && (
              <motion.div
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                className="absolute left-0 top-full mt-2 bg-[#1a1f2e] border border-[#00f3ff]/30 rounded-lg overflow-hidden shadow-xl z-50 min-w-[140px]"
              >
                {aiProviders.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => handleProviderChange(provider.id)}
                    className={`w-full px-4 py-2 flex items-center gap-3 hover:bg-[#00f3ff]/10 transition-colors text-left ${aiProvider === provider.id ? 'bg-[#00f3ff]/10' : ''
                      }`}
                  >
                    <span className="text-lg">{provider.icon}</span>
                    <span className="text-sm text-white/80">{provider.name}</span>
                    {aiProvider === provider.id && (
                      <span className="ml-auto text-[#00f3ff]">✓</span>
                    )}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button
          onClick={() => setShowLangSelector(!showLangSelector)}
          className="px-2 sm:px-3 py-1 sm:py-1.5 bg-[#1a1f2e] border border-[#00f3ff]/20 rounded-lg hover:border-[#00f3ff]/40 transition-all"
        >
          <Globe className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-[#00f3ff]/60 inline mr-1" />
          <span className="text-[10px] sm:text-xs text-[#00f3ff]/60">
            {languages.find(l => l.code === selectedLang)?.flag}
          </span>
        </button>
      </div>

      {/* Language dropdown */}
      <AnimatePresence>
        {showLangSelector && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-[400px] bg-[#1a1f2e] border border-[#00f3ff]/30 rounded-lg overflow-hidden shadow-xl z-50"
          >
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`w-full px-4 py-2 flex items-center gap-3 hover:bg-[#00f3ff]/10 transition-colors ${selectedLang === lang.code ? 'bg-[#00f3ff]/10' : ''
                  }`}
              >
                <span className="text-lg">{lang.flag}</span>
                <span className="text-sm text-white/80">{lang.name}</span>
                {selectedLang === lang.code && (
                  <span className="ml-auto text-[#00f3ff]">✓</span>
                )}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default VoiceButton;
