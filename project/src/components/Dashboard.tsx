import { useState, useEffect } from 'react';
import { Activity, TrendingUp, Cpu, Wifi, HardDrive, CloudRain, Music2, Calendar } from 'lucide-react';
import { io } from 'socket.io-client';

interface SystemStats {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_mbps: number;
  network_speed_download: number;
  network_speed_upload: number;
  active_tasks: number;
}

interface WeatherData {
  temperature: string;
  description: string;
  humidity: string;
  wind_speed: string;
  icon?: string;
}

interface SpotifyData {
  is_playing: boolean;
  track_name: string;
  artist_name: string;
  progress?: number;
  duration?: number;
}

const Dashboard = () => {
  const [systemStats, setSystemStats] = useState<SystemStats>({
    cpu_usage: 0,
    memory_usage: 0,
    disk_usage: 0,
    network_mbps: 0,
    network_speed_download: 0,
    network_speed_upload: 0,
    active_tasks: 0
  });
  const [weather, setWeather] = useState<WeatherData>({
    temperature: 'Loading...',
    description: 'Fetching weather data...',
    humidity: '--',
    wind_speed: '--'
  });
  const [spotify, setSpotify] = useState<SpotifyData>({
    is_playing: false,
    track_name: 'Loading...',
    artist_name: 'Connecting to Spotify...'
  });
  const [activities, setActivities] = useState<Array<{time: string, action: string, status: string}>>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [loadingStates, setLoadingStates] = useState({
    weather: true,
    spotify: true,
    system: true,
    activities: true
  });
  const [errorStates, setErrorStates] = useState({
    weather: null as string | null,
    spotify: null as string | null,
    system: null as string | null,
    activities: null as string | null
  });

  useEffect(() => {
    // Initialize WebSocket connection
    const socketInstance = io();

    const fetchAllData = () => {
      fetchSystemStats();
      fetchWeather();
      fetchSpotify();
      fetchActivities();
    };

    socketInstance.on('connect', () => {
      console.log('Dashboard connected to backend');
      setIsConnected(true);
      // Request initial data immediately upon connection
      fetchAllData();
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });

    socketInstance.on('system_stats_update', (data: SystemStats) => {
      setSystemStats(data);
      setLoadingStates(prev => ({ ...prev, system: false }));
      setErrorStates(prev => ({ ...prev, system: null }));
    });

    // Request initial data on component mount
    fetchAllData();

    // Set up periodic data refresh
    const systemStatsInterval = setInterval(fetchSystemStats, 5000); // Every 5 seconds
    const weatherInterval = setInterval(fetchWeather, 300000); // Every 5 minutes
    const spotifyInterval = setInterval(fetchSpotify, 10000); // Every 10 seconds
    const activitiesInterval = setInterval(fetchActivities, 30000); // Every 30 seconds

    return () => {
      socketInstance.disconnect();
      clearInterval(systemStatsInterval);
      clearInterval(weatherInterval);
      clearInterval(spotifyInterval);
      clearInterval(activitiesInterval);
    };
  }, []); // Empty dependency array is correct here since all functions are defined locally

  // Remove this redundant function since it's now defined inside useEffect
  // const fetchAllData = () => {
  //   fetchSystemStats();
  //   fetchWeather();
  //   fetchSpotify();
  //   fetchActivities();
  // };

  const fetchSystemStats = async () => {
    try {
      setLoadingStates(prev => ({ ...prev, system: true }));
      const response = await fetch('/api/system/stats');
      if (response.ok) {
        const data = await response.json();
        setSystemStats(data);
        setErrorStates(prev => ({ ...prev, system: null }));
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch system stats:', error);
      setErrorStates(prev => ({ ...prev, system: 'Failed to load system stats' }));
    } finally {
      setLoadingStates(prev => ({ ...prev, system: false }));
    }
  };

  const fetchWeather = async () => {
    try {
      setLoadingStates(prev => ({ ...prev, weather: true }));
      const response = await fetch('/api/weather');
      if (response.ok) {
        const data = await response.json();
        setWeather(data);
        setErrorStates(prev => ({ ...prev, weather: null }));
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch weather:', error);
      setErrorStates(prev => ({ ...prev, weather: 'Weather service unavailable' }));
      setWeather({
        temperature: 'N/A',
        description: 'Weather unavailable',
        humidity: 'N/A',
        wind_speed: 'N/A'
      });
    } finally {
      setLoadingStates(prev => ({ ...prev, weather: false }));
    }
  };

  const fetchSpotify = async () => {
    try {
      setLoadingStates(prev => ({ ...prev, spotify: true }));
      const response = await fetch('/api/spotify/status');
      if (response.ok) {
        const data = await response.json();
        setSpotify(data);
        setErrorStates(prev => ({ ...prev, spotify: null }));
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch Spotify status:', error);
      setErrorStates(prev => ({ ...prev, spotify: 'Spotify not connected' }));
      setSpotify({
        is_playing: false,
        track_name: 'Spotify unavailable',
        artist_name: 'Connect your Spotify account'
      });
    } finally {
      setLoadingStates(prev => ({ ...prev, spotify: false }));
    }
  };

  const fetchActivities = async () => {
    try {
      setLoadingStates(prev => ({ ...prev, activities: true }));
      const response = await fetch('/api/activity');
      if (response.ok) {
        const data = await response.json();
        setActivities(data);
        setErrorStates(prev => ({ ...prev, activities: null }));
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch activities:', error);
      setErrorStates(prev => ({ ...prev, activities: 'Activity feed unavailable' }));
    } finally {
      setLoadingStates(prev => ({ ...prev, activities: false }));
    }
  };

  const controlSpotify = async (action: string) => {
    try {
      const response = await fetch('/api/spotify/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      });
      
      if (response.ok) {
        // Refresh Spotify status after control action
        setTimeout(fetchSpotify, 1000);
      }
    } catch (error) {
      console.error('Spotify control error:', error);
    }
  };

  const refreshData = () => {
    fetchSystemStats();
    fetchWeather();
    fetchSpotify();
    fetchActivities();
  };

  const formatNetworkSpeed = (mbps: number): string => {
    if (mbps < 1) return `${(mbps * 1000).toFixed(0)} Kbps`;
    if (mbps < 1000) return `${mbps.toFixed(1)} Mbps`;
    return `${(mbps / 1000).toFixed(1)} Gbps`;
  };

  const getNetworkPercentage = (downloadMbps: number, uploadMbps: number): number => {
    // Calculate percentage based on typical broadband speeds (100 Mbps as baseline)
    const avgSpeed = (downloadMbps + uploadMbps) / 2;
    return Math.min((avgSpeed / 100) * 100, 100);
  };

  const systemStatsConfig = [
    { label: 'CPU Usage', value: `${systemStats.cpu_usage.toFixed(1)}%`, icon: Cpu, color: 'from-[#00CEC9] to-[#6C5CE7]', percentage: systemStats.cpu_usage },
    { label: 'Memory', value: `${systemStats.memory_usage.toFixed(1)}%`, icon: HardDrive, color: 'from-[#6C5CE7] to-[#E17055]', percentage: systemStats.memory_usage },
    { label: 'Disk Usage', value: `${systemStats.disk_usage.toFixed(1)}%`, icon: HardDrive, color: 'from-[#00B894] to-[#00CEC9]', percentage: systemStats.disk_usage },
    { label: 'WiFi Speed', value: formatNetworkSpeed(systemStats.network_speed_download), icon: Wifi, color: 'from-[#E17055] to-[#FDCB6E]', percentage: getNetworkPercentage(systemStats.network_speed_download, systemStats.network_speed_upload), subtitle: `↑ ${formatNetworkSpeed(systemStats.network_speed_upload)}` },
    { label: 'Active Tasks', value: systemStats.active_tasks.toString(), icon: Activity, color: 'from-[#FDCB6E] to-[#00B894]', percentage: Math.min(systemStats.active_tasks / 100 * 100, 100) },
  ];

  return (
    <div className="min-h-screen py-8 animate-fade-in">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-gradient">Multi-Modal Dashboard</h1>
          <p className="text-[#DDDDDD]">Real-time system monitoring and activity feed</p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
            isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <button
            onClick={refreshData}
            className="px-4 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors flex items-center gap-2"
            title="Refresh all data"
          >
            <Wifi size={16} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        {systemStatsConfig.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="glass-strong p-6 rounded-2xl hover-lift">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                  <Icon size={24} />
                </div>
                <TrendingUp size={20} className="text-[#00B894]" />
              </div>
              <div className="text-3xl font-bold mb-1">{stat.value}</div>
              <div className="text-sm text-[#DDDDDD]">{stat.label}</div>
              {(stat as any).subtitle && (
                <div className="text-xs text-[#AAAAAA] mt-1">{(stat as any).subtitle}</div>
              )}
              <div className="mt-4 h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${stat.color} rounded-full transition-all duration-500`}
                  ref={(el) => {
                    if (el) {
                      el.style.width = `${stat.percentage}%`;
                    }
                  }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 glass-strong p-6 rounded-2xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Activity size={24} className="text-[#00CEC9]" />
            System Performance
          </h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[#DDDDDD]">CPU</span>
                <span className="text-[#00CEC9]">{systemStats.cpu_usage.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#00CEC9] to-[#6C5CE7] rounded-full transition-all duration-500"
                  ref={(el) => {
                    if (el) {
                      el.style.width = `${systemStats.cpu_usage}%`;
                    }
                  }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[#DDDDDD]">Memory</span>
                <span className="text-[#00CEC9]">{systemStats.memory_usage.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#6C5CE7] to-[#E17055] rounded-full transition-all duration-500"
                  ref={(el) => {
                    if (el) {
                      el.style.width = `${systemStats.memory_usage}%`;
                    }
                  }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[#DDDDDD]">Network Speed</span>
                <span className="text-[#00CEC9]">{formatNetworkSpeed(systemStats.network_speed_download)}</span>
              </div>
              <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#E17055] to-[#FDCB6E] rounded-full transition-all duration-500"
                  ref={(el) => {
                    if (el) {
                      el.style.width = `${getNetworkPercentage(systemStats.network_speed_download, systemStats.network_speed_upload)}%`;
                    }
                  }}
                ></div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[#DDDDDD]">Disk I/O</span>
                <span className="text-[#00CEC9]">{systemStats.disk_usage.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#00B894] to-[#00CEC9] rounded-full transition-all duration-500"
                  ref={(el) => {
                    if (el) {
                      el.style.width = `${systemStats.disk_usage}%`;
                    }
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-strong p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <CloudRain size={24} className="text-[#00CEC9]" />
              Weather
            </h2>
            {loadingStates.weather && (
              <div className="animate-spin w-5 h-5 border-2 border-[#00CEC9] border-t-transparent rounded-full"></div>
            )}
          </div>
          
          {errorStates.weather ? (
            <div className="text-center py-8 text-red-400">
              <p>{errorStates.weather}</p>
              <button 
                onClick={fetchWeather}
                className="mt-2 px-4 py-2 bg-[#00CEC9] rounded-lg hover:bg-[#00B5A8] transition-colors"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="text-center">
              <div className="text-6xl mb-4">{weather.icon || '☀️'}</div>
              <div className="text-4xl font-bold mb-2">{weather.temperature}</div>
              <div className="text-[#DDDDDD] mb-4">{weather.description}</div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-[#DDDDDD]">Humidity</div>
                  <div className="font-semibold">{weather.humidity}</div>
                </div>
                <div>
                  <div className="text-[#DDDDDD]">Wind</div>
                  <div className="font-semibold">{weather.wind_speed}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-strong p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Music2 size={24} className="text-[#6C5CE7]" />
              Now Playing
            </h2>
            {loadingStates.spotify && (
              <div className="animate-spin w-5 h-5 border-2 border-[#6C5CE7] border-t-transparent rounded-full"></div>
            )}
          </div>
          
          {errorStates.spotify ? (
            <div className="text-center py-8 text-red-400">
              <p>{errorStates.spotify}</p>
              <button 
                onClick={fetchSpotify}
                className="mt-2 px-4 py-2 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors"
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-4 mb-4">
                <div className={`w-20 h-20 rounded-xl flex-shrink-0 ${
                  spotify.is_playing 
                    ? 'bg-gradient-to-br from-[#6C5CE7] to-[#E17055] animate-pulse' 
                    : 'bg-gray-600'
                }`}></div>
                <div className="flex-1">
                  <div className="font-semibold text-lg mb-1">{spotify.track_name}</div>
                  <div className="text-[#DDDDDD] text-sm mb-3">{spotify.artist_name}</div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-[#6C5CE7] to-[#E17055] rounded-full transition-all duration-300"
                      ref={(el) => {
                        if (el) {
                          el.style.width = spotify.duration && spotify.progress 
                            ? `${(spotify.progress / spotify.duration) * 100}%` 
                            : '33%';
                        }
                      }}
                    ></div>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center justify-center gap-4">
                <button
                  onClick={() => controlSpotify('previous')}
                  className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
                  title="Previous track"
                >
                  ⏮️
                </button>
                <button
                  onClick={() => controlSpotify('play_pause')}
                  className="w-12 h-12 rounded-full bg-gradient-to-r from-[#6C5CE7] to-[#E17055] flex items-center justify-center hover:scale-105 transition-transform"
                  title={spotify.is_playing ? 'Pause' : 'Play'}
                >
                  {spotify.is_playing ? '⏸️' : '▶️'}
                </button>
                <button
                  onClick={() => controlSpotify('next')}
                  className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
                  title="Next track"
                >
                  ⏭️
                </button>
              </div>
            </>
          )}
        </div>

        <div className="glass-strong p-6 rounded-2xl">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Calendar size={24} className="text-[#00B894]" />
            Activity Feed
          </h2>
          <div className="space-y-4">
            {activities.map((activity, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  activity.status === 'success' ? 'bg-[#00B894]' : 'bg-[#00CEC9]'
                }`}></div>
                <div className="flex-1">
                  <div className="text-sm">{activity.action}</div>
                  <div className="text-xs text-[#DDDDDD]/70">{activity.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
