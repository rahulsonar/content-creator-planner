# Authentication System

This application uses JWT (JSON Web Tokens) for authentication.

## Features

- ✅ User login with email and password
- ✅ User registration (signup)
- ✅ JWT token generation
- ✅ Secure HTTP-only cookies for token storage
- ✅ LocalStorage token storage for API calls
- ✅ Protected routes via middleware
- ✅ Logout functionality
- ✅ Password hashing with bcrypt

## API Endpoints

### POST /api/auth/login
Login with existing credentials.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "...",
    "email": "user@example.com",
    "name": "John Doe",
    "createdAt": "...",
    "updatedAt": "..."
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful"
}
```

### POST /api/auth/signup
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "...",
    "email": "user@example.com",
    "name": "John Doe",
    "createdAt": "...",
    "updatedAt": "..."
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Account created successfully"
}
```

### POST /api/auth/logout
Logout and clear authentication cookie.

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Token Storage

The authentication system uses a **dual storage approach** for maximum flexibility and security:

1. **HTTP-only Cookies** (Primary, More Secure)
   - Automatically set by the server
   - Cannot be accessed by JavaScript (XSS protection)
   - Sent automatically with requests to the same domain
   - Expires in 7 days

2. **LocalStorage** (Secondary, For Client-Side Access)
   - Token is also returned in the response body
   - Stored in `localStorage` for client-side API calls
   - Accessible via `localStorage.getItem('auth-token')`
   - User data stored in `localStorage.getItem('user')`

## Using the Authentication Token

### From Server-Side (Recommended)
The middleware automatically reads the token from cookies, so no additional configuration is needed for server-side routes.

### From Client-Side (API Calls)
```typescript
const token = localStorage.getItem('auth-token');

const response = await fetch('/api/tasks', {
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});
```

## Protected Routes

The middleware in `middleware.ts` automatically protects all routes except:
- `/login`
- `/api/auth/login`
- `/api/auth/signup`

To add more public routes, update the `publicRoutes` array in the middleware.

## Environment Variables

Add to your `.env` file:

```env
JWT_SECRET=your-very-secure-secret-key-here-change-this-in-production
```

**Important:** Change the default JWT_SECRET in production!

## Security Features

- ✅ Passwords are hashed using bcrypt (10 rounds)
- ✅ Tokens expire after 7 days
- ✅ HTTP-only cookies prevent XSS attacks
- ✅ Secure flag enabled in production
- ✅ SameSite=lax prevents CSRF attacks
- ✅ Passwords never returned in API responses
- ✅ Email validation and duplicate checking

## Testing the Authentication

You can test the login with the seeded user:

```bash
# Run the seed script (if not already done)
docker exec -it content-planner-app npm run db:seed

# Test login with curl
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

Or use the provided test script:
```bash
./test-login.sh
```
