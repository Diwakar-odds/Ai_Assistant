import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Globe, Zap } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';
import { useState, useEffect } from 'react';

// Modern Circular Audio Waveform (like the reference image)
const ModernWaveform = ({ audioLevel, isActive }: { audioLevel: number; isActive: boolean }) => {
  const points = 100;
  const centerY = 100;
  const amplitude = isActive ? 30 + (audioLevel / 100) * 40 : 20;

  // Generate smooth waveform path
  const generateWavePath = () => {
    let path = `M 0 ${centerY}`;

    for (let i = 0; i <= points; i++) {
      const x = (i / points) * 200;
      const frequency = 0.05;
      const time = Date.now() * 0.001;

      // Multiple sine waves for organic feel
      const y = centerY +
        Math.sin(i * frequency + time * 2) * amplitude * 0.4 +
        Math.sin(i * frequency * 2 + time * 3) * amplitude * 0.3 +
        Math.sin(i * frequency * 0.5 + time) * amplitude * 0.3;

      path += ` L ${x} ${y}`;
    }

    return path;
  };

  const [path, setPath] = useState(generateWavePath());

  useEffect(() => {
    if (!isActive && audioLevel < 5) return;

    const interval = setInterval(() => {
      setPath(generateWavePath());
    }, 50);

    return () => clearInterval(interval);
  }, [isActive, audioLevel]);

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 200 200"
      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Waveform */}
      <motion.path
        d={path}
        stroke="#00f3ff"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        initial={{ opacity: 0 }}
        animate={{
          opacity: isActive ? [0.6, 1, 0.6] : 0.3,
          filter: isActive ? 'drop-shadow(0 0 8px #00f3ff)' : 'none'
        }}
        transition={{
          opacity: { duration: 2, repeat: Infinity, ease: 'easeInOut' }
        }}
      />

      {/* Mirror waveform */}
      <motion.path
        d={path}
        stroke="#00f3ff"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        className="origin-center scale-y-[-1]"
        initial={{ opacity: 0 }}
        animate={{
          opacity: isActive ? [0.4, 0.7, 0.4] : 0.2,
          filter: isActive ? 'drop-shadow(0 0 6px #00f3ff)' : 'none'
        }}
        transition={{
          opacity: { duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }
        }}
      />
    </svg>
  );
};

const VoiceButton = () => {
  const {
    isVoiceActive,
    interimTranscript,
    audioLevel,
    toggleVoice,
    setVoiceLanguage,
    alwaysActive,
    toggleAlwaysActive,
    __aiMode,
    aiProvider,
    setAIProvider,
    __toggleAIMode
  } = useDashboard();

  const [showLangSelector, setShowLangSelector] = useState(false);
  const [showProviderSelector, setShowProviderSelector] = useState(false);
  const [selectedLang, setSelectedLang] = useState('en-US');

  const languages = [
    { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
    { code: 'en-IN', name: 'English (India)', flag: '🇮🇳' },
    { code: 'hi-IN', name: 'हिंदी (Hindi)', flag: '🇮🇳' },
    { code: 'auto', name: 'Auto Detect', flag: '🌐' },
  ];

  const aiProviders = [
    { id: 'gemini' as const, name: 'Gemini', icon: '🔷', color: 'blue' },
    { id: 'openai' as const, name: 'OpenAI', icon: '🟢', color: 'green' },
    { id: 'ollama' as const, name: 'Ollama', icon: '🤖', color: 'purple' },
  ];

  const currentProvider = aiProviders.find(p => p.id === aiProvider) || aiProviders[0];

  const handleLanguageChange = (langCode: string) => {
    setSelectedLang(langCode);
    setVoiceLanguage?.(langCode);
    setShowLangSelector(false);
  };

  const handleProviderChange = (providerId: 'gemini' | 'openai' | 'ollama') => {
    setAIProvider(providerId);
    setShowProviderSelector(false);
  };

  const isListening = isVoiceActive || alwaysActive;

  return (
    <motion.div
      className="flex flex-col items-center gap-2 sm:gap-3 w-full max-w-sm mx-auto"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      {/* Main circular visualizer */}
      <div className="relative w-full max-w-[180px] sm:max-w-[220px] md:max-w-[240px] lg:max-w-[260px] aspect-square overflow-visible">
        {/* Outer glowing circle */}
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-[#00f3ff]"
          style={{
            boxShadow: isListening ? '0 0 40px rgba(0, 217, 255, 0.4), inset 0 0 40px rgba(0, 217, 255, 0.1)' : '0 0 20px rgba(0, 217, 255, 0.2)',
          }}
          animate={{
            scale: isListening ? [1, 1.02, 1] : 1,
            opacity: isListening ? [0.8, 1, 0.8] : 0.6,
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* Waveform visualization */}
        <ModernWaveform audioLevel={audioLevel} isActive={isListening} />

        {/* Center microphone button */}
        <motion.button
          onClick={toggleVoice}
          className="absolute inset-0 m-auto w-[28%] h-[28%] rounded-full bg-gradient-to-br from-[#1a1f2e] to-[#0f1419] border-2 border-[#00f3ff]/30 flex items-center justify-center cursor-pointer group z-10"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          animate={{
            boxShadow: isListening
              ? ['0 0 20px rgba(0, 217, 255, 0.5)', '0 0 30px rgba(0, 217, 255, 0.7)', '0 0 20px rgba(0, 217, 255, 0.5)']
              : '0 0 10px rgba(0, 217, 255, 0.2)',
          }}
          transition={{
            boxShadow: {
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            },
          }}
        >
          {isListening ? (
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              <Mic className="w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8 text-[#00f3ff]" strokeWidth={2} />
            </motion.div>
          ) : (
            <MicOff className="w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8 text-[#00f3ff]/60 group-hover:text-[#00f3ff] transition-colors" strokeWidth={2} />
          )}
        </motion.button>

        {/* Pulsing rings when active */}
        {isListening && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-[#00f3ff]/40"
              animate={{
                scale: [1, 1.15, 1.15],
                opacity: [0.6, 0, 0],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
            <motion.div
              className="absolute inset-0 rounded-full border-2 border-[#00f3ff]/40"
              animate={{
                scale: [1, 1.15, 1.15],
                opacity: [0.6, 0, 0],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeOut',
                delay: 0.7,
              }}
            />
          </>
        )}
      </div>

      {/* Status text */}
      <motion.div
        className="text-center"
        animate={{
          opacity: isListening ? [0.7, 1, 0.7] : 0.5,
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <p className="text-[#00f3ff] text-sm sm:text-base md:text-lg font-light tracking-wide">
          {isListening ? 'Listening...' : 'Tap to speak'}
        </p>
        {isListening && interimTranscript && (
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-white/60 text-xs sm:text-sm mt-2 max-w-md px-4"
          >
            {interimTranscript}
          </motion.p>
        )}
      </motion.div>

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
        >
          <Zap className="w-2.5 h-2.5 sm:w-3 sm:h-3 inline mr-1" />
          Always On
        </motion.button>

        {/* AI Provider Selector */}
        <div className="relative">
          <motion.button
            onClick={() => setShowProviderSelector(!showProviderSelector)}
            className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${aiProvider === 'ollama'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-400/40'
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
