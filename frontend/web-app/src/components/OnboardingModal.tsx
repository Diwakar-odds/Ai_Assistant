import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ArrowRight, Shield, Mic, Wand2, Cpu, KeyRound, X, Loader2 } from 'lucide-react';
import { apiUrl } from '../lib/api';

type ProviderChoice = 'gemini' | 'openai' | 'gguf';

const TOTAL_STEPS = 4;

export default function OnboardingModal({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(1);
  const [agreed, setAgreed] = useState(false);
  const [provider, setProvider] = useState<ProviderChoice>('gemini');
  const [geminiKey, setGeminiKey] = useState('');
  const [openAIKey, setOpenAIKey] = useState('');
  const [micGranted, setMicGranted] = useState<boolean | null>(null);
  const [requestingMic, setRequestingMic] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [loading, setLoading] = useState(false);

  const effectiveStep = Math.min(TOTAL_STEPS, Math.max(1, step));

  const handleNext = () => setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  const handleBack = () => setStep((s) => Math.max(1, s - 1));

  const handleFinish = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const apiKeys: Record<string, string> = {};
      if (geminiKey.trim()) apiKeys.googleGemini = geminiKey.trim();
      if (openAIKey.trim()) apiKeys.openAI = openAIKey.trim();

      await fetch(apiUrl('/api/settings/complete_onboarding'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme,
          defaultProvider: provider,
          micGranted: micGranted === true,
          apiKeys,
        }),
      });
      onComplete();
    } catch (e) {
      console.error('Failed to complete onboarding', e);
      onComplete(); // Still complete even if it fails so user doesn't get stuck
    } finally {
      setLoading(false);
    }
  };

  const requestMic = async () => {
    if (requestingMic) return;
    setRequestingMic(true);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicGranted(true);
      handleNext();
    } catch {
      setMicGranted(false);
      alert('Microphone permission was not granted. You can enable voice commands later from Windows Privacy Settings.');
    } finally {
      setRequestingMic(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="bg-[#1A1D24] border border-[#2A2D35] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden"
      >
        {/* Step Progress Header */}
        <div className="px-8 pt-6 pb-2 flex items-center justify-between border-b border-[#2A2D35]/70">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Pulsar AI Setup — Step {effectiveStep} of {TOTAL_STEPS}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex gap-1.5">
              {[1, 2, 3, 4].map((idx) => (
                <div
                  key={idx}
                  className={`h-1.5 w-8 rounded-full transition-colors ${
                    idx <= effectiveStep ? 'bg-blue-500' : 'bg-[#2A2D35]'
                  }`}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={handleFinish}
              disabled={loading}
              title="Skip setup and go to dashboard"
              className="text-gray-400 hover:text-white p-1 rounded hover:bg-[#2A2D35] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {effectiveStep === 1 && (
            <motion.div key="step1" exit={{ opacity: 0, x: -20 }} className="p-8">
              <div className="flex items-center gap-3 mb-5">
                <Shield className="w-8 h-8 text-blue-500" />
                <h2 className="text-2xl font-bold text-white">Welcome to Pulsar AI</h2>
              </div>
              <p className="text-gray-300 mb-5 text-sm leading-relaxed">
                Before we begin, please review our data and privacy policy. Pulsar learns from your
                interactions to personalize your desktop experience, storing history and preferences
                locally on your Windows machine.
              </p>

              <div className="bg-[#14151A] p-4 rounded-lg mb-6 max-h-40 overflow-y-auto text-xs text-gray-400 font-mono space-y-2 border border-[#2A2D35]">
                <div className="text-gray-200 font-semibold">END USER LICENSE AGREEMENT &amp; PRIVACY POLICY</div>
                <p>1. Local Storage: Conversations, preferences, and knowledge graph remain on your PC.</p>
                <p>2. Secure Secrets: Cloud API keys are encrypted via Windows Credential Manager.</p>
                <p>3. Optional Cloud Routing: Prompts only hit Google Gemini / OpenAI if selected by you.</p>
              </div>

              <label className="flex items-center gap-3 cursor-pointer group mb-7">
                <div
                  className={`w-6 h-6 rounded border flex items-center justify-center transition-colors ${
                    agreed ? 'bg-blue-500 border-blue-500' : 'border-gray-500 group-hover:border-gray-400'
                  }`}
                >
                  {agreed && <Check className="w-4 h-4 text-white" />}
                </div>
                <input
                  type="checkbox"
                  className="hidden"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                />
                <span className="text-gray-200 text-sm">I agree to the terms and privacy policy</span>
              </label>

              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={!agreed}
                  onClick={handleNext}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {effectiveStep === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="p-8"
            >
              <div className="flex items-center gap-3 mb-4">
                <Cpu className="w-7 h-7 text-cyan-400" />
                <h2 className="text-2xl font-bold text-white">Choose Your AI Engine</h2>
              </div>
              <p className="text-gray-300 text-sm mb-5">
                Pick your default AI backend and optionally enter a cloud API key (you can change this anytime in Settings).
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
                {[
                  { id: 'gemini', title: 'Google Gemini', desc: 'Fast Cloud AI (Recommended)' },
                  { id: 'openai', title: 'OpenAI GPT', desc: 'GPT-4o / GPT-4o-mini' },
                  { id: 'gguf', title: 'Local GGUF', desc: '100% Offline Built-in Model' },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setProvider(item.id as ProviderChoice)}
                    className={`text-left p-3.5 rounded-lg border transition-all ${
                      provider === item.id
                        ? 'bg-blue-500/15 border-blue-500 text-white'
                        : 'bg-[#14151A] border-[#2A2D35] text-gray-300 hover:border-gray-500'
                    }`}
                  >
                    <div className="font-semibold text-sm">{item.title}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{item.desc}</div>
                  </button>
                ))}
              </div>

              {(provider === 'gemini' || provider === 'openai') && (
                <div className="bg-[#14151A] border border-[#2A2D35] rounded-lg p-4 mb-6">
                  <label className="flex items-center gap-2 text-xs font-medium text-gray-300 mb-2">
                    <KeyRound className="w-3.5 h-3.5 text-blue-400" />
                    {provider === 'gemini' ? 'Google Gemini API Key (Optional)' : 'OpenAI API Key (Optional)'}
                  </label>
                  <input
                    type="password"
                    value={provider === 'gemini' ? geminiKey : openAIKey}
                    onChange={(e) =>
                      provider === 'gemini' ? setGeminiKey(e.target.value) : setOpenAIKey(e.target.value)
                    }
                    placeholder={provider === 'gemini' ? 'AIzaSy...' : 'sk-...'}
                    className="w-full px-3 py-2 bg-[#1A1D24] border border-[#2A2D35] rounded-md text-sm text-white focus:border-blue-500 outline-none"
                  />
                  <p className="text-[11px] text-gray-500 mt-1.5">
                    Stored encrypted in Windows Credential Manager — never written in plain text.
                  </p>
                </div>
              )}

              <div className="flex justify-between">
                <button
                  type="button"
                  onClick={handleBack}
                  className="px-5 py-2.5 bg-[#2A2D35] hover:bg-[#343842] text-gray-200 rounded-lg font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleNext}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {effectiveStep === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="p-8 text-center"
            >
              <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-5">
                <Mic className="w-8 h-8 text-blue-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Microphone &amp; Voice Access</h2>
              <p className="text-gray-300 mb-8 max-w-md mx-auto text-sm">
                Pulsar supports hands-free voice commands and the &quot;Hey Pulsar&quot; wake word. Grant mic access now or skip to use text chat.
              </p>
              <div className="flex justify-center gap-4">
                <button
                  type="button"
                  disabled={requestingMic}
                  onClick={handleBack}
                  className="px-5 py-2.5 bg-[#2A2D35] hover:bg-[#343842] text-gray-200 rounded-lg font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={requestingMic}
                  onClick={() => {
                    setMicGranted(false);
                    handleNext();
                  }}
                  className="px-6 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                >
                  Skip for now
                </button>
                <button
                  type="button"
                  disabled={requestingMic}
                  onClick={requestMic}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  {requestingMic ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Grant Access
                </button>
              </div>
            </motion.div>
          )}

          {effectiveStep === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="p-8 text-center"
            >
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-5">
                <Wand2 className="w-8 h-8 text-green-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">You&apos;re All Set!</h2>
              <p className="text-gray-300 mb-6 max-w-md mx-auto text-sm">
                Choose your preferred appearance theme and start using Pulsar AI.
              </p>

              <div className="flex justify-center gap-3 mb-7">
                {(['dark', 'light'] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTheme(t)}
                    className={`px-5 py-2 rounded-lg border text-sm capitalize transition-colors ${
                      theme === t
                        ? 'bg-blue-500/20 border-blue-500 text-white'
                        : 'bg-[#14151A] border-[#2A2D35] text-gray-400'
                    }`}
                  >
                    {t} Mode
                  </button>
                ))}
              </div>

              <div className="flex justify-center gap-3">
                <button
                  type="button"
                  disabled={loading}
                  onClick={handleBack}
                  className="px-5 py-2.5 bg-[#2A2D35] hover:bg-[#343842] text-gray-200 rounded-lg font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleFinish}
                  disabled={loading}
                  className="px-8 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg font-bold flex items-center gap-2 transition-colors"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {loading ? 'Saving...' : 'Start Using Pulsar'} <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
