import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { 
  ArrowLeftIcon,
  PlayIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { useRoute, useRouteTest } from '@/hooks/useApi';
import type { TestRequest, TestResponse } from '@/types';

export function RouteTester() {
  const { id } = useParams<{ id: string }>();
  const { data: route, loading: loadingRoute } = useRoute(id!);
  const { testRoute, testing, testResult, testError } = useRouteTest();
  
  const [testRequest, setTestRequest] = useState<TestRequest>({
    method: 'GET',
    path: '',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'l8e-harbor-ui/1.0'
    },
    body: ''
  });
  
  const [headerInput, setHeaderInput] = useState('');

  // Initialize path when route loads
  React.useEffect(() => {
    if (route && !testRequest.path) {
      setTestRequest(prev => ({ ...prev, path: route.path + '/' }));
    }
  }, [route, testRequest.path]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!route) return;
    
    try {
      await testRoute(route.id, testRequest);
    } catch (error) {
      // Error is handled by the hook
    }
  };

  const handleHeadersChange = (value: string) => {
    setHeaderInput(value);
    
    try {
      const headers: Record<string, string> = {};
      value.split('\n').forEach(line => {
        const [key, ...valueParts] = line.split(':');
        if (key && valueParts.length > 0) {
          headers[key.trim()] = valueParts.join(':').trim();
        }
      });
      
      setTestRequest(prev => ({ ...prev, headers }));
    } catch {
      // Invalid header format, ignore
    }
  };

  const formatHeaders = (headers: Record<string, string>) => {
    return Object.entries(headers)
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n');
  };

  // Initialize headers text
  React.useEffect(() => {
    if (!headerInput) {
      setHeaderInput(formatHeaders(testRequest.headers));
    }
  }, [testRequest.headers, headerInput]);

  if (loadingRoute) {
    return <div className="text-center py-8">Loading route...</div>;
  }

  if (!route) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-4">Route not found</div>
        <Link to="/routes">
          <Button variant="outline">Back to Routes</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link to={`/routes/${route.id}`}>
          <Button
            variant="ghost"
            leftIcon={<ArrowLeftIcon className="h-4 w-4" />}
          >
            Back to Route
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold text-primary-900">
            Test Route: {route.id}
          </h1>
          <p className="text-primary-600">
            Send test requests to {route.path} and view responses
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Request Panel */}
        <div className="space-y-6">
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-medium text-primary-900 mb-4">
              Test Request
            </h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Method and Path */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-1">
                    Method
                  </label>
                  <select
                    value={testRequest.method}
                    onChange={(e) => setTestRequest(prev => ({ 
                      ...prev, 
                      method: e.target.value 
                    }))}
                    className="block w-full rounded-md border-primary-300 shadow-sm focus:border-harbor-500 focus:ring-harbor-500 sm:text-sm"
                  >
                    {route.methods.map(method => (
                      <option key={method} value={method}>{method}</option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2">
                  <Input
                    label="Path"
                    value={testRequest.path}
                    onChange={(e) => setTestRequest(prev => ({ 
                      ...prev, 
                      path: e.target.value 
                    }))}
                    placeholder="/api/v1/example"
                  />
                </div>
              </div>

              {/* Headers */}
              <div>
                <label className="block text-sm font-medium text-primary-700 mb-1">
                  Headers
                </label>
                <textarea
                  value={headerInput}
                  onChange={(e) => handleHeadersChange(e.target.value)}
                  rows={6}
                  className="block w-full rounded-md border-primary-300 shadow-sm focus:border-harbor-500 focus:ring-harbor-500 sm:text-sm font-mono"
                  placeholder="Content-Type: application/json&#10;Authorization: Bearer token"
                />
              </div>

              {/* Request Body */}
              {['POST', 'PUT', 'PATCH'].includes(testRequest.method) && (
                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-1">
                    Request Body
                  </label>
                  <textarea
                    value={testRequest.body || ''}
                    onChange={(e) => setTestRequest(prev => ({ 
                      ...prev, 
                      body: e.target.value 
                    }))}
                    rows={8}
                    className="block w-full rounded-md border-primary-300 shadow-sm focus:border-harbor-500 focus:ring-harbor-500 sm:text-sm font-mono"
                    placeholder='{"key": "value"}'
                  />
                </div>
              )}

              {/* Submit Button */}
              <div className="flex justify-end">
                <Button
                  type="submit"
                  variant="primary"
                  loading={testing}
                  leftIcon={<PlayIcon className="h-4 w-4" />}
                >
                  Send Request
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Response Panel */}
        <div className="space-y-6">
          {(testResult || testError) && (
            <div className="bg-white shadow-sm rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium text-primary-900">
                  Response
                </h2>
                {testResult && (
                  <div className="flex items-center space-x-2">
                    <StatusIndicator status={testResult.status} />
                    <div className="flex items-center text-sm text-primary-500">
                      <ClockIcon className="h-4 w-4 mr-1" />
                      {testResult.duration}ms
                    </div>
                  </div>
                )}
              </div>

              {testError ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center text-red-800 mb-2">
                    <XCircleIcon className="h-5 w-5 mr-2" />
                    Test Failed
                  </div>
                  <p className="text-red-700">{testError}</p>
                </div>
              ) : testResult ? (
                <div className="space-y-4">
                  {/* Status */}
                  <div>
                    <h4 className="text-sm font-medium text-primary-700 mb-2">Status</h4>
                    <div className="flex items-center space-x-2">
                      <StatusIndicator status={testResult.status} />
                      <span className="font-mono text-sm">{testResult.status}</span>
                    </div>
                  </div>

                  {/* Headers */}
                  {Object.keys(testResult.headers).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-primary-700 mb-2">
                        Response Headers
                      </h4>
                      <div className="bg-primary-50 rounded-lg p-3">
                        <pre className="text-sm font-mono text-primary-800">
                          {Object.entries(testResult.headers)
                            .map(([key, value]) => `${key}: ${value}`)
                            .join('\n')}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Body */}
                  {testResult.body && (
                    <div>
                      <h4 className="text-sm font-medium text-primary-700 mb-2">
                        Response Body
                      </h4>
                      <div className="bg-primary-50 rounded-lg p-3 max-h-96 overflow-auto">
                        <pre className="text-sm font-mono text-primary-800 whitespace-pre-wrap">
                          {testResult.body}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* Test History (placeholder) */}
          <div className="bg-white shadow-sm rounded-lg p-6">
            <h2 className="text-lg font-medium text-primary-900 mb-4 flex items-center">
              <DocumentTextIcon className="h-5 w-5 mr-2" />
              Recent Tests
            </h2>
            <p className="text-sm text-primary-500 text-center py-8">
              Test history will appear here after running tests
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Status indicator component
function StatusIndicator({ status }: { status: number }) {
  const getVariant = (status: number) => {
    if (status >= 200 && status < 300) return 'success';
    if (status >= 300 && status < 400) return 'info';
    if (status >= 400 && status < 500) return 'warning';
    return 'error';
  };

  const getIcon = (status: number) => {
    if (status >= 200 && status < 400) {
      return <CheckCircleIcon className="h-4 w-4" />;
    }
    return <XCircleIcon className="h-4 w-4" />;
  };

  return (
    <Badge variant={getVariant(status)} className="flex items-center space-x-1">
      {getIcon(status)}
      <span>{status}</span>
    </Badge>
  );
}