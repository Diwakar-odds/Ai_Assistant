import React from 'react';
import { motion } from 'framer-motion';

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
  id?: string;
  ariaLabel?: string;
}

export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  id,
  ariaLabel,
}) => {
  const isSm = size === 'sm';
  const widthClass = isSm ? 'w-9 h-5' : 'w-11 h-6';
  const knobSize = isSm ? 'h-4 w-4' : 'h-5 w-5';
  const translateClass = isSm ? 'translate-x-4' : 'translate-x-5';

  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`
        relative inline-flex items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-[#3B82F6]/50 focus:ring-offset-2 focus:ring-offset-[#1F2228]
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${checked ? 'bg-[#3B82F6]' : 'bg-[#2A2D35] hover:bg-[#3A3D45]'}
        ${widthClass} border border-[#3A3D45]
      `}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={`
          inline-block transform rounded-full bg-white shadow-md transition-transform
          ${knobSize} ${checked ? translateClass : 'translate-x-0.5'}
        `}
      />
    </button>
  );
};
