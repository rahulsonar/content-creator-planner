/**
 * Shared secrets resolution.
 * Falls back to dev-only defaults locally, but refuses to run in production
 * without real values. Resolved lazily so `next build` doesn't need them.
 */

function requireSecret(name: string, devFallback: string): string {
  const value = process.env[name];
  if (value) return value;
  if (process.env.NODE_ENV === 'production') {
    throw new Error(`${name} must be set in production`);
  }
  return devFallback;
}

export const getJwtSecret = () =>
  requireSecret('JWT_SECRET', 'your-secret-key-change-in-production');

export const getInternalApiSecret = () =>
  requireSecret('INTERNAL_API_SECRET', 'dev-secret-change-in-production');
