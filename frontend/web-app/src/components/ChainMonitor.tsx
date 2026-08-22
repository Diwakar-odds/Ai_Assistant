import React, { useEffect, useState } from 'react';

// Assuming you have a Socket instance or context
// import { useSocket } from '../contexts/SocketContext';

interface ChainStep {
  id: string;
  type: string;
  description: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  verification?: {
    success: boolean;
    confidence: number;
    details: string;
  };
}

interface ChainState {
  id: string;
  command: string;
  status: 'CREATED' | 'DECOMPOSED' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  steps: ChainStep[];
}

interface ChainMonitorProps {
  chainId: string;
}

const ChainMonitor: React.FC<ChainMonitorProps> = ({ chainId }) => {
  // const { socket } = useSocket();
  const [chain, setChain] = useState<ChainState | null>(null);

  useEffect(() => {
    // 1. Fetch initial state
    fetch(`/api/chains/${chainId}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
      .then(res => res.json())
      .then(data => setChain(data))
      .catch(err => console.error("Failed to fetch chain", err));

    // 2. Setup WebSocket (Mock implementation of how it would look)
    const __setupWebSocket = () => {
      // socket.emit('subscribe_chain', { chain_id: chainId });
      
      // socket.on('chain.started', (data) => setChain(prev => prev ? {...prev, status: 'EXECUTING'} : null));
      // socket.on('chain.step_completed', (data) => { ...update specific step });
      // socket.on('chain.step_failed', (data) => { ...update specific step });
      // socket.on('chain.completed', (data) => setChain(prev => prev ? {...prev, status: 'COMPLETED'} : null));
      
      // return () => {
      //   socket.emit('unsubscribe_chain', { chain_id: chainId });
      //   socket.off('chain.started'); ...
      // }
    };
    
    // __setupWebSocket();
  }, [chainId]);

  if (!chain) return <div className="p-4 border rounded shadow-sm">Loading Chain {chainId}...</div>;

  return (
    <div className="p-4 border rounded-lg shadow-md bg-white dark:bg-gray-800">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Chain Execution</h2>
        <span className={`px-2 py-1 rounded text-sm font-semibold ${
          chain.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
          chain.status === 'FAILED' ? 'bg-red-100 text-red-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          {chain.status}
        </span>
      </div>
      
      <div className="mb-4">
        <span className="font-semibold text-gray-600 dark:text-gray-300">Command:</span>
        <span className="ml-2">"{chain.command}"</span>
      </div>

      <div className="space-y-3">
        {chain.steps?.map((step, idx) => (
          <div key={step.id} className="p-3 border rounded border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="flex justify-between">
              <span className="font-medium">Step {idx + 1}: {step.type}</span>
              <span className={`text-xs px-2 py-1 rounded ${
                step.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                step.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                step.status === 'RUNNING' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-200 text-gray-800'
              }`}>
                {step.status}
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{step.description}</p>
            
            {step.verification && (
              <div className="mt-2 text-xs border-t pt-2 border-gray-200 dark:border-gray-700">
                <span className="font-semibold mr-2">Verification:</span>
                {step.verification.success ? '✅ Passed' : '❌ Failed'}
                <span className="ml-2 text-gray-500">({step.verification.details})</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChainMonitor;
