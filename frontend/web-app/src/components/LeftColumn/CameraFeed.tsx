import { motion } from 'framer-motion';
import { Video, VideoOff, Camera, UserCheck } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';

const CameraFeed = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [error, setError] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  const { analyzeCameraFrame, checkPresence, presenceData } = useDashboard();

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

  const handleShowAndAsk = () => {
    const frame = captureFrame();
    if (frame) {
      setIsAnalyzing(true);
      analyzeCameraFrame(frame, "What is the main object or text visible in this image? Be concise.");
      
      // Reset analyzing state after a delay (or based on response if we tracked specific request IDs)
      setTimeout(() => setIsAnalyzing(false), 3000);
    }
  };

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
              ref={videoRef}
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
    </motion.div>
  );
};

export default CameraFeed;
