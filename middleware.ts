import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Force Node.js runtime for middleware
export const runtime = 'nodejs';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes that don't require authentication
  const publicRoutes = ['/login', '/api/auth/login', '/api/auth/signup', '/api/auth/logout'];
  
  if (publicRoutes.includes(pathname)) {
    return NextResponse.next();
  }

  // Check for token in cookies or Authorization header
  const token = request.cookies.get('auth-token')?.value || 
                request.headers.get('authorization')?.replace('Bearer ', '');

  // If no token, redirect to login
  if (!token) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }
    return NextResponse.redirect(new URL('/login', request.url));
  }

  try {
    // Verify token - dynamic import to ensure it works in Node runtime
    const jwt = require('jsonwebtoken');
    jwt.verify(token, JWT_SECRET);
    return NextResponse.next();
  } catch (error) {
    // Invalid token
    if (pathname.startsWith('/api/')) {
      return NextResponse.json(
        { error: 'Invalid or expired token' },
        { status: 401 }
      );
    }
    return NextResponse.redirect(new URL('/login', request.url));
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public folder)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
