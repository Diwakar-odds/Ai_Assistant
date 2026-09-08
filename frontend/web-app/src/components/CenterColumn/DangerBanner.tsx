import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Check, X } from 'lucide-react';

interface DangerBannerProps {
  /** The pending action that requires authorization */
  pendingAction: { id: string; description: string } | null;
  /** Callback when user authorizes */
  onAuthorize: () => void;
  /** Callback when user cancels */
  onCancel: () => void;
}

const DangerBanner = ({ pendingAction, onAuthorize, onCancel }: DangerBannerProps) => {
  return (
    <AnimatePresence>
      {pendingAction && (
        <motion.div
          initial={{ opacity: 0, y: -20, scaleY: 0 }}
          animate={{ opacity: 1, y: 0, scaleY: 1 }}
          exit={{ opacity: 0, y: -20, scaleY: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="w-full max-w-2xl mx-auto mb-2"
          style={{ transformOrigin: 'top' }}
        >
          <div className="relative overflow-hidden rounded-lg border border-orange-500/50 bg-gradient-to-r from-orange-950/80 via-red-950/60 to-orange-950/80 backdrop-blur-md px-4 py-3">
            {/* Animated border glow */}
            <motion.div
              className="absolute inset-0 rounded-lg"
              style={{
                boxShadow: '0 0 20px rgba(249, 115, 22, 0.3), inset 0 0 20px rgba(249, 115, 22, 0.05)',
              }}
              animate={{
                boxShadow: [
                  '0 0 15px rgba(249, 115, 22, 0.2), inset 0 0 15px rgba(249, 115, 22, 0.03)',
                  '0 0 25px rgba(249, 115, 22, 0.4), inset 0 0 25px rgba(249, 115, 22, 0.08)',
                  '0 0 15px rgba(249, 115, 22, 0.2), inset 0 0 15px rgba(249, 115, 22, 0.03)',
                ],
              }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            />

            <div className="relative flex items-center gap-3">
              {/* Icon */}
              <motion.div
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
              >
                <ShieldAlert className="w-5 h-5 text-orange-400 flex-shrink-0" />
              </motion.div>

              {/* Text */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-orange-300/70 font-medium uppercase tracking-wider">
                  High Risk Action Paused
                </p>
                <p className="text-sm text-orange-100 font-medium truncate">
                  {pendingAction.description}
                </p>
              </div>

              {/* Buttons */}
              <div className="flex gap-2 flex-shrink-0">
                <motion.button
                  onClick={onAuthorize}
                  className="px-3 py-1.5 rounded-md bg-orange-500/20 border border-orange-400/50 text-orange-200 text-xs font-bold uppercase tracking-wider hover:bg-orange-500/40 transition-colors flex items-center gap-1.5"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Check className="w-3.5 h-3.5" />
                  Authorize
                </motion.button>
                <motion.button
                  onClick={onCancel}
                  className="px-3 py-1.5 rounded-md bg-slate-700/50 border border-slate-500/30 text-slate-300 text-xs font-bold uppercase tracking-wider hover:bg-slate-600/50 transition-colors flex items-center gap-1.5"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <X className="w-3.5 h-3.5" />
                  Cancel
                </motion.button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default DangerBanner;
