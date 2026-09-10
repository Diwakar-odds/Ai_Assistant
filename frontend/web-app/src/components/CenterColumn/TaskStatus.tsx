import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useDashboard, ActiveChain } from '../../contexts/DashboardContext';

const SingleChainStatus = ({ chain }: { chain: ActiveChain }) => {
  const progress = useMotionValue(0);
  const progressPercent = useTransform(progress, (value) => Math.round(value));

  useEffect(() => {
    const controls = animate(progress, chain.progress, {
      duration: 1,
      ease: 'easeOut',
    });
    return controls.stop;
  }, [progress, chain.progress]);

  const circumference = 2 * Math.PI * 9;
  
  const isComplete = chain.status === 'completed';
  const isFailed = chain.status === 'failed';
  const isCancelled = chain.status === 'cancelled';
  
  let color = '#3B82F6'; // Blue for executing
  if (isComplete) color = '#10B981'; // Green
  else if (isFailed) color = '#EF4444'; // Red
  else if (isCancelled) color = '#6B7280'; // Gray

  return (
    <div className="flex flex-col items-center flex-shrink-0 mx-1">
      <div className="relative">
        <svg className="w-[22px] h-[22px] sm:w-[24px] sm:h-[24px] -rotate-90" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="9" fill="none" stroke="#1F2228" strokeWidth="2.5" />
          <motion.circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={useTransform(progress, [0, 100], [circumference, 0])}
            style={{ filter: `drop-shadow(0 0 6px ${color}66)` }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[8px] sm:text-[10px] font-bold text-white">
            <motion.span>{progressPercent}</motion.span>
            <span className="text-[6px] text-[#9CA3AF]">%</span>
          </div>
        </div>
      </div>

      <motion.div
        className="mt-1 px-1.5 py-0.5 rounded-full"
        style={{ backgroundColor: `${color}1A` }}
        animate={!isComplete && !isFailed && !isCancelled ? { opacity: [1, 0.6, 1] } : {}}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      >
        <span className="text-[6px] sm:text-[8px] font-medium" style={{ color }}>
          {chain.status.toUpperCase()}
        </span>
      </motion.div>

      <p className="mt-0.5 text-[6px] sm:text-[7px] text-[#9CA3AF] text-center max-w-[60px] truncate" title={chain.command}>
        {chain.app_context ? `[${chain.app_context}] ` : ''}{chain.command}
      </p>
    </div>
  );
};

const TaskStatus = () => {
  const { brainStatus, sendCommand } = useDashboard();
  
  if (!brainStatus || (!brainStatus.is_busy && brainStatus.active_chains.length === 0)) {
    return null; // Don't show if brain is completely idle
  }

  const handleCancel = () => {
    sendCommand('stop'); // Routes to Executive Brain as high-priority stop
  };

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg p-2 flex flex-col items-center flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
    >
      <div className="flex justify-between items-center w-full mb-2 px-1">
        <h3 className="text-[9px] sm:text-[10px] font-bold text-white">Brain Active</h3>
        {brainStatus.is_busy && (
          <button 
            onClick={handleCancel}
            className="text-[8px] bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 px-1.5 py-0.5 rounded transition-colors"
          >
            STOP
          </button>
        )}
      </div>

      <div className="flex flex-row overflow-x-auto max-w-[200px] hide-scrollbar pb-1">
        {brainStatus.active_chains.map((chain: ActiveChain) => (
          <SingleChainStatus key={chain.chain_id} chain={chain} />
        ))}
      </div>
    </motion.div>
  );
};

export default TaskStatus;
