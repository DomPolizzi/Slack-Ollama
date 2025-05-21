'use client';
import React from 'react';
import Chat from '@/components/Chat';
import DirectAPITest from '../components/DirectAPITest';
import TracingTool from '../components/TracingTool';
import DebugChat from '../components/DebugChat';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4 md:p-8 bg-gray-50">
      {/* Page header */}
      <header className="w-full text-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Agent</h1>
        <p className="text-gray-600">Powered by advanced language models to assist with your tasks</p>
      </header>

      {/* Chat Interface */}
      <section className="w-full mb-8 h-[600px]">
        <h2 className="text-xl font-semibold mb-4">Chat Interface</h2>
        <Chat />
      </section>

      {/* Direct API Test */}
      <section className="w-full mb-8">
        <DirectAPITest />
      </section>

      {/* Tracing Tool */}
      <section className="w-full mb-8">
        <TracingTool />
      </section>

      {/* Debug Chat */}
      <section className="w-full mb-8">
        <DebugChat />
      </section>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-sm text-gray-500">
        © {new Date().getFullYear()} AI Agent | All rights reserved
      </footer>
    </main>
  );
}
