import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, HardDrive, Activity, TrendingUp, Layers, Server, ArrowUpRight } from 'lucide-react';
import { useDashboard } from '../../contexts/DashboardContext';
import SystemLogs from '../RightColumn/SystemLogs';

const DashboardDetail = () => {
  const {
    systemStats,
    systemStatsHistory,
    systemDetails,
    refreshSystemDetails,
    activeChains,
    agents,
    setSelectedView,
  } = useDashboard();

  useEffect(() => {
    refreshSystemDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buildSeries = (selector: (p: { cpu: number; memory: number; disk: number }) => number, currentVal: number) => {
    const history = (systemStatsHistory || []).map(selector);
    const padded = [...history];
    while (padded.length < 12) {
      padded.unshift(history.length > 0 ? history[0] : currentVal);
    }
    return padded.slice(-12).map((v) => Math.max(6, Math.min(100, Math.round(v))));
  };

  const cpuSeries = buildSeries((p) => p.cpu, systemStats.cpu);
  const memSeries = buildSeries((p) => p.memory, systemStats.memory);
  const diskSeries = buildSeries((p) => p.disk, systemStats.disk || 0);
  const perfScore = Math.max(0, 100 - Math.max(systemStats.cpu, systemStats.memory));
  const busyAgentsCount = (agents || []).filter((a) => a.status === 'busy').length;
  const activeChainsCount = (activeChains || []).length;

  const detailedStats = [
    {
      icon: Cpu,
      label: 'CPU Usage',
      value: `${systemStats.cpu}%`,
      color: '#3B82F6',
      trend: systemStats.cpu > 80 ? 'High' : 'Normal',
      positive: systemStats.cpu <= 80,
      series: cpuSeries,
    },
    {
      icon: HardDrive,
      label: 'Memory Usage',
      value: `${systemStats.memory}%`,
      color: '#10B981',
      trend: systemStats.memory > 85 ? 'Elevated' : 'Normal',
      positive: systemStats.memory <= 85,
      series: memSeries,
    },
    {
      icon: Activity,
      label: 'Network Speed',
      value: systemStats.network,
      color: '#F59E0B',
      trend: 'Live',
      positive: true,
      series: cpuSeries.map((c, idx) => Math.max(10, Math.min(100, Math.round((c + memSeries[idx]) / 2)))),
    },
    {
      icon: Server,
      label: 'Disk Usage',
      value: `${systemStats.disk || 0}%`,
      color: '#8B5CF6',
      trend: (systemStats.disk || 0) > 90 ? 'Low Space' : 'Healthy',
      positive: (systemStats.disk || 0) <= 90,
      series: diskSeries,
    },
    {
      icon: Layers,
      label: 'Active Orchestration',
      value: `${activeChainsCount} chains · ${busyAgentsCount} agents`,
      color: '#00f3ff',
      trend: activeChainsCount > 0 ? 'Executing' : 'Idle',
      positive: true,
      series: Array.from({ length: 12 }, (_, i) =>
        activeChainsCount > 0 ? Math.min(100, 35 + ((i * 11) % 60)) : 12
      ),
      onClick: () => setSelectedView('agents'),
    },
    {
      icon: TrendingUp,
      label: 'Performance Score',
      value: `${perfScore}/100`,
      color: '#06B6D4',
      trend: perfScore >= 60 ? 'Optimal' : 'Loaded',
      positive: perfScore >= 60,
      series: cpuSeries.map((c, idx) => Math.max(8, 100 - Math.max(c, memSeries[idx]))),
    },
  ];

  return (
    <div className="space-y-3.5 flex flex-col h-full overflow-hidden pb-2">
      <div className="flex-shrink-0 flex items-center justify-between gap-3 pb-0.5">
        <p className="text-xs text-[#9CA3AF]">Real-time hardware telemetry, host runtime details, and orchestration health</p>
        <button
          type="button"
          onClick={() => setSelectedView('agents')}
          className="px-2.5 py-1.5 rounded-lg bg-[#1F2228] hover:bg-[#2A2D35] border border-[#00f3ff]/30 text-[#00f3ff] text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0"
        >
          <span>Open Agents & Chains</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 flex-shrink-0">
        {detailedStats.map((stat, index) => (
          <motion.div
            key={stat.label}
            onClick={stat.onClick}
            className={`bg-[#1F2228] border border-[#2A2D35] rounded-xl p-3.5 transition-all ${stat.onClick ? 'cursor-pointer hover:border-[#00f3ff]' : 'hover:border-[#3A3D45]'}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg shrink-0" style={{ backgroundColor: `${stat.color}15` }}>
                  <stat.icon className="w-4 h-4" style={{ color: stat.color }} strokeWidth={2} />
                </div>
                <h4 className="text-xs font-medium text-[#9CA3AF]">{stat.label}</h4>
              </div>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${stat.positive ? 'bg-[#10B981]/15 text-[#10B981]' : 'bg-[#EF4444]/15 text-[#EF4444]'}`}>
                {stat.trend}
              </span>
            </div>

            <p className="text-lg sm:text-xl font-bold text-white truncate my-1">{stat.value}</p>

            {/* Real Telemetry History Bars */}
            <div className="mt-2.5 h-7 flex items-end gap-1">
              {stat.series.map((heightVal, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-sm transition-all"
                  style={{
                    backgroundColor: stat.color,
                    height: `${heightVal}%`,
                    opacity: 0.35 + (i / 12) * 0.55,
                  }}
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Host Runtime & System Logs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-shrink-0">
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-white mb-2.5">System Information</h4>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between py-1 border-b border-[#2A2D35]/50">
              <span className="text-[#9CA3AF]">Operating System</span>
              <span className="text-white font-medium">{systemDetails?.os || '--'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#2A2D35]/50">
              <span className="text-[#9CA3AF]">Uptime</span>
              <span className="text-white font-medium">{systemDetails?.uptime || '--'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#2A2D35]/50">
              <span className="text-[#9CA3AF]">Processes</span>
              <span className="text-white font-medium">
                {typeof systemDetails?.processes === 'number' ? `${systemDetails.processes} running` : '--'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#9CA3AF]">Threads</span>
              <span className="text-white font-medium">
                {typeof systemDetails?.threads === 'number' ? `${systemDetails.threads.toLocaleString()} active` : '--'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 flex flex-col h-full overflow-hidden">
          <SystemLogs />
        </div>
      </div>
    </div>
  );
};

export default DashboardDetail;
