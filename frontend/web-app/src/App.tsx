import { motion } from 'framer-motion';
import { DashboardProvider, useDashboard } from './contexts/DashboardContext';
import QuickOptions from './components/LeftColumn/QuickOptions';
import CameraFeed from './components/LeftColumn/CameraFeed';
import AILearningDashboard from './components/LeftColumn/AILearningDashboard';
import StatusBar from './components/CenterColumn/StatusBar';
import VoiceButton from './components/CenterColumn/VoiceButton';
import CommandInput from './components/CenterColumn/CommandInput';
import TaskStatus from './components/CenterColumn/TaskStatus';
import ConversationTracker from './components/RightColumn/ConversationTracker';
import DetailView from './components/DetailView';
import DashboardDetail from './components/DetailViews/DashboardDetail';
import AppsDetail from './components/DetailViews/AppsDetail';
import IntegrationsDetail from './components/DetailViews/IntegrationsDetail';
import ChatDetail from './components/DetailViews/ChatDetail';
import VoiceDetail from './components/DetailViews/VoiceDetail';
import SettingsDetail from './components/DetailViews/SettingsDetail';
import AILearningDetail from './components/DetailViews/AILearningDetail';
import { PWAInstallPrompt } from './components/PWAInstallPrompt';
import { OfflineIndicator } from './components/OfflineIndicator';
import OnboardingModal from './components/OnboardingModal';
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

function AppContent() {
  const { selectedView, closeDetailView } = useDashboard();
  const [activeTab, setActiveTab] = useState<'main' | 'options' | 'stats'>('main');
  const [showOptions, setShowOptions] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [hasCheckedOnboarding, setHasCheckedOnboarding] = useState(false);

  useEffect(() => {
    fetch('/api/settings/all')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.settings && data.settings.onboarded === false) {
          setShowOnboarding(true);
        }
        setHasCheckedOnboarding(true);
      })
      .catch(() => setHasCheckedOnboarding(true));
  }, []);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    // Start tour
    const tour = driver({
      showProgress: true,
      steps: [
        { element: '#command-input', popover: { title: 'Chat Interface', description: 'Here is where you chat with your assistant.' } },
        { element: '#voice-button', popover: { title: 'Voice Control', description: 'Click here to use hands-free voice commands.' } },
      ]
    });
    setTimeout(() => tour.drive(), 500);
  };

  const getDetailContent = () => {
    switch (selectedView) {
      case 'dashboard':
        return { title: 'System Dashboard', content: <DashboardDetail /> };
      case 'apps':
        return { title: 'Integrated Applications', content: <AppsDetail /> };
      case 'integrations':
        return { title: 'Web Services & APIs', content: <IntegrationsDetail /> };
      case 'chat':
        return { title: 'Chat History', content: <ChatDetail /> };
      case 'voice':
        return { title: 'Voice Control', content: <VoiceDetail /> };
      case 'settings':
        return { title: 'Settings', content: <SettingsDetail /> };
      case 'ai-learning':
      case 'database':
      case 'systems':
      case 'conversations':
        return { title: 'AI Learning Dashboard', content: <AILearningDetail /> };
      default:
        return null;
    }
  };

  const detailContent = getDetailContent();
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const columnVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: 'easeOut' }
    }
  };

  return (
    <div className="h-screen bg-deep-space text-gray-100 overflow-hidden flex flex-col">
      {/* Offline Indicator */}
      <OfflineIndicator />
      
      {showOnboarding && <OnboardingModal onComplete={handleOnboardingComplete} />}

      <motion.div
        className="flex-1 px-2 sm:px-3 md:px-4 py-2 sm:py-3 md:py-4 max-w-[2000px] mx-auto w-full overflow-hidden flex flex-col"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Mobile Tabs - Show on small screens */}
        <div className="md:hidden flex gap-2 mb-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('main')}
            className={`px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${activeTab === 'main'
                ? 'bg-[#3B82F6] text-white'
                : 'bg-[#16181D] text-[#9CA3AF] border border-[#1F2228]'
              }`}
          >
            Voice Control
          </button>
          <button
            onClick={() => setActiveTab('options')}
            className={`px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${activeTab === 'options'
                ? 'bg-[#3B82F6] text-white'
                : 'bg-[#16181D] text-[#9CA3AF] border border-[#1F2228]'
              }`}
          >
            Options
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${activeTab === 'stats'
                ? 'bg-[#3B82F6] text-white'
                : 'bg-[#16181D] text-[#9CA3AF] border border-[#1F2228]'
              }`}
          >
            Conversation
          </button>
        </div>

        {/* Mobile Layout - Stack vertically */}
        <div className="md:hidden flex-1 overflow-y-auto space-y-3">
          {/* Main Voice Control - Always visible on 'main' tab */}
          {activeTab === 'main' && (
            <motion.div
              className="flex flex-col gap-2 min-h-0"
              variants={columnVariants}
            >
              <StatusBar />
              <div className="flex-1 flex items-center justify-center min-h-[300px] overflow-visible py-4">
                <VoiceButton />
              </div>
              <CommandInput />
              <TaskStatus />
            </motion.div>
          )}

          {/* Options Tab */}
          {activeTab === 'options' && (
            <motion.div
              className="flex flex-col gap-3"
              variants={columnVariants}
            >
              <QuickOptions />
              <CameraFeed />
              <AILearningDashboard />
            </motion.div>
          )}

          {/* Stats Tab */}
          {activeTab === 'stats' && (
            <motion.div
              className="flex flex-col gap-3 flex-1 min-h-0"
              variants={columnVariants}
            >
              <ConversationTracker />
            </motion.div>
          )}
        </div>

        {/* Desktop Layout - 3 columns on large screens */}
        <div className="hidden md:grid grid-cols-12 gap-2 lg:gap-4 flex-1 overflow-hidden min-h-0">
          <motion.div
            className="col-span-3 lg:col-span-3 flex flex-col gap-3 overflow-y-auto min-h-0 pr-1"
            variants={columnVariants}
          >
            <QuickOptions />
            <CameraFeed />
            <AILearningDashboard />
          </motion.div>

          <motion.div
            className="col-span-5 lg:col-span-6 flex flex-col gap-1.5 overflow-hidden min-h-0 px-1"
            variants={columnVariants}
          >
            <StatusBar />
            <div className="flex-1 flex items-center justify-center min-h-0 overflow-visible py-2">
              <VoiceButton />
            </div>
            <CommandInput />
            <TaskStatus />
          </motion.div>

          <motion.div
            className="col-span-4 lg:col-span-3 flex flex-col gap-3 overflow-hidden min-h-0 pl-1"
            variants={columnVariants}
          >
            <ConversationTracker />
          </motion.div>
        </div>
      </motion.div>

      {/* Detail View Modal */}
      {detailContent && (
        <DetailView
          isOpen={!!selectedView}
          onClose={closeDetailView}
          title={detailContent.title}
        >
          {detailContent.content}
        </DetailView>
      )}

      {/* PWA Install Prompt */}
      <PWAInstallPrompt />
    </div>
  );
}

function App() {
  return (
    <DashboardProvider>
      <AppContent />
    </DashboardProvider>
  );
}

export default App;
