import { motion } from 'framer-motion';
import { ExternalLink, Star, Clock, RefreshCw } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { apiUrl } from '../../lib/api';

interface DiscoveredApp {
  name: string;
  path: string;
  category: string;
  usage: number;
  description: string;
}

const AppsDetail = () => {
  const { socket } = useDashboard();
  const [apps, setApps] = useState<DiscoveredApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Fetch apps from backend
  const fetchApps = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(apiUrl('/api/apps'));
      if (!response.ok) {
        throw new Error(`Failed to fetch apps: ${response.statusText}`);
      }
      const data = await response.json();
      console.log('Fetched apps data:', data);
      console.log('Data type:', typeof data);
      console.log('Is array?', Array.isArray(data));
      
      // Ensure data is always an array
      if (Array.isArray(data)) {
        setApps(data);
        console.log(`Successfully loaded ${data.length} apps`);
      } else if (data && typeof data === 'object' && data.apps) {
        // Handle case where apps are nested in an object
        const appsArray = Array.isArray(data.apps) ? data.apps : [];
        setApps(appsArray);
        console.log(`Successfully loaded ${appsArray.length} apps from nested object`);
      } else if (data && typeof data === 'object' && data.error) {
        // Backend returned an error
        throw new Error(data.error);
      } else {
        console.error('Unexpected data format:', data);
        setError('Received unexpected data format from server');
        setApps([]);
      }
    } catch (_err) {
      console.error('Error fetching apps:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load apps';
      setError(`${errorMessage}. Is the backend running?`);
      setApps([]);
    } finally {
      setLoading(false);
    }
  };

  // Refresh apps list
  const refreshApps = async () => {
    setLoading(true);
    try {
      const response = await fetch(apiUrl('/api/apps/refresh'), {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to refresh apps');
      }
      const data = await response.json();
      console.log('Refresh response:', data);
      
      if (data.success && data.apps && Array.isArray(data.apps)) {
        setApps(data.apps);
      } else if (data.success) {
        // Fallback to fetching apps again
        await fetchApps();
      }
    } catch (_err) {
      console.error('Error refreshing apps:', err);
      setError('Failed to refresh apps');
    } finally {
      setLoading(false);
    }
  };

  // Launch an app
  const launchApp = async (appName: string) => {
    if (socket && socket.connected) {
      // FIX: Backend reads data.get('command'), not data.get('text')
      socket.emit('command', { command: `open ${appName}`, source: 'apps_panel' });
    } else {
      // Fallback to REST API
      try {
        const { apiUrl } = await import('../../lib/api');
        await fetch(apiUrl('/api/apps/launch'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ app_name: appName }),
        });
      } catch (_err) {
        console.error('Failed to launch app:', err);
      }
    }
  };


  // Load apps on mount
  useEffect(() => {
    if (!isInitialized) {
      setIsInitialized(true);
      fetchApps();
    }
  }, [isInitialized]);

  // Listen for apps_discovered WebSocket event
  useEffect(() => {
    if (socket) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const handleAppsDiscovered = (data: any) => {
        console.log('🎉 Apps discovered event received:', data);
        // Auto-refresh app list when backend completes scan
        fetchApps();
      };

      socket.on('apps_discovered', handleAppsDiscovered);

      return () => {
        socket.off('apps_discovered', handleAppsDiscovered);
      };
    }
  }, [socket]);

  // Category icon mapping
  const getCategoryIcon = (category: string): string => {
    const iconMap: { [key: string]: string } = {
      'Browser': '🌐',
      'Communication': '✉️',
      'Productivity': '📝',
      'Media': '🎵',
      'Development': '💻',
      'System Tools': '⚙️',
      'Games': '🎮',
      'Graphics': '🎨',
      'Security': '🔒',
      'Education': '📚',
      'Other': '📦',
    };
    return iconMap[category] || '📦';
  };

  // Category color mapping
  const _getCategoryColor = (category: string): string => {
    const colorMap: { [key: string]: string } = {
      'Browser': '#3B82F6',
      'Communication': '#06B6D4',
      'Productivity': '#10B981',
      'Media': '#EF4444',
      'Development': '#8B5CF6',
      'System Tools': '#F59E0B',
      'Games': '#EC4899',
      'Graphics': '#14B8A6',
      'Security': '#F97316',
      'Education': '#6366F1',
      'Other': '#9CA3AF',
    };
    return colorMap[category] || '#9CA3AF';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Integrated Applications</h3>
          <p className="text-[#9CA3AF]">
            {loading ? 'Loading apps...' : `${apps.length} applications discovered on your system`}
          </p>
        </div>
        <button
          onClick={refreshApps}
          disabled={loading}
          className="px-4 py-2 bg-[#3B82F6]/20 text-[#3B82F6] rounded-lg hover:bg-[#3B82F6]/30 transition-colors font-medium flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {loading && apps.length === 0 ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#3B82F6]"></div>
          <p className="text-[#9CA3AF] mt-4">Loading applications...</p>
        </div>
      ) : apps.length === 0 ? (
        <div className="text-center py-12 bg-[#1F2228] border border-[#2A2D35] rounded-lg">
          <p className="text-[#9CA3AF] text-lg">No applications found</p>
          <p className="text-[#6B7280] text-sm mt-2">Try refreshing the app list</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.isArray(apps) && apps.map((app, index) => (
            <motion.div
              key={app.name + index}
              className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-5 hover:border-[#3B82F6]/50 transition-all cursor-pointer group"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.02 }}
              whileHover={{ scale: 1.03 }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="text-4xl">{getCategoryIcon(app.category)}</div>
                <div className="px-2 py-1 rounded-full text-xs font-medium bg-[#3B82F6]/20 text-[#3B82F6]">
                  {app.category}
                </div>
              </div>

              <h4 className="text-lg font-semibold text-white mb-2 group-hover:text-[#3B82F6] transition-colors truncate" title={app.name}>
                {app.name}
              </h4>

              <p className="text-sm text-[#9CA3AF] mb-3 line-clamp-2" title={app.description}>
                {app.description}
              </p>

              <div className="flex items-center gap-2 text-sm text-[#6B7280] mb-4">
                <Clock className="w-4 h-4" />
                <span>Used {app.usage} times</span>
              </div>

              <div className="flex gap-2">
                <button 
                  onClick={() => launchApp(app.name)}
                  className="flex-1 px-3 py-2 bg-[#3B82F6]/20 text-[#3B82F6] rounded hover:bg-[#3B82F6]/30 transition-colors text-sm font-medium"
                >
                  Open
                </button>
                <button 
                  className="px-3 py-2 bg-[#2A2D35] text-[#9CA3AF] rounded hover:bg-[#3A3D45] transition-colors" 
                  aria-label="Add to favorites"
                  title="Add to favorites"
                >
                  <Star className="w-4 h-4" />
                </button>
                <button 
                  className="px-3 py-2 bg-[#2A2D35] text-[#9CA3AF] rounded hover:bg-[#3A3D45] transition-colors" 
                  aria-label="Open in new window"
                  title="App details"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <div className="bg-[#1F2228] border border-[#2A2D35] rounded-lg p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Quick Actions</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button 
            onClick={() => fetchApps()}
            className="px-4 py-3 bg-[#3B82F6]/20 text-[#3B82F6] rounded-lg hover:bg-[#3B82F6]/30 transition-colors font-medium"
          >
            Reload Apps
          </button>
          <button 
            onClick={refreshApps}
            disabled={loading}
            className="px-4 py-3 bg-[#10B981]/20 text-[#10B981] rounded-lg hover:bg-[#10B981]/30 transition-colors font-medium disabled:opacity-50"
          >
            Rescan System
          </button>
          <button 
            onClick={() => {
              const mostUsed = [...apps].sort((a, b) => b.usage - a.usage).slice(0, 10);
              setApps(mostUsed);
            }}
            className="px-4 py-3 bg-[#F59E0B]/20 text-[#F59E0B] rounded-lg hover:bg-[#F59E0B]/30 transition-colors font-medium"
          >
            Most Used
          </button>
          <button 
            onClick={() => fetchApps()}
            className="px-4 py-3 bg-[#8B5CF6]/20 text-[#8B5CF6] rounded-lg hover:bg-[#8B5CF6]/30 transition-colors font-medium"
          >
            Show All
          </button>
        </div>
      </div>
    </div>
  );
};

export default AppsDetail;
