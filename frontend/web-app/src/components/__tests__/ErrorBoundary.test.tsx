import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ErrorBoundary } from '../ErrorBoundary';

const ProblemChild = () => {
  throw new Error('Test rendering crash');
};

describe('ErrorBoundary Component', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Normal Content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Normal Content')).toBeInTheDocument();
  });

  it('renders fallback UI when a child crashes', () => {
    // Suppress console.error in test output
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    render(
      <ErrorBoundary fallbackTitle="Custom Error Notice">
        <ProblemChild />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error Notice')).toBeInTheDocument();
    expect(screen.getByText(/Test rendering crash/i)).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();

    spy.mockRestore();
  });
});
