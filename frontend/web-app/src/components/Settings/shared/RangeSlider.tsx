import React from 'react';

interface RangeSliderProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  showValue?: boolean;
  disabled?: boolean;
}

export const RangeSlider: React.FC<RangeSliderProps> = ({
  value,
  onChange,
  min,
  max,
  step = 1,
  unit = '',
  showValue = true,
  disabled = false,
}) => {
  const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));

  return (
    <div className="flex items-center gap-3 w-full sm:w-64">
      <div className="relative flex-1 flex items-center">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={Number.isNaN(value) ? min : value}
          disabled={disabled}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-[#2A2D35] rounded-lg appearance-none cursor-pointer accent-[#3B82F6] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none"
          style={{
            background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${percentage}%, #2A2D35 ${percentage}%, #2A2D35 100%)`,
          }}
        />
      </div>
      {showValue && (
        <span className="min-w-[3.5rem] px-2 py-1 text-center text-xs font-mono font-medium text-white bg-[#2A2D35] border border-[#3A3D45] rounded-md shadow-inner">
          {Number.isInteger(value) ? value : value.toFixed(1)}
          {unit ? ` ${unit}` : ''}
        </span>
      )}
    </div>
  );
};
