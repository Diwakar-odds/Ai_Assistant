import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';

interface TagInputProps {
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  disabled?: boolean;
}

export const TagInput: React.FC<TagInputProps> = ({
  values,
  onChange,
  placeholder = 'Add phrase...',
  maxTags = 10,
  disabled = false,
}) => {
  const [inputVal, setInputVal] = useState('');

  const addTag = (text: string) => {
    const trimmed = text.trim().toLowerCase();
    if (trimmed && !values.includes(trimmed) && values.length < maxTags) {
      onChange([...values, trimmed]);
      setInputVal('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(inputVal);
    } else if (e.key === 'Backspace' && !inputVal && values.length > 0) {
      removeTag(values.length - 1);
    }
  };

  const removeTag = (idx: number) => {
    if (disabled) return;
    onChange(values.filter((_, i) => i !== idx));
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 p-2 bg-[#2A2D35] border border-[#3A3D45] rounded-lg min-h-[42px] w-full focus-within:border-[#3B82F6] transition-colors">
      {values.map((tag, idx) => (
        <span
          key={`${tag}-${idx}`}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-[#3B82F6]/20 border border-[#3B82F6]/40 rounded-md"
        >
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={() => removeTag(idx)}
              className="hover:text-red-400 focus:outline-none transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}
      {values.length < maxTags && !disabled && (
        <div className="flex items-center gap-1 flex-1 min-w-[120px]">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={values.length === 0 ? placeholder : ''}
            className="flex-1 bg-transparent text-sm text-white placeholder-[#9CA3AF] outline-none px-1 py-0.5"
          />
          {inputVal.trim() && (
            <button
              type="button"
              onClick={() => addTag(inputVal)}
              className="p-1 text-xs text-[#3B82F6] hover:bg-[#3B82F6]/10 rounded"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
};
