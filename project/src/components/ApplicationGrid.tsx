import { useState, useEffect } from 'react';
import { Search, Chrome, Mail, FileText, Image, Video, Code, Database, Terminal, Globe, Loader, RefreshCw, Grid, List, Filter } from 'lucide-react';
import { io, Socket } from 'socket.io-client';

interface Application {
  name: string;
  path: string;
  category?: string;
  usage?: number;
  icon?: string;
  description?: string;
  lastUsed?: string;
}

const ApplicationGrid = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [launchingApp, setLaunchingApp] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'name' | 'usage' | 'category'>('name');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const getIconForApp = (appName: string) => {
    const name = appName.toLowerCase();
    if (name.includes('chrome') || name.includes('browser')) return Chrome;
    if (name.includes('mail') || name.includes('outlook')) return Mail;
    if (name.includes('document') || name.includes('word') || name.includes('notepad')) return FileText;
    if (name.includes('photo') || name.includes('image') || name.includes('paint')) return Image;
    if (name.includes('video') || name.includes('vlc') || name.includes('media')) return Video;
    if (name.includes('code') || name.includes('studio') || name.includes('editor')) return Code;
    if (name.includes('database') || name.includes('sql')) return Database;
    if (name.includes('terminal') || name.includes('cmd') || name.includes('powershell')) return Terminal;
    if (name.includes('portal') || name.includes('web')) return Globe;
    return Code;
  };

  const getColorForCategory = (category: string) => {
    const colors = [
      'from-[#00CEC9] to-[#6C5CE7]',
      'from-[#6C5CE7] to-[#E17055]', 
      'from-[#00B894] to-[#00CEC9]',
      'from-[#E17055] to-[#00B894]',
      'from-[#00CEC9] to-[#00B894]',
      'from-[#6C5CE7] to-[#00CEC9]',
      'from-[#00B894] to-[#6C5CE7]',
      'from-[#E17055] to-[#6C5CE7]',
      'from-[#00CEC9] to-[#E17055]'
    ];
    return colors[Math.abs(category.split('').reduce((a, b) => a + b.charCodeAt(0), 0)) % colors.length];
  };

  useEffect(() => {
    // Initialize WebSocket connection
    const socketInstance = io();
    setSocket(socketInstance);

    socketInstance.on('connect', () => {
      console.log('ApplicationGrid connected to backend');
      fetchApplications();
    });

    socketInstance.on('disconnect', () => {
      console.log('ApplicationGrid disconnected from backend');
    });

    socketInstance.on('app_launched', (data) => {
      console.log('App launched:', data);
      setLaunchingApp(null);
    });

    // Initial fetch
    const fetchApplications = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch('/api/apps');
        if (response.ok) {
          const data = await response.json();
          // Enhance app data with better categorization
          const enhancedApps = data.map((app: Application) => ({
            ...app,
            category: app.category || categorizeApp(app.name),
            description: app.description || generateDescription(app.name),
            lastUsed: app.lastUsed || 'Unknown'
          }));
          setApplications(enhancedApps);
        } else {
          throw new Error(`HTTP ${response.status}: Failed to fetch applications`);
        }
      } catch (error) {
        console.error('Failed to fetch applications:', error);
        setError(error instanceof Error ? error.message : 'Failed to load applications');
        // Set fallback applications for demo
        setApplications(getFallbackApplications());
      } finally {
        setLoading(false);
      }
    };
    
    fetchApplications();

    return () => {
      socketInstance.disconnect();
    };
  }, []);

  const refreshApplications = async () => {
    setIsRefreshing(true);
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/apps');
      if (response.ok) {
        const data = await response.json();
        // Enhance app data with better categorization
        const enhancedApps = data.map((app: Application) => ({
          ...app,
          category: app.category || categorizeApp(app.name),
          description: app.description || generateDescription(app.name),
          lastUsed: app.lastUsed || 'Unknown'
        }));
        setApplications(enhancedApps);
      } else {
        throw new Error(`HTTP ${response.status}: Failed to fetch applications`);
      }
    } catch (error) {
      console.error('Failed to fetch applications:', error);
      setError(error instanceof Error ? error.message : 'Failed to load applications');
      // Set fallback applications for demo
      setApplications(getFallbackApplications());
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const categorizeApp = (appName: string): string => {
    const name = appName.toLowerCase();
    if (name.includes('chrome') || name.includes('firefox') || name.includes('browser')) return 'Web Browsers';
    if (name.includes('mail') || name.includes('outlook') || name.includes('thunderbird')) return 'Communication';
    if (name.includes('word') || name.includes('document') || name.includes('notepad') || name.includes('office')) return 'Productivity';
    if (name.includes('photo') || name.includes('image') || name.includes('paint') || name.includes('gimp')) return 'Graphics & Design';
    if (name.includes('video') || name.includes('vlc') || name.includes('media')) return 'Media & Entertainment';
    if (name.includes('code') || name.includes('studio') || name.includes('editor') || name.includes('ide')) return 'Development';
    if (name.includes('database') || name.includes('sql') || name.includes('mongo')) return 'Database';
    if (name.includes('terminal') || name.includes('cmd') || name.includes('powershell')) return 'System Tools';
    if (name.includes('game') || name.includes('steam')) return 'Games';
    return 'Other';
  };

  const generateDescription = (appName: string): string => {
    const descriptions: Record<string, string> = {
      'chrome': 'Fast and secure web browser by Google',
      'firefox': 'Open source web browser by Mozilla',
      'outlook': 'Email and calendar application by Microsoft',
      'notepad': 'Simple text editor for Windows',
      'code': 'Lightweight code editor by Microsoft',
      'vlc': 'Versatile media player for all formats'
    };
    
    const key = Object.keys(descriptions).find(key => 
      appName.toLowerCase().includes(key)
    );
    
    return key ? descriptions[key] : `${appName} application`;
  };

  const getFallbackApplications = (): Application[] => [
    { name: 'Google Chrome', path: 'chrome.exe', category: 'Web Browsers', usage: 89, description: 'Fast and secure web browser' },
    { name: 'Microsoft Outlook', path: 'outlook.exe', category: 'Communication', usage: 76, description: 'Email and calendar application' },
    { name: 'Microsoft Word', path: 'word.exe', category: 'Productivity', usage: 65, description: 'Document editing software' },
    { name: 'Windows Photos', path: 'photos.exe', category: 'Graphics & Design', usage: 52, description: 'Photo viewing and editing' },
    { name: 'VLC Media Player', path: 'vlc.exe', category: 'Media & Entertainment', usage: 43, description: 'Versatile media player' },
    { name: 'Visual Studio Code', path: 'code.exe', category: 'Development', usage: 92, description: 'Lightweight code editor' },
    { name: 'pgAdmin', path: 'pgadmin.exe', category: 'Database', usage: 67, description: 'PostgreSQL administration tool' },
    { name: 'Windows Terminal', path: 'cmd.exe', category: 'System Tools', usage: 78, description: 'Command line interface' },
  ];

  const launchApplication = async (app: Application) => {
    setLaunchingApp(app.name);
    setError(null);
    
    try {
      // Try WebSocket first for real-time feedback
      if (socket) {
        socket.emit('launch_app', { app_name: app.name, app_path: app.path });
      }
      
      // Also use REST API as backup
      const response = await fetch('/api/apps/launch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ app_name: app.name, app_path: app.path }),
      });
      
      const result = await response.json();
      if (result.success) {
        console.log(`✅ Successfully launched ${app.name}`);
        // Update usage statistics
        setApplications(prev => prev.map(a => 
          a.name === app.name 
            ? { ...a, usage: (a.usage || 0) + 1, lastUsed: new Date().toLocaleString() }
            : a
        ));
      } else {
        throw new Error(result.error || 'Unknown launch error');
      }
    } catch (error) {
      console.error('❌ Failed to launch app:', error);
      setError(`Failed to launch ${app.name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setTimeout(() => setLaunchingApp(null), 1000);
    }
  };

  // Computed filtered apps
  const filteredApps = applications.filter(app => {
    const matchesSearch = app.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (app.description && app.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = selectedCategory === 'All' || app.category === selectedCategory;
    return matchesSearch && matchesCategory;
  }).sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name);
      case 'usage':
        return (b.usage || 0) - (a.usage || 0);
      case 'category':
        return (a.category || '').localeCompare(b.category || '');
      default:
        return 0;
    }
  });

  const categories = ['All', ...Array.from(new Set(applications.map(app => app.category || 'Unknown')))];

  return (
    <div className="min-h-screen py-8 animate-fade-in">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-gradient">Application Grid</h1>
          <p className="text-[#DDDDDD]">Quick access to all your applications</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={refreshApplications}
            disabled={isRefreshing}
            className="px-4 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors flex items-center gap-2 disabled:opacity-50"
            title="Refresh applications"
          >
            <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
          <div className="flex items-center gap-2 bg-white/10 rounded-lg p-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded ${viewMode === 'grid' ? 'bg-[#6C5CE7]' : 'hover:bg-white/10'}`}
              title="Grid view"
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded ${viewMode === 'list' ? 'bg-[#6C5CE7]' : 'hover:bg-white/10'}`}
              title="List view"
            >
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400">
          {error}
          <button 
            onClick={() => setError(null)}
            className="float-right text-sm hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Search and Filters */}
      <div className="glass-strong p-4 rounded-2xl mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search Bar */}
          <div className="flex items-center gap-3 flex-1">
            <Search size={20} className="text-[#00CEC9]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search applications, categories, or descriptions..."
              className="flex-1 bg-transparent text-white outline-none placeholder-[#DDDDDD]/50"
            />
          </div>
          
          {/* Category Filter */}
          <div className="flex items-center gap-3">
            <Filter size={16} className="text-[#DDDDDD]" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-white/10 text-white rounded-lg px-3 py-2 outline-none"
              aria-label="Filter by category"
            >
              {categories.map(category => (
                <option key={category} value={category} className="bg-[#0A0E27]">
                  {category} {category !== 'All' && `(${applications.filter(app => app.category === category).length})`}
                </option>
              ))}
            </select>
          </div>
          
          {/* Sort Options */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#DDDDDD]">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'usage' | 'category')}
              className="bg-white/10 text-white rounded-lg px-3 py-2 outline-none"
              aria-label="Sort applications by"
            >
              <option value="name" className="bg-[#0A0E27]">Name</option>
              <option value="usage" className="bg-[#0A0E27]">Usage</option>
              <option value="category" className="bg-[#0A0E27]">Category</option>
            </select>
          </div>
        </div>
        
        {/* Stats */}
        <div className="mt-4 flex items-center justify-between text-sm text-[#DDDDDD]">
          <span>
            Showing {filteredApps.length} of {applications.length} applications
            {selectedCategory !== 'All' && ` in ${selectedCategory}`}
          </span>
          <span>
            Total categories: {categories.length - 1}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader className="animate-spin" size={48} />
          <span className="ml-4 text-xl">Loading applications...</span>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {filteredApps.map((app, index) => {
              const Icon = getIconForApp(app.name);
              const color = getColorForCategory(app.category || 'Unknown');
              const isLaunching = launchingApp === app.name;
              
              return (
                <div
                  key={index}
                  onClick={() => launchApplication(app)}
                  className="glass-strong p-6 rounded-2xl hover-lift cursor-pointer group relative overflow-hidden transition-all duration-300"
                >
                  {isLaunching && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-2xl z-10">
                      <Loader className="animate-spin text-[#00CEC9]" size={24} />
                    </div>
                  )}
                  
                  <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform ${isLaunching ? 'opacity-50' : ''}`}>
                    <Icon size={32} />
                  </div>
                  <div className="font-semibold mb-1">{app.name}</div>
                  <div className="text-xs text-[#DDDDDD] mb-3">{app.category || 'Application'}</div>

                  {app.usage && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[#DDDDDD]">Usage</span>
                        <span className="text-[#00CEC9]">{app.usage}%</span>
                      </div>
                      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-500`}
                          data-width={app.usage}
                          ref={(el) => {
                            if (el && app.usage) {
                              el.style.width = `${app.usage}%`;
                            }
                          }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {filteredApps.length === 0 && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4 opacity-50">🔍</div>
              <p className="text-[#DDDDDD]">No applications found</p>
            </div>
          )}

          <div className="mt-12 glass-strong p-6 rounded-2xl">
            <h2 className="text-2xl font-bold mb-6">Usage Analytics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <div className="text-3xl font-bold mb-1 text-[#00CEC9]">{applications.length}</div>
                <div className="text-sm text-[#DDDDDD]">Total Applications</div>
              </div>
              <div>
                <div className="text-3xl font-bold mb-1 text-[#6C5CE7]">
                  {applications.filter(app => app.usage && app.usage > 50).length}
                </div>
                <div className="text-sm text-[#DDDDDD]">Frequently Used</div>
              </div>
              <div>
                <div className="text-3xl font-bold mb-1 text-[#00B894]">{filteredApps.length}</div>
                <div className="text-sm text-[#DDDDDD]">Showing Results</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ApplicationGrid;
