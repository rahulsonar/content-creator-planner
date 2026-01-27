/**
 * Get current user information
 * Returns user data and token from HTTP-only cookie
 */

import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth/helpers';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth-token')?.value;

    if (!token) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Verify the token
    const decoded = await verifyToken(token);
    if (!decoded) {
      return NextResponse.json(
        { error: 'Invalid or expired token' },
        { status: 401 }
      );
    }

    // Return user info and token for localStorage
    return NextResponse.json({
      user: {
        id: decoded.userId,
        email: decoded.email,
        name: decoded.name,
      },
      token: token, // Send token so client can store it in localStorage for WebSocket
    });
  } catch (error) {
    console.error('Get user error:', error);
    return NextResponse.json(
      { error: 'An error occurred' },
      { status: 500 }
    );
  }
}
