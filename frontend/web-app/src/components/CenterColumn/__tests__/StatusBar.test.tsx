import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import StatusBar from '../StatusBar';

const mockSetSelectedView = vi.fn();
const mockToggleLeftSidebar = vi.fn();
const mockToggleRightSidebar = vi.fn();

vi.mock('../../../contexts/DashboardContext', () => ({
  useDashboard: vi.fn(),
}));

import { useDashboard } from '../../../contexts/DashboardContext';

describe('StatusBar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders time and connected status correctly', () => {
    vi.mocked(useDashboard).mockReturnValue({
      isConnected: true,
      setSelectedView: mockSetSelectedView,
      isLeftSidebarOpen: true,
      isRightSidebarOpen: true,
      toggleLeftSidebar: mockToggleLeftSidebar,
      toggleRightSidebar: mockToggleRightSidebar,
      systemLogs: [],
      activeChains: [],
    } as any);

    render(<StatusBar />);
    expect(screen.getByTitle('Backend Connected')).toBeInTheDocument();
    expect(screen.getByLabelText('Open Multi-Agent & Chain Orchestrator')).toBeInTheDocument();
  });

  it('displays active chain count badge and navigates to agents view on click', () => {
    vi.mocked(useDashboard).mockReturnValue({
      isConnected: true,
      setSelectedView: mockSetSelectedView,
      isLeftSidebarOpen: true,
      isRightSidebarOpen: false,
      toggleLeftSidebar: mockToggleLeftSidebar,
      toggleRightSidebar: mockToggleRightSidebar,
      systemLogs: [{ id: '1', message: 'System booted', type: 'info', time: '12:00:00' }],
      activeChains: [{ chain_id: 'chain_1', command: 'test', status: 'executing' }] as any,
    } as any);

    render(<StatusBar />);
    const orchestratorBtn = screen.getByLabelText('Open Multi-Agent & Chain Orchestrator');
    expect(orchestratorBtn).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();

    fireEvent.click(orchestratorBtn);
    expect(mockSetSelectedView).toHaveBeenCalledWith('agents');
  });

  it('handles sidebar toggles and shows disconnected state', () => {
    vi.mocked(useDashboard).mockReturnValue({
      isConnected: false,
      setSelectedView: mockSetSelectedView,
      isLeftSidebarOpen: false,
      isRightSidebarOpen: true,
      toggleLeftSidebar: mockToggleLeftSidebar,
      toggleRightSidebar: mockToggleRightSidebar,
      systemLogs: [],
      activeChains: [],
    } as any);

    render(<StatusBar />);
    expect(screen.getByTitle('Backend Disconnected')).toBeInTheDocument();

    const leftToggle = screen.getByTitle('Show Left Sidebar');
    fireEvent.click(leftToggle);
    expect(mockToggleLeftSidebar).toHaveBeenCalled();

    const rightToggle = screen.getByTitle('Hide Conversation History');
    fireEvent.click(rightToggle);
    expect(mockToggleRightSidebar).toHaveBeenCalled();
  });
});
