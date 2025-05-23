import { NextRequest } from 'next/server';

export async function POST(req: NextRequest) {
  const { message, chat_history } = await req.json();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://api:8080';

  // Proxy streaming from backend
  const backendRes = await fetch(`${apiUrl}/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, chat_history }),
  });

  if (!backendRes.ok || !backendRes.body) {
    return new Response('Streaming unavailable', { status: 500 });
  }

  return new Response(backendRes.body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Transfer-Encoding': 'chunked'
    }
  });
}
