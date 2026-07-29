import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-8 rounded-2xl border border-dashed border-white/10 bg-white/[0.01] py-16">
      {Icon && <Icon className="h-10 w-10 text-slate-600 mb-4" />}
      <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      {description && <p className="text-xs text-slate-500 mt-1.5 max-w-xs">{description}</p>}
      {action && (
        <button onClick={action.onClick} className="btn-primary mt-4 py-2 px-4 text-xs font-medium">
          {action.label}
        </button>
      )}
    </div>
  );
}