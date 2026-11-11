import React, { useState } from 'react';
import { Eye, EyeOff, Check, Loader2 } from 'lucide-react';

interface PasswordInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  onVerify?: () => Promise<boolean>;
  className?: string;
}

export const PasswordInput: React.FC<PasswordInputProps> = ({
  value,
  onChange,
  placeholder = '••••••••••••••••',
  disabled = false,
  onVerify,
  className = '',
}) => {
  const [show, setShow] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifiedState, setVerifiedState] = useState<'idle' | 'success' | 'failed'>('idle');

  const handleVerify = async () => {
    if (!onVerify || verifying || !value) return;
    setVerifying(true);
    setVerifiedState('idle');
    try {
      const ok = await onVerify();
      setVerifiedState(ok ? 'success' : 'failed');
    } catch {
      setVerifiedState('failed');
    } finally {
      setVerifying(false);
      setTimeout(() => setVerifiedState('idle'), 3000);
    }
  };

  return (
    <div className={`flex items-center gap-2 w-full sm:w-80 ${className}`}>
      <div className="relative flex-1">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full py-2 pl-3 pr-9 bg-[#2A2D35] hover:bg-[#323640] border border-[#3A3D45] focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] rounded-lg text-white text-sm outline-none transition-colors duration-150 font-mono disabled:opacity-50"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setShow(!show)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-white transition-colors"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>

      {onVerify && value && (
        <button
          type="button"
          onClick={handleVerify}
          disabled={verifying || disabled}
          className={`
            px-3 py-2 text-xs font-medium rounded-lg border transition-all flex items-center gap-1.5 whitespace-nowrap
            ${verifiedState === 'success'
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
              : verifiedState === 'failed'
              ? 'bg-red-500/20 text-red-400 border-red-500/30'
              : 'bg-[#2A2D35] hover:bg-[#323640] text-[#9CA3AF] hover:text-white border-[#3A3D45]'
            }
          `}
        >
          {verifying ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : verifiedState === 'success' ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Valid</span>
            </>
          ) : (
            <span>Test</span>
          )}
        </button>
      )}
    </div>
  );
};
