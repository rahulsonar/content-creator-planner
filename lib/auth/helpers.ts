import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

export interface JWTPayload {
  userId: string;
  email: string;
  name: string | null;
}

export function verifyToken(token: string): JWTPayload | null {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as JWTPayload;
    return decoded;
  } catch (error) {
    return null;
  }
}

export function generateToken(payload: JWTPayload): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '7d' });
}

// Client-side helpers
export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth-token');
}

export function getStoredUser(): any | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

export function clearAuth(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth-token');
  localStorage.removeItem('user');
}
