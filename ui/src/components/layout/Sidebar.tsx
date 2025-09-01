import React from 'react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import {
  MapIcon,
  ChartBarIcon,
  KeyIcon,
  CogIcon,
  BookOpenIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth, usePermissions } from '@/hooks/useAuth';
import type { NavigationItem } from '@/types';

// Navigation items configuration
const navigationItems: NavigationItem[] = [
  {
    name: 'Routes',
    path: '/routes',
    icon: MapIcon,
  },
  {
    name: 'System Status',
    path: '/system',
    icon: ChartBarIcon,
  },
  {
    name: 'Authentication',
    path: '/auth',
    icon: KeyIcon,
    roles: ['harbor-master'],
  },
  {
    name: 'Settings',
    path: '/settings',
    icon: CogIcon,
  },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const permissions = usePermissions();

  const filteredNavigation = navigationItems.filter(item => {
    if (!item.roles) return true;
    return item.roles.some(role => permissions.hasRole(role));
  });

  return (
    <div className="flex flex-col w-64 bg-white h-full">
      {/* Header */}
      <div className="flex items-center flex-shrink-0 px-6 py-6 border-b border-gray-100">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-gradient-to-br from-orange-400 to-red-500 rounded-lg flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-sm">⚓</span>
            </div>
          </div>
          <div className="ml-3">
            <p className="text-lg font-semibold text-gray-900">l8e-harbor</p>
            <p className="text-xs text-gray-500">Control Plane</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {filteredNavigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                'group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-orange-50 text-orange-700 border-r-2 border-orange-500'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              )
            }
          >
            <item.icon
              className={clsx(
                "mr-3 flex-shrink-0 h-5 w-5 transition-colors duration-200"
              )}
              aria-hidden="true"
            />
            {item.name}
          </NavLink>
        ))}
        
        {/* Documentation link */}
        <div className="pt-4 mt-4 border-t border-gray-100">
          <a
            href="https://docs.l8e-harbor.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-gray-50 hover:text-gray-900 transition-all duration-200"
          >
            <BookOpenIcon
              className="mr-3 flex-shrink-0 h-5 w-5"
              aria-hidden="true"
            />
            Documentation
          </a>
        </div>
      </nav>

      {/* User menu */}
      <div className="flex-shrink-0 border-t border-gray-100 p-4">
        <div className="flex items-center mb-4">
          <div className="flex-shrink-0">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-sm">
              <span className="text-white text-sm font-semibold">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
          </div>
          <div className="ml-3 flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">
              {user?.username || 'Unknown'}
            </p>
            <p className="text-xs text-gray-500 capitalize">
              {user?.role?.replace('-', ' ') || 'User'}
            </p>
          </div>
        </div>
        
        <button
          onClick={logout}
          className="w-full flex items-center justify-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-all duration-200 group"
        >
          <ArrowRightOnRectangleIcon className="mr-2 h-4 w-4 group-hover:translate-x-0.5 transition-transform duration-200" />
          Sign out
        </button>
      </div>
    </div>
  );
}