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
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws'
  
  // WebSocket connection
  const [socket, setSocket] = useState<WebSocket | null>(null)
  
  useEffect(() => {
    // Initialize WebSocket connection
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.response) {
          setMessages(prev => [...prev, { role: 'assistant' as const, content: data.response }])
          setIsLoading(false)
        } else if (data.error) {
          console.error('Error from server:', data.error)
          setIsLoading(false)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
        setIsLoading(false)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setIsLoading(false)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }
    
    setSocket(ws)
    
    // Clean up on unmount
    return () => {
      ws.close()
    }
  }, [wsUrl])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    
    const userMessage = { role: 'user' as const, content: input }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    
    // Send message via WebSocket if connected
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        query: input,
        chat_history: messages
      }))
      setInput('')
    } else {
      // Fallback to REST API if WebSocket is not connected
      try {
        const response = await fetch(`${apiUrl}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: input,
            chat_history: messages
          }),
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        setMessages(prev => [...prev, { role: 'assistant' as const, content: data.response }])
        setInput('')
      } catch (error) {
        console.error('Error sending message:', error)
        setMessages(prev => [...prev, { role: 'assistant' as const, content: 'Sorry, there was an error processing your request.' }])
      } finally {
        setIsLoading(false)
      }
    }
  }

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="text-3xl font-bold text-center mb-8">
          LLM Agent with LangGraph, Langfuse, Ollama, and ChromaDB
        </h1>
        
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
