import jwt from 'jsonwebtoken';
import { getJwtSecret } from './secrets';


export interface JWTPayload {
  userId: number;
  email: string;
  name: string | null;
}

export function verifyToken(token: string): JWTPayload | null {
  try {
    const decoded = jwt.verify(token, getJwtSecret()) as JWTPayload;
    return decoded;
  } catch (error) {
    return null;
  }
}

export function generateToken(payload: JWTPayload): string {
  return jwt.sign(payload, getJwtSecret(), { expiresIn: '7d' });
}

// Re-export client-side helpers for backwards compatibility
export { getStoredToken, getStoredUser, clearAuth } from './client';
