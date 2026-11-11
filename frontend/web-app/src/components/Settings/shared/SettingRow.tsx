import React, { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface SettingRowProps {
  icon?: LucideIcon;
  label: string;
  description?: string;
  children: ReactNode;
  badge?: string;
  disabled?: boolean;
  error?: string;
  danger?: boolean;
  id?: string;
}

export const SettingRow: React.FC<SettingRowProps> = ({
  icon: Icon,
  label,
  description,
  children,
  badge,
  disabled = false,
  error,
  danger = false,
  id,
}) => {
  return (
    <div
      id={id}
      className={`
        flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3.5 px-4 rounded-xl
        transition-colors duration-150 border border-transparent hover:border-[#2A2D35] hover:bg-[#252830]/40
        ${disabled ? 'opacity-50 pointer-events-none' : ''}
        ${danger ? 'hover:border-red-500/20 hover:bg-red-500/5' : ''}
      `}
    >
      <div className="flex items-start gap-3 flex-1 min-w-0 pr-2">
        {Icon && (
          <div
            className={`
              p-2 rounded-lg mt-0.5 shrink-0
              ${danger ? 'bg-red-500/10 text-red-400' : 'bg-[#2A2D35] text-[#9CA3AF]'}
            `}
          >
            <Icon className="w-4 h-4" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`text-sm font-medium ${danger ? 'text-red-400' : 'text-white'}`}
            >
              {label}
            </span>
            {badge && (
              <span className="px-1.5 py-0.5 text-[10px] uppercase font-semibold tracking-wider rounded bg-[#3B82F6]/20 text-[#3B82F6] border border-[#3B82F6]/30">
                {badge}
              </span>
            )}
          </div>
          {description && (
            <p className="text-xs text-[#9CA3AF] mt-0.5 leading-relaxed break-words">
              {description}
            </p>
          )}
          {error && (
            <p className="text-xs text-red-400 mt-1">{error}</p>
          )}
        </div>
      </div>

      <div className="shrink-0 flex items-center justify-end self-end sm:self-center">
        {children}
      </div>
    </div>
  );
};
