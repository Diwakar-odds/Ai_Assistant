import { motion } from 'framer-motion';
import { useState } from 'react';

interface ArcReactorRingsProps {
  /** Mood state: 'focused' | 'calm' | 'happy' | 'stressed' | 'neutral' */
  mood: string;
  /** Project completion 0–100 */
  projectProgress: number;
  /** Project name */
  projectName: string;
  /** System health 0–100 */
  systemHealth: number;
  /** When true, all rings turn orange/red and pulse */
  dangerMode: boolean;
}

const MOOD_COLORS: Record<string, string> = {
  focused: '#22c55e',   // green
  calm: '#3b82f6',      // blue
  happy: '#facc15',     // yellow
  stressed: '#f97316',  // orange
  frustrated: '#ef4444',// red
  neutral: '#00f3ff',   // cyan (default)
};

const DANGER_COLOR = '#f97316';
const DANGER_PULSE_COLOR = '#ef4444';

const ArcReactorRings = ({
  mood,
  projectProgress,
  projectName,
  systemHealth,
  dangerMode,
}: ArcReactorRingsProps) => {
  const [hovered, setHovered] = useState(false);

  const moodColor = dangerMode ? DANGER_COLOR : (MOOD_COLORS[mood] || MOOD_COLORS.neutral);
  const progressColor = dangerMode ? DANGER_PULSE_COLOR : '#00f3ff';
  const healthColor = dangerMode ? DANGER_COLOR : '#00d4ff';

  // SVG circle math
  const center = 130;
  const innerR = 105;
  const middleR = 115;
  const outerR = 125;

  const innerCircumference = 2 * Math.PI * innerR;
  const middleCircumference = 2 * Math.PI * middleR;
  const outerCircumference = 2 * Math.PI * outerR;

  // Progress dash
  const progressDash = (projectProgress / 100) * middleCircumference;
  const progressGap = middleCircumference - progressDash;

  // Health dash
  const healthDash = (systemHealth / 100) * outerCircumference;
  const healthGap = outerCircumference - healthDash;

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ pointerEvents: 'auto' }}
    >
      <svg
        viewBox={`0 0 ${center * 2} ${center * 2}`}
        className="absolute inset-0 w-full h-full"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Glow filters */}
          <filter id="glow-inner" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-mid" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-outer" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ─── INNER RING: Mood ─── */}
        <motion.circle
          cx={center}
          cy={center}
          r={innerR}
          fill="none"
          stroke={moodColor}
          strokeWidth={2}
          strokeDasharray="6 4"
          filter="url(#glow-inner)"
          opacity={0.8}
          animate={
            dangerMode
              ? { opacity: [0.5, 1, 0.5], rotate: [0, 360] }
              : { rotate: [0, 360] }
          }
          transition={
            dangerMode
              ? { opacity: { duration: 0.8, repeat: Infinity }, rotate: { duration: 8, repeat: Infinity, ease: 'linear' } }
              : { rotate: { duration: 20, repeat: Infinity, ease: 'linear' } }
          }
          style={{ transformOrigin: `${center}px ${center}px` }}
        />

        {/* ─── MIDDLE RING: Project Progress ─── */}
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={middleR}
          fill="none"
          stroke={progressColor}
          strokeWidth={3}
          opacity={0.15}
        />
        {/* Progress fill */}
        <motion.circle
          cx={center}
          cy={center}
          r={middleR}
          fill="none"
          stroke={progressColor}
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={`${progressDash} ${progressGap}`}
          strokeDashoffset={middleCircumference * 0.25}
          filter="url(#glow-mid)"
          animate={
            dangerMode
              ? { opacity: [0.4, 1, 0.4], rotate: [0, -360] }
              : { rotate: [0, -360] }
          }
          transition={
            dangerMode
              ? { opacity: { duration: 0.6, repeat: Infinity }, rotate: { duration: 12, repeat: Infinity, ease: 'linear' } }
              : { rotate: { duration: 30, repeat: Infinity, ease: 'linear' } }
          }
          style={{ transformOrigin: `${center}px ${center}px` }}
        />

        {/* ─── OUTER RING: System Health ─── */}
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={outerR}
          fill="none"
          stroke={healthColor}
          strokeWidth={1.5}
          opacity={0.1}
        />
        {/* Health fill */}
        <motion.circle
          cx={center}
          cy={center}
          r={outerR}
          fill="none"
          stroke={healthColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeDasharray={`${healthDash} ${healthGap}`}
          strokeDashoffset={outerCircumference * 0.25}
          filter="url(#glow-outer)"
          animate={
            dangerMode
              ? { opacity: [0.3, 1, 0.3] }
              : { opacity: [0.6, 0.9, 0.6] }
          }
          transition={{
            opacity: { duration: dangerMode ? 0.5 : 3, repeat: Infinity, ease: 'easeInOut' },
          }}
        />

        {/* ─── FLOATING LABELS (on hover) ─── */}
        {hovered && !dangerMode && (
          <>
            {/* Mood label — left */}
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              <rect
                x={center - innerR - 52}
                y={center - 24}
                width={48}
                height={20}
                rx={4}
                fill="rgba(0,0,0,0.7)"
                stroke={moodColor}
                strokeWidth={0.5}
              />
              <text
                x={center - innerR - 28}
                y={center - 11}
                textAnchor="middle"
                fill={moodColor}
                fontSize="8"
                fontFamily="monospace"
              >
                {mood || 'neutral'}
              </text>
            </motion.g>

            {/* Project label — right */}
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <rect
                x={center + middleR + 4}
                y={center - 30}
                width={52}
                height={28}
                rx={4}
                fill="rgba(0,0,0,0.7)"
                stroke={progressColor}
                strokeWidth={0.5}
              />
              <text
                x={center + middleR + 30}
                y={center - 18}
                textAnchor="middle"
                fill={progressColor}
                fontSize="7"
                fontFamily="monospace"
              >
                {projectName ? projectName.slice(0, 8) : 'Project'}
              </text>
              <text
                x={center + middleR + 30}
                y={center - 8}
                textAnchor="middle"
                fill={progressColor}
                fontSize="10"
                fontWeight="bold"
                fontFamily="monospace"
              >
                {Math.round(projectProgress)}%
              </text>
            </motion.g>

            {/* Health label — bottom */}
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              <rect
                x={center - 28}
                y={center + outerR + 6}
                width={56}
                height={18}
                rx={4}
                fill="rgba(0,0,0,0.7)"
                stroke={healthColor}
                strokeWidth={0.5}
              />
              <text
                x={center}
                y={center + outerR + 18}
                textAnchor="middle"
                fill={healthColor}
                fontSize="8"
                fontFamily="monospace"
              >
                Health {systemHealth}%
              </text>
            </motion.g>
          </>
        )}
      </svg>
    </div>
  );
};

export default ArcReactorRings;
