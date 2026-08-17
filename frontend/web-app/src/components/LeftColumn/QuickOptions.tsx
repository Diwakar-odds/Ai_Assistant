import { motion } from 'framer-motion';
import { Grid3x3, BarChart3, Settings, MoreHorizontal } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

const QuickOptions = () => {
  const { setSelectedView } = useDashboard();

  const options = [
    {
      icon: Grid3x3,
      label: 'Apps',
      onClick: () => {
        setSelectedView('apps');
      }
    },
    {
      icon: BarChart3,
      label: 'AI Learning',
      onClick: () => {
        setSelectedView('ai-learning');
      }
    },
    {
      icon: Settings,
      label: 'Settings',
      onClick: () => {
        setSelectedView('settings');
      }
    },
    {
      icon: MoreHorizontal,
      label: 'Integrations',
      onClick: () => {
        setSelectedView('integrations');
      }
    },
  ];

  return (
    <motion.div
      className="space-y-2 flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <h3 className="text-xs sm:text-sm font-medium text-white px-1">Quick Options</h3>
      <div className="grid grid-cols-2 gap-2 sm:gap-2.5">
        {options.map((option, index) => (
          <motion.button
            key={option.label}
            onClick={option.onClick}
            className="glass-panel rounded-lg p-2.5 sm:p-3.5 flex flex-col items-center justify-center gap-2 sm:gap-2.5 hover:border-neon-cyan hover:shadow-[0_0_12px_rgba(0,243,255,0.3)] transition-all duration-200 cursor-pointer group"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 * index }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <option.icon
              className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 text-neon-cyan group-hover:scale-110 transition-transform"
              strokeWidth={1.5}
            />
            <span className="text-[10px] sm:text-xs text-[#9CA3AF] group-hover:text-white transition-colors font-medium">
              {option.label}
            </span>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
};

export default QuickOptions;
