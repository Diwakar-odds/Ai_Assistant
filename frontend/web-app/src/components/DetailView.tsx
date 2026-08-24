import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { ReactNode } from 'react';

import ErrorBoundary from './ErrorBoundary';

interface DetailViewProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

const DetailView = ({ isOpen, onClose, title, children }: DetailViewProps) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          
          {/* Detail Card */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="bg-[#16181D] border border-[#1F2228] rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-[#1F2228]">
                <h2 className="text-xl font-semibold text-white">{title}</h2>
                <motion.button
                  onClick={onClose}
                  className="p-2 hover:bg-[#1F2228] rounded-lg transition-colors"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <X className="w-5 h-5 text-[#9CA3AF] hover:text-white" />
                </motion.button>
              </div>
              
              {/* Content */}
              <div className="overflow-y-auto max-h-[calc(90vh-80px)] p-6">
                <ErrorBoundary fallbackTitle={`Error displaying ${title}`}>
                  {children}
                </ErrorBoundary>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default DetailView;
