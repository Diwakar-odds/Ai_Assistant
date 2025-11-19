import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });

    // Log error to backend for monitoring
    this.logErrorToService(error, errorInfo);
  }

  logErrorToService = async (error: Error, errorInfo: React.ErrorInfo) => {
    try {
      await fetch('/api/error/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      });
    } catch (logError) {
      console.warn('Failed to log error to backend:', logError);
    }
  };

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={this.state.error!} reset={this.handleReset} />;
      }

      return (
        <div className="min-h-screen bg-primary flex items-center justify-center p-8">
          <div className="max-w-md w-full text-center">
            <div className="glass-strong p-8 rounded-2xl">
              <div className="w-20 h-20 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-6">
                <AlertTriangle size={40} className="text-red-400" />
              </div>
              
              <h1 className="text-2xl font-bold mb-4">Something went wrong</h1>
              <p className="text-[#DDDDDD] mb-6">
                The application encountered an unexpected error. Don't worry, your data is safe.
              </p>
              
              {import.meta.env.DEV && this.state.error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-left">
                  <h3 className="font-semibold text-red-400 mb-2">Error Details:</h3>
                  <pre className="text-sm text-red-300 overflow-x-auto">
                    {this.state.error.message}
                  </pre>
                  {this.state.error.stack && (
                    <pre className="text-xs text-red-300/70 mt-2 overflow-x-auto">
                      {this.state.error.stack.slice(0, 500)}...
                    </pre>
                  )}
                </div>
              )}
              
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={this.handleReset}
                  className="flex-1 px-4 py-3 bg-[#6C5CE7] rounded-lg hover:bg-[#5A4BD6] transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw size={16} />
                  Try Again
                </button>
                <button
                  onClick={this.handleReload}
                  className="flex-1 px-4 py-3 bg-[#00CEC9] rounded-lg hover:bg-[#00B5A8] transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw size={16} />
                  Reload Page
                </button>
                <button
                  onClick={this.handleHome}
                  className="flex-1 px-4 py-3 bg-[#00B894] rounded-lg hover:bg-[#009A7A] transition-colors flex items-center justify-center gap-2"
                >
                  <Home size={16} />
                  Go Home
                </button>
              </div>
              
              <p className="text-xs text-[#DDDDDD]/50 mt-6">
                Error ID: {Date.now().toString(36)}
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;