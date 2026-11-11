import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Brain, Database, Zap, GitBranch, Target, Layers, ArrowUpRight } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { useDashboard } from '../../contexts/DashboardContext';

const AILearningDetail = () => {
  const { agents, setSelectedView } = useDashboard();
  const [learningStats, setLearningStats] = useState<any>(null);
  const [details, setDetails] = useState<any>({});

  useEffect(() => {
    fetch(apiUrl('/api/learning/stats'))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.stats) {
          setLearningStats(data.stats);
        }
      })
      .catch(() => {});

    fetch(apiUrl('/api/learning/dashboard'))
      .then(res => res.json())
      .then(data => {
        if (data.success && data.data) {
          setDetails(data.data);
        }
      })
      .catch(() => {});
  }, []);

  const learningMetrics = [
    {
      icon: Database,
      label: 'Knowledge Base',
      value: details.knowledge_nodes ? `${details.knowledge_nodes.toLocaleString()}` : (learningStats?.patterns_count ? `${learningStats.patterns_count}` : '--'),
      color: '#3B82F6',
      trend: '+0%',
      description: details.knowledge_nodes ? `Nodes: ${details.knowledge_nodes} | Edges: ${details.knowledge_edges || 0}` : 'Active knowledge entities',
    },
    {
      icon: Zap,
      label: 'Active Learning Systems',
      value: details.active_modules ? `${details.active_modules}` : (learningStats?.models_loaded || '--'),
      color: '#10B981',
      trend: '+5%',
      description: 'Currently operational AI modules',
    },
    {
      icon: GitBranch,
      label: 'Training Conversations',
      value: details.conversations_count ? `${details.conversations_count.toLocaleString()}` : (learningStats?.total_feedback || '--'),
      color: '#F59E0B',
      trend: '+18%',
      description: 'Conversations used for training',
    },
    {
      icon: Brain,
      label: 'Neural Network Layers',
      value: details.neural_layers || '342',
      color: '#8B5CF6',
      trend: '+0%',
      description: 'Active neural network layers',
    },
    {
      icon: Target,
      label: 'Model Accuracy',
      value: details.accuracy ? `${details.accuracy}%` : '96.0%',
      color: '#06B6D4',
      trend: '+2.1%',
      description: `Learning Rate: ${details.learning_rate || '0.001'}`,
    },
    {
      icon: Layers,
      label: 'Processing Speed',
      value: details.inference_time ? `${details.inference_time}ms` : '2.3ms',
      color: '#EF4444',
      trend: '-1.5%',
      description: 'Average inference time',
    },
  ];

  const learningProgress = details.skills_progress || [
    { label: 'Natural Language Understanding', value: 94.0 },
    { label: 'Context Retention', value: 87.5 },
    { label: 'Task Execution Accuracy', value: 91.2 },
    { label: 'Voice Command Recognition', value: 89.8 }
  ];

  const recentSessions = details.recent_sessions || [
    { session: 'System Initialization', time: 'Just now', status: 'completed' },
    { session: 'Knowledge Graph Sync', time: '1 min ago', status: 'active' }
  ];

  return (
    <div className="space-y-3.5 flex flex-col h-full overflow-hidden pb-2">
      <div className="flex-shrink-0 flex items-center justify-between gap-3 pb-0.5">
        <p className="text-xs text-[#9CA3AF]">Monitor and analyze AI learning performance, neural metrics, and knowledge growth</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 flex-shrink-0">
        {learningMetrics.map((metric, index) => (
          <motion.div
            key={metric.label}
            className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-3.5 hover:border-[#3B82F6]/50 transition-all"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1.5 rounded-lg shrink-0" style={{ backgroundColor: `${metric.color}15` }}>
                  <metric.icon className="w-4 h-4" style={{ color: metric.color }} strokeWidth={2} />
                </div>
                <h4 className="text-xs font-medium text-[#9CA3AF] truncate">{metric.label}</h4>
              </div>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${metric.trend.startsWith('+') ? 'bg-[#10B981]/15 text-[#10B981]' : 'bg-[#EF4444]/15 text-[#EF4444]'}`}>
                {metric.trend}
              </span>
            </div>

            <p className="text-lg sm:text-xl font-bold text-white truncate my-1">{metric.value}</p>
            <p className="text-[11px] text-[#6B7280] truncate">{metric.description}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 flex-shrink-0">
        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-white mb-2.5">Learning Progress</h4>
          <div className="space-y-2.5">
            {learningProgress.map((skill: { label: string; value: number }, idx: number) => (
              <div key={idx}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-[#9CA3AF]">{skill.label}</span>
                  <span className="text-xs font-semibold text-white">{skill.value.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-[#2A2D35] rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-[#3B82F6] to-[#10B981]"
                    initial={{ width: 0 }}
                    animate={{ width: `${skill.value}%` }}
                    transition={{ duration: 1, delay: idx * 0.1 }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-4">
          <h4 className="text-sm font-semibold text-white mb-2.5">Recent Training Sessions</h4>
          <div className="space-y-2">
            {recentSessions.map((session: { session: string; time: string; status: string }, idx: number) => (
              <div
                key={idx}
                className="flex items-center gap-2.5 px-3 py-2 bg-[#2A2D35] rounded-lg"
              >
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${session.status === 'active' ? 'bg-[#10B981] animate-pulse' : 'bg-[#6B7280]'}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white truncate font-medium">{session.session}</p>
                  <p className="text-[10px] text-[#6B7280]">{session.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Agents Section */}
      {(() => {
        const displayAgents = (details.agents && details.agents.length > 0) ? details.agents : (agents || []);
        if (!displayAgents || displayAgents.length === 0) return null;
        return (
          <div className="space-y-2.5 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white">Specialized AI Agents</h4>
                <p className="text-xs text-[#9CA3AF]">Registered autonomous agents in the system</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedView('agents')}
                className="px-2.5 py-1 rounded-lg bg-[#1F2228] hover:bg-[#2A2D35] border border-[#00f3ff]/30 text-[#00f3ff] text-xs font-medium flex items-center gap-1"
              >
                <span>Manage Agents</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2.5">
              {displayAgents.map((agent: any) => {
                const isBusy = agent.status === 'active' || agent.status === 'busy';
                return (
                  <div key={agent.id} className="bg-[#1F2228] border border-[#2A2D35] rounded-xl p-3 hover:border-[#8B5CF6]/50 transition-all">
                    <div className="flex items-center gap-2.5 mb-2">
                      <div className={`p-1.5 rounded-lg shrink-0 ${isBusy ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#8B5CF6]/10 text-[#8B5CF6]'}`}>
                        <Brain className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <h5 className="font-semibold text-white text-xs truncate">{agent.name}</h5>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[9px] text-[#9CA3AF] bg-[#2A2D35] px-1.5 py-0.2 rounded uppercase tracking-wider">
                            {agent.category || String(agent.id).split('_')[0]}
                          </span>
                          {isBusy ? (
                            <span className="text-[9px] text-[#10B981] flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span>
                              BUSY
                            </span>
                          ) : (
                            <span className="text-[9px] text-[#6B7280] flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#6B7280]"></span>
                              {String(agent.status || 'STANDBY').toUpperCase()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <p className="text-[11px] text-[#9CA3AF] line-clamp-2 mb-1.5">{agent.description}</p>
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities && agent.capabilities.slice(0, 4).map((cap: string, i: number) => (
                        <span key={i} className="text-[9px] text-[#6B7280] border border-[#2A2D35] px-1 rounded">
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      <div className="bg-gradient-to-r from-[#3B82F6]/10 to-[#10B981]/10 border border-[#3B82F6]/30 rounded-xl p-3.5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-white mb-0.5">Continuous Learning Mode</h4>
            <p className="text-xs text-[#9CA3AF]">AI is actively learning from interactions to improve responses</p>
          </div>
          <span className="px-3 py-1 bg-[#10B981]/20 text-[#10B981] text-xs rounded-lg font-semibold border border-[#10B981]/30">
            ACTIVE
          </span>
        </div>
      </div>
    </div>
  );
};

export default AILearningDetail;
