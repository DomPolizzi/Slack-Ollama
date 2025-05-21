'use client';

import React, { useState } from 'react';

export default function TracingTool() {
  const [isCollecting, setIsCollecting] = useState(false);
  const [traces, setTraces] = useState<any[]>([]);
  const [requestInfo, setRequestInfo] = useState({
    endpoint: '/api/chat',
    method: 'POST',
    contentType: 'application/json',
    accept: 'application/json',
    body: JSON.stringify({ message: "Hello, this is a tracing test" }, null, 2)
  });

  const formatHeaderValue = (value: string): string => {
    if (value.startsWith('{') && value.endsWith('}')) {
      try {
        const json = JSON.parse(value);
        return JSON.stringify(json, null, 2);
      } catch (e) {
        return value;
      }
    }
    return value;
  };

  const startTracing = async () => {
    setIsCollecting(true);
    setTraces([]);
    
    try {
      // Add trace entry for request start
      const newTrace = {
        timestamp: new Date().toISOString(),
        type: 'request',
        data: {
          endpoint: requestInfo.endpoint,
          method: requestInfo.method,
          headers: {
            'Content-Type': requestInfo.contentType,
            'Accept': requestInfo.accept
          },
          body: formatHeaderValue(requestInfo.body)
        }
      };
      
      setTraces([newTrace]);
      
      // Parse the body for the fetch request
      let parsedBody;
      try {
        parsedBody = JSON.parse(requestInfo.body);
      } catch (e) {
        parsedBody = { error: "Invalid JSON in request body", raw: requestInfo.body };
        setTraces(prev => [...prev, {
          timestamp: new Date().toISOString(),
          type: 'error',
          data: { message: 'Failed to parse request body as JSON', error: String(e) }
        }]);
      }
      
      // Make the fetch request
      const fetchStartTime = performance.now();
      
      setTraces(prev => [...prev, {
        timestamp: new Date().toISOString(),
        type: 'info',
        data: { message: `Sending fetch request to ${requestInfo.endpoint}...` }
      }]);
      
      const response = await fetch(requestInfo.endpoint, {
        method: requestInfo.method,
        headers: {
          'Content-Type': requestInfo.contentType,
          'Accept': requestInfo.accept,
        },
        body: JSON.stringify(parsedBody),
      });
      
      const fetchEndTime = performance.now();
      const fetchDuration = fetchEndTime - fetchStartTime;
      
      // Add trace for response received
      setTraces(prev => [...prev, {
        timestamp: new Date().toISOString(),
        type: 'response',
        data: {
          status: response.status,
          statusText: response.statusText,
          headers: Array.from(response.headers).reduce((obj, [key, value]) => {
            obj[key] = value;
            return obj;
          }, {} as Record<string, string>),
          duration: `${fetchDuration.toFixed(2)}ms`,
        }
      }]);
      
      // Try to parse response based on content type
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        try {
          const jsonResponse = await response.json();
          setTraces(prev => [...prev, {
            timestamp: new Date().toISOString(),
            type: 'data',
            data: { responseBody: jsonResponse }
          }]);
        } catch (e) {
          setTraces(prev => [...prev, {
            timestamp: new Date().toISOString(),
            type: 'error',
            data: { message: 'Failed to parse response as JSON', error: String(e) }
          }]);
        }
      } else {
        try {
          const textResponse = await response.text();
          setTraces(prev => [...prev, {
            timestamp: new Date().toISOString(),
            type: 'data',
            data: { responseBody: textResponse }
          }]);
        } catch (e) {
          setTraces(prev => [...prev, {
            timestamp: new Date().toISOString(),
            type: 'error',
            data: { message: 'Failed to read response as text', error: String(e) }
          }]);
        }
      }
      
    } catch (error) {
      setTraces(prev => [...prev, {
        timestamp: new Date().toISOString(),
        type: 'error',
        data: { message: 'Fetch error', error: error instanceof Error ? error.message : String(error) }
      }]);
    } finally {
      setIsCollecting(false);
    }
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-2xl font-bold mb-4">API Request Tracer</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Endpoint URL
          </label>
          <input
            type="text"
            value={requestInfo.endpoint}
            onChange={(e) => setRequestInfo({...requestInfo, endpoint: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            HTTP Method
          </label>
          <select
            value={requestInfo.method}
            onChange={(e) => setRequestInfo({...requestInfo, method: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Content-Type
          </label>
          <input
            type="text"
            value={requestInfo.contentType}
            onChange={(e) => setRequestInfo({...requestInfo, contentType: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Accept
          </label>
          <input
            type="text"
            value={requestInfo.accept}
            onChange={(e) => setRequestInfo({...requestInfo, accept: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Request Body
          </label>
          <textarea
            value={requestInfo.body}
            onChange={(e) => setRequestInfo({...requestInfo, body: e.target.value})}
            rows={5}
            className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
          />
        </div>
      </div>
      
      <div className="mb-6">
        <button
          onClick={startTracing}
          disabled={isCollecting}
          className={`px-5 py-2 rounded-md text-white ${
            isCollecting ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {isCollecting ? 'Collecting...' : 'Send Request & Trace'}
        </button>
      </div>
      
      <div>
        <h3 className="text-xl font-semibold mb-3">Trace Results</h3>
        
        {traces.length === 0 ? (
          <div className="bg-gray-50 border border-gray-200 rounded-md p-4 text-gray-500 text-center">
            No trace data yet. Click "Send Request & Trace" to begin.
          </div>
        ) : (
          <div className="border border-gray-200 rounded-md overflow-hidden">
            {traces.map((trace, index) => (
              <div 
                key={index}
                className={`p-3 border-b border-gray-200 ${
                  trace.type === 'error' ? 'bg-red-50' :
                  trace.type === 'request' ? 'bg-blue-50' :
                  trace.type === 'response' ? 'bg-green-50' :
                  'bg-gray-50'
                }`}
              >
                <div className="flex items-start mb-2">
                  <span className="text-xs text-gray-500 mr-2">{trace.timestamp}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    trace.type === 'error' ? 'bg-red-100 text-red-800' :
                    trace.type === 'request' ? 'bg-blue-100 text-blue-800' :
                    trace.type === 'response' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {trace.type.toUpperCase()}
                  </span>
                </div>
                
                <div className="text-sm text-gray-800">
                  {trace.type === 'error' ? (
                    <div className="text-red-700">
                      <div className="font-semibold">{trace.data.message}</div>
                      <div className="font-mono text-xs mt-1">{trace.data.error}</div>
                    </div>
                  ) : trace.type === 'info' ? (
                    <div>{trace.data.message}</div>
                  ) : (
                    <pre className="bg-white p-2 rounded border border-gray-200 overflow-auto max-h-40 text-xs font-mono">
                      {JSON.stringify(trace.data, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
