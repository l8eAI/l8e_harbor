import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeftIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { YamlEditor } from '@/components/editor/YamlEditor';
import { useRoute, useAsyncOperation } from '@/hooks/useApi';
import { apiClient } from '@/utils/api';
import { 
  validateRouteSpec, 
  routeSpecToYaml, 
  yamlToRouteSpec, 
  validateYaml 
} from '@/utils/validation';
import type { ValidationError, RouteSpec } from '@/types';

export function RouteEditor() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditing = Boolean(id);
  
  const { data: existingRoute, loading: loadingRoute } = useRoute(id || '');
  
  const [yamlContent, setYamlContent] = useState('');
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  
  const { execute: saveRoute, loading: saving } = useAsyncOperation(
    (routeId: string, routeData: Partial<RouteSpec>) => 
      isEditing 
        ? apiClient.updateRoute(routeId, routeData)
        : apiClient.createRoute(routeId, routeData)
  );

  // Initialize YAML content
  useEffect(() => {
    if (isEditing && existingRoute) {
      setYamlContent(routeSpecToYaml(existingRoute));
    } else if (!isEditing && !yamlContent) {
      // Set default template for new routes
      const defaultRoute: Partial<RouteSpec> = {
        id: 'new-route',
        description: 'New route description',
        path: '/api/v1',
        methods: ['GET', 'POST'],
        backends: [{
          url: 'http://example-service:8080',
          weight: 100,
          health_check_path: '/healthz'
        }],
        priority: 10,
        timeout_ms: 5000,
        strip_prefix: true,
        sticky_session: false,
        retry_policy: {
          max_retries: 2,
          backoff_ms: 200,
          retry_on: ['5xx', 'timeout']
        },
        circuit_breaker: {
          enabled: true,
          failure_threshold: 50,
          minimum_requests: 20,
          interval_ms: 60000,
          timeout_ms: 30000
        },
        middleware: [{
          name: 'logging',
          config: { level: 'info' }
        }],
        matchers: []
      };
      setYamlContent(routeSpecToYaml(defaultRoute));
    }
  }, [existingRoute, isEditing, yamlContent]);

  const handleYamlChange = (newYaml: string) => {
    setYamlContent(newYaml);
    setHasChanges(true);
  };

  const handleValidationChange = (errors: ValidationError[]) => {
    setValidationErrors(errors);
  };

  const handleSave = async () => {
    // First validate YAML syntax
    const { isValid, errors: yamlErrors } = validateYaml(yamlContent);
    if (!isValid) {
      setValidationErrors(yamlErrors);
      return;
    }

    try {
      // Parse YAML to route spec
      const routeSpec = yamlToRouteSpec(yamlContent);
      
      // Validate route specification
      const routeErrors = validateRouteSpec(routeSpec);
      if (routeErrors.length > 0) {
        setValidationErrors(routeErrors);
        return;
      }

      // Save route
      await saveRoute(routeSpec.id, routeSpec);
      
      // Navigate back to route list
      navigate('/routes');
    } catch (error) {
      console.error('Failed to save route:', error);
      setValidationErrors([{
        field: 'save',
        message: error instanceof Error ? error.message : 'Failed to save route'
      }]);
    }
  };

  const handleCancel = () => {
    if (hasChanges && !confirm('You have unsaved changes. Are you sure you want to cancel?')) {
      return;
    }
    navigate('/routes');
  };

  const canSave = yamlContent && validationErrors.length === 0 && !saving;

  if (isEditing && loadingRoute) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-primary-500">Loading route...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/routes')}
            leftIcon={<ArrowLeftIcon className="h-4 w-4" />}
          >
            Back to Routes
          </Button>
          <div>
            <h1 className="text-2xl font-semibold text-primary-900">
              {isEditing ? `Edit Route: ${id}` : 'Create New Route'}
            </h1>
            <p className="text-primary-600">
              {isEditing 
                ? 'Modify the route configuration below and save your changes'
                : 'Define your new route configuration in YAML format'
              }
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            onClick={handleCancel}
            leftIcon={<XMarkIcon className="h-4 w-4" />}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!canSave}
            loading={saving}
            leftIcon={<CheckIcon className="h-4 w-4" />}
          >
            {isEditing ? 'Save Changes' : 'Create Route'}
          </Button>
        </div>
      </div>

      {/* Validation summary */}
      {validationErrors.length > 0 && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Please fix the following errors before saving:
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <ul className="list-disc list-inside space-y-1">
                  {validationErrors.map((error, index) => (
                    <li key={index}>
                      <strong>{error.field}</strong>: {error.message}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Split view: Editor + Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* YAML Editor */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-primary-900">YAML Configuration</h2>
          <YamlEditor
            value={yamlContent}
            onChange={handleYamlChange}
            onValidationChange={handleValidationChange}
            height="600px"
            showValidation={true}
            autoFormat={true}
          />
        </div>

        {/* Preview Panel */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-primary-900">Route Preview</h2>
          <div className="bg-white border border-primary-300 rounded-lg p-6">
            {yamlContent && validationErrors.length === 0 ? (
              <RoutePreview yamlContent={yamlContent} />
            ) : (
              <div className="text-center text-primary-500 py-8">
                <p>Fix validation errors to see route preview</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Route preview component
function RoutePreview({ yamlContent }: { yamlContent: string }) {
  const [route, setRoute] = useState<RouteSpec | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const parsed = yamlToRouteSpec(yamlContent);
      setRoute(parsed);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse YAML');
      setRoute(null);
    }
  }, [yamlContent]);

  if (error) {
    return (
      <div className="text-red-600">
        <p className="font-medium">Parse Error:</p>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!route) {
    return <div className="text-primary-500">No valid route to preview</div>;
  }

  return (
    <div className="space-y-4">
      {/* Route summary */}
      <div>
        <h3 className="font-medium text-primary-900">{route.id}</h3>
        {route.description && (
          <p className="text-sm text-primary-600">{route.description}</p>
        )}
      </div>

      {/* Route details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="font-medium text-primary-700">Path:</span>
          <span className="ml-2">{route.path}</span>
        </div>
        <div>
          <span className="font-medium text-primary-700">Priority:</span>
          <span className="ml-2">{route.priority}</span>
        </div>
        <div>
          <span className="font-medium text-primary-700">Methods:</span>
          <span className="ml-2">{route.methods.join(', ')}</span>
        </div>
        <div>
          <span className="font-medium text-primary-700">Timeout:</span>
          <span className="ml-2">{route.timeout_ms}ms</span>
        </div>
      </div>

      {/* Backends */}
      <div>
        <h4 className="font-medium text-primary-700 mb-2">Backends</h4>
        <div className="space-y-2">
          {route.backends.map((backend, index) => (
            <div key={index} className="bg-primary-50 p-3 rounded text-sm">
              <div className="font-medium">{backend.url}</div>
              <div className="text-primary-600">
                Weight: {backend.weight}, Health Check: {backend.health_check_path}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Middleware */}
      {route.middleware.length > 0 && (
        <div>
          <h4 className="font-medium text-primary-700 mb-2">Middleware</h4>
          <div className="space-y-2">
            {route.middleware.map((middleware, index) => (
              <div key={index} className="bg-primary-50 p-3 rounded text-sm">
                <div className="font-medium">{middleware.name}</div>
                {Object.keys(middleware.config).length > 0 && (
                  <div className="text-primary-600">
                    Config: {JSON.stringify(middleware.config)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Circuit breaker and retry policy */}
      {(route.circuit_breaker.enabled || route.retry_policy.max_retries > 0) && (
        <div className="space-y-2">
          {route.circuit_breaker.enabled && (
            <div className="text-sm">
              <span className="font-medium text-primary-700">Circuit Breaker:</span>
              <span className="ml-2">
                {route.circuit_breaker.failure_threshold}% failure threshold, 
                {route.circuit_breaker.minimum_requests} min requests
              </span>
            </div>
          )}
          {route.retry_policy.max_retries > 0 && (
            <div className="text-sm">
              <span className="font-medium text-primary-700">Retry Policy:</span>
              <span className="ml-2">
                Max {route.retry_policy.max_retries} retries, 
                {route.retry_policy.backoff_ms}ms backoff
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}