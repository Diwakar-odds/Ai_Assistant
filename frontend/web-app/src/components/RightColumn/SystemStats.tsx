import { motion } from 'framer-motion';
import { Activity, Cpu, HardDrive } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';

const SystemStats = () => {
  const { systemStats, setSelectedView } = useDashboard();

  const stats = [
    { icon: Cpu, label: 'CPU Usage', value: `${systemStats.cpu}%`, color: '#3B82F6' },
    { icon: HardDrive, label: 'Memory', value: `${systemStats.memory}%`, color: '#3B82F6' },
    { icon: Activity, label: 'Network', value: systemStats.network, color: '#3B82F6' },
  ];

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg p-2 sm:p-3 cursor-pointer hover:border-[#3B82F6]/50 transition-all flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      whileHover={{ scale: 1.02 }}
      onClick={() => setSelectedView('dashboard')}
    >
      <h3 className="text-xs sm:text-sm font-medium text-white mb-2">System Stats</h3>
      <div className="grid grid-cols-3 gap-2">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            className="bg-[#1F2228] rounded-lg p-1.5 sm:p-2 text-center"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 * index }}
            whileHover={{ scale: 1.05 }}
          >
            <stat.icon className="w-3 h-3 sm:w-4 sm:h-4 md:w-5 md:h-5 mx-auto mb-1 sm:mb-2" style={{ color: stat.color }} strokeWidth={1.5} />
            <p className="text-[8px] sm:text-[10px] text-[#9CA3AF] mb-0.5 sm:mb-1">{stat.label}</p>
            <p className="text-sm sm:text-base md:text-lg font-bold text-white">{stat.value}</p>
            <div className="mt-1 sm:mt-2 h-6 sm:h-8 relative">
              <div className="absolute bottom-0 left-0 right-0 h-full flex items-end justify-center gap-0.5">
                {[...Array(10)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-1 bg-[#3B82F6] rounded-t"
                    initial={{ height: 0 }}
                    animate={{
                      height: `${Math.random() * 100}%`,
                    }}
                    transition={{
                      duration: 0.5,
                      delay: i * 0.05,
                      repeat: Infinity,
                      repeatType: 'reverse',
                      repeatDelay: Math.random() * 2,
                    }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default SystemStats;
