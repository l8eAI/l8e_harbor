import type { 
  RouteSpec, 
  RouteListResponse, 
  LoginRequest, 
  LoginResponse,
  SystemStatus,
  ApiError,
  TestRequest,
  TestResponse
} from '@/types';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// HTTP client with error handling
class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.loadToken();
  }

  private loadToken() {
    this.token = localStorage.getItem('harbor_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('harbor_token', token);
    } else {
      localStorage.removeItem('harbor_token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorDetail = 'An error occurred';
        try {
          const errorData = await response.json() as ApiError;
          errorDetail = errorData.detail || errorDetail;
        } catch {
          errorDetail = response.statusText || errorDetail;
        }
        
        const error = new Error(errorDetail) as Error & { status: number };
        error.status = response.status;
        throw error;
      }

      // Handle empty responses
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error occurred');
    }
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    this.setToken(response.access_token);
    return response;
  }

  logout() {
    this.setToken(null);
  }

  // Routes
  async getRoutes(filters?: { path?: string; backend?: string }): Promise<RouteListResponse> {
    const params = new URLSearchParams();
    if (filters?.path) params.set('path', filters.path);
    if (filters?.backend) params.set('backend', filters.backend);
    
    const query = params.toString();
    const endpoint = `/routes${query ? `?${query}` : ''}`;
    
    return this.request<RouteListResponse>(endpoint);
  }

  async getRoute(id: string): Promise<RouteSpec> {
    return this.request<RouteSpec>(`/routes/${id}`);
  }

  async createRoute(id: string, route: Partial<RouteSpec>): Promise<RouteSpec> {
    return this.request<RouteSpec>(`/routes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(route),
    });
  }

  async updateRoute(id: string, route: Partial<RouteSpec>): Promise<RouteSpec> {
    return this.request<RouteSpec>(`/routes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(route),
    });
  }

  async deleteRoute(id: string): Promise<void> {
    await this.request<void>(`/routes/${id}`, {
      method: 'DELETE',
    });
  }

  async bulkApplyRoutes(routes: Partial<RouteSpec>[]): Promise<{ results: Array<{ id: string; status: string }> }> {
    return this.request<{ results: Array<{ id: string; status: string }> }>('/routes:bulk-apply', {
      method: 'POST',
      body: JSON.stringify(routes),
    });
  }

  async exportRoutes(): Promise<{ apiVersion: string; kind: string; items: RouteSpec[] }> {
    return this.request<{ apiVersion: string; kind: string; items: RouteSpec[] }>('/routes:export');
  }

  // System status (mock implementation - would need real endpoint)
  async getSystemStatus(): Promise<SystemStatus> {
    // This would be a real endpoint in the backend
    return {
      service: 'UP',
      uptime: Date.now() - (24 * 60 * 60 * 1000), // 24 hours ago
      route_store_sync: {
        status: 'OK',
        last_sync: new Date().toISOString(),
      },
      secret_provider: {
        status: 'OK',
      },
      backend_health: {
        healthy: 3,
        total: 4,
      },
      metrics: {
        total_routes: 12,
        request_rate: 45.2,
        error_rate: 0.1,
        avg_response_time: 125,
      },
      recent_events: [
        {
          timestamp: new Date(Date.now() - 300000).toISOString(),
          type: 'route_change',
          message: 'Route api-v1 updated',
        },
        {
          timestamp: new Date(Date.now() - 600000).toISOString(),
          type: 'route_change',
          message: 'Route analytics-api created',
        },
      ],
    };
  }

  // Route testing
  async testRoute(routeId: string, testRequest: TestRequest): Promise<TestResponse> {
    const startTime = Date.now();
    
    try {
      // This would proxy through the actual route
      // For now, mock a successful response
      await new Promise(resolve => setTimeout(resolve, Math.random() * 500 + 100));
      
      return {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'x-request-id': 'req_' + Math.random().toString(36).substr(2, 9),
        },
        body: JSON.stringify({ message: 'Test successful', timestamp: new Date().toISOString() }, null, 2),
        duration: Date.now() - startTime,
      };
    } catch (error) {
      return {
        status: 500,
        headers: {},
        body: '',
        duration: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Health check for a specific backend
  async checkBackendHealth(backendUrl: string): Promise<{ healthy: boolean; response_time?: number; error?: string }> {
    try {
      const startTime = Date.now();
      // This would be implemented as a backend endpoint
      await new Promise(resolve => setTimeout(resolve, Math.random() * 200 + 50));
      
      return {
        healthy: Math.random() > 0.2, // 80% chance of healthy
        response_time: Date.now() - startTime,
      };
    } catch (error) {
      return {
        healthy: false,
        error: error instanceof Error ? error.message : 'Health check failed',
      };
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);

// Export types for convenience
export type { ApiError };