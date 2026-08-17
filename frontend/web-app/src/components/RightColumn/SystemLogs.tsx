import { motion } from 'framer-motion';
import { Terminal } from 'lucide-react';
import { useRef, useEffect } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';

const SystemLogs = () => {
  const logsScrollRef = useRef<HTMLDivElement>(null);
  const { systemLogs } = useDashboard();

  useEffect(() => {
    if (logsScrollRef.current) {
      logsScrollRef.current.scrollTop = logsScrollRef.current.scrollHeight;
    }
  }, [systemLogs]);

  const getLogColor = (type: string) => {
    switch (type) {
      case 'info':
        return 'text-[#3B82F6]';
      case 'success':
        return 'text-[#10B981]';
      case 'warning':
        return 'text-[#F59E0B]';
      case 'error':
        return 'text-[#EF4444]';
      default:
        return 'text-[#9CA3AF]';
    }
  };

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg overflow-hidden flex flex-col flex-1"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <div className="p-3 border-b border-[#1F2228] flex items-center gap-2">
        <Terminal className="w-4 h-4 text-[#3B82F6]" />
        <h3 className="text-sm font-medium text-white">System Logs</h3>
      </div>

      <div
        ref={logsScrollRef}
        className="p-3 space-y-1.5 flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-[#3B82F6] scrollbar-track-[#1F2228] font-mono text-xs"
      >
        {systemLogs.length === 0 ? (
          <p className="text-[#6B7280] text-center py-4">No logs yet</p>
        ) : (
          systemLogs.map((log, index) => (
            <motion.div
              key={log.id}
              className="flex items-start gap-2"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.02 }}
            >
              <span className="text-[#6B7280] shrink-0">[{log.time}]</span>
              <span className={`${getLogColor(log.type)} font-semibold shrink-0 uppercase text-[10px]`}>
                [{log.type}]
              </span>
              <span className="text-[#9CA3AF]">{log.message}</span>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
};

export default SystemLogs;
