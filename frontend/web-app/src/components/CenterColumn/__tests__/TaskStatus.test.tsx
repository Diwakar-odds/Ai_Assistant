import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import TaskStatus from '../TaskStatus';

const mockOpenChainMonitor = vi.fn();
const mockPauseChain = vi.fn();
const mockResumeChain = vi.fn();
const mockCancelChain = vi.fn();
const mockEmergencyStop = vi.fn();

vi.mock('../../../contexts/DashboardContext', () => ({
    useDashboard: vi.fn(),
}));

import { useDashboard } from '../../../contexts/DashboardContext';

describe('TaskStatus Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('returns null when idle with no active chains', () => {
        vi.mocked(useDashboard).mockReturnValue({
            brainStatus: { is_busy: false, active_chains: [] },
            activeChains: [],
            openChainMonitor: mockOpenChainMonitor,
            pauseChain: mockPauseChain,
            resumeChain: mockResumeChain,
            cancelChain: mockCancelChain,
            emergencyStop: mockEmergencyStop,
        } as any);

        const { container } = render(<TaskStatus />);
        expect(container).toBeEmptyDOMElement();
    });

    it('renders active chains, step progress, STOP button, and handles inspect click', () => {
        vi.mocked(useDashboard).mockReturnValue({
            brainStatus: { is_busy: true },
            activeChains: [
                {
                    chain_id: 'chain_live_001',
                    command: 'analyze dataset && plot chart',
                    status: 'executing',
                    progress_percentage: 45,
                    actions_completed: 1,
                    total_actions: 2,
                    current_action: 'Running regression',
                    current_agent: 'DataAnalystAgent',
                    actions: [],
                },
            ] as any,
            openChainMonitor: mockOpenChainMonitor,
            pauseChain: mockPauseChain,
            resumeChain: mockResumeChain,
            cancelChain: mockCancelChain,
            emergencyStop: mockEmergencyStop,
        } as any);

        render(<TaskStatus />);

        expect(screen.getByText(/Orchestrator Active/i)).toBeInTheDocument();
        expect(screen.getByText('analyze dataset && plot chart')).toBeInTheDocument();
        expect(screen.getByText('1/2')).toBeInTheDocument();
        expect(screen.getByText('DataAnalystAgent')).toBeInTheDocument();
        expect(screen.getByText('Running regression')).toBeInTheDocument();

        // Inspect header button
        const inspectBtn = screen.getByText('Inspect');
        fireEvent.click(inspectBtn);
        expect(mockOpenChainMonitor).toHaveBeenCalledWith('chain_live_001');

        // STOP emergency stop button
        const stopBtn = screen.getByText('STOP');
        fireEvent.click(stopBtn);
        expect(mockEmergencyStop).toHaveBeenCalled();
    });

    it('handles per-chain pause and cancel buttons', () => {
        vi.mocked(useDashboard).mockReturnValue({
            brainStatus: { is_busy: true },
            activeChains: [
                {
                    chain_id: 'chain_pause_test',
                    command: 'step 1 && step 2',
                    status: 'executing',
                    actions_completed: 0,
                    total_actions: 2,
                    actions: [],
                },
            ] as any,
            openChainMonitor: mockOpenChainMonitor,
            pauseChain: mockPauseChain,
            resumeChain: mockResumeChain,
            cancelChain: mockCancelChain,
            emergencyStop: mockEmergencyStop,
        } as any);

        render(<TaskStatus />);

        const pauseBtn = screen.getByLabelText('Pause chain_pause_test');
        fireEvent.click(pauseBtn);
        expect(mockPauseChain).toHaveBeenCalledWith('chain_pause_test');

        const cancelBtn = screen.getByLabelText('Cancel chain_pause_test');
        fireEvent.click(cancelBtn);
        expect(mockCancelChain).toHaveBeenCalledWith('chain_pause_test');
    });
});
