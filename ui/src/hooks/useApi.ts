import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/utils/api';
import type { RouteSpec, SystemStatus, TestRequest, TestResponse } from '@/types';

// Generic API hook for data fetching
export function useApi<T>(
  fetchFn: () => Promise<T>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchFn();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [fetchFn]);

  useEffect(() => {
    refetch();
  }, dependencies);

  return {
    data,
    loading,
    error,
    refetch,
  };
}

// Hook for managing routes
export function useRoutes(filters?: { path?: string; backend?: string }) {
  const fetchRoutes = useCallback(
    () => apiClient.getRoutes(filters),
    [filters?.path, filters?.backend]
  );

  const { data, loading, error, refetch } = useApi(fetchRoutes, [filters]);

  const createRoute = useCallback(async (id: string, route: Partial<RouteSpec>) => {
    await apiClient.createRoute(id, route);
    await refetch();
  }, [refetch]);

  const updateRoute = useCallback(async (id: string, route: Partial<RouteSpec>) => {
    await apiClient.updateRoute(id, route);
    await refetch();
  }, [refetch]);

  const deleteRoute = useCallback(async (id: string) => {
    await apiClient.deleteRoute(id);
    await refetch();
  }, [refetch]);

  return {
    routes: data?.routes || [],
    loading,
    error,
    refetch,
    createRoute,
    updateRoute,
    deleteRoute,
  };
}

// Hook for a single route
export function useRoute(id: string) {
  const fetchRoute = useCallback(() => apiClient.getRoute(id), [id]);
  
  return useApi(fetchRoute, [id]);
}

// Hook for system status
export function useSystemStatus() {
  const fetchStatus = useCallback(() => apiClient.getSystemStatus(), []);
  
  return useApi(fetchStatus);
}

// Hook for route testing
export function useRouteTest() {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const testRoute = useCallback(async (routeId: string, testRequest: TestRequest) => {
    try {
      setTesting(true);
      setTestError(null);
      const result = await apiClient.testRoute(routeId, testRequest);
      setTestResult(result);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Test failed';
      setTestError(message);
      setTestResult(null);
      throw error;
    } finally {
      setTesting(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setTestResult(null);
    setTestError(null);
  }, []);

  return {
    testing,
    testResult,
    testError,
    testRoute,
    clearResults,
  };
}

// Hook for backend health checks
export function useBackendHealth(backendUrl?: string) {
  const [checking, setChecking] = useState(false);
  const [health, setHealth] = useState<{ healthy: boolean; response_time?: number; error?: string } | null>(null);

  const checkHealth = useCallback(async (url: string) => {
    try {
      setChecking(true);
      const result = await apiClient.checkBackendHealth(url);
      setHealth(result);
      return result;
    } catch (error) {
      const errorResult = {
        healthy: false,
        error: error instanceof Error ? error.message : 'Health check failed',
      };
      setHealth(errorResult);
      return errorResult;
    } finally {
      setChecking(false);
    }
  }, []);

  // Auto-check health if backendUrl is provided
  useEffect(() => {
    if (backendUrl) {
      checkHealth(backendUrl);
    }
  }, [backendUrl, checkHealth]);

  return {
    checking,
    health,
    checkHealth,
  };
}

// Hook for async operations with loading states
export function useAsyncOperation<T extends any[], R>(
  operation: (...args: T) => Promise<R>
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<R | null>(null);

  const execute = useCallback(async (...args: T): Promise<R> => {
    try {
      setLoading(true);
      setError(null);
      const result = await operation(...args);
      setResult(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Operation failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [operation]);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setResult(null);
  }, []);

  return {
    loading,
    error,
    result,
    execute,
    reset,
  };
}

// Hook for debounced search
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Hook for local storage state
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
}