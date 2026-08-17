import { motion } from 'framer-motion';
import { Send } from 'lucide-react';
import { useState } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';

const CommandInput = () => {
  const [command, setCommand] = useState('');
  const { sendCommand } = useDashboard();

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!command.trim()) return;

    sendCommand(command);
    setCommand('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <motion.div
      className="flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <div className="glass-panel rounded-lg p-1 sm:p-1 flex items-center gap-2 sm:gap-2 focus-within:border-neon-cyan/50 transition-colors">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a command or ask anything..."
          className="flex-1 bg-transparent text-white placeholder-gray-400 px-3 sm:px-3 py-2 sm:py-2 text-sm sm:text-sm focus:outline-none"
        />
        <motion.button
          onClick={() => handleSubmit()}
          disabled={!command.trim()}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="bg-[#3B82F6] text-white px-4 sm:px-4 py-2 sm:py-2 rounded-md flex items-center gap-1.5 font-medium text-sm sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all touch-manipulation"
        >
          <Send className="w-4 h-4 sm:w-4 sm:h-4" />
          <span className="hidden xs:inline">Send</span>
        </motion.button>
      </div>
    </motion.div>
  );
};

export default CommandInput;
