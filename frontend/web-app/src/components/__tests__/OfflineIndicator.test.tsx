import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { OfflineIndicator } from '../OfflineIndicator';

vi.mock('../../hooks/useNetworkStatus', () => ({
  useNetworkStatus: vi.fn(),
}));

import { useNetworkStatus } from '../../hooks/useNetworkStatus';

describe('OfflineIndicator Component', () => {
  it('renders nothing when online', () => {
    vi.mocked(useNetworkStatus).mockReturnValue(true);
    const { container } = render(<OfflineIndicator />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders warning banner when offline', () => {
    vi.mocked(useNetworkStatus).mockReturnValue(false);
    render(<OfflineIndicator />);
    expect(screen.getByText(/You are offline/i)).toBeInTheDocument();
  });
});
