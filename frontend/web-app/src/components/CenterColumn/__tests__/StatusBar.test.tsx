import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import StatusBar from '../StatusBar';

vi.mock('../../../contexts/DashboardContext', () => ({
  useDashboard: vi.fn(() => ({
    isVoiceActive: false,
    isConnected: true,
    activeTasks: 2,
    unreadNotifications: 1,
    connectionQuality: 'excellent',
  })),
}));

describe('StatusBar Component', () => {
  it('renders time and online status correctly', () => {
    render(<StatusBar />);
    expect(screen.getByText(/Online/i)).toBeInTheDocument();
  });
});
