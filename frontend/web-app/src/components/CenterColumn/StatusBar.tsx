import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, Bell, Battery, Mic, Terminal, PanelLeft, PanelRight } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';

const StatusBar = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [batteryLevel, setBatteryLevel] = useState<number>(0);
  const [isCharging, setIsCharging] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const { isVoiceActive, isConnected, setSelectedView, isLeftSidebarOpen, isRightSidebarOpen, toggleLeftSidebar, toggleRightSidebar, systemLogs } = useDashboard();

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Get battery status
  useEffect(() => {
    const getBatteryStatus = async () => {
      if ('getBattery' in navigator) {
        try {
           
          const battery: any = await (navigator as any).getBattery();

          const updateBattery = () => {
            setBatteryLevel(Math.round(battery.level * 100));
            setIsCharging(battery.charging);
          };

          updateBattery();

          battery.addEventListener('levelchange', updateBattery);
          battery.addEventListener('chargingchange', updateBattery);

          return () => {
            battery.removeEventListener('levelchange', updateBattery);
            battery.removeEventListener('chargingchange', updateBattery);
          };
        } catch (error) {
          console.log('Battery API not available:', error);
          // Fallback to a reasonable default
          setBatteryLevel(100);
        }
      } else {
        // Battery API not supported
        setBatteryLevel(100);
      }
    };

    getBatteryStatus();
  }, []);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const getBatteryIcon = () => {
    if (isCharging) return '🔌';
    if (batteryLevel > 80) return '🔋';
    if (batteryLevel > 20) return '🔋';
    return '🪫';
  };

  const getBatteryColor = () => {
    if (isCharging) return 'text-[#3B82F6]';
    if (batteryLevel > 20) return 'text-[#10B981]';
    return 'text-[#EF4444]';
  };

  return (
    <motion.div
      className="w-full bg-[#1a1f2e]/40 backdrop-blur-md rounded-lg border border-white/5 px-4 sm:px-6 py-3 flex items-center justify-between shadow-sm"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      {/* Left Group */}
      <div className="flex items-center gap-4 sm:gap-6 flex-1">
        {/* Left Sidebar Toggle */}
        <motion.div
          className="relative cursor-pointer"
          whileHover={{ scale: 1.1 }}
          onClick={toggleLeftSidebar}
          title={isLeftSidebarOpen ? "Hide Left Sidebar" : "Show Left Sidebar"}
        >
          <PanelLeft className={`w-5 h-5 transition-colors ${isLeftSidebarOpen ? 'text-[#00f3ff]' : 'text-[#9CA3AF] hover:text-white'}`} strokeWidth={1.5} />
        </motion.div>

        {/* Terminal/Logs */}
        <motion.div
          className="relative cursor-pointer hidden sm:block"
          whileHover={{ scale: 1.1 }}
          onClick={() => setSelectedView('dashboard')}
          title="System Logs & Dashboard"
        >
          <Terminal className="w-5 h-5 text-[#9CA3AF] hover:text-[#00f3ff] transition-colors" strokeWidth={1.5} />
        </motion.div>
      </div>

      {/* Center Group - Clock */}
      <div className="flex items-center justify-center">
        <span className="text-lg sm:text-xl font-mono text-white tracking-widest font-light drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]">
          {formatTime(currentTime)}
        </span>
      </div>

      {/* Right Group */}
      <motion.div
        className="flex items-center gap-5 sm:gap-7 flex-1 justify-end"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        {/* Bell Notification */}
        <div className="relative">
          <motion.div
            className="cursor-pointer"
            whileHover={{ scale: 1.1 }}
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <Bell className={`w-5 h-5 transition-colors ${showNotifications ? 'text-white' : 'text-[#9CA3AF] hover:text-white'}`} strokeWidth={1.5} />
            {/* Show dot only if there are logs (or unread logic later) */}
            {systemLogs.length > 0 && (
              <span className="absolute 1 top-0 right-0 w-2 h-2 bg-[#EF4444] rounded-full border-2 border-[#1a1f2e]" />
            )}
          </motion.div>

          {/* Dropdown Menu */}
          <AnimatePresence>
            {showNotifications && (
              <>
                {/* Backdrop to close when clicking outside */}
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowNotifications(false)}
                />
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="absolute right-0 top-10 w-72 bg-[#1a1f2e]/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-[0_10px_30px_rgba(0,0,0,0.5)] z-50 overflow-hidden"
                >
                  <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-black/20">
                    <span className="text-xs font-bold tracking-widest text-[#9CA3AF] uppercase">Recent Activity</span>
                    <span className="text-[10px] text-white/40">{systemLogs.length} logs</span>
                  </div>
                  <div className="max-h-64 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-white/10">
                    {systemLogs.length > 0 ? (
                      systemLogs.slice(0, 5).map((log) => {
                        const colors = {
                          info: 'text-[#00f3ff] bg-[#00f3ff]/10',
                          success: 'text-[#10B981] bg-[#10B981]/10',
                          warning: 'text-[#F59E0B] bg-[#F59E0B]/10',
                          error: 'text-[#EF4444] bg-[#EF4444]/10'
                        };
                        return (
                          <div key={log.id} className="flex gap-3 items-start p-2.5 rounded-lg hover:bg-white/5 transition-colors">
                            <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${colors[log.type] ? colors[log.type].split(' ')[0].replace('text', 'bg') : 'bg-gray-400'}`} />
                            <div className="flex flex-col gap-0.5">
                              <span className="text-xs text-white/90 leading-snug">{log.message}</span>
                              <span className="text-[9px] text-white/40 font-mono">{log.time}</span>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="p-4 text-center text-xs text-white/40">No recent activity</div>
                    )}
                  </div>
                  <div 
                    className="p-2 border-t border-white/5 text-center bg-black/20 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => {
                      setSelectedView('dashboard');
                      setShowNotifications(false);
                    }}
                  >
                    <span className="text-[10px] text-[#00f3ff] uppercase tracking-widest font-semibold">View All Logs</span>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>

        {/* Connection Status */}
        <div className="flex items-center" title={isConnected ? 'Backend Connected' : 'Backend Disconnected'}>
          <div className="relative flex items-center justify-center">
            <Wifi className={`w-5 h-5 ${isConnected ? 'text-[#10B981]' : 'text-[#EF4444]'} transition-colors`} strokeWidth={1.5} />
            {isConnected ? (
              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[#10B981] rounded-full shadow-[0_0_8px_rgba(16,185,129,1)] animate-pulse" />
            ) : (
              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[#EF4444] rounded-full shadow-[0_0_8px_rgba(239,68,68,1)] animate-ping" />
            )}
          </div>
        </div>

        {/* Minimal Battery */}
        <div className="flex items-center gap-2" title={`Battery: ${batteryLevel}% ${isCharging ? '(Charging)' : ''}`}>
          <div className="relative w-7 h-3.5 rounded-sm border border-[#9CA3AF] flex items-center p-[1px]">
            {/* Battery fill */}
            <motion.div 
              className={`h-full rounded-sm ${isCharging ? 'bg-[#3B82F6]' : batteryLevel > 20 ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`}
              initial={{ width: 0 }}
              animate={{ width: `${batteryLevel}%` }}
              transition={{ duration: 1 }}
            />
            {/* Battery tip */}
            <div className="absolute -right-[3px] top-1/2 -translate-y-1/2 w-[2px] h-1.5 bg-[#9CA3AF] rounded-r-sm" />
          </div>
        </div>

        {/* Right Sidebar Toggle */}
        <motion.div
          className="relative cursor-pointer hidden md:block ml-2"
          whileHover={{ scale: 1.1 }}
          onClick={toggleRightSidebar}
          title={isRightSidebarOpen ? "Hide Conversation History" : "Show Conversation History"}
        >
          <PanelRight className={`w-5 h-5 transition-colors ${isRightSidebarOpen ? 'text-[#00f3ff]' : 'text-[#9CA3AF] hover:text-white'}`} strokeWidth={1.5} />
        </motion.div>
      </motion.div>
    </motion.div>
  );
};

export default StatusBar;
