import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import ChainMonitor from '../ChainMonitor';
import { normalizeChainDTO } from '../../lib/api';

const mockPauseChain = vi.fn().mockResolvedValue({ success: true });
const mockResumeChain = vi.fn().mockResolvedValue({ success: true });
const mockCancelChain = vi.fn().mockResolvedValue({ success: true });
const mockEmergencyStop = vi.fn().mockResolvedValue({ success: true });

vi.mock('../../contexts/DashboardContext', () => ({
    useDashboard: vi.fn(),
}));

vi.mock('../../lib/api', async (importOriginal) => {
    const mod = await importOriginal<typeof import('../../lib/api')>();
    return {
        ...mod,
        apiFetchJson: vi.fn().mockResolvedValue({ ok: true, data: null }),
    };
});

import { useDashboard } from '../../contexts/DashboardContext';

describe('ChainMonitor Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useDashboard).mockReturnValue({
            socket: null,
            isConnected: false,
            activeChains: [],
            chainHistory: [],
            pauseChain: mockPauseChain,
            resumeChain: mockResumeChain,
            cancelChain: mockCancelChain,
            emergencyStop: mockEmergencyStop,
        } as any);
    });

    it('renders empty placeholder when no chain is selected', () => {
        render(<ChainMonitor chainId={null} chain={null} />);
        expect(screen.getByText('No Chain Selected')).toBeInTheDocument();
    });

    it('renders executing chain with steps, progress, and agent tags', () => {
        const rawChain = {
            chain_id: 'chain_test123',
            command: 'open browser && scrape data',
            status: 'executing',
            progress_percentage: 50,
            actions_completed: 1,
            total_actions: 2,
            actions: [
                {
                    id: 'act_1',
                    type: 'browser_action',
                    description: 'Launch Chrome browser',
                    status: 'completed',
                    agent_name: 'BrowserAgent',
                    verified: true,
                    verification_result: { confidence: 0.95, details: 'Window opened' },
                },
                {
                    id: 'act_2',
                    type: 'scrape_action',
                    description: 'Extract headline text',
                    status: 'executing',
                    agent_name: 'ScraperAgent',
                    dependencies: ['act_1'],
                },
            ],
        };
        const chain = normalizeChainDTO(rawChain)!;

        render(<ChainMonitor chain={chain} />);

        expect(screen.getByText('chain_test123')).toBeInTheDocument();
        expect(screen.getByText('open browser && scrape data')).toBeInTheDocument();
        expect(screen.getByText('50%')).toBeInTheDocument();
        expect(screen.getByText('Launch Chrome browser')).toBeInTheDocument();
        expect(screen.getByText('Extract headline text')).toBeInTheDocument();
        expect(screen.getByText('BrowserAgent')).toBeInTheDocument();
        expect(screen.getByText('ScraperAgent')).toBeInTheDocument();
        expect(screen.getByText('Verified')).toBeInTheDocument();
        expect(screen.getByText('(95% confidence)')).toBeInTheDocument();
        expect(screen.getByText('Depends on:')).toBeInTheDocument();
        expect(screen.getByText('act_1')).toBeInTheDocument();
    });

    it('calls pauseChain on pause button click', async () => {
        const rawChain = {
            chain_id: 'chain_exec456',
            command: 'long running pipeline',
            status: 'executing',
            actions: [
                { id: 'step_1', type: 'task', description: 'Step 1', status: 'executing' },
            ],
        };
        const chain = normalizeChainDTO(rawChain)!;

        render(<ChainMonitor chain={chain} />);

        const pauseBtn = screen.getByRole('button', { name: /pause/i });
        fireEvent.click(pauseBtn);

        await waitFor(() => {
            expect(mockPauseChain).toHaveBeenCalledWith('chain_exec456');
        });
    });

    it('calls cancelChain on cancel button click', async () => {
        const rawChain = {
            chain_id: 'chain_cancel123',
            command: 'cancellable pipeline',
            status: 'executing',
            actions: [
                { id: 'step_1', type: 'task', description: 'Step 1', status: 'executing' },
            ],
        };
        const chain = normalizeChainDTO(rawChain)!;

        render(<ChainMonitor chain={chain} />);

        const cancelBtn = screen.getByRole('button', { name: /cancel/i });
        fireEvent.click(cancelBtn);

        await waitFor(() => {
            expect(mockCancelChain).toHaveBeenCalledWith('chain_cancel123');
        });
    });

    it('calls resumeChain when paused', async () => {
        const pausedChain = normalizeChainDTO({
            chain_id: 'chain_paused789',
            command: 'paused pipeline',
            status: 'paused',
            actions: [{ id: 's1', type: 'task', description: 'Step 1', status: 'paused' }],
        })!;

        render(<ChainMonitor chain={pausedChain} />);
        const resumeBtn = screen.getByRole('button', { name: /resume/i });
        fireEvent.click(resumeBtn);

        await waitFor(() => {
            expect(mockResumeChain).toHaveBeenCalledWith('chain_paused789');
        });
    });

    it('calls authorize when waiting_confirmation', async () => {
        const waitingChain = normalizeChainDTO({
            chain_id: 'chain_wait101',
            command: 'dangerous delete pipeline',
            status: 'waiting_confirmation',
            actions: [{ id: 's1', type: 'task', description: 'Step 1', status: 'waiting_confirmation' }],
        })!;

        render(<ChainMonitor chain={waitingChain} />);
        const authBtn = screen.getByRole('button', { name: /authorize/i });
        fireEvent.click(authBtn);

        await waitFor(() => {
            expect(mockResumeChain).toHaveBeenCalledWith('chain_wait101', 'yes');
        });
    });

    it('supports legacy steps schema fallback and displays final output', () => {
        const legacyChain = normalizeChainDTO({
            id: 'chain_legacy_999',
            command: 'legacy format run',
            status: 'completed',
            steps: [
                { step_id: 'st_1', type: 'run', description: 'Legacy Step 1', status: 'completed' },
            ],
            output: 'Pipeline finished with code 0',
        })!;

        render(<ChainMonitor chain={legacyChain} />);
        expect(screen.getByText('Legacy Step 1')).toBeInTheDocument();
        expect(screen.getByText('Final Output')).toBeInTheDocument();
        expect(screen.getByText(/Pipeline finished with code 0/i)).toBeInTheDocument();
    });
});
