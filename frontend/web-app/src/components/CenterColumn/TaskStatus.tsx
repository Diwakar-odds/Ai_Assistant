import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useState } from 'react';

const TaskStatus = () => {
  const [targetProgress] = useState(() => Math.floor(Math.random() * 30) + 50); // Random 50-80%
  const progress = useMotionValue(0);
  const progressPercent = useTransform(progress, (value) => Math.round(value));

  useEffect(() => {
    const controls = animate(progress, targetProgress, {
      duration: 2,
      delay: 0.5,
      ease: 'easeOut',
    });

    return controls.stop;
  }, [progress, targetProgress]);

  const circumference = 2 * Math.PI * 9;

  return (
    <motion.div
      className="bg-[#16181D] border border-[#1F2228] rounded-lg p-1 flex flex-col items-center flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
    >
      <h3 className="text-[8px] sm:text-[9px] font-medium text-white mb-0.5">Task Status</h3>

      <div className="relative">
        <svg className="w-[22px] h-[22px] sm:w-[24px] sm:h-[24px] -rotate-90" viewBox="0 0 24 24">
          <circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke="#1F2228"
            strokeWidth="2.5"
          />

          <motion.circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke="#3B82F6"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={useTransform(
              progress,
              [0, 100],
              [circumference, 0]
            )}
            style={{
              filter: 'drop-shadow(0 0 6px rgba(59, 130, 246, 0.4))',
            }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[10px] sm:text-xs font-bold text-white">
            <motion.span>{progressPercent}</motion.span>
            <span className="text-[7px] sm:text-[8px] text-[#9CA3AF]">%</span>
          </div>
        </div>
      </div>

      <motion.div
        className="mt-0.5 px-1 py-0.5 bg-[#3B82F6]/10 rounded-full"
        animate={{
          opacity: [1, 0.6, 1],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <span className="text-[6px] sm:text-[8px] font-medium text-[#3B82F6]">ACTIVE</span>
      </motion.div>

      <p className="mt-0.5 text-[6px] sm:text-[8px] text-[#9CA3AF] text-center max-w-[200px]">
        Processing tasks
      </p>
    </motion.div>
  );
};

export default TaskStatus;
