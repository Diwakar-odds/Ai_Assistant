import React, { useState } from 'react';
import { Lock, User, LogIn, UserPlus, AlertCircle } from 'lucide-react';

interface AuthProps {
  onAuthSuccess: (token: string, username: string) => void;
}

const Auth = ({ onAuthSuccess }: AuthProps) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const validateInputs = () => {
    if (!username || !password) {
      setError('Username and password are required');
      return false;
    }

    if (username.length < 3 || username.length > 20) {
      setError('Username must be 3-20 characters');
      return false;
    }

    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setError('Username can only contain letters, numbers, and underscores');
      return false;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return false;
    }

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateInputs()) {
      return;
    }

    setIsLoading(true);

    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Authentication failed');
      }

      // Store token in localStorage
      localStorage.setItem('yourdaddy-token', data.access_token);
      localStorage.setItem('yourdaddy-username', username);

      // Call success callback
      onAuthSuccess(data.access_token, username);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] via-[#16213e] to-[#0f0f1e] p-4" role="main" aria-labelledby="auth-title">
      <div className="glass-strong p-8 rounded-2xl w-full max-w-md shadow-2xl animate-bounce-in">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-[#6C5CE7] to-[#A855F7] rounded-full mb-4 animate-glow" aria-hidden="true">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <h1 id="auth-title" className="text-3xl font-bold gradient-text mb-2">
            {isLogin ? 'Welcome Back' : 'Create Account'}
          </h1>
          <p className="text-[#AAAAAA]">
            {isLogin ? 'Sign in to YourDaddy Assistant' : 'Join YourDaddy Assistant'}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-start gap-3 animate-slide-up" role="alert" aria-live="polite">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5" aria-label={isLogin ? 'Login form' : 'Registration form'}>
          {/* Username */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-[#DDDDDD] mb-2">
              Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none" aria-hidden="true">
                <User className="w-5 h-5 text-[#888888]" />
              </div>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="glass-input pl-10 w-full"
                placeholder="Enter username"
                disabled={isLoading}
                autoComplete="username"
                required
                aria-required="true"
                aria-invalid={!!(error.includes('username') || error.includes('Username'))}
                aria-describedby={error.includes('username') || error.includes('Username') ? 'username-error' : undefined}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#DDDDDD] mb-2">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none" aria-hidden="true">
                <Lock className="w-5 h-5 text-[#888888]" />
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="glass-input pl-10 w-full"
                placeholder="Enter password"
                disabled={isLoading}
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                required
                aria-required="true"
                aria-invalid={!!(error.includes('password') || error.includes('Password'))}
                aria-describedby={error.includes('password') || error.includes('Password') ? 'password-error' : undefined}
              />
            </div>
          </div>

          {/* Confirm Password (Register only) */}
          {!isLogin && (
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-[#DDDDDD] mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="w-5 h-5 text-[#888888]" />
                </div>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="glass-input pl-10 w-full"
                  placeholder="Confirm password"
                  disabled={isLoading}
                  autoComplete="new-password"
                />
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Processing...</span>
              </>
            ) : (
              <>
                {isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
                <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
              </>
            )}
          </button>
        </form>

        {/* Toggle Login/Register */}
        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
              setPassword('');
              setConfirmPassword('');
            }}
            className="text-[#AAAAAA] hover:text-[#6C5CE7] transition-colors text-sm"
            disabled={isLoading}
          >
            {isLogin ? (
              <>Don't have an account? <span className="font-semibold">Sign up</span></>
            ) : (
              <>Already have an account? <span className="font-semibold">Sign in</span></>
            )}
          </button>
        </div>

        {/* Demo Credentials */}
        {isLogin && (
          <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-xs text-blue-400 text-center">
              <strong>Demo:</strong> admin / {import.meta.env.VITE_ADMIN_PASSWORD || 'changeme123'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Auth;
