"use client";
import React from 'react';

interface DateRangePickerProps {
  value: { from: string; to: string };
  onChange: (range: { from: string; to: string }) => void;
  label?: string;
}

export function DateRangePicker({ value, onChange, label }: DateRangePickerProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="stat-label">{label}</label>}
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={value.from}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          className="vault-input py-2 text-xs"
        />
        <span className="text-slate-600 text-xs">to</span>
        <input
          type="date"
          value={value.to}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          className="vault-input py-2 text-xs"
        />
      </div>
    </div>
  );
}