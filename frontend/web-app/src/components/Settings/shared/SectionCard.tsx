import React, { ReactNode, useState } from 'react';
import { LucideIcon, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SectionCardProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: string;
  children: ReactNode;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  className?: string;
  danger?: boolean;
  action?: ReactNode;
}

export const SectionCard: React.FC<SectionCardProps> = ({
  title,
  description,
  icon: Icon,
  badge,
  children,
  collapsible = false,
  defaultExpanded = true,
  className = '',
  danger = false,
  action,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div
      className={`
        bg-[#1F2228] border rounded-xl overflow-hidden shadow-lg transition-all
        ${danger ? 'border-red-500/30 bg-red-950/10' : 'border-[#2A2D35]'}
        ${className}
      `}
    >
      <div
        className={`
          flex items-center justify-between px-5 py-4 border-b border-[#2A2D35]
          ${collapsible ? 'cursor-pointer hover:bg-[#252830]/50 select-none' : ''}
        `}
        onClick={() => collapsible && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {Icon && (
            <div
              className={`
                p-2 rounded-lg
                ${danger ? 'bg-red-500/10 text-red-400' : 'bg-[#2A2D35] text-[#3B82F6]'}
              `}
            >
              <Icon className="w-5 h-5" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <h4 className={`text-base font-semibold ${danger ? 'text-red-400' : 'text-white'}`}>
                {title}
              </h4>
              {badge && (
                <span className="px-2 py-0.5 text-[10px] uppercase font-semibold rounded-full bg-[#3B82F6]/20 text-[#3B82F6] border border-[#3B82F6]/30">
                  {badge}
                </span>
              )}
            </div>
            {description && (
              <p className="text-xs text-[#9CA3AF] mt-0.5">{description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {action}
          {collapsible && (
            <motion.div
              animate={{ rotate: expanded ? 0 : -90 }}
              transition={{ duration: 0.2 }}
              className="text-[#9CA3AF] p-1 cursor-pointer"
              onClick={() => setExpanded(!expanded)}
            >
              <ChevronDown className="w-4 h-4" />
            </motion.div>
          )}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {(!collapsible || expanded) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="p-4 sm:p-5 divide-y divide-[#2A2D35]/50"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
