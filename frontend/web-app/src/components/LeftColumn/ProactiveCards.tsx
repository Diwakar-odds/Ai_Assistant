import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDashboard } from '../../contexts/DashboardContext';

export default function ProactiveCards() {
  const [cards, setCards] = useState<any[]>([]);
  const { socket } = useDashboard();

  useEffect(() => {
    if (!socket) return;
    
    // Listen for proactive events from backend
    const handleProactiveEvent = (data: any) => {
      setCards(prev => {
        const newCards = [data, ...prev].slice(0, 3); // keep latest 3
        return newCards;
      });
    };

    socket.on('proactive_suggestion', handleProactiveEvent);
    
    // Add some initial mock cards if empty just to show the polish
    setCards([
      { id: 1, type: 'weather', title: 'Weather Update', content: 'It looks like it might rain soon in your area. Grab an umbrella!' },
      { id: 2, type: 'schedule', title: 'Upcoming Meeting', content: 'Standup at 10:00 AM. Would you like me to join and take notes?' }
    ]);

    return () => {
      socket.off('proactive_suggestion', handleProactiveEvent);
    };
  }, [socket]);

  return (
    <div className="bg-[#16181D] rounded-xl border border-[#1F2228] p-4 flex flex-col gap-3 shadow-lg">
      <h3 className="text-sm font-semibold text-[#9CA3AF] uppercase tracking-wider flex items-center gap-2">
        <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        Proactive Insights
      </h3>
      
      <div className="flex flex-col gap-2">
        <AnimatePresence>
          {cards.map((card, idx) => (
            <motion.div
              key={card.id || idx}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.3 }}
              className="bg-[#1F2228] p-3 rounded-lg border border-[#2A2E35] hover:border-blue-500/50 transition-colors cursor-pointer"
            >
              <div className="text-xs font-bold text-blue-400 mb-1">{card.title}</div>
              <div className="text-xs text-gray-300 leading-relaxed">{card.content}</div>
            </motion.div>
          ))}
          {cards.length === 0 && (
            <div className="text-xs text-gray-500 text-center py-2">No active insights</div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
