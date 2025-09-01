import React from 'react';
import { useLocation } from 'react-router-dom';

// Breadcrumb configuration
const breadcrumbMap: Record<string, string[]> = {
  '/': ['Dashboard'],
  '/routes': ['Routes'],
  '/routes/new': ['Routes', 'Create Route'],
  '/routes/edit': ['Routes', 'Edit Route'],
  '/system': ['System Status'],
  '/auth': ['Authentication'],
  '/auth/tokens': ['Authentication', 'Tokens'],
  '/auth/audit': ['Authentication', 'Audit Log'],
  '/settings': ['Settings'],
};

export function Header() {
  const location = useLocation();
  
  // Get breadcrumbs for current path
  const getBreadcrumbs = () => {
    const path = location.pathname;
    
    // Check for exact match
    if (breadcrumbMap[path]) {
      return breadcrumbMap[path];
    }
    
    // Check for dynamic routes (e.g., /routes/:id)
    for (const [pattern, breadcrumbs] of Object.entries(breadcrumbMap)) {
      if (pattern.includes(':')) {
        const patternParts = pattern.split('/');
        const pathParts = path.split('/');
        
        if (patternParts.length === pathParts.length) {
          let matches = true;
          for (let i = 0; i < patternParts.length; i++) {
            if (!patternParts[i].startsWith(':') && patternParts[i] !== pathParts[i]) {
              matches = false;
              break;
            }
          }
          if (matches) {
            return breadcrumbs;
          }
        }
      }
    }
    
    // Default breadcrumb based on path segments
    const segments = path.split('/').filter(Boolean);
    return segments.map(segment => 
      segment.charAt(0).toUpperCase() + segment.slice(1).replace('-', ' ')
    );
  };
  
  const breadcrumbs = getBreadcrumbs();
  
  return (
    <header className="bg-white shadow-sm border-b border-primary-200">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Breadcrumbs */}
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-2">
              {breadcrumbs.map((crumb, index) => (
                <li key={index} className="flex items-center">
                  {index > 0 && (
                    <svg
                      className="flex-shrink-0 h-4 w-4 text-primary-400 mx-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  <span
                    className={
                      index === breadcrumbs.length - 1
                        ? 'text-primary-900 font-medium'
                        : 'text-primary-500'
                    }
                  >
                    {crumb}
                  </span>
                </li>
              ))}
            </ol>
          </nav>

          {/* Right side - could add search, notifications, etc. */}
          <div className="flex items-center space-x-4">
            {/* Status indicator */}
            <div className="flex items-center text-sm text-primary-600">
              <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
              System Healthy
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}