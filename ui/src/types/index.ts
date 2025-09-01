// Core l8e-harbor API types
export interface RouteSpec {
  id: string;
  description?: string;
  path: string;
  methods: string[];
  backends: BackendSpec[];
  priority: number;
  strip_prefix: boolean;
  sticky_session: boolean;
  timeout_ms: number;
  retry_policy: RetryPolicy;
  circuit_breaker: CircuitBreakerSpec;
  middleware: MiddlewareSpec[];
  matchers?: MatcherSpec[];
  created_at: string;
  updated_at: string;
}

export interface BackendSpec {
  url: string;
  weight: number;
  health_check_path: string;
  tls?: TLSConfig;
}

export interface TLSConfig {
  insecure_skip_verify?: boolean;
  ca_cert_secret?: string;
  cert_secret?: string;
}

export interface RetryPolicy {
  max_retries: number;
  backoff_ms: number;
  retry_on: string[];
}

export interface CircuitBreakerSpec {
  enabled: boolean;
  failure_threshold: number;
  minimum_requests: number;
  interval_ms: number;
  timeout_ms: number;
}

export interface MiddlewareSpec {
  name: string;
  config: Record<string, any>;
}

export interface MatcherSpec {
  name: string;
  value?: string;
  op: 'equals' | 'contains' | 'regex' | 'exists';
}

// API Response types
export interface RouteListResponse {
  routes: RouteSpec[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  expires_in: number;
  token_type: string;
}

export interface SystemStatus {
  service: 'UP' | 'DOWN';
  uptime?: number;
  route_store_sync: {
    status: 'OK' | 'ERROR';
    last_sync: string;
  };
  secret_provider: {
    status: 'OK' | 'ERROR';
  };
  backend_health: {
    healthy: number;
    total: number;
  };
  metrics: {
    total_routes: number;
    request_rate: number;
    error_rate: number;
    avg_response_time: number;
  };
  recent_events: SystemEvent[];
}

export interface SystemEvent {
  timestamp: string;
  type: 'route_change' | 'error' | 'restart';
  message: string;
  details?: Record<string, any>;
}

// Authentication types
export interface User {
  id: string;
  username: string;
  role: 'harbor-master' | 'captain';
  exp?: number;
}

export interface AuthContext {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}

// UI State types
export interface RouteFormData {
  id: string;
  description: string;
  path: string;
  methods: string[];
  backends: BackendSpec[];
  priority: number;
  strip_prefix: boolean;
  sticky_session: boolean;
  timeout_ms: number;
  retry_policy: RetryPolicy;
  circuit_breaker: CircuitBreakerSpec;
  middleware: MiddlewareSpec[];
  matchers: MatcherSpec[];
}

export interface TestRequest {
  method: string;
  path: string;
  headers: Record<string, string>;
  body?: string;
}

export interface TestResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
  duration: number;
  error?: string;
}

// Navigation types
export type NavigationItem = {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: string[];
};

// API Error types
export interface ApiError {
  detail: string;
  status?: number;
}

// Route validation types
export interface ValidationError {
  field: string;
  message: string;
  line?: number;
}