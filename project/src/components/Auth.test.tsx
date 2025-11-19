import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Auth from './Auth';

describe('Auth component', () => {
  test('renders login form and handles input', () => {
    const mockSuccess = vi.fn();
    render(<Auth onAuthSuccess={mockSuccess} />);

    const usernameInput = screen.getByPlaceholderText(/enter username/i);
    const passwordInput = screen.getByPlaceholderText(/enter password/i);
    const submitButton = screen.getByRole('button', { name: /sign in|create account/i });

    expect(usernameInput).toBeInTheDocument();
    expect(passwordInput).toBeInTheDocument();
    expect(submitButton).toBeInTheDocument();

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect((usernameInput as HTMLInputElement).value).toBe('testuser');
    expect((passwordInput as HTMLInputElement).value).toBe('password123');
  });
});
