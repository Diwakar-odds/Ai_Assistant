import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDashboard } from '../../contexts/DashboardContext';
import { Sparkles, Calendar, Activity, Info, AlertTriangle, Target, ClipboardList, Cpu } from 'lucide-react';

const BriefingCard = () => {
    const { hudData, systemStats, systemLogs } = useDashboard();
    const [currentCardIndex, setCurrentCardIndex] = useState(0);

    const getTimeGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning, Sir.';
        if (hour < 17) return 'Good afternoon, Sir.';
        return 'Good evening, Sir.';
    };

    // Build the dynamic cards list
    const getCards = () => {
        const cards = [];

        // 1. Greeting & Basic Status
        cards.push({
            id: 'greeting',
            icon: <Sparkles className="w-5 h-5 text-cyan-400" />,
            title: 'System Briefing',
            content: (
                <div className="flex flex-col gap-1">
                    <p className="text-sm font-medium text-white">{getTimeGreeting()}</p>
                    <p className="text-xs text-white/60">All core systems are operational and standing by.</p>
                </div>
            )
        });

        // 1.5 Pending Commitment/Task
        if (hudData.pendingTask) {
            cards.push({
                id: 'pending_task',
                icon: <ClipboardList className="w-5 h-5 text-purple-400" />,
                title: 'Pending Commitment',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-purple-200 line-clamp-2 leading-snug">{hudData.pendingTask}</p>
                        <p className="text-[10px] text-purple-400/80 uppercase tracking-wider mt-0.5">Awaiting completion</p>
                    </div>
                )
            });
        }

        // 1.8 AI Engine Status
        if (hudData.activeModel) {
            cards.push({
                id: 'ai_engine',
                icon: <Cpu className="w-5 h-5 text-indigo-400" />,
                title: 'AI Engine',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-indigo-200 truncate">{hudData.activeModel}</p>
                        <p className="text-[10px] text-indigo-400/80 uppercase tracking-wider mt-0.5">Primary Processing Core</p>
                    </div>
                )
            });
        }

        // 2. Project Status (if active)
        if (hudData.projectName) {
            cards.push({
                id: 'project',
                icon: <Target className="w-5 h-5 text-green-400" />,
                title: 'Active Project',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-white truncate">{hudData.projectName}</p>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <motion.div 
                                    className="h-full bg-green-500" 
                                    initial={{ width: 0 }}
                                    animate={{ width: `${hudData.projectProgress}%` }}
                                    transition={{ duration: 1 }}
                                />
                            </div>
                            <span className="text-xs text-green-400 font-mono">{Math.round(hudData.projectProgress)}%</span>
                        </div>
                    </div>
                )
            });
        }

        // 3. System Health Warning (if low)
        if (hudData.systemHealth < 50) {
            cards.push({
                id: 'health',
                icon: <AlertTriangle className="w-5 h-5 text-orange-400" />,
                title: 'System Alert',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-orange-200">High Resource Usage</p>
                        <p className="text-xs text-orange-400/80">CPU: {systemStats.cpu}% | RAM: {systemStats.memory}%</p>
                    </div>
                )
            });
        } else {
             // Normal System Status
             cards.push({
                id: 'health_ok',
                icon: <Activity className="w-5 h-5 text-blue-400" />,
                title: 'System Health',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-medium text-blue-200">Optimal Performance</p>
                        <p className="text-xs text-blue-400/80">CPU: {systemStats.cpu}% | Mem: {systemStats.memory}% | Net: {systemStats.network}</p>
                    </div>
                )
            });
        }

        // 4. Latest Log (if recent)
        const recentLog = systemLogs.length > 0 ? systemLogs[0] : null;
        if (recentLog) {
            const logColor = 
                recentLog.type === 'error' ? 'text-red-400' : 
                recentLog.type === 'warning' ? 'text-orange-400' :
                recentLog.type === 'success' ? 'text-green-400' : 'text-cyan-400';
            
            cards.push({
                id: 'latest_log',
                icon: <Info className={`w-5 h-5 ${logColor}`} />,
                title: 'Recent Activity',
                content: (
                    <div className="flex flex-col gap-1">
                        <p className="text-xs text-white/50">{recentLog.time}</p>
                        <p className={`text-xs ${logColor} line-clamp-2`}>{recentLog.message}</p>
                    </div>
                )
            });
        }

        return cards;
    };

    const cards = getCards();

    // Rotate cards every 8 seconds
    useEffect(() => {
        if (cards.length <= 1) return;
        const interval = setInterval(() => {
            setCurrentCardIndex((prev) => (prev + 1) % cards.length);
        }, 8000);
        return () => clearInterval(interval);
    }, [cards.length]);

    // Ensure index doesn't go out of bounds if cards array shrinks
    const activeIndex = currentCardIndex >= cards.length ? 0 : currentCardIndex;
    const activeCard = cards[activeIndex];

    return (
        <div className="bg-[#1a1f2e] border border-[#00f3ff]/20 rounded-xl overflow-hidden flex flex-col flex-1 min-h-[140px] relative w-full transition-all duration-300 hover:border-[#00f3ff]/40 shadow-[0_0_15px_rgba(0,0,0,0.5)]">
            {/* Header / Title */}
            <div className="px-3 py-2 border-b border-[#00f3ff]/10 flex items-center justify-between bg-black/20 z-10">
                <span className="text-xs font-semibold text-[#00f3ff] uppercase tracking-widest flex items-center gap-1.5">
                   <Calendar className="w-3.5 h-3.5" />
                   Briefing
                </span>
                {/* Pagination Dots */}
                <div className="flex gap-1.5 items-center">
                    {cards.map((_, idx) => (
                        <div 
                            key={idx} 
                            className={`rounded-full transition-all duration-500 ease-out ${idx === activeIndex ? 'w-4 h-1.5 bg-[#00f3ff] shadow-[0_0_8px_#00f3ff]' : 'w-1.5 h-1.5 bg-[#00f3ff]/30'}`} 
                        />
                    ))}
                </div>
            </div>

            {/* Card Content Area with AnimatePresence */}
            <div className="flex-1 relative overflow-hidden">
                <AnimatePresence mode="wait">
                    {activeCard && (
                        <motion.div
                            key={activeCard.id}
                            initial={{ opacity: 0, x: 20, filter: 'blur(4px)' }}
                            animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                            exit={{ opacity: 0, x: -20, filter: 'blur(4px)' }}
                            transition={{ duration: 0.5, ease: "anticipate" }}
                            className="absolute inset-0 p-4 flex items-center gap-4"
                        >
                            <div className="p-3 rounded-xl bg-black/40 border border-[#00f3ff]/10 shrink-0 shadow-inner">
                                {activeCard.icon}
                            </div>
                            <div className="flex flex-col min-w-0 flex-1 justify-center">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-[#00f3ff]/60 mb-1">
                                    {activeCard.title}
                                </span>
                                {activeCard.content}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
            
            {/* Ambient Background Glow */}
            <div className="absolute -bottom-10 -right-10 w-32 h-32 bg-[#00f3ff]/10 blur-3xl rounded-full pointer-events-none" />
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00f3ff]/30 to-transparent" />
        </div>
    );
};

export default BriefingCard;
