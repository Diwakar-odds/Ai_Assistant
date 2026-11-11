import React from 'react';
import { LucideIcon } from 'lucide-react';

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  type?: 'text' | 'number' | 'email';
  className?: string;
  icon?: LucideIcon;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

export const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  placeholder = '',
  disabled = false,
  type = 'text',
  className = '',
  icon: Icon,
  onKeyDown,
}) => {
  return (
    <div className={`relative w-full sm:w-64 ${className}`}>
      {Icon && (
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] pointer-events-none">
          <Icon className="w-4 h-4" />
        </div>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className={`
          w-full py-2 bg-[#2A2D35] hover:bg-[#323640] border border-[#3A3D45]
          focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] rounded-lg text-white text-sm
          outline-none transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed
          ${Icon ? 'pl-9 pr-3' : 'px-3'}
        `}
      />
    </div>
  );
};
