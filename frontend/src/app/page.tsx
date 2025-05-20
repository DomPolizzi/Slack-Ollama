'use client'

import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

export default function Home() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Direct URLs to the API server
  const apiUrl = 'http://localhost:8080';
  const wsUrl = 'ws://localhost:8080/ws';

  // Connection status state
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  
  // Force use of REST API since WebSocket seems problematic
  const [useWebSocket, setUseWebSocket] = useState(false);
  
  // Test API connectivity on component mount
  useEffect(() => {
    const checkApiConnection = async () => {
      try {
        console.log('Testing API connection to:', apiUrl);
        const response = await fetch(`${apiUrl}`);
        if (response.ok) {
          console.log('API connection successful!');
          setApiStatus('connected');
        } else {
          console.log('API connection failed with status:', response.status);
          setApiStatus('disconnected');
        }
      } catch (error) {
        console.error('Error connecting to API:', error);
        setApiStatus('disconnected');
      }
    };
    
    checkApiConnection();
  }, [apiUrl]);
  
  // Don't test WebSocket for now - just use REST API

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    
    const currentInput = input.trim();
    const userMessage = { role: 'user' as const, content: currentInput }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setInput('')
    
    console.log('Sending message:', currentInput);
    console.log('Using WebSocket:', useWebSocket);
    
    if (useWebSocket) {
      try {
        console.log('Creating new WebSocket connection for this message');
        const ws = new WebSocket(wsUrl);
        
        // Set timeout for the whole operation
        const timeoutId = setTimeout(() => {
          if (isLoading) {
            console.log('Request timed out');
            ws.close();
            setIsLoading(false);
            setMessages(prev => [...prev, { 
              role: 'assistant' as const, 
              content: "I'm sorry, the request timed out. Please try again."
            }]);
          }
        }, 30000); // 30 second timeout
        
        // Define event handlers
        ws.onopen = () => {
          console.log('WebSocket opened, sending message');
          const payload = {
            query: currentInput,
            chat_history: messages
          };
          ws.send(JSON.stringify(payload));
        };
        
        ws.onmessage = (event) => {
          clearTimeout(timeoutId);
          try {
            const data = JSON.parse(event.data);
            console.log('Received response:', data);
            
            if (data.response) {
              setMessages(prev => [...prev, { 
                role: 'assistant' as const, 
                content: data.response 
              }]);
            } else if (data.error) {
              setMessages(prev => [...prev, { 
                role: 'assistant' as const, 
                content: 'Error: ' + data.error 
              }]);
            }
          } catch (error) {
            console.error('Error parsing response:', error);
            setMessages(prev => [...prev, { 
              role: 'assistant' as const, 
              content: 'Sorry, there was an error processing the response.'
            }]);
          } finally {
            setIsLoading(false);
            ws.close();
          }
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          clearTimeout(timeoutId);
          ws.close();
          // Fall back to REST API
          console.log('Falling back to REST API');
          sendViaRESTAPI(currentInput);
        };
        
        ws.onclose = () => {
          console.log('WebSocket closed');
        };
        
        return () => {
          clearTimeout(timeoutId);
          ws.close();
        };
      } catch (error) {
        console.error('Error setting up WebSocket:', error);
        // Fall back to REST API
        sendViaRESTAPI(currentInput);
      }
    } else {
      // Use REST API
      sendViaRESTAPI(currentInput);
    }
  };
  
  // Helper function to send via REST API
  const sendViaRESTAPI = async (currentInput: string) => {
    try {
      console.log('Sending via REST API to:', apiUrl);
      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          chat_history: messages
        }),
      });
      
      console.log('REST response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('REST response data:', data);
      
      setMessages(prev => [...prev, { 
        role: 'assistant' as const, 
        content: data.response 
      }]);
    } catch (error) {
      console.error('Error sending message via REST API:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant' as const, 
        content: 'Sorry, there was an error processing your request. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="text-3xl font-bold text-center mb-6">
          LLM Agent with LangGraph, Langfuse, Ollama, and ChromaDB
        </h1>
        
        <div className="text-center mb-4">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
            apiStatus === 'connected' 
              ? 'bg-green-100 text-green-800' 
              : apiStatus === 'checking' 
                ? 'bg-yellow-100 text-yellow-800' 
                : 'bg-red-100 text-red-800'
          }`}>
            <span className={`w-2 h-2 rounded-full mr-2 ${
              apiStatus === 'connected' 
                ? 'bg-green-500' 
                : apiStatus === 'checking' 
                  ? 'bg-yellow-500' 
                  : 'bg-red-500'
            }`}></span>
            {apiStatus === 'connected' 
              ? 'API Connected' 
              : apiStatus === 'checking' 
                ? 'Checking API Connection...' 
                : 'API Disconnected (Messages will not be sent)'}
          </div>
        </div>
        
        <div className="chat-container mb-24">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 my-8">
              <p>Start a conversation with the LLM Agent</p>
              <p className="text-sm mt-2">
                The agent uses LangGraph for orchestration, Langfuse for observability, 
                Ollama for local LLM inference, and ChromaDB for vector storage.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div 
                key={index} 
                className={`message-container ${
                  message.role === 'user' ? 'user-message' : 'assistant-message'
                }`}
              >
                <div className="font-bold mb-1">
                  {message.role === 'user' ? 'You' : 'Assistant'}:
                </div>
                <ReactMarkdown>
                  {message.content}
                </ReactMarkdown>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="input-container">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <textarea
              className="flex-1 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
              rows={3}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}
