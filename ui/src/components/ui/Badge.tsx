import React from 'react';
import clsx from 'clsx';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Badge({ 
  children, 
  variant = 'default', 
  size = 'md', 
  className 
}: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        
        // Size variants
        {
          'px-2 py-0.5 text-xs': size === 'sm',
          'px-2.5 py-0.5 text-sm': size === 'md',
          'px-3 py-1 text-sm': size === 'lg',
        },
        
        // Color variants
        {
          'bg-primary-100 text-primary-800': variant === 'default',
          'bg-green-100 text-green-800': variant === 'success',
          'bg-yellow-100 text-yellow-800': variant === 'warning',
          'bg-red-100 text-red-800': variant === 'error',
          'bg-blue-100 text-blue-800': variant === 'info',
        },
        
        className
      )}
    >
      {children}
    </span>
  );
}

// Status-specific badge components
export function StatusBadge({ status }: { status: 'healthy' | 'unhealthy' | 'unknown' }) {
  const variant = {
    healthy: 'success' as const,
    unhealthy: 'error' as const,
    unknown: 'warning' as const,
  }[status];

  const label = {
    healthy: 'Healthy',
    unhealthy: 'Unhealthy', 
    unknown: 'Unknown',
  }[status];

  return <Badge variant={variant}>{label}</Badge>;
}

export function MethodBadge({ method }: { method: string }) {
  const variant = {
    GET: 'info' as const,
    POST: 'success' as const,
    PUT: 'warning' as const,
    DELETE: 'error' as const,
    PATCH: 'default' as const,
    OPTIONS: 'default' as const,
    HEAD: 'default' as const,
  }[method] || 'default' as const;

  return <Badge variant={variant} size="sm">{method}</Badge>;
}