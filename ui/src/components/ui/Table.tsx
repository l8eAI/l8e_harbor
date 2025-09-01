import React from 'react';
import clsx from 'clsx';
import { ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/20/solid';

export interface Column<T> {
  key: string;
  header: string;
  accessor?: keyof T | ((row: T) => React.ReactNode);
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (key: string) => void;
  emptyMessage?: string;
  className?: string;
}

export function Table<T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  sortBy,
  sortDirection,
  onSort,
  emptyMessage = 'No data available',
  className,
}: TableProps<T>) {
  const handleSort = (key: string, sortable?: boolean) => {
    if (!sortable || !onSort) return;
    onSort(key);
  };

  const getCellValue = (row: T, column: Column<T>) => {
    if (column.accessor) {
      if (typeof column.accessor === 'function') {
        return column.accessor(row);
      }
      return row[column.accessor];
    }
    return row[column.key];
  };

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-4 bg-primary-200 rounded w-full"></div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-4 bg-primary-100 rounded w-full"></div>
        ))}
      </div>
    );
  }

  return (
    <div className={clsx('overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg', className)}>
      <table className="min-w-full divide-y divide-primary-300">
        <thead className="bg-primary-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={clsx(
                  'px-6 py-3 text-xs font-medium uppercase tracking-wider',
                  {
                    'text-left': column.align === 'left' || !column.align,
                    'text-center': column.align === 'center',
                    'text-right': column.align === 'right',
                    'cursor-pointer select-none hover:bg-primary-100': column.sortable,
                  },
                  column.width && { width: column.width }
                )}
                onClick={() => handleSort(column.key, column.sortable)}
              >
                <div className="flex items-center space-x-1">
                  <span className="text-primary-500">{column.header}</span>
                  {column.sortable && (
                    <div className="flex flex-col">
                      <ChevronUpIcon
                        className={clsx(
                          'h-3 w-3 -mb-1',
                          sortBy === column.key && sortDirection === 'asc'
                            ? 'text-harbor-600'
                            : 'text-primary-400'
                        )}
                      />
                      <ChevronDownIcon
                        className={clsx(
                          'h-3 w-3',
                          sortBy === column.key && sortDirection === 'desc'
                            ? 'text-harbor-600'
                            : 'text-primary-400'
                        )}
                      />
                    </div>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-primary-200">
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-6 py-8 text-center text-sm text-primary-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, index) => (
              <tr key={index} className="hover:bg-primary-50">
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={clsx(
                      'px-6 py-4 whitespace-nowrap text-sm text-primary-900',
                      {
                        'text-left': column.align === 'left' || !column.align,
                        'text-center': column.align === 'center',
                        'text-right': column.align === 'right',
                      }
                    )}
                  >
                    {getCellValue(row, column)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}