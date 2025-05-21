'use client';

import React, { useState, useEffect } from 'react';

export default function DirectAPITest() {
  const [input, setInput] = useState('Hello, I am testing the API connection');
  const [responses, setResponses] = useState<{endpoint: string, status: string, response?: any, error?: string}[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [runCount, setRunCount] = useState(0);

  // Run test every 5 seconds if enabled
  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        setRunCount(prev => prev + 1);
        runTests();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [isRunning, input]);

  const runTests = async () => {
    setResponses([]);
    
    const endpoints = [
      { url: '/api/chat', displayName: 'Next.js API Route' },
      { url: 'http://localhost:8080/chat', displayName: 'Backend Direct (localhost)' },
      { url: 'http://api:8080/chat', displayName: 'Backend Direct (Docker)' },
      { url: 'http://localhost:8080/v1/chat', displayName: 'Backend v1 (localhost)' },
      { url: 'http://api:8080/v1/chat', displayName: 'Backend v1 (Docker)' }
    ];
    
    // Test all endpoints in parallel
    const results = await Promise.all(
      endpoints.map(async endpoint => {
        try {
          setResponses(prev => [...prev, {
            endpoint: endpoint.displayName,
            status: 'Testing...'
          }]);
          
          const response = await fetch(endpoint.url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: input }),
          });
          
          if (!response.ok) {
            return {
              endpoint: endpoint.displayName,
              status: 'Failed',
              error: `Error: HTTP ${response.status} - ${response.statusText}`
            };
          }
          
          let responseData;
          const contentType = response.headers.get('content-type');
          
          if (contentType && contentType.includes('application/json')) {
            responseData = await response.json();
          } else {
            const text = await response.text();
            responseData = { rawText: text };
          }
          
          return {
            endpoint: endpoint.displayName,
            status: 'Success',
            response: responseData
          };
          
        } catch (error) {
          return {
            endpoint: endpoint.displayName,
            status: 'Error',
            error: error instanceof Error ? error.message : 'Unknown error'
          };
        }
      })
    );
    
    setResponses(results);
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-2xl font-bold mb-4">Direct API Connection Test</h2>
      
      <div className="flex items-center gap-4 mb-6">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Test message"
        />
        
        <div className="flex gap-2">
          <button
            onClick={runTests}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors"
          >
            Run Test
          </button>
          
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`px-4 py-2 rounded-md ${
              isRunning 
                ? 'bg-red-600 hover:bg-red-700 text-white' 
                : 'bg-green-600 hover:bg-green-700 text-white'
            } transition-colors`}
          >
            {isRunning ? 'Stop Auto' : 'Auto Test'}
          </button>
        </div>
      </div>
      
      {isRunning && (
        <div className="mb-4 text-sm text-gray-600">
          Auto-testing is active. Run count: {runCount}
        </div>
      )}
      
      <div className="grid grid-cols-1 gap-4">
        {responses.map((result, index) => (
          <div 
            key={index} 
            className={`p-4 rounded-md ${
              result.status === 'Success' ? 'bg-green-50 border border-green-200' :
              result.status === 'Failed' || result.status === 'Error' ? 'bg-red-50 border border-red-200' :
              'bg-gray-50 border border-gray-200'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold">{result.endpoint}</h3>
              <span 
                className={`inline-block px-2 py-1 text-xs rounded-full ${
                  result.status === 'Success' ? 'bg-green-100 text-green-800' :
                  result.status === 'Failed' || result.status === 'Error' ? 'bg-red-100 text-red-800' :
                  'bg-gray-200 text-gray-800'
                }`}
              >
                {result.status}
              </span>
            </div>
            
            {result.error && (
              <div className="text-red-700 mt-2 text-sm">
                {result.error}
              </div>
            )}
            
            {result.response && (
              <div className="mt-2">
                <div className="text-sm font-medium text-gray-700 mb-1">Response:</div>
                <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-40">
                  {JSON.stringify(result.response, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
