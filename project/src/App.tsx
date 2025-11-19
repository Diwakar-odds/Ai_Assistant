import { useState, useEffect } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import Sidebar from './components/Sidebar';
import CommandCenter from './components/CommandCenter';
import Dashboard from './components/Dashboard';
import ApplicationGrid from './components/ApplicationGrid';
import VoiceInterface from './components/VoiceInterface';
import ConversationSpace from './components/ConversationSpace';
import SettingsPanel from './components/SettingsPanel';
import ParticleBackground from './components/ParticleBackground';
import Auth from './components/Auth';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const [activeSection, setActiveSection] = useState('command');
  const [theme, setTheme] = useState('dark');
  const [language, setLanguage] = useState('hinglish');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  useEffect(() => {
    document.body.className = theme;
    
    // Load saved theme and language from localStorage
    const savedTheme = localStorage.getItem('yourdaddy-theme');
    if (savedTheme) {
      setTheme(savedTheme);
    }
    
    const savedLanguage = localStorage.getItem('yourdaddy-language');
    if (savedLanguage) {
      setLanguage(savedLanguage);
    }

    // Check for existing auth token
    const savedToken = localStorage.getItem('yourdaddy-token');
    const savedUsername = localStorage.getItem('yourdaddy-username');
    
    if (savedToken && savedUsername) {
      // Validate token with backend
      fetch('/api/auth/verify', {
        headers: {
          'Authorization': `Bearer ${savedToken}`,
        },
      })
        .then(response => {
          if (response.ok) {
            setAuthToken(savedToken);
            setUsername(savedUsername);
            setIsAuthenticated(true);
          } else {
            // Token invalid, clear it
            localStorage.removeItem('yourdaddy-token');
            localStorage.removeItem('yourdaddy-username');
          }
        })
        .catch(() => {
          // Network error, will try again later
        })
        .finally(() => {
          setIsCheckingAuth(false);
        });
    } else {
      setIsCheckingAuth(false);
    }
  }, [theme]);

  useEffect(() => {
    // Save theme and language to localStorage when they change
    localStorage.setItem('yourdaddy-theme', theme);
    localStorage.setItem('yourdaddy-language', language);
  }, [theme, language]);

  useEffect(() => {
    // Monitor online status
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    // Check backend status with exponential backoff
    const checkBackendStatus = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch('/api/status', { 
          signal: controller.signal,
          headers: authToken ? {
            'Authorization': `Bearer ${authToken}`,
          } : {},
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          setBackendStatus('connected');
          setReconnectAttempts(0); // Reset on successful connection
        } else {
          setBackendStatus('disconnected');
        }
      } catch (error) {
        console.warn('Backend status check failed:', error);
        setBackendStatus('disconnected');
        
        // Implement exponential backoff
        setReconnectAttempts(prev => Math.min(prev + 1, 10));
      }
    };
    
    checkBackendStatus();
    
    // Calculate backoff delay: 30s, 60s, 120s, up to 300s (5 min)
    const backoffDelay = Math.min(30000 * Math.pow(2, reconnectAttempts), 300000);
    const interval = setInterval(checkBackendStatus, backoffDelay);
    
    return () => clearInterval(interval);
  }, [authToken, reconnectAttempts]);

  const renderSection = () => {
    try {
      switch (activeSection) {
        case 'command':
          return <CommandCenter language={language} setLanguage={setLanguage} />;
        case 'dashboard':
          return <Dashboard language={language} />;
        case 'apps':
          return <ApplicationGrid language={language} />;
        case 'voice':
          return <VoiceInterface language={language} setLanguage={setLanguage} />;
        case 'chat':
          return <ConversationSpace language={language} />;
        case 'settings':
          return <SettingsPanel theme={theme} setTheme={setTheme} language={language} setLanguage={setLanguage} />;
        default:
          return <CommandCenter language={language} setLanguage={setLanguage} />;
      }
    } catch (error) {
      console.error('Error rendering section:', error);
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="glass-strong p-8 rounded-2xl text-center max-w-md">
            <h2 className="text-xl font-bold text-red-400 mb-4">Section Error</h2>
            <p className="text-[#DDDDDD] mb-4">
              Failed to load the {activeSection} section. Please try switching to a different section.
            </p>
            <button
              onClick={() => setActiveSection('command')}
              className="px-4 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors"
            >
              Go to Command Center
            </button>
          </div>
        </div>
      );
    }
  };

  const handleAuthSuccess = (token: string, user: string) => {
    setAuthToken(token);
    setUsername(user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('yourdaddy-token');
    localStorage.removeItem('yourdaddy-username');
    setAuthToken(null);
    setUsername(null);
    setIsAuthenticated(false);
  };

  // Show loading spinner while checking auth
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#1a1a2e] via-[#16213e] to-[#0f0f1e] flex items-center justify-center">
        <LoadingSpinner size="lg" message="Loading YourDaddy Assistant..." fullScreen={false} />
      </div>
    );
  }

  // Show auth screen if not authenticated
  if (!isAuthenticated) {
    return <Auth onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-primary text-white overflow-hidden relative">
        <ParticleBackground />
        
        {/* Offline/Backend Status Bar */}
        {(!isOnline || backendStatus === 'disconnected') && (
          <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-2 text-center text-sm">
            {!isOnline && "📡 No internet connection. Some features may not work."}
            {isOnline && backendStatus === 'disconnected' && "🔌 Backend server disconnected. Retrying..."}
          </div>
        )}
        
        <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} username={username} onLogout={handleLogout} />
        <main className={`ml-20 transition-all duration-500 ease-out ${(!isOnline || backendStatus === 'disconnected') ? 'mt-10' : ''}`}>
          <div className="container-custom">
            <ErrorBoundary>
              {renderSection()}
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
