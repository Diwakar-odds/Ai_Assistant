import { useEffect, useRef, useState, useCallback } from 'react';
import { FilesetResolver, GestureRecognizer, DrawingUtils, HandLandmarker } from '@mediapipe/tasks-vision';

interface Point {
    x: number;
    y: number;
}

export interface SpatialGestureState {
    cursorPosition: Point | null;
    isPinching: boolean;
    pinchDistance: number;
    activeGesture: string | null; // e.g. "MissionControl"
}

export const useSpatialGestures = (videoElement: HTMLVideoElement | null, isActive: boolean) => {
    const [state, setState] = useState<SpatialGestureState>({
        cursorPosition: null,
        isPinching: false,
        pinchDistance: 0,
        activeGesture: null,
    });
    
    const gestureRecognizerRef = useRef<GestureRecognizer | null>(null);
    const requestRef = useRef<number>();
    const lastVideoTimeRef = useRef(-1);
    
    // Initialize MediaPipe Gesture Recognizer
    useEffect(() => {
        let isMounted = true;
        
        const initMediaPipe = async () => {
            try {
                console.log("Initializing MediaPipe Tasks Vision...");
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
                );
                
                const recognizer = await GestureRecognizer.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
                        delegate: "GPU"
                    },
                    runningMode: "VIDEO",
                    numHands: 1
                });
                
                if (isMounted) {
                    gestureRecognizerRef.current = recognizer;
                    console.log("MediaPipe Gesture Recognizer initialized!");
                }
            } catch (err) {
                console.error("Failed to initialize MediaPipe:", err);
            }
        };
        
        initMediaPipe();
        
        return () => {
            isMounted = false;
            if (gestureRecognizerRef.current) {
                gestureRecognizerRef.current.close();
                gestureRecognizerRef.current = null;
            }
        };
    }, []);

    // Frame processing loop
    const predictWebcam = useCallback(() => {
        if (!videoElement || !gestureRecognizerRef.current || !isActive) {
            return;
        }

        const nowInMs = Date.now();
        
        // Only process if video has new frame
        if (videoElement.currentTime !== lastVideoTimeRef.current) {
            lastVideoTimeRef.current = videoElement.currentTime;
            
            try {
                const results = gestureRecognizerRef.current.recognizeForVideo(videoElement, nowInMs);
                
                if (results.landmarks && results.landmarks.length > 0) {
                    const landmarks = results.landmarks[0];
                    
                    // 1. Air Cursor (Track Index Finger Tip: Landmark 8)
                    const indexTip = landmarks[8];
                    
                    // Mirror X coordinate because webcam is mirrored
                    const cursorX = (1 - indexTip.x) * window.innerWidth;
                    const cursorY = indexTip.y * window.innerHeight;
                    
                    // 2. Pinch Detection (Distance between Thumb Tip [4] and Index Tip [8])
                    const thumbTip = landmarks[4];
                    
                    // Calculate euclidean distance (using normalized coordinates, threshold ~0.05)
                    const dx = indexTip.x - thumbTip.x;
                    const dy = indexTip.y - thumbTip.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    const isPinching = distance < 0.05;
                    
                    // 3. Three-finger swipe up (Mission Control)
                    // Simple heuristic: If index, middle, ring are extended and moving up quickly.
                    // For now, let's use the built-in gestures if possible, or build a custom check.
                    // We'll rely on pinch for now, and add Mission Control check later.
                    let activeGesture = null;
                    if (results.gestures && results.gestures.length > 0) {
                        const recognizedCategory = results.gestures[0][0].categoryName;
                        if (recognizedCategory === 'Open_Palm') {
                            activeGesture = 'MissionControl'; // Hack: mapping Open Palm to Mission Control for simplicity initially
                        }
                    }

                    setState({
                        cursorPosition: { x: cursorX, y: cursorY },
                        isPinching,
                        pinchDistance: distance,
                        activeGesture
                    });
                } else {
                    // No hands detected
                    setState(prev => prev.cursorPosition ? { cursorPosition: null, isPinching: false, pinchDistance: 0, activeGesture: null } : prev);
                }
            } catch (err) {
                console.error("Gesture recognition error:", err);
            }
        }
        
        // Loop
        if (isActive) {
            requestRef.current = requestAnimationFrame(predictWebcam);
        }
    }, [videoElement, isActive]);

    useEffect(() => {
        if (isActive && videoElement) {
            // Start the loop
            requestRef.current = requestAnimationFrame(predictWebcam);
        } else {
            // Stop the loop
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
            setState({ cursorPosition: null, isPinching: false, pinchDistance: 0, activeGesture: null });
        }
        
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [isActive, videoElement, predictWebcam]);

    return state;
};
