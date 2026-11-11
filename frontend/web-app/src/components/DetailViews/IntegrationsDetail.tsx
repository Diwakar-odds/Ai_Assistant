import { motion } from 'framer-motion';
import { Calendar, Mail, Music, MessageCircle, Github, Link, Unlink, ExternalLink, RefreshCw, Key, Server, X } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useDashboard } from '../../contexts/DashboardContext';
import { API_ENDPOINTS, apiFetchJson } from '../../lib/api';

type IntegrationStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

interface Integration {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: any;
  color: string;
  status: IntegrationStatus;
  lastSync?: string;
  error?: string;
  tools?: any[];
  isEnabled?: boolean;
}

const initialIntegrations: Integration[] = [
  {
    id: 'google_calendar',
    name: 'Google Calendar',
    description: 'Sync your schedule and let the AI manage your meetings.',
    category: 'Productivity',
    icon: Calendar,
    color: '#4285F4',
    status: 'disconnected',
  },
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Read and draft emails automatically with AI assistance.',
    category: 'Communication',
    icon: Mail,
    color: '#EA4335',
    status: 'disconnected',
  },
  {
    id: 'spotify',
    name: 'Spotify',
    description: 'Control your music playback and discover new tracks.',
    category: 'Media',
    icon: Music,
    color: '#1DB954',
    status: 'disconnected',
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    description: 'Send and receive messages hands-free.',
    category: 'Communication',
    icon: MessageCircle,
    color: '#25D366',
    status: 'disconnected',
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Manage PRs, issues, and repositories directly.',
    category: 'Development',
    icon: Github,
    color: '#F0F6FC',
    status: 'disconnected',
  },
];

