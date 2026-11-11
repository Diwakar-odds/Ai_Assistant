import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import CommandInput from '../CommandInput';

const mockSendCommand = vi.fn();
const mockEmergencyStop = vi.fn();

vi.mock('../../../contexts/DashboardContext', () => ({
    useDashboard: vi.fn(),
}));

import { useDashboard } from '../../../contexts/DashboardContext';

describe('CommandInput Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useDashboard).mockReturnValue({
            sendCommand: mockSendCommand,
            emergencyStop: mockEmergencyStop,
            agents: [
                { id: 'web_search', name: 'Web Search', status: 'idle', category: 'web', capabilities: [] },
                { id: 'code_exec', name: 'Code Exec', status: 'busy', category: 'coding', capabilities: [] },
            ],
            activeChains: [],
            brainStatus: { is_busy: false },
        } as any);
    });

    it('submits command on Enter and clears textarea', () => {
        render(<CommandInput />);
        const textarea = screen.getByPlaceholderText(/Type a command/i);

        fireEvent.change(textarea, { target: { value: 'run system diagnosis' } });
        fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

        expect(mockSendCommand).toHaveBeenCalledWith('run system diagnosis', undefined);
        expect((textarea as HTMLTextAreaElement).value).toBe('');
    });

    it('does not submit on Shift+Enter', () => {
        render(<CommandInput />);
        const textarea = screen.getByPlaceholderText(/Type a command/i);

        fireEvent.change(textarea, { target: { value: 'first line\n' } });
        fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

        expect(mockSendCommand).not.toHaveBeenCalled();
    });

    it('displays multi-step preview badge when command has multiple steps', () => {
        render(<CommandInput />);
        const textarea = screen.getByPlaceholderText(/Type a command/i);

        fireEvent.change(textarea, { target: { value: 'step 1 && step 2 -> step 3' } });
        expect(screen.getByText(/Multi-Step Chain \(3 steps\)/i)).toBeInTheDocument();
    });

    it('routes command to chosen target agent when selected', () => {
        render(<CommandInput />);
        const select = screen.getByLabelText('Target Agent');
        expect(select).toBeInTheDocument();

        fireEvent.change(select, { target: { value: 'web_search' } });

        const textarea = screen.getByPlaceholderText(/Type a command/i);
        fireEvent.change(textarea, { target: { value: 'find latest papers' } });
        fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

        expect(mockSendCommand).toHaveBeenCalledWith('find latest papers', { agentId: 'web_search' });
    });

    it('displays Stop button when system is busy and triggers emergencyStop', () => {
        vi.mocked(useDashboard).mockReturnValue({
            sendCommand: mockSendCommand,
            emergencyStop: mockEmergencyStop,
            agents: [],
            activeChains: [{ chain_id: 'c1', status: 'executing' }] as any,
            brainStatus: { is_busy: true },
        } as any);

        render(<CommandInput />);
        const stopBtn = screen.getByLabelText('Emergency Stop');
        expect(stopBtn).toBeInTheDocument();

        fireEvent.click(stopBtn);
        expect(mockEmergencyStop).toHaveBeenCalled();
    });
});
