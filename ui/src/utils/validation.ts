import * as yaml from 'js-yaml';
import type { RouteSpec, ValidationError, RouteFormData } from '@/types';

// YAML validation utilities
export function validateYaml(yamlString: string): { isValid: boolean; errors: ValidationError[] } {
  const errors: ValidationError[] = [];
  
  try {
    const parsed = yaml.load(yamlString);
    
    if (!parsed || typeof parsed !== 'object') {
      errors.push({
        field: 'root',
        message: 'YAML must contain a valid object',
        line: 1,
      });
    }
    
    return { isValid: errors.length === 0, errors };
  } catch (error) {
    if (error instanceof yaml.YAMLException) {
      errors.push({
        field: 'yaml',
        message: error.message,
        line: error.mark?.line ? error.mark.line + 1 : undefined,
      });
    } else {
      errors.push({
        field: 'yaml',
        message: 'Invalid YAML syntax',
      });
    }
    
    return { isValid: false, errors };
  }
}

// Route specification validation
export function validateRouteSpec(route: Partial<RouteSpec>): ValidationError[] {
  const errors: ValidationError[] = [];
  
  // Required fields
  if (!route.id) {
    errors.push({ field: 'id', message: 'Route ID is required' });
  } else if (!/^[a-z0-9-]+$/.test(route.id)) {
    errors.push({ field: 'id', message: 'Route ID must contain only lowercase letters, numbers, and hyphens' });
  }
  
  if (!route.path) {
    errors.push({ field: 'path', message: 'Path is required' });
  } else if (!route.path.startsWith('/')) {
    errors.push({ field: 'path', message: 'Path must start with /' });
  }
  
  if (!route.backends || route.backends.length === 0) {
    errors.push({ field: 'backends', message: 'At least one backend is required' });
  } else {
    // Validate each backend
    route.backends.forEach((backend, index) => {
      if (!backend.url) {
        errors.push({
          field: `backends[${index}].url`,
          message: 'Backend URL is required',
        });
      } else {
        try {
          new URL(backend.url);
        } catch {
          errors.push({
            field: `backends[${index}].url`,
            message: 'Backend URL must be a valid HTTP/HTTPS URL',
          });
        }
      }
      
      if (backend.weight !== undefined && (backend.weight < 1 || backend.weight > 1000)) {
        errors.push({
          field: `backends[${index}].weight`,
          message: 'Backend weight must be between 1 and 1000',
        });
      }
    });
  }
  
  // Validate methods
  if (route.methods && route.methods.length > 0) {
    const validMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'];
    const invalidMethods = route.methods.filter(method => !validMethods.includes(method.toUpperCase()));
    
    if (invalidMethods.length > 0) {
      errors.push({
        field: 'methods',
        message: `Invalid HTTP methods: ${invalidMethods.join(', ')}`,
      });
    }
  }
  
  // Validate priority
  if (route.priority !== undefined && route.priority < 0) {
    errors.push({ field: 'priority', message: 'Priority must be a non-negative number' });
  }
  
  // Validate timeout
  if (route.timeout_ms !== undefined && (route.timeout_ms < 100 || route.timeout_ms > 300000)) {
    errors.push({
      field: 'timeout_ms',
      message: 'Timeout must be between 100ms and 300000ms (5 minutes)',
    });
  }
  
  // Validate retry policy
  if (route.retry_policy) {
    if (route.retry_policy.max_retries < 0 || route.retry_policy.max_retries > 10) {
      errors.push({
        field: 'retry_policy.max_retries',
        message: 'Max retries must be between 0 and 10',
      });
    }
    
    if (route.retry_policy.backoff_ms < 0) {
      errors.push({
        field: 'retry_policy.backoff_ms',
        message: 'Backoff time must be non-negative',
      });
    }
    
    const validRetryOn = ['5xx', 'gateway-error', 'timeout'];
    const invalidRetryOn = route.retry_policy.retry_on?.filter(
      condition => !validRetryOn.includes(condition)
    );
    
    if (invalidRetryOn && invalidRetryOn.length > 0) {
      errors.push({
        field: 'retry_policy.retry_on',
        message: `Invalid retry conditions: ${invalidRetryOn.join(', ')}`,
      });
    }
  }
  
  // Validate circuit breaker
  if (route.circuit_breaker?.enabled) {
    if (route.circuit_breaker.failure_threshold < 1 || route.circuit_breaker.failure_threshold > 100) {
      errors.push({
        field: 'circuit_breaker.failure_threshold',
        message: 'Failure threshold must be between 1 and 100 percent',
      });
    }
    
    if (route.circuit_breaker.minimum_requests < 1) {
      errors.push({
        field: 'circuit_breaker.minimum_requests',
        message: 'Minimum requests must be at least 1',
      });
    }
  }
  
  return errors;
}

// Convert route spec to form data
export function routeSpecToFormData(route: RouteSpec): RouteFormData {
  return {
    id: route.id,
    description: route.description || '',
    path: route.path,
    methods: route.methods,
    backends: route.backends,
    priority: route.priority,
    strip_prefix: route.strip_prefix,
    sticky_session: route.sticky_session,
    timeout_ms: route.timeout_ms,
    retry_policy: route.retry_policy,
    circuit_breaker: route.circuit_breaker,
    middleware: route.middleware,
    matchers: route.matchers || [],
  };
}

// Convert form data to route spec
export function formDataToRouteSpec(formData: RouteFormData): Partial<RouteSpec> {
  return {
    id: formData.id,
    description: formData.description || undefined,
    path: formData.path,
    methods: formData.methods,
    backends: formData.backends,
    priority: formData.priority,
    strip_prefix: formData.strip_prefix,
    sticky_session: formData.sticky_session,
    timeout_ms: formData.timeout_ms,
    retry_policy: formData.retry_policy,
    circuit_breaker: formData.circuit_breaker,
    middleware: formData.middleware,
    matchers: formData.matchers.length > 0 ? formData.matchers : undefined,
  };
}

// Convert route spec to YAML string
export function routeSpecToYaml(route: RouteSpec | Partial<RouteSpec>): string {
  const routeData = {
    apiVersion: 'harbor.l8e/v1',
    kind: 'Route',
    metadata: {
      name: route.id,
    },
    spec: {
      ...route,
    },
  };
  
  // Remove metadata fields from spec
  delete (routeData.spec as any).created_at;
  delete (routeData.spec as any).updated_at;
  
  return yaml.dump(routeData, {
    indent: 2,
    lineWidth: 120,
    noRefs: true,
  });
}

// Parse YAML to route spec
export function yamlToRouteSpec(yamlString: string): RouteSpec {
  const parsed = yaml.load(yamlString) as any;
  
  if (!parsed?.spec) {
    throw new Error('YAML must contain a spec field');
  }
  
  return {
    ...parsed.spec,
    id: parsed.spec.id || parsed.metadata?.name,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  } as RouteSpec;
}

// Format validation errors for display
export function formatValidationErrors(errors: ValidationError[]): string {
  if (errors.length === 0) return '';
  
  return errors
    .map(error => {
      const location = error.line ? ` (line ${error.line})` : '';
      return `${error.field}${location}: ${error.message}`;
    })
    .join('\n');
}