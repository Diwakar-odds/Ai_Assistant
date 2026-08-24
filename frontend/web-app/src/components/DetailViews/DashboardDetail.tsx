import { motion } from 'framer-motion';
import { Cpu, HardDrive, Activity, TrendingUp, Zap, Server } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';
import SystemLogs from '../RightColumn/SystemLogs';

const DashboardDetail = () => {
  const { systemStats } = useDashboard();

  const detailedStats = [
    { icon: Cpu, label: 'CPU Usage', value: `${systemStats.cpu}%`, color: '#3B82F6', trend: systemStats.cpu > 80 ? '+High' : 'Stable' },
    { icon: HardDrive, label: 'Memory Usage', value: `${systemStats.memory}%`, color: '#10B981', trend: 'Stable' },
    { icon: Activity, label: 'Network Speed', value: systemStats.network, color: '#F59E0B', trend: 'Live' },
    { icon: Server, label: 'Disk Usage', value: `${systemStats.disk || 0}%`, color: '#8B5CF6', trend: 'Stable' },
    { icon: Zap, label: 'Power Consumption', value: '--', color: '#EF4444', trend: 'N/A' },
    { icon: TrendingUp, label: 'Performance Score', value: `${Math.max(0, 100 - Math.max(systemStats.cpu, systemStats.memory))}/100`, color: '#06B6D4', trend: 'Dynamic' },
  ];

  return (
    <div className="space-y-6 flex flex-col h-full overflow-hidden pb-4">
      <div className="flex-shrink-0">
        <h3 className="text-2xl font-bold text-white mb-2">System Dashboard</h3>
        <p className="text-[#9CA3AF]">Comprehensive overview of system performance and metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 flex-shrink-0">
        {detailedStats.map((stat, index) => (
          <motion.div
            key={stat.label}
            className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.03, borderColor: stat.color }}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-3 rounded-lg" style={{ backgroundColor: `${stat.color}15` }}>
                <stat.icon className="w-6 h-6" style={{ color: stat.color }} strokeWidth={1.5} />
              </div>
              <span className={`text-sm font-semibold ${stat.trend.startsWith('+') ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
                {stat.trend}
              </span>
            </div>
            <h4 className="text-sm text-[#9CA3AF] mb-2">{stat.label}</h4>
            <p className="text-3xl font-bold text-white">{stat.value}</p>

            {/* Mini chart visualization */}
            <div className="mt-4 h-12 flex items-end gap-1">
              {[...Array(12)].map((_, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t transition-all"
                  style={{
                    backgroundColor: stat.color,
                    height: `${Math.random() * 100}%`,
                    opacity: 0.6
                  }}
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Additional system information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-shrink-0">
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
          <h4 className="text-lg font-semibold text-white mb-4">System Information</h4>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-[#9CA3AF]">Operating System</span>
              <span className="text-white font-medium">Windows 11 Pro</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#9CA3AF]">Uptime</span>
              <span className="text-white font-medium">3d 14h 23m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#9CA3AF]">Processes</span>
              <span className="text-white font-medium">247 running</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#9CA3AF]">Threads</span>
              <span className="text-white font-medium">3,842 active</span>
            </div>
          </div>
        </div>

        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6 flex flex-col h-full overflow-hidden">
          <SystemLogs />
        </div>
      </div>
    </div>
  );
};

export default DashboardDetail;
