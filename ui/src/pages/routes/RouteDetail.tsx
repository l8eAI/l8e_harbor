import React from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeftIcon, 
  PencilIcon, 
  PlayIcon,
  ClockIcon,
  ServerIcon 
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Badge, MethodBadge, StatusBadge } from '@/components/ui/Badge';
import { useRoute, useBackendHealth } from '@/hooks/useApi';
import { usePermissions } from '@/hooks/useAuth';
import { formatDistanceToNow } from 'date-fns';
import type { RouteSpec } from '@/types';

export function RouteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const permissions = usePermissions();
  
  const { data: route, loading, error } = useRoute(id!);

  if (loading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-primary-200 rounded w-1/3"></div>
        <div className="space-y-4">
          <div className="h-4 bg-primary-200 rounded"></div>
          <div className="h-4 bg-primary-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (error || !route) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">
          {error || 'Route not found'}
        </div>
        <Link to="/routes">
          <Button variant="outline">Back to Routes</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/routes">
            <Button
              variant="ghost"
              leftIcon={<ArrowLeftIcon className="h-4 w-4" />}
            >
              Back to Routes
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-primary-900">{route.id}</h1>
            {route.description && (
              <p className="text-primary-600">{route.description}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <Link to={`/routes/${route.id}/test`}>
            <Button
              variant="outline"
              leftIcon={<PlayIcon className="h-4 w-4" />}
            >
              Test Route
            </Button>
          </Link>
          {permissions.canManageRoutes && (
            <Link to={`/routes/${route.id}/edit`}>
              <Button
                variant="primary"
                leftIcon={<PencilIcon className="h-4 w-4" />}
              >
                Edit Route
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Route overview */}
      <div className="bg-white shadow-sm rounded-lg p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-sm font-medium text-primary-500 mb-2">Path</h3>
            <p className="text-lg font-mono text-primary-900">{route.path}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-primary-500 mb-2">Methods</h3>
            <div className="flex flex-wrap gap-1">
              {route.methods.map(method => (
                <MethodBadge key={method} method={method} />
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium text-primary-500 mb-2">Priority</h3>
            <p className="text-lg text-primary-900">{route.priority}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Backends */}
        <div className="bg-white shadow-sm rounded-lg p-6">
          <h2 className="text-lg font-medium text-primary-900 mb-4 flex items-center">
            <ServerIcon className="h-5 w-5 mr-2" />
            Backends ({route.backends.length})
          </h2>
          <div className="space-y-4">
            {route.backends.map((backend, index) => (
              <BackendCard key={index} backend={backend} />
            ))}
          </div>
        </div>

        {/* Configuration */}
        <div className="bg-white shadow-sm rounded-lg p-6">
          <h2 className="text-lg font-medium text-primary-900 mb-4 flex items-center">
            <ClockIcon className="h-5 w-5 mr-2" />
            Configuration
          </h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-primary-700">Timeout:</span>
                <span className="ml-2">{route.timeout_ms}ms</span>
              </div>
              <div>
                <span className="font-medium text-primary-700">Strip Prefix:</span>
                <span className="ml-2">{route.strip_prefix ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="font-medium text-primary-700">Sticky Session:</span>
                <span className="ml-2">{route.sticky_session ? 'Yes' : 'No'}</span>
              </div>
              <div>
                <span className="font-medium text-primary-700">Last Modified:</span>
                <span className="ml-2">
                  {formatDistanceToNow(new Date(route.updated_at), { addSuffix: true })}
                </span>
              </div>
            </div>

            {/* Retry Policy */}
            {route.retry_policy.max_retries > 0 && (
              <div className="border-t pt-4">
                <h4 className="font-medium text-primary-700 mb-2">Retry Policy</h4>
                <div className="text-sm text-primary-600">
                  <p>Max retries: {route.retry_policy.max_retries}</p>
                  <p>Backoff: {route.retry_policy.backoff_ms}ms</p>
                  <p>Retry on: {route.retry_policy.retry_on.join(', ')}</p>
                </div>
              </div>
            )}

            {/* Circuit Breaker */}
            {route.circuit_breaker.enabled && (
              <div className="border-t pt-4">
                <h4 className="font-medium text-primary-700 mb-2">Circuit Breaker</h4>
                <div className="text-sm text-primary-600">
                  <p>Failure threshold: {route.circuit_breaker.failure_threshold}%</p>
                  <p>Minimum requests: {route.circuit_breaker.minimum_requests}</p>
                  <p>Timeout: {route.circuit_breaker.timeout_ms}ms</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Middleware */}
      {route.middleware.length > 0 && (
        <div className="bg-white shadow-sm rounded-lg p-6">
          <h2 className="text-lg font-medium text-primary-900 mb-4">
            Middleware ({route.middleware.length})
          </h2>
          <div className="space-y-3">
            {route.middleware.map((middleware, index) => (
              <div key={index} className="bg-primary-50 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-primary-900">{middleware.name}</h4>
                  <Badge variant="info">Active</Badge>
                </div>
                {Object.keys(middleware.config).length > 0 && (
                  <div className="mt-2">
                    <pre className="text-sm text-primary-700 bg-white p-2 rounded border">
                      {JSON.stringify(middleware.config, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Backend card component with health check
function BackendCard({ backend }: { backend: RouteSpec['backends'][0] }) {
  const { health, checking, checkHealth } = useBackendHealth(backend.url);
  
  return (
    <div className="border border-primary-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-primary-900">{backend.url}</h4>
        <div className="flex items-center space-x-2">
          {health && <StatusBadge status={health.healthy ? 'healthy' : 'unhealthy'} />}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => checkHealth(backend.url)}
            loading={checking}
          >
            Check Health
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm text-primary-600">
        <div>
          <span className="font-medium">Weight:</span>
          <span className="ml-1">{backend.weight}</span>
        </div>
        <div>
          <span className="font-medium">Health Check:</span>
          <span className="ml-1">{backend.health_check_path}</span>
        </div>
        {health?.response_time && (
          <div>
            <span className="font-medium">Response Time:</span>
            <span className="ml-1">{health.response_time}ms</span>
          </div>
        )}
        {health?.error && (
          <div className="col-span-2">
            <span className="font-medium text-red-600">Error:</span>
            <span className="ml-1 text-red-600">{health.error}</span>
          </div>
        )}
      </div>
    </div>
  );
}