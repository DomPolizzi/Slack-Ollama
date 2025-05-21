import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const message = body.message;
  console.log('API /api/chat received message:', message);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://api:8080';

  // Determine if client requested streaming
  const accept = req.headers.get('accept') || '';
  if (accept.includes('text/plain')) {
    // Proxy streaming endpoint
    const backend = await fetch(`${apiUrl}/v1/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    return new Response(backend.body, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
      },
    });
  }

  // Fallback to JSON endpoint
  const backend = await fetch(`${apiUrl}/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  const data = await backend.json();
  return NextResponse.json({ response: data.response });
}
