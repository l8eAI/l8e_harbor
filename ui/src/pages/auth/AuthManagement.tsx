import React from 'react';
import { KeyIcon, UserIcon, ShieldCheckIcon, ClockIcon, UserPlusIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/hooks/useAuth';

const StatCard = ({ icon: Icon, title, value, description, color = 'blue' }: {
  icon: React.ComponentType<any>;
  title: string;
  value: string | number;
  description?: string;
  color?: 'blue' | 'green' | 'orange' | 'purple';
}) => {
  const colorStyles = {
    blue: 'from-blue-100 to-blue-50 text-blue-600 bg-blue-50',
    green: 'from-green-100 to-green-50 text-green-600 bg-green-50',
    orange: 'from-orange-100 to-orange-50 text-orange-600 bg-orange-50',
    purple: 'from-purple-100 to-purple-50 text-purple-600 bg-purple-50',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-all duration-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {description && <p className="text-sm text-gray-500 mt-1">{description}</p>}
        </div>
        <div className={`w-12 h-12 bg-gradient-to-br ${colorStyles[color]} rounded-lg flex items-center justify-center`}>
          <Icon className={`h-6 w-6 ${colorStyles[color].split(' ')[2]}`} />
        </div>
      </div>
    </div>
  );
};

const StatusBadge = ({ status, label }: { status: 'active' | 'inactive' | 'warning'; label: string }) => {
  const styles = {
    active: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
    inactive: 'bg-gray-50 text-gray-700 ring-gray-600/20',
    warning: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  };
  
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${styles[status]}`}>
      {label}
    </span>
  );
};

export function AuthManagement() {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="border-b border-gray-100 pb-6">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <KeyIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Authentication</h1>
            <p className="text-gray-600 mt-1">Manage users, roles, and authentication settings</p>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <StatCard
          icon={UserIcon}
          title="Total Users"
          value="1"
          description="System administrators"
          color="blue"
        />
        <StatCard
          icon={ShieldCheckIcon}
          title="Active Sessions"
          value="1"
          description="Currently authenticated"
          color="green"
        />
        <StatCard
          icon={KeyIcon}
          title="Auth Method"
          value="Local"
          description="SimpleLocalAuthAdapter"
          color="purple"
        />
      </div>

      {/* Content sections */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* User Management */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start space-x-4 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
              <UserIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">User Management</h3>
              <p className="text-sm text-gray-600">Manage system users and their permissions</p>
            </div>
          </div>

          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <UserPlusIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-sm font-semibold text-gray-900">User Management Coming Soon</h3>
            <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
              Advanced user management features including user creation, role assignment, and permission management are in development.
            </p>
            <div className="mt-6">
              <button
                type="button"
                disabled
                className="inline-flex items-center px-4 py-2 border border-gray-200 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <UserPlusIcon className="mr-2 h-4 w-4" />
                Add User
              </button>
            </div>
          </div>
        </div>

        {/* Authentication Settings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start space-x-4 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg flex items-center justify-center">
              <Cog6ToothIcon className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Authentication Settings</h3>
              <p className="text-sm text-gray-600">Configure authentication adapters and security settings</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-600">Auth Adapter</span>
              <span className="text-sm text-gray-900 font-mono bg-gray-50 px-2 py-1 rounded">SimpleLocalAuthAdapter</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-600">JWT Token Expiry</span>
              <span className="text-sm text-gray-900">15 minutes</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-600">Password Policy</span>
              <span className="text-sm text-gray-900">32+ characters, cryptographically secure</span>
            </div>
            <div className="flex items-center justify-between py-3">
              <span className="text-sm font-medium text-gray-600">Security Level</span>
              <StatusBadge status="active" label="High" />
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-100">
            <button
              type="button"
              disabled
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-200 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Cog6ToothIcon className="mr-2 h-4 w-4" />
              Configure Authentication
            </button>
          </div>
        </div>
      </div>

      {/* Current Session */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start space-x-4 mb-6">
          <div className="w-10 h-10 bg-gradient-to-br from-orange-100 to-red-100 rounded-lg flex items-center justify-center">
            <ClockIcon className="h-5 w-5 text-orange-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Current Session</h3>
            <p className="text-sm text-gray-600">Information about your current authentication session</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">{user?.username || 'admin'}</div>
            <div className="text-sm text-gray-600 mt-1">Username</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900 capitalize">{user?.role?.replace('-', ' ') || 'Harbor Master'}</div>
            <div className="text-sm text-gray-600 mt-1">Role</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold text-gray-900">Local Auth</div>
            <div className="text-sm text-gray-600 mt-1">Login Method</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-center">
              <StatusBadge status="active" label="Active" />
            </div>
            <div className="text-sm text-gray-600 mt-2">Session Status</div>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Session expires:</span> 15 minutes after login
            </div>
            <div className="text-sm text-gray-600">
              <span className="font-medium">Last activity:</span> Now
            </div>
          </div>
        </div>
      </div>

      {/* Security Notice */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200 p-6">
        <div className="flex items-start space-x-3">
          <ShieldCheckIcon className="h-6 w-6 text-blue-600 mt-0.5" />
          <div>
            <h4 className="text-lg font-semibold text-gray-900">Security Information</h4>
            <p className="text-sm text-gray-600 mt-1">Your l8e-harbor deployment is secured with industry-standard practices</p>
            <ul className="mt-3 space-y-1 text-sm text-gray-600">
              <li>• JWT tokens with RS256 signing algorithm</li>
              <li>• Bcrypt password hashing with high cost factor</li>
              <li>• Automatic token expiration and renewal</li>
              <li>• Role-based access control (RBAC)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}