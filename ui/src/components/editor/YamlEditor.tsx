import React, { useRef, useEffect, useState } from 'react';
import Editor, { OnMount, OnChange } from '@monaco-editor/react';
import { Button } from '@/components/ui/Button';
import { validateYaml, formatValidationErrors } from '@/utils/validation';
import type { ValidationError } from '@/types';

export interface YamlEditorProps {
  value: string;
  onChange?: (value: string) => void;
  onValidationChange?: (errors: ValidationError[]) => void;
  readOnly?: boolean;
  height?: string;
  language?: string;
  theme?: 'light' | 'dark';
  showValidation?: boolean;
  autoFormat?: boolean;
}

export function YamlEditor({
  value,
  onChange,
  onValidationChange,
  readOnly = false,
  height = '400px',
  language = 'yaml',
  theme = 'light',
  showValidation = true,
  autoFormat = false,
}: YamlEditorProps) {
  const editorRef = useRef<any>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Configure YAML language support
    monaco.languages.setLanguageConfiguration('yaml', {
      brackets: [
        ['{', '}'],
        ['[', ']'],
        ['(', ')']
      ],
      autoClosingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '"', close: '"' },
        { open: "'", close: "'" }
      ],
      surroundingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '"', close: '"' },
        { open: "'", close: "'" }
      ],
      folding: {
        offSide: true
      },
      indentationRules: {
        increaseIndentPattern: /^(\s*)([^#\s].*:|\s*-\s+[^#\s].*:).*$/,
        decreaseIndentPattern: /^\s*\}|\s*\]$/
      }
    });

    // Set editor options
    editor.updateOptions({
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
      minimap: { enabled: false },
      lineNumbers: 'on',
      wordWrap: 'on',
      scrollBeyondLastLine: false,
      automaticLayout: true,
      tabSize: 2,
      insertSpaces: true,
    });

    // Add keyboard shortcuts
    editor.addAction({
      id: 'format-yaml',
      label: 'Format YAML',
      keybindings: [
        monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF
      ],
      run: () => {
        formatYaml();
      }
    });

    // Initial validation
    if (showValidation && value) {
      validateContent(value);
    }
  };

  const handleEditorChange: OnChange = (newValue) => {
    if (newValue !== undefined) {
      onChange?.(newValue);
      
      if (showValidation) {
        validateContent(newValue);
      }
    }
  };

  const validateContent = (content: string) => {
    setIsValidating(true);
    
    // Debounce validation
    setTimeout(() => {
      const { errors } = validateYaml(content);
      setValidationErrors(errors);
      onValidationChange?.(errors);
      setIsValidating(false);
    }, 300);
  };

  const formatYaml = () => {
    if (editorRef.current) {
      editorRef.current.getAction('editor.action.formatDocument').run();
    }
  };

  const insertTemplate = () => {
    const template = `apiVersion: harbor.l8e/v1
kind: Route
metadata:
  name: example-route
spec:
  id: example-route
  description: "Example route configuration"
  path: /api/v1
  methods: ["GET", "POST"]
  backends:
    - url: http://example-service:8080
      weight: 100
      health_check_path: /healthz
  priority: 10
  timeout_ms: 5000
  retry_policy:
    max_retries: 2
    backoff_ms: 200
    retry_on: ["5xx", "timeout"]
  circuit_breaker:
    enabled: true
    failure_threshold: 50
    minimum_requests: 20
  middleware:
    - name: logging
      config:
        level: info`;

    if (editorRef.current) {
      editorRef.current.setValue(template);
      onChange?.(template);
    }
  };

  const copyToClipboard = () => {
    if (editorRef.current) {
      const content = editorRef.current.getValue();
      navigator.clipboard.writeText(content);
    }
  };

  return (
    <div className="border border-primary-300 rounded-lg overflow-hidden">
      {/* Editor toolbar */}
      <div className="bg-primary-50 border-b border-primary-300 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-primary-700">
            YAML Editor
          </span>
          {showValidation && (
            <div className="flex items-center space-x-2">
              {isValidating ? (
                <span className="text-sm text-primary-500">Validating...</span>
              ) : validationErrors.length > 0 ? (
                <span className="text-sm text-red-600">
                  {validationErrors.length} error{validationErrors.length > 1 ? 's' : ''}
                </span>
              ) : (
                <span className="text-sm text-green-600">Valid</span>
              )}
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={insertTemplate}
            disabled={readOnly}
          >
            Insert Template
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={formatYaml}
            disabled={readOnly}
          >
            Format
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={copyToClipboard}
          >
            Copy
          </Button>
        </div>
      </div>

      {/* Editor */}
      <Editor
        height={height}
        language={language}
        theme={theme === 'dark' ? 'vs-dark' : 'vs'}
        value={value}
        onChange={handleEditorChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          contextmenu: true,
          selectOnLineNumbers: true,
          automaticLayout: true,
        }}
        loading={<div className="p-4 text-center text-primary-500">Loading editor...</div>}
      />

      {/* Validation errors */}
      {showValidation && validationErrors.length > 0 && (
        <div className="bg-red-50 border-t border-red-200 px-4 py-3">
          <h4 className="text-sm font-medium text-red-800 mb-2">
            Validation Errors:
          </h4>
          <div className="text-sm text-red-700 space-y-1">
            {validationErrors.map((error, index) => (
              <div key={index} className="flex items-start space-x-2">
                <span className="flex-shrink-0 w-2 h-2 bg-red-400 rounded-full mt-1.5"></span>
                <span>
                  <strong>{error.field}</strong>
                  {error.line && <span className="text-red-600"> (line {error.line})</span>}
                  : {error.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}