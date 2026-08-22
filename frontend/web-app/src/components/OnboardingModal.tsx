import React, { useState, _useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ArrowRight, Shield, Mic, Wand2 } from 'lucide-react';
import { _apiService } from '../lib/api';

export default function OnboardingModal({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(1);
  const [agreed, setAgreed] = useState(false);
  const [_micGranted, setMicGranted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleNext = () => setStep(s => s + 1);

  const handleFinish = async () => {
    setLoading(true);
    try {
      await fetch('/api/settings/complete_onboarding', {
        method: 'POST',
      });
      onComplete();
    } catch (_e) {
      console.error('Failed to complete onboarding', e);
      onComplete(); // Still complete even if it fails so they don't get stuck
    }
  };

  const requestMic = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicGranted(true);
      handleNext();
    } catch (_err) {
      alert("Microphone access is required for voice commands.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="bg-[#1A1D24] border border-[#2A2D35] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden"
      >
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div key="step1" exit={{ opacity: 0, x: -20 }} className="p-8">
              <div className="flex items-center gap-3 mb-6">
                <Shield className="w-8 h-8 text-blue-500" />
                <h2 className="text-2xl font-bold text-white">Welcome to YourDaddy AI</h2>
              </div>
              <p className="text-gray-300 mb-6">
                Before we begin, please review our data and privacy policy. 
                Your assistant learns from your interactions and builds a local Knowledge Graph 
                to personalize your experience. All data is stored locally on your machine.
              </p>
              
              <div className="bg-[#14151A] p-4 rounded-lg mb-6 max-h-40 overflow-y-auto text-sm text-gray-400 font-mono">
                END USER LICENSE AGREEMENT & PRIVACY POLICY...
                <br/><br/>
                1. Data Storage: Your data remains on your local disk.
                <br/>
                2. Continuous Learning: The AI will store facts about you.
                <br/>
                3. Third-party APIs: Voice/text may be routed to OpenAI or Google if configured.
              </div>

              <label className="flex items-center gap-3 cursor-pointer group mb-8">
                <div className={`w-6 h-6 rounded border flex items-center justify-center transition-colors ${agreed ? 'bg-blue-500 border-blue-500' : 'border-gray-500 group-hover:border-gray-400'}`}>
                  {agreed && <Check className="w-4 h-4 text-white" />}
                </div>
                <input type="checkbox" className="hidden" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
                <span className="text-gray-200">I agree to the terms and privacy policy</span>
              </label>

              <div className="flex justify-end">
                <button 
                  disabled={!agreed}
                  onClick={handleNext}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="p-8 text-center">
              <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Mic className="w-8 h-8 text-blue-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">Microphone Access</h2>
              <p className="text-gray-300 mb-8 max-w-md mx-auto">
                Your assistant is voice-first. Please grant microphone access so you can issue hands-free commands.
              </p>
              <div className="flex justify-center gap-4">
                <button onClick={handleNext} className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors">
                  Skip for now
                </button>
                <button onClick={requestMic} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
                  Grant Access
                </button>
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="p-8 text-center">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Wand2 className="w-8 h-8 text-green-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">You're All Set!</h2>
              <p className="text-gray-300 mb-8 max-w-md mx-auto">
                We'll now give you a quick tour of the interface so you know how to use your new AI Assistant.
              </p>
              <button 
                onClick={handleFinish} 
                disabled={loading}
                className="px-8 py-3 bg-green-600 hover:bg-green-500 text-white rounded-lg font-bold flex items-center gap-2 mx-auto transition-colors"
              >
                {loading ? 'Starting...' : 'Start Tour'} <ArrowRight className="w-5 h-5" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
