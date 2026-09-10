import { motion, AnimatePresence } from 'framer-motion';
import { Video, VideoOff, Camera, UserCheck, Hand } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useDashboard } from '../../contexts/DashboardContext';
import { useSpatialGestures } from '../../hooks/useSpatialGestures';
import { SpatialCursor } from '../SpatialCursor';

const CameraFeed = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [error, setError] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  const { analyzeCameraFrame, checkPresence, presenceData, checkGesture, lastGesture, setSelectedView } = useDashboard();
  
  // Local state for gesture UI badge (shows momentarily)
  const [activeGesture, setActiveGesture] = useState<string | null>(null);
  const [videoEl, setVideoEl] = useState<HTMLVideoElement | null>(null);
  const spatialGestures = useSpatialGestures(videoEl, isRecording && hasPermission);

  // Handle Mission Control gesture from local spatial tracker
  useEffect(() => {
      if (spatialGestures.activeGesture === 'MissionControl') {
          // Trigger Mission Control view
          setSelectedView('dashboard'); // Assuming dashboard is the overview
          setActiveGesture('MISSION_CONTROL');
          setTimeout(() => setActiveGesture(null), 2000);
      }
      
      // Orb Manipulation
      const orb = document.getElementById('ai-orb');
      if (orb) {
          if (spatialGestures.isPinching) {
              // Scale orb relative to pinch distance (closer = smaller)
              const scale = 0.5 + (spatialGestures.pinchDistance / 0.05) * 0.5;
              orb.style.transform = `scale(${Math.max(0.5, Math.min(1.2, scale))})`;
          } else {
              orb.style.transform = `scale(1)`;
          }
      }
  }, [spatialGestures.activeGesture, setSelectedView, spatialGestures.isPinching, spatialGestures.pinchDistance]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Frame capture utility
  const captureFrame = useCallback((): string | null => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      
      // Ensure canvas matches video dimensions
      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }
      
      const context = canvas.getContext('2d');
      if (context) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg', 0.6); // Compress to 60% quality
      }
    }
    return null;
  }, []);

  // Presence detection loop
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    
    if (isRecording && hasPermission) {
      // Check presence every 10 seconds
      intervalId = setInterval(() => {
        const frame = captureFrame();
        if (frame) {
          checkPresence(frame);
        }
      }, 10000);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRecording, hasPermission, captureFrame, checkPresence]);

  // Gesture detection loop
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    if (isRecording && hasPermission) {
      // Check gesture every 250ms (4 FPS) to support Swipe tracking
      intervalId = setInterval(() => {
        const frame = captureFrame();
        if (frame) {
          checkGesture(frame);
        }
      }, 250);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRecording, hasPermission, captureFrame, checkGesture]);

  const handleShowAndAsk = useCallback(() => {
    if (isAnalyzing) return; // Prevent double trigger
    
    const frame = captureFrame();
    if (frame) {
      setIsAnalyzing(true);
      analyzeCameraFrame(frame, "What is the main object or text visible in this image? Be concise.");
      
      // Reset analyzing state after a delay
      setTimeout(() => setIsAnalyzing(false), 3000);
    }
  }, [captureFrame, isAnalyzing, analyzeCameraFrame]);

  // Handle specific local gesture actions
  useEffect(() => {
    if (lastGesture && lastGesture.gesture) {
      // Show badge UI
      setActiveGesture(lastGesture.gesture);
      const timer = setTimeout(() => setActiveGesture(null), 2000);
      
      // Trigger actions
      if (lastGesture.gesture === 'PEACE' && !isAnalyzing) {
        handleShowAndAsk();
      }
      
      return () => clearTimeout(timer);
    }
  }, [lastGesture, handleShowAndAsk, isAnalyzing]);

  const startCamera = async () => {
    try {
      console.log('🎥 Starting camera...');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      });

      console.log('✅ Camera stream obtained:', stream);
      console.log('📹 Video tracks:', stream.getVideoTracks());

      // Set state FIRST to render the video element
      streamRef.current = stream;
      setHasPermission(true);
      setIsRecording(true);
      setError('');

      // Wait for next render cycle, then set the stream
      setTimeout(() => {
        if (videoRef.current) {
          console.log('📺 Setting video srcObject...');
          videoRef.current.srcObject = stream;

          videoRef.current.onloadedmetadata = async () => {
            console.log('🎬 Video metadata loaded');
            try {
              await videoRef.current?.play();
              console.log('▶️ Video playing');
            } catch (playErr) {
              console.error('❌ Video play error:', playErr);
            }
          };
        } else {
          console.error('❌ Video ref is still null after state update');
        }
      }, 100);

    } catch (err) {
      console.error('❌ Camera access error:', err);
      setError('Camera access denied');
      setHasPermission(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsRecording(false);
  };

  const toggleCamera = () => {
    console.log('🔄 Toggle camera - current state:', isRecording);
    if (isRecording) {
      stopCamera();
    } else {
      startCamera();
    }
  };

  return (
    <motion.div
      className="glass-panel rounded-lg p-2 sm:p-2.5 flex-shrink-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs sm:text-sm font-medium text-white">Camera Feed</h3>
        <motion.button
          onClick={toggleCamera}
          className="text-[10px] sm:text-xs text-[#9CA3AF] hover:text-white transition-colors"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isRecording ? 'Stop' : 'Start'}
        </motion.button>
      </div>

      <div className="relative bg-[#0A0E12] rounded-lg overflow-hidden aspect-video group cursor-pointer">
        {hasPermission && isRecording ? (
          <div className="relative w-full h-full">
            <video
              ref={(el) => {
                  videoRef.current = el;
                  if (el !== videoEl) setVideoEl(el);
              }}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
              style={{ display: 'block', position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
              onLoadedMetadata={() => {
                console.log('Video metadata loaded');
                if (videoRef.current) {
                  videoRef.current.play().catch(err => console.error('Play error:', err));
                }
              }}
            />

            {isRecording && (
              <>
                <motion.div
                  className="absolute top-3 left-3 flex items-center gap-2 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-full z-10"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5 }}
                >
                  <motion.div
                    className="w-2 h-2 bg-red-500 rounded-full"
                    animate={{
                      opacity: [1, 0.3, 1],
                      scale: [1, 0.8, 1],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  />
                  <span className="text-xs font-medium text-white">REC</span>
                </motion.div>

                 {presenceData && presenceData.analysis && (
                   <motion.div
                     className="absolute top-3 right-3 flex items-center gap-2 bg-black/50 backdrop-blur-sm px-3 py-1.5 rounded-full z-10"
                     initial={{ opacity: 0, scale: 0.8 }}
                     animate={{ opacity: 1, scale: 1 }}
                   >
                     <UserCheck className={`w-3 h-3 ${presenceData.analysis.present ? 'text-green-400' : 'text-gray-400'}`} />
                     <span className="text-xs font-medium text-white capitalize">{presenceData.analysis.mood || (presenceData.analysis.present ? 'Present' : 'Away')}</span>
                   </motion.div>
                )}

                <AnimatePresence>
                  {activeGesture && (
                     <motion.div
                       className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center gap-1 bg-black/60 backdrop-blur-md px-4 py-3 rounded-2xl z-20 pointer-events-none"
                       initial={{ opacity: 0, scale: 0.5, y: '-40%' }}
                       animate={{ opacity: 1, scale: 1, y: '-50%' }}
                       exit={{ opacity: 0, scale: 0.8 }}
                     >
                       <Hand className="w-8 h-8 text-blue-400" />
                       <span className="text-sm font-bold text-white tracking-widest">{activeGesture.replace('_', ' ')}</span>
                     </motion.div>
                  )}
                </AnimatePresence>

                <div className="absolute bottom-3 left-0 right-0 flex justify-center z-10">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleShowAndAsk}
                    disabled={isAnalyzing}
                    className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-all ${
                      isAnalyzing 
                        ? 'bg-blue-500/50 text-white cursor-wait' 
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)]'
                    }`}
                  >
                    <Camera className="w-3.5 h-3.5" />
                    {isAnalyzing ? 'Analyzing...' : 'Show & Ask'}
                  </motion.button>
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            <motion.div
              className="absolute inset-0 bg-gradient-to-br from-[#16181D] to-[#0A0E12]"
              animate={{
                opacity: [0.5, 0.7, 0.5],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            <motion.div
              whileHover={{ scale: 1.1 }}
              transition={{ duration: 0.2 }}
              className="relative z-10 flex flex-col items-center gap-2"
            >
              {error ? (
                <>
                  <VideoOff className="w-12 h-12 text-[#EF4444] opacity-60" strokeWidth={1.5} />
                  <span className="text-xs text-[#EF4444]">{error}</span>
                  <button
                    onClick={startCamera}
                    className="mt-2 px-3 py-1 bg-[#3B82F6] text-white text-xs rounded-md hover:bg-[#3B82F6]/80 transition-colors"
                  >
                    Retry
                  </button>
                </>
              ) : (
                <>
                  <Video className="w-12 h-12 text-neon-cyan opacity-60 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
                  <span className="text-xs text-[#9CA3AF]">Click to enable</span>
                </>
              )}
            </motion.div>
          </>
        )}
      </div>
      
      {/* Hidden canvas for frame extraction */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      
      {spatialGestures.cursorPosition && createPortal(
          <SpatialCursor 
              x={spatialGestures.cursorPosition.x} 
              y={spatialGestures.cursorPosition.y} 
              isPinching={spatialGestures.isPinching} 
          />,
          document.body
      )}
    </motion.div>
  );
};

export default CameraFeed;
