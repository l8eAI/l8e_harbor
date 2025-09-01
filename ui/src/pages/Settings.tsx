import React from 'react';
import { CogIcon, ServerIcon, CircleStackIcon, ShieldCheckIcon, ChartBarIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const StatusBadge = ({ status, label }: { status: 'success' | 'warning' | 'info'; label: string }) => {
  const styles = {
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
    warning: 'bg-amber-50 text-amber-700 ring-amber-600/20',
    info: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  };
  
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${styles[status]}`}>
      {label}
    </span>
  );
};

const ConfigCard = ({ icon: Icon, title, description, children }: {
  icon: React.ComponentType<any>;
  title: string;
  description: string;
  children: React.ReactNode;
}) => (
  <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-all duration-200">
    <div className="flex items-start space-x-4 mb-4">
      <div className="flex-shrink-0">
        <div className="w-10 h-10 bg-gradient-to-br from-orange-100 to-red-100 rounded-lg flex items-center justify-center">
          <Icon className="h-5 w-5 text-orange-600" />
        </div>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
    <div className="space-y-3">
      {children}
    </div>
  </div>
);

const ConfigItem = ({ label, value, type = 'text' }: { label: string; value: string | React.ReactNode; type?: 'text' | 'code' | 'status' }) => (
  <div className="flex items-center justify-between py-2">
    <dt className="text-sm font-medium text-gray-600">{label}</dt>
    <dd className={`text-sm ${type === 'code' ? 'font-mono bg-gray-50 px-2 py-1 rounded text-gray-800' : 'text-gray-900'}`}>
      {value}
    </dd>
  </div>
);

export function Settings() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-gray-100 pb-6">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-orange-400 to-red-500 rounded-lg flex items-center justify-center">
            <CogIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">Configure your l8e-harbor deployment settings and adapters</p>
          </div>
        </div>
      </div>

      {/* Configuration Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Server Configuration */}
        <ConfigCard
          icon={ServerIcon}
          title="Server Configuration"
          description="Core server settings and network configuration"
        >
          <ConfigItem label="Host" value="0.0.0.0" />
          <ConfigItem label="Port" value="8443" />
          <ConfigItem label="TLS" value={<StatusBadge status="success" label="Enabled" />} />
          <ConfigItem label="Log Level" value="INFO" />
          <ConfigItem label="CORS" value={<StatusBadge status="success" label="Enabled" />} />
        </ConfigCard>

        {/* Storage Configuration */}
        <ConfigCard
          icon={CircleStackIcon}
          title="Storage Configuration"
          description="Data storage and persistence settings"
        >
          <ConfigItem label="Route Store" value="File-based (JSON)" />
          <ConfigItem label="Secret Provider" value="Local Filesystem" />
          <ConfigItem label="Data Path" value="/app/data" type="code" />
          <ConfigItem label="Backup Strategy" value={<StatusBadge status="warning" label="Manual" />} />
        </ConfigCard>

        {/* Security Configuration */}
        <ConfigCard
          icon={ShieldCheckIcon}
          title="Security Settings"
          description="Authentication and security configuration"
        >
          <ConfigItem label="Auth Adapter" value="SimpleLocalAuthAdapter" />
          <ConfigItem label="JWT Algorithm" value="RS256" type="code" />
          <ConfigItem label="Token Expiry" value="15 minutes" />
          <ConfigItem label="Password Policy" value="32+ characters" />
        </ConfigCard>

        {/* Monitoring Configuration */}
        <ConfigCard
          icon={ChartBarIcon}
          title="Monitoring & Observability"
          description="Metrics, logging, and tracing configuration"
        >
          <ConfigItem label="Prometheus Metrics" value={<StatusBadge status="success" label="Enabled" />} />
          <ConfigItem label="Metrics Endpoint" value="/metrics" type="code" />
          <ConfigItem label="Structured Logging" value="JSON Format" />
          <ConfigItem label="Distributed Tracing" value={<StatusBadge status="info" label="Available" />} />
        </ConfigCard>
      </div>

      {/* Environment Information */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
            <CheckCircleIcon className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Environment Information</h3>
            <p className="text-sm text-gray-600">Current deployment and runtime environment details</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">v1.0.0-dev</div>
            <div className="text-sm text-gray-600 mt-1">Version</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">Docker</div>
            <div className="text-sm text-gray-600 mt-1">Deployment</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">Development</div>
            <div className="text-sm text-gray-600 mt-1">Build Mode</div>
          </div>
        </div>
      </div>

      {/* Configuration Management */}
      <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-xl border border-orange-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <ExclamationTriangleIcon className="h-6 w-6 text-orange-600 mt-0.5" />
            <div>
              <h4 className="text-lg font-semibold text-gray-900">Configuration Management</h4>
              <p className="text-sm text-gray-600 mt-1">Export current configuration or modify system settings</p>
            </div>
          </div>
          <div className="flex space-x-3">
            <button
              type="button"
              disabled
              className="inline-flex items-center px-4 py-2 border border-gray-200 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Export Configuration
            </button>
            <button
              type="button"
              disabled
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Apply Changes
            </button>
          </div>
        </div>
        <div className="mt-3 text-xs text-orange-700 bg-orange-100 rounded-md px-3 py-2">
          Configuration management features are coming soon. Currently in read-only mode.
        </div>
      </div>
    </div>
  );
}