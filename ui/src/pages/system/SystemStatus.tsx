import React from 'react';
import { 
  ArrowPathIcon,
  ServerIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { useSystemStatus } from '@/hooks/useApi';
import { formatDistanceToNow } from 'date-fns';
import type { SystemStatus as SystemStatusType } from '@/types';

export function SystemStatus() {
  const { data: status, loading, error, refetch } = useSystemStatus();

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-primary-200 rounded w-1/3"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-primary-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-primary-900 mb-2">
          Unable to Load System Status
        </h3>
        <p className="text-primary-600 mb-4">
          {error || 'Failed to fetch system status'}
        </p>
        <Button onClick={refetch} leftIcon={<ArrowPathIcon className="h-4 w-4" />}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary-900">System Status</h1>
          <p className="text-primary-600">
            Monitor l8e-harbor health and performance
          </p>
        </div>
        <Button
          variant="outline"
          onClick={refetch}
          leftIcon={<ArrowPathIcon className="h-4 w-4" />}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Service Status */}
        <StatusCard
          title="Service Status"
          value={status.service}
          icon={<ServerIcon className="h-6 w-6" />}
          variant={status.service === 'UP' ? 'success' : 'error'}
          subtitle={status.uptime ? `Up for ${formatDistanceToNow(status.uptime)}` : undefined}
        />

        {/* Route Store */}
        <StatusCard
          title="Route Store"
          value={status.route_store_sync.status}
          icon={<ChartBarIcon className="h-6 w-6" />}
          variant={status.route_store_sync.status === 'OK' ? 'success' : 'error'}
          subtitle={`Last sync: ${formatDistanceToNow(new Date(status.route_store_sync.last_sync), { addSuffix: true })}`}
        />

        {/* Secret Provider */}
        <StatusCard
          title="Secret Provider"
          value={status.secret_provider.status}
          icon={<ServerIcon className="h-6 w-6" />}
          variant={status.secret_provider.status === 'OK' ? 'success' : 'error'}
          subtitle="Connected"
        />

        {/* Backend Health */}
        <StatusCard
          title="Backend Health"
          value={`${status.backend_health.healthy}/${status.backend_health.total}`}
          icon={<ServerIcon className="h-6 w-6" />}
          variant={status.backend_health.healthy === status.backend_health.total ? 'success' : 'warning'}
          subtitle="Backends healthy"
        />
      </div>

      {/* Metrics Overview */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <h2 className="text-lg font-medium text-primary-900 mb-4">Quick Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            label="Total Routes"
            value={status.metrics.total_routes}
            unit="routes"
          />
          <MetricCard
            label="Request Rate"
            value={status.metrics.request_rate}
            unit="req/sec"
            precision={1}
          />
          <MetricCard
            label="Error Rate"
            value={status.metrics.error_rate}
            unit="%"
            precision={2}
            variant={status.metrics.error_rate > 5 ? 'error' : 'success'}
          />
          <MetricCard
            label="Avg Response Time"
            value={status.metrics.avg_response_time}
            unit="ms"
            precision={0}
          />
        </div>
      </div>

      {/* Recent Events */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <h2 className="text-lg font-medium text-primary-900 mb-4 flex items-center">
          <ClockIcon className="h-5 w-5 mr-2" />
          Recent Events
        </h2>
        {status.recent_events.length === 0 ? (
          <p className="text-center text-primary-500 py-8">
            No recent events
          </p>
        ) : (
          <div className="space-y-3">
            {status.recent_events.map((event, index) => (
              <EventItem key={index} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Status card component
interface StatusCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  variant: 'success' | 'warning' | 'error' | 'info';
  subtitle?: string;
}

function StatusCard({ title, value, icon, variant, subtitle }: StatusCardProps) {
  const getColors = (variant: string) => {
    switch (variant) {
      case 'success':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-harbor-600 bg-harbor-100';
    }
  };

  return (
    <div className="bg-white shadow-sm rounded-lg p-6">
      <div className="flex items-center">
        <div className={`flex-shrink-0 p-2 rounded-lg ${getColors(variant)}`}>
          {icon}
        </div>
        <div className="ml-4 flex-1 min-w-0">
          <p className="text-sm font-medium text-primary-600 truncate">{title}</p>
          <div className="flex items-center">
            <p className="text-lg font-semibold text-primary-900">{value}</p>
            <StatusBadge 
              status={variant === 'success' ? 'healthy' : variant === 'error' ? 'unhealthy' : 'unknown'} 
            />
          </div>
          {subtitle && (
            <p className="text-sm text-primary-500 truncate">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Metric card component
interface MetricCardProps {
  label: string;
  value: number;
  unit: string;
  precision?: number;
  variant?: 'success' | 'warning' | 'error' | 'info';
}

function MetricCard({ 
  label, 
  value, 
  unit, 
  precision = 0, 
  variant = 'info' 
}: MetricCardProps) {
  const formatValue = (val: number) => {
    if (precision === 0) return val.toString();
    return val.toFixed(precision);
  };

  const getTextColor = () => {
    switch (variant) {
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-primary-900';
    }
  };

  return (
    <div className="text-center">
      <p className="text-sm text-primary-600">{label}</p>
      <p className={`text-2xl font-semibold ${getTextColor()}`}>
        {formatValue(value)}
        <span className="text-lg text-primary-500 ml-1">{unit}</span>
      </p>
    </div>
  );
}

// Event item component
function EventItem({ event }: { event: SystemStatusType['recent_events'][0] }) {
  const getEventIcon = (type: string) => {
    switch (type) {
      case 'route_change':
        return <ChartBarIcon className="h-4 w-4 text-blue-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />;
      case 'restart':
        return <ArrowPathIcon className="h-4 w-4 text-green-500" />;
      default:
        return <ServerIcon className="h-4 w-4 text-primary-500" />;
    }
  };

  const getBadgeVariant = (type: string) => {
    switch (type) {
      case 'route_change':
        return 'info' as const;
      case 'error':
        return 'error' as const;
      case 'restart':
        return 'success' as const;
      default:
        return 'default' as const;
    }
  };

  return (
    <div className="flex items-center justify-between p-3 bg-primary-50 rounded-lg">
      <div className="flex items-center space-x-3">
        {getEventIcon(event.type)}
        <div>
          <p className="text-sm font-medium text-primary-900">{event.message}</p>
          <p className="text-xs text-primary-500">
            {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>
      <Badge variant={getBadgeVariant(event.type)} size="sm">
        {event.type.replace('_', ' ')}
      </Badge>
    </div>
  );
}