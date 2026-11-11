import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  description?: string;
}

interface SelectDropdownProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

export const SelectDropdown: React.FC<SelectDropdownProps> = ({
  value,
  onChange,
  options,
  disabled = false,
  className = '',
  placeholder,
}) => {
  return (
    <div className={`relative inline-block w-full sm:w-64 ${className}`}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`
          w-full appearance-none pl-3 pr-9 py-2 bg-[#2A2D35] hover:bg-[#323640] border border-[#3A3D45]
          focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] rounded-lg text-white text-sm
          outline-none transition-colors duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
        `}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-[#1F2228] text-white py-1">
            {opt.label}
          </option>
        ))}
      </select>
      <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-[#9CA3AF]">
        <ChevronDown className="w-4 h-4" />
      </div>
    </div>
  );
};
