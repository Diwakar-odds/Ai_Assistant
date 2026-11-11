import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import AgentsChainsDetail from '../AgentsChainsDetail';

const mockRefreshChains = vi.fn().mockResolvedValue(undefined);
const mockRefreshAgents = vi.fn().mockResolvedValue(undefined);
const mockCreateAndRunChain = vi.fn().mockResolvedValue({ chain_id: 'chain_new' });
const mockEmergencyStop = vi.fn().mockResolvedValue(undefined);
const mockLoadAgent = vi.fn().mockResolvedValue(undefined);
const mockDispatchAgentTask = vi.fn().mockResolvedValue({
    task_id: 'task_001',
    agent_id: 'DataAnalystAgent',
    status: 'completed',
});
const mockCancelAgentTask = vi.fn().mockResolvedValue(undefined);
const mockSetSelectedChainId = vi.fn();

vi.mock('../../../contexts/DashboardContext', () => ({
    useDashboard: vi.fn(),
}));

// Mock child ChainMonitor so this unit test focuses on AgentsChainsDetail container logic
vi.mock('../../ChainMonitor', () => ({
    default: ({ chainId }: { chainId: string | null }) => (
        <div data-testid="mock-chain-monitor">Monitor for {chainId || 'none'}</div>
    ),
}));

import { useDashboard } from '../../../contexts/DashboardContext';

describe('AgentsChainsDetail Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useDashboard).mockReturnValue({
            activeChains: [
                {
                    chain_id: 'chain_1',
                    command: 'open browser && scrape',
                    status: 'executing',
                    progress_percentage: 50,
                    actions_completed: 1,
                    total_actions: 2,
                    actions: [],
                },
            ],
            chainHistory: [],
            selectedChainId: 'chain_1',
            setSelectedChainId: mockSetSelectedChainId,
            agents: [
                {
                    id: 'DataAnalystAgent',
                    name: 'Data Analyst Agent',
                    category: 'analysis',
                    description: 'Analyzes tabular datasets and generates visualizations',
                    capabilities: ['pandas', 'numpy', 'matplotlib'],
                    status: 'idle',
                    active_tasks: 0,
                    completed_tasks: 5,
                    failed_tasks: 0,
                },
                {
                    id: 'DatabaseAgent',
                    name: 'Database Agent',
                    category: 'database',
                    description: 'Executes SQL queries and schema introspection',
                    capabilities: ['sql', 'sqlite', 'postgres'],
                    status: 'busy',
                    active_tasks: 1,
                    completed_tasks: 3,
                    failed_tasks: 0,
                },
            ],
            agentTasks: [],
            refreshChains: mockRefreshChains,
            refreshAgents: mockRefreshAgents,
            createAndRunChain: mockCreateAndRunChain,
            emergencyStop: mockEmergencyStop,
            loadAgent: mockLoadAgent,
            dispatchAgentTask: mockDispatchAgentTask,
            cancelAgentTask: mockCancelAgentTask,
        } as any);
    });

    it('renders KPI summary cards and mounts with chain data', () => {
        render(<AgentsChainsDetail />);

        expect(screen.getByText('Active Chains')).toBeInTheDocument();
        expect(screen.getByText('Registered Agents')).toBeInTheDocument();
        expect(screen.getByText('Agents Busy')).toBeInTheDocument();
        expect(screen.getByText('Completed Runs')).toBeInTheDocument();
        expect(screen.getByTestId('mock-chain-monitor')).toHaveTextContent('Monitor for chain_1');
    });

    it('launches a new multi-step chain from the chain launcher input', async () => {
        render(<AgentsChainsDetail />);

        const launcherInput = screen.getByLabelText('Launch Multi-Step Command Chain');
        fireEvent.change(launcherInput, {
            target: { value: 'open terminal && run tests -> summarize' },
        });

        expect(screen.getByText(/3 steps detected/i)).toBeInTheDocument();

        const runChainBtn = screen.getByRole('button', { name: /Run Chain/i });
        fireEvent.click(runChainBtn);

        await waitFor(() => {
            expect(mockCreateAndRunChain).toHaveBeenCalledWith(
                'open terminal && run tests -> summarize',
                { autoExecute: true }
            );
        });
    });

    it('switches to Specialized Agents tab, filters agents, and dispatches a direct task', async () => {
        render(<AgentsChainsDetail />);

        const agentsTabBtn = screen.getByRole('button', { name: /Specialized Agents/i });
        fireEvent.click(agentsTabBtn);

        expect(screen.getByText('Data Analyst Agent')).toBeInTheDocument();
        expect(screen.getByText('Database Agent')).toBeInTheDocument();

        // Filter by capability or query
        const searchInput = screen.getByPlaceholderText(/Filter agents/i);
        fireEvent.change(searchInput, { target: { value: 'sql' } });

        expect(screen.queryByText('Data Analyst Agent')).not.toBeInTheDocument();
        expect(screen.getByText('Database Agent')).toBeInTheDocument();

        // Clear filter
        fireEvent.change(searchInput, { target: { value: '' } });
        expect(screen.getByText('Data Analyst Agent')).toBeInTheDocument();

        // Open task prompt on agent card
        const runTaskBtns = screen.getAllByRole('button', { name: 'Run Task' });
        fireEvent.click(runTaskBtns[0]);

        const agentPromptInput = screen.getByPlaceholderText(/Task for Data Analyst Agent/i);
        fireEvent.change(agentPromptInput, { target: { value: 'Analyze sales.csv revenue' } });

        const submitTaskBtn = agentPromptInput.parentElement?.querySelector('button');
        expect(submitTaskBtn).toBeTruthy();
        fireEvent.click(submitTaskBtn!);

        await waitFor(() => {
            expect(mockDispatchAgentTask).toHaveBeenCalledWith('Analyze sales.csv revenue', {
                agentId: 'DataAnalystAgent',
                asyncRun: true,
            });
        });
    });
});
