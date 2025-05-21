'use client';

import React, { useState } from 'react';

export default function DebugChat() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const addLog = (log: string) => {
    setLogs(prev => [...prev, `[${new Date().toISOString()}] ${log}`]);
  };

  const testEndpoint = async (url: string) => {
    try {
      addLog(`Testing endpoint: ${url}`);
      setLoading(true);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ message: input }),
      });
      
      addLog(`Response status: ${response.status}`);
      
      if (!response.ok) {
        throw new Error(`Failed with status: ${response.status}`);
      }
      
      // Try to read the response as text first
      const text = await response.text();
      addLog(`Raw response: ${text.substring(0, 150)}${text.length > 150 ? '...' : ''}`);
      
      try {
        // Then parse it as JSON if possible
        const data = JSON.parse(text);
        addLog(`Parsed JSON: ${JSON.stringify(data).substring(0, 150)}${JSON.stringify(data).length > 150 ? '...' : ''}`);
        return { success: true, data, text };
      } catch (e) {
        addLog(`Not valid JSON, returning text`);
        return { success: true, text, data: null };
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Unknown error';
      addLog(`Error: ${errorMessage}`);
      return { success: false, error: errorMessage };
    }
  };

  const handleTest = async () => {
    setError(null);
    setResponse(null);
    setLoading(true);
    
    const endpoints = [
      '/api/chat',
      'http://localhost:8080/chat',
      'http://api:8080/chat',
      'http://localhost:8080/v1/chat',
      'http://api:8080/v1/chat'
    ];
    
    for (const endpoint of endpoints) {
      const result = await testEndpoint(endpoint);
      
      if (result.success) {
        if (result.data) {
          setResponse(JSON.stringify(result.data, null, 2));
          setLoading(false);
          return;
        } else {
          setResponse(result.text || "Empty response");
          setLoading(false);
          return;
        }
      }
    }
    
    setError('All endpoints failed');
    setLoading(false);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 bg-white rounded-xl shadow-lg border border-gray-200">
      <h2 className="text-xl font-bold mb-4">API Connection Debugger</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Message to send
        </label>
        <div className="flex">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter a message to test"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <button
            onClick={handleTest}
            disabled={loading || !input.trim()}
            className={`px-4 py-2 rounded-r-md text-white ${
              loading || !input.trim() 
                ? 'bg-indigo-400 cursor-not-allowed' 
                : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {loading ? 'Testing...' : 'Test Endpoints'}
          </button>
        </div>
      </div>
      
      {response && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-green-600 mb-2">Success Response:</h3>
          <pre className="bg-gray-100 p-3 rounded-md overflow-auto max-h-60">
            {response}
          </pre>
        </div>
      )}
      
      {error && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-red-600 mb-2">Error:</h3>
          <div className="bg-red-50 border border-red-200 p-3 rounded-md text-red-800">
            {error}
          </div>
        </div>
      )}
      
      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold">Logs:</h3>
          <button
            onClick={clearLogs}
            className="px-2 py-1 text-sm text-gray-600 hover:text-gray-800"
          >
            Clear
          </button>
        </div>
        <div className="bg-gray-900 text-gray-200 p-3 rounded-md overflow-auto max-h-80 font-mono text-sm">
          {logs.length > 0 ? (
            logs.map((log, i) => (
              <div key={i} className="mb-1">
                {log}
              </div>
            ))
          ) : (
            <div className="text-gray-500 italic">No logs yet. Click "Test Endpoints" to begin.</div>
          )}
        </div>
      </div>
    </div>
  );
}
