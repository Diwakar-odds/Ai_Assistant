import { useState, useEffect, useRef } from 'react';
import { Mic, Volume2, Settings as SettingsIcon, MicOff, Loader } from 'lucide-react';
import { io, Socket } from 'socket.io-client';

const VoiceInterface = () => {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [waveform, setWaveform] = useState<number[]>(Array(20).fill(0.2));
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    // Initialize WebSocket connection
    const socketInstance = io();
    setSocket(socketInstance);

    socketInstance.on('connect', () => {
      setIsConnected(true);
      console.log('Voice interface connected to backend');
      fetchCommandHistory();
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });

    socketInstance.on('voice_status', (data) => {
      setIsListening(data.listening);
    });

    socketInstance.on('voice_transcript', (data) => {
      setTranscript(data.text);
      setCommandHistory(prev => [data.text, ...prev.slice(0, 9)]);
    });

    socketInstance.on('voice_response', (data) => {
      setResponse(data.response);
      setIsProcessing(false);
    });

    socketInstance.on('voice_start_response', (data) => {
      if (data.success) {
        console.log('Voice listening started successfully');
      } else {
        console.error('Failed to start voice listening:', data.error);
        setIsListening(false);
      }
    });

    socketInstance.on('voice_stop_response', (data) => {
      if (data.success) {
        console.log('Voice listening stopped successfully');
      }
    });

    return () => {
      socketInstance.disconnect();
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const fetchCommandHistory = async () => {
    try {
      const response = await fetch('/api/voice/history');
      if (response.ok) {
        const history = await response.json();
        setCommandHistory(history);
      }
    } catch (error) {
      console.error('Failed to fetch command history:', error);
    }
  };

  useEffect(() => {
    if (isListening) {
      const interval = setInterval(() => {
        setWaveform(Array(20).fill(0).map(() => Math.random()));
      }, 100);
      return () => clearInterval(interval);
    } else {
      setWaveform(Array(20).fill(0.2));
    }
  }, [isListening]);

  const toggleListening = async () => {
    if (!isConnected || !socket) {
      setTranscript('Not connected to server');
      return;
    }

    if (isListening) {
      // Stop listening
      socket.emit('stop_voice_listening');
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    } else {
      // Start listening
      setTranscript('Initializing voice recognition...');
      setResponse('');
      socket.emit('start_voice_listening');
      
      try {
        // Also start browser-based recording as fallback
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          // Convert to base64 and send to server if needed
          const reader = new FileReader();
          reader.onloadend = () => {
            if (socket && reader.result) {
              const base64Audio = (reader.result as string).split(',')[1];
              socket.emit('voice_audio_data', { audio_data: base64Audio });
            }
          };
          reader.readAsDataURL(audioBlob);
        };

        mediaRecorder.start();
        setTranscript('Listening... Speak now!');
      } catch (error) {
        console.error('Failed to access microphone:', error);
        setTranscript('Microphone access denied. Please enable microphone permissions.');
      }
    }
  };

  const speakText = (text: string) => {
    if (socket) {
      socket.emit('request_tts', { text });
    }
  };

  return (
    <div className="min-h-screen py-8 animate-fade-in flex flex-col items-center justify-center">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-2 text-gradient">Voice Interface</h1>
        <p className="text-[#DDDDDD]">Speak naturally, I'm listening</p>
      </div>

      <div className="relative mb-16">
        <div className="relative w-80 h-80 flex items-center justify-center">
          {isListening && (
            <>
              <div className="absolute w-80 h-80 rounded-full border-2 border-[#00CEC9] animate-ping opacity-30"></div>
              <div className="absolute w-96 h-96 rounded-full border border-[#6C5CE7] animate-pulse opacity-20"></div>
            </>
          )}

          <div
            className={`relative w-48 h-48 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 ${
              isListening
                ? 'bg-gradient-to-br from-[#00CEC9] via-[#6C5CE7] to-[#E17055] scale-110 shadow-2xl shadow-[#00CEC9]/50'
                : 'bg-gradient-to-br from-[#6C5CE7] to-[#00CEC9] hover:scale-105'
            } ${!isConnected ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={toggleListening}
          >
            <div className="w-44 h-44 rounded-full bg-[#0A0E27] flex items-center justify-center">
              {isProcessing ? (
                <Loader size={64} className="text-[#00CEC9] animate-spin" />
              ) : isListening ? (
                <Volume2 size={64} className="text-[#00CEC9] animate-pulse" />
              ) : !isConnected ? (
                <MicOff size={64} className="text-gray-500" />
              ) : (
                <Mic size={64} className="text-[#6C5CE7]" />
              )}
            </div>
          </div>

          <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 w-full">
            <div className="flex items-end justify-center gap-1 h-20">
              {waveform.map((height, index) => (
                <div
                  key={index}
                  className={`w-2 rounded-full transition-all duration-100 ${
                    isListening ? 'bg-gradient-to-t from-[#00CEC9] to-[#6C5CE7]' : 'bg-[#6C5CE7]/30'
                  }`}
                  ref={(el) => {
                    if (el) {
                      el.style.height = `${height * 100}%`;
                    }
                  }}
                ></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {transcript && (
        <div className="glass-strong p-6 rounded-2xl mb-4 max-w-2xl w-full">
          <div className="text-sm text-[#DDDDDD] mb-2">You said:</div>
          <p className="text-xl text-[#00CEC9]">{transcript}</p>
        </div>
      )}

      {response && (
        <div className="glass-strong p-6 rounded-2xl mb-8 max-w-2xl w-full">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-[#DDDDDD]">Assistant:</div>
            <button
              onClick={() => speakText(response)}
              className="text-[#6C5CE7] hover:text-[#00CEC9] transition-colors"
              title="Speak response"
            >
              <Volume2 size={16} />
            </button>
          </div>
          <p className="text-lg text-white">{response}</p>
        </div>
      )}

      {!isConnected && (
        <div className="glass-strong p-4 rounded-xl mb-8 max-w-2xl w-full text-center">
          <p className="text-yellow-400">⚠️ Not connected to voice server</p>
        </div>
      )}

      <div className="max-w-2xl w-full space-y-4">
        <div className="glass-strong p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Command History</h2>
            <SettingsIcon size={20} className="text-[#DDDDDD] cursor-pointer hover:text-[#00CEC9] transition-colors" />
          </div>
          <div className="space-y-3">
            {commandHistory.map((command, index) => (
              <div
                key={index}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors cursor-pointer"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00CEC9] to-[#6C5CE7] flex items-center justify-center flex-shrink-0">
                  <Mic size={16} />
                </div>
                <span className="text-[#DDDDDD]">{command}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-strong p-6 rounded-2xl">
          <h2 className="text-xl font-bold mb-4">Voice Settings</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[#DDDDDD]">Wake Word Detection</span>
              <div className="w-12 h-6 bg-gradient-to-r from-[#00CEC9] to-[#6C5CE7] rounded-full cursor-pointer relative">
                <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#DDDDDD]">Voice Feedback</span>
              <div className="w-12 h-6 bg-gradient-to-r from-[#00CEC9] to-[#6C5CE7] rounded-full cursor-pointer relative">
                <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[#DDDDDD]">Microphone Sensitivity</span>
                <span className="text-[#00CEC9]">75%</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#00CEC9] to-[#6C5CE7] rounded-full w-3/4"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceInterface;
