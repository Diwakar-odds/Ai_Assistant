import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SpatialCursorProps {
    x: number;
    y: number;
    isPinching: boolean;
}

export const SpatialCursor: React.FC<SpatialCursorProps> = ({ x, y, isPinching }) => {
    // Smoothed coordinates
    const [smoothX, setSmoothX] = useState(x);
    const [smoothY, setSmoothY] = useState(y);

    useEffect(() => {
        // Simple low-pass filter to smooth jitter
        setSmoothX(prev => prev + (x - prev) * 0.4);
        setSmoothY(prev => prev + (y - prev) * 0.4);
    }, [x, y]);

    // Fire simulated click event on pinch transition
    useEffect(() => {
        if (isPinching) {
            // Find element under cursor and click it
            const el = document.elementFromPoint(smoothX, smoothY) as HTMLElement;
            if (el && typeof el.click === 'function') {
                el.click();
                
                // Add a visual ripple effect class (requires CSS)
                el.classList.add('active-scale');
                setTimeout(() => el.classList.remove('active-scale'), 200);
            }
        }
    }, [isPinching, smoothX, smoothY]);

    return (
        <motion.div
            className="fixed z-[9999] pointer-events-none flex items-center justify-center"
            style={{ 
                left: smoothX, 
                top: smoothY,
                transform: 'translate(-50%, -50%)'
            }}
        >
            <motion.div
                className={`rounded-full border-2 ${isPinching ? 'bg-blue-500 border-blue-400' : 'bg-white/50 border-white/80 backdrop-blur-sm'}`}
                animate={{
                    width: isPinching ? 16 : 24,
                    height: isPinching ? 16 : 24,
                    scale: isPinching ? 0.8 : 1
                }}
                transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                style={{
                    boxShadow: isPinching 
                        ? '0 0 20px rgba(59, 130, 246, 0.8)' 
                        : '0 0 10px rgba(255, 255, 255, 0.3)'
                }}
            />
        </motion.div>
    );
};