const IntegrationsDetail = () => {
  const { setSelectedView } = useDashboard();
  const [integrations, setIntegrations] = useState<Integration[]>(initialIntegrations);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'info' | 'error' | 'success'; text: string } | null>(null);
  const [selectedToolsIntegration, setSelectedToolsIntegration] = useState<Integration | null>(null);
  const [activeTab, setActiveTab] = useState<
    'all' | 'connected' | 'productivity' | 'communication' | 'media' | 'development' | 'mcp'
  >('all');

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const [statusRes, mcpRes] = await Promise.all([
        apiFetchJson<any>(API_ENDPOINTS.integrations.status),
        apiFetchJson<any>(API_ENDPOINTS.integrations.mcp),
      ]);

      const data = statusRes.ok && statusRes.data ? statusRes.data : null;
      const mcpServers: any[] =
        mcpRes.ok && mcpRes.data?.success && Array.isArray(mcpRes.data.servers)
          ? mcpRes.data.servers
          : [];

      setIntegrations((prev) => {
        const updated = prev.map((integration) => {
          if (data?.success && data.integrations?.[integration.id]) {
            const backendData = data.integrations[integration.id];
            const st = (backendData.status || 'disconnected') as IntegrationStatus;
            return {
              ...integration,
              status: st,
              lastSync: st === 'connected' ? backendData.lastSync || 'Synced' : undefined,
            };
          }
          return integration;
        });

        mcpServers.forEach((server) => {
          const existingIdx = updated.findIndex((i) => i.id === server.id);
          const desc =
            (server.description || 'MCP Integration') +
            (server.tools?.length > 0 ? ` (${server.tools.length} tools available)` : '');

          if (existingIdx >= 0) {
            updated[existingIdx] = {
              ...updated[existingIdx],
              status: server.status || 'disconnected',
              name: server.name || updated[existingIdx].name,
              description: desc,
              tools: server.tools,
              isEnabled: server.isEnabled,
            };
          } else {
            updated.push({
              id: server.id,
              name: server.name || server.id,
              description: desc,
              category: server.category || 'MCP',
              icon: Server,
              color: '#8B5CF6',
              status: server.status || 'disconnected',
              tools: server.tools,
              isEnabled: server.isEnabled,
            });
          }
        });

        return updated;
      });
    } catch (e) {
      console.error('Failed to fetch integration status', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleConnect = async (id: string) => {
    setFeedback(null);
    setIntegrations((prev) =>
      prev.map((init) => (init.id === id ? { ...init, status: 'connecting' } : init))
    );

    const res = await apiFetchJson<any>(API_ENDPOINTS.integrations.connect, {
      method: 'POST',
      body: JSON.stringify({ integration_id: id }),
    });

    if (res.ok && res.data?.success) {
      setFeedback({ type: 'success', text: `Connected ${id} successfully.` });
      fetchStatus();
    } else {
      setFeedback({
        type: 'error',
        text: `Failed to connect ${id}: ${res.error || res.data?.error || 'Backend integration route unavailable'}`,
      });
      setIntegrations((prev) =>
        prev.map((init) => (init.id === id ? { ...init, status: 'disconnected' } : init))
      );
    }
  };

  const handleDisconnect = async (id: string) => {
    setFeedback(null);
    const res = await apiFetchJson<any>(API_ENDPOINTS.integrations.disconnect, {
      method: 'POST',
      body: JSON.stringify({ integration_id: id }),
    });

    setIntegrations((prev) =>
      prev.map((init) =>
        init.id === id ? { ...init, status: 'disconnected', lastSync: undefined } : init
      )
    );

    if (res.ok && res.data?.success) {
      setFeedback({ type: 'info', text: `Disconnected ${id}.` });
    } else {
      setFeedback({
        type: 'info',
        text: `Disconnected ${id} locally${res.error ? ` (${res.error})` : ''}.`,
      });
    }
  };

  const filteredIntegrations = integrations.filter((integration) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'connected') return integration.status === 'connected';
    return integration.category.toLowerCase() === activeTab;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 mb-2">
            Web Services & APIs
          </h3>
          <p className="text-[#9CA3AF] max-w-lg">
            Connect third-party apps and MCP servers to grant your AI assistant new capabilities.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => fetchStatus()}
            disabled={loading}
            className="px-4 py-2 bg-[#2A2D35]/50 text-white rounded-lg hover:bg-[#3B82F6]/20 transition-all duration-300 font-medium flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setSelectedView('settings')}
            className="px-4 py-2 bg-gradient-to-r from-[#3B82F6]/20 to-[#8B5CF6]/20 text-white rounded-lg hover:from-[#3B82F6]/30 hover:to-[#8B5CF6]/30 border border-[#3B82F6]/30 transition-all duration-300 font-medium flex items-center gap-2 shadow-[0_0_15px_rgba(59,130,246,0.1)]"
          >
            <Key className="w-4 h-4 text-[#3B82F6]" />
            Manage API Keys
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`flex items-center justify-between gap-2 px-4 py-2.5 rounded-lg border text-xs ${
            feedback.type === 'error'
              ? 'bg-red-500/10 border-red-500/30 text-red-300'
              : feedback.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-blue-500/10 border-blue-500/30 text-blue-200'
          }`}
        >
          <span>{feedback.text}</span>
          <button type="button" onClick={() => setFeedback(null)} aria-label="Dismiss message">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
        {(['all', 'connected', 'productivity', 'communication', 'media', 'development', 'mcp'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 whitespace-nowrap ${
              activeTab === tab
                ? 'bg-white text-black shadow-lg scale-105'
                : 'bg-[#1A1D24] text-[#9CA3AF] hover:bg-[#2A2D35] hover:text-white border border-[#2A2D35]'
            }`}
          >
            {tab === 'mcp' ? 'MCP' : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredIntegrations.map((integration, index) => (
          <motion.div
            key={integration.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06, duration: 0.3 }}
            whileHover={{ y: -4 }}
            className={`relative overflow-hidden bg-[#16181D] rounded-xl border border-[#2A2D35] p-6 group transition-all duration-300 hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)] ${
              integration.status === 'connected' ? 'border-[#10B981]/30 bg-gradient-to-br from-[#16181D] to-[#10B981]/5' : ''
            }`}
          >
            {/* Top row: Icon & Status Badge */}
            <div className="flex justify-between items-start mb-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110 shadow-lg"
                style={{ backgroundColor: `${integration.color}15`, color: integration.color, border: `1px solid ${integration.color}30` }}
              >
                <integration.icon className="w-6 h-6" />
              </div>

              {integration.status === 'connected' && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#10B981]/15 border border-[#10B981]/30 text-[#10B981] text-xs font-semibold">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></div>
                  Connected
                </div>
              )}
              {integration.status === 'connecting' && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/30 text-[#F59E0B] text-xs font-semibold">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Connecting
                </div>
              )}
            </div>

            {/* Content info */}
            <h4 className="text-xl font-semibold text-white mb-2">{integration.name}</h4>
            <p className="text-[#8B949E] text-sm line-clamp-2 h-10 mb-6">
              {integration.description}
            </p>

            {/* Bottom Actions */}
            <div className="mt-auto flex items-center justify-between pt-4 border-t border-[#2A2D35]">
              {integration.status === 'connected' ? (
                <>
                  <span className="text-xs text-[#6B7280]">
                    {integration.lastSync ? `Sync: ${integration.lastSync}` : 'Active'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedToolsIntegration(integration)}
                      title="Inspect integration details"
                      className="p-2 text-[#9CA3AF] hover:text-white hover:bg-[#2A2D35] rounded-lg transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDisconnect(integration.id)}
                      className="p-2 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded-lg transition-colors"
                      title="Disconnect"
                    >
                      <Unlink className="w-4 h-4" />
                    </button>
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => handleConnect(integration.id)}
                  disabled={integration.status === 'connecting'}
                  className="w-full py-2.5 bg-white text-black font-semibold rounded-lg hover:bg-gray-200 active:scale-[0.98] transition-all flex justify-center items-center gap-2"
                >
                  {integration.status === 'connecting' ? (
                    'Connecting...'
                  ) : (
                    <>
                      <Link className="w-4 h-4" />
                      Connect {integration.name}
                    </>
                  )}
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {selectedToolsIntegration && (
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h5 className="text-sm font-semibold text-white">
              {selectedToolsIntegration.name} — Integration Details
            </h5>
            <button
              type="button"
              onClick={() => setSelectedToolsIntegration(null)}
              className="text-[#9CA3AF] hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-[#9CA3AF]">{selectedToolsIntegration.description}</p>
          {selectedToolsIntegration.tools && selectedToolsIntegration.tools.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {selectedToolsIntegration.tools.map((t: any, i: number) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-[#0D1017] border border-[#2A2D35] text-cyan-300">
                  {typeof t === 'string' ? t : t.name || 'tool'}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {filteredIntegrations.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-[#2A2D35] rounded-xl bg-[#16181D]/50">
          <div className="w-16 h-16 rounded-full bg-[#1A1D24] border border-[#2A2D35] flex items-center justify-center mb-4">
            <Link className="w-6 h-6 text-[#6B7280]" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No integrations found</h3>
          <p className="text-[#9CA3AF] max-w-sm">
            We couldn't find any integrations matching this category. Check back later for more supported apps.
          </p>
        </div>
      )}
    </div>
  );
};

export default IntegrationsDetail;
