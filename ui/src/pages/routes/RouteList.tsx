import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  PlusIcon, 
  MagnifyingGlassIcon,
  ArrowPathIcon,
  PencilIcon,
  TrashIcon,
  PlayIcon
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Table } from '@/components/ui/Table';
import { Badge, StatusBadge, MethodBadge } from '@/components/ui/Badge';
import { useRoutes, useBackendHealth, useAsyncOperation, useDebounce } from '@/hooks/useApi';
import { usePermissions } from '@/hooks/useAuth';
import { formatDistanceToNow } from 'date-fns';
import type { RouteSpec, Column } from '@/types';

export function RouteList() {
  const navigate = useNavigate();
  const permissions = usePermissions();
  
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<string>('updated_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedRoutes, setSelectedRoutes] = useState<string[]>([]);

  const debouncedSearch = useDebounce(search, 300);
  
  const { routes, loading, error, refetch, deleteRoute } = useRoutes();
  const { execute: handleDelete, loading: deleting } = useAsyncOperation(deleteRoute);

  // Filter and sort routes
  const filteredRoutes = useMemo(() => {
    let filtered = routes;

    // Apply search filter
    if (debouncedSearch) {
      filtered = routes.filter(route => 
        route.id.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        route.path.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        route.description?.toLowerCase().includes(debouncedSearch.toLowerCase())
      );
    }

    // Apply sorting
    return filtered.sort((a, b) => {
      let aValue: any = a[sortBy as keyof RouteSpec];
      let bValue: any = b[sortBy as keyof RouteSpec];

      // Handle special cases
      if (sortBy === 'backends') {
        aValue = a.backends.length;
        bValue = b.backends.length;
      } else if (sortBy === 'methods') {
        aValue = a.methods.join(',');
        bValue = b.methods.join(',');
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [routes, debouncedSearch, sortBy, sortDirection]);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDirection('asc');
    }
  };

  const handleDeleteRoute = async (id: string) => {
    if (!confirm(`Are you sure you want to delete route "${id}"?`)) {
      return;
    }
    
    try {
      await handleDelete(id);
    } catch (error) {
      console.error('Failed to delete route:', error);
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedRoutes.length} routes?`)) {
      return;
    }

    try {
      await Promise.all(selectedRoutes.map(id => handleDelete(id)));
      setSelectedRoutes([]);
    } catch (error) {
      console.error('Failed to delete routes:', error);
    }
  };

  // Backend health component
  const BackendHealth = ({ backends }: { backends: RouteSpec['backends'] }) => {
    const { health } = useBackendHealth(backends[0]?.url);
    
    if (backends.length === 1) {
      return <StatusBadge status={health?.healthy ? 'healthy' : 'unhealthy'} />;
    }
    
    return (
      <Badge variant="info">
        {backends.length} backend{backends.length > 1 ? 's' : ''}
      </Badge>
    );
  };

  // Table columns
  const columns: Column<RouteSpec>[] = [
    {
      key: 'id',
      header: 'Name',
      sortable: true,
      accessor: (route) => (
        <div>
          <Link 
            to={`/routes/${route.id}`}
            className="font-medium text-harbor-600 hover:text-harbor-800"
          >
            {route.id}
          </Link>
          {route.description && (
            <p className="text-sm text-primary-500 mt-1">{route.description}</p>
          )}
        </div>
      ),
    },
    {
      key: 'path',
      header: 'Path',
      sortable: true,
      accessor: 'path',
    },
    {
      key: 'methods',
      header: 'Methods',
      sortable: true,
      accessor: (route) => (
        <div className="flex flex-wrap gap-1">
          {route.methods.slice(0, 3).map(method => (
            <MethodBadge key={method} method={method} />
          ))}
          {route.methods.length > 3 && (
            <Badge size="sm">+{route.methods.length - 3}</Badge>
          )}
        </div>
      ),
    },
    {
      key: 'backends',
      header: 'Backends',
      sortable: true,
      accessor: (route) => <BackendHealth backends={route.backends} />,
    },
    {
      key: 'updated_at',
      header: 'Last Modified',
      sortable: true,
      accessor: (route) => (
        <span className="text-sm text-primary-500">
          {formatDistanceToNow(new Date(route.updated_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      accessor: (route) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/routes/${route.id}/test`)}
            leftIcon={<PlayIcon className="h-4 w-4" />}
          >
            Test
          </Button>
          {permissions.canManageRoutes && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/routes/${route.id}/edit`)}
                leftIcon={<PencilIcon className="h-4 w-4" />}
              >
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDeleteRoute(route.id)}
                leftIcon={<TrashIcon className="h-4 w-4" />}
                loading={deleting}
              >
                Delete
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-primary-900">Routes</h1>
          <p className="text-primary-600">
            Manage your route configurations and test endpoints
          </p>
        </div>
        
        {permissions.canManageRoutes && (
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              leftIcon={<ArrowPathIcon className="h-4 w-4" />}
              onClick={refetch}
              loading={loading}
            >
              Refresh
            </Button>
            <Link to="/routes/new">
              <Button 
                variant="primary"
                leftIcon={<PlusIcon className="h-4 w-4" />}
              >
                Create Route
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Filters and search */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 max-w-sm">
          <Input
            placeholder="Search routes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<MagnifyingGlassIcon className="h-4 w-4" />}
          />
        </div>
        
        {selectedRoutes.length > 0 && permissions.canManageRoutes && (
          <Button
            variant="danger"
            onClick={handleBulkDelete}
            loading={deleting}
          >
            Delete Selected ({selectedRoutes.length})
          </Button>
        )}
      </div>

      {/* Routes table */}
      {error ? (
        <div className="rounded-md bg-red-50 p-4">
          <div className="text-sm text-red-700">
            Error loading routes: {error}
          </div>
        </div>
      ) : (
        <div className="bg-white shadow-sm rounded-lg">
          <Table
            data={filteredRoutes}
            columns={columns}
            loading={loading}
            sortBy={sortBy}
            sortDirection={sortDirection}
            onSort={handleSort}
            emptyMessage={
              debouncedSearch
                ? `No routes found matching "${debouncedSearch}"`
                : 'No routes configured yet. Create your first route to get started.'
            }
          />
        </div>
      )}
    </div>
  );
}