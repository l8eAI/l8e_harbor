import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { apiClient } from '@/utils/api';
import type { User, AuthContext, LoginRequest } from '@/types';

// Auth state type
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

// Auth actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGIN_ERROR'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'CLEAR_ERROR' };

// Initial state
const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null,
};

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return {
        ...state,
        loading: true,
        error: null,
      };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        loading: false,
        error: null,
      };
    case 'LOGIN_ERROR':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: action.payload,
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
}

// Parse JWT token to extract user information
function parseJwtPayload(token: string): User | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    
    const payload = JSON.parse(jsonPayload);
    
    return {
      id: payload.sub || payload.jti,
      username: payload.sub,
      role: payload.role,
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

// Create auth context
const AuthContextProvider = createContext<AuthContext | null>(null);

// Auth provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth state from localStorage
  useEffect(() => {
    const token = localStorage.getItem('harbor_token');
    if (token) {
      const user = parseJwtPayload(token);
      if (user && user.exp && user.exp > Date.now() / 1000) {
        dispatch({
          type: 'LOGIN_SUCCESS',
          payload: { user, token },
        });
      } else {
        // Token expired, clean up
        localStorage.removeItem('harbor_token');
        apiClient.logout();
      }
    }
  }, []);

  const login = async (credentials: LoginRequest): Promise<void> => {
    dispatch({ type: 'LOGIN_START' });
    
    try {
      const response = await apiClient.login(credentials);
      const user = parseJwtPayload(response.access_token);
      
      if (!user) {
        throw new Error('Invalid token received');
      }
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user,
          token: response.access_token,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      dispatch({
        type: 'LOGIN_ERROR',
        payload: message,
      });
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('harbor_token');
    apiClient.logout();
    dispatch({ type: 'LOGOUT' });
  };

  const contextValue: AuthContext = {
    user: state.user,
    token: state.token,
    isAuthenticated: state.isAuthenticated,
    login,
    logout,
  };

  return (
    <AuthContextProvider.Provider value={contextValue}>
      {children}
    </AuthContextProvider.Provider>
  );
}

// Auth hook
export function useAuth(): AuthContext {
  const context = useContext(AuthContextProvider);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for route protection
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requiredRoles?: string[]
) {
  return function AuthenticatedComponent(props: P) {
    const { user, isAuthenticated } = useAuth();

    if (!isAuthenticated || !user) {
      return <div>Please log in to access this page.</div>;
    }

    if (requiredRoles && !requiredRoles.includes(user.role)) {
      return <div>You don't have permission to access this page.</div>;
    }

    return <Component {...props} />;
  };
}

// Hook for checking permissions
export function usePermissions() {
  const { user } = useAuth();
  
  return {
    isHarborMaster: user?.role === 'harbor-master',
    isCaptain: user?.role === 'captain',
    hasRole: (role: string) => user?.role === role,
    canManageRoutes: user?.role === 'harbor-master',
    canViewAuth: user?.role === 'harbor-master',
  };
}