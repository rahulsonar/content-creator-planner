# Copilot Instructions: Content Creator Planner

## Project Overview
A Next.js 16 App Router application for content creators to plan, organize, and track their projects. Built with TypeScript, Prisma ORM (PostgreSQL), JWT authentication, and Docker containerization. Focused on task management with hierarchical subtasks, calendar views, and Kanban boards.

**⚠️ Prototype Mode**: This is a prototype project. Do not create test cases or documentation. Keep implementations simple and focused on functionality.

## Project Structure
The repository is organized into separate directories:
- **nextjs/** - Next.js 16 application (frontend, API routes, middleware, Prisma ORM)
- **python-agents/** - Python FastAPI service for AI agents
- **docs/** - Project documentation

## Architecture & Key Decisions

### Authentication Flow
- **JWT-based authentication** using `jsonwebtoken` library
- **Dual token storage**: HTTP-only cookies (server) + localStorage (client-side API calls)
- **Middleware protection** ([nextjs/middleware.ts](nextjs/middleware.ts)) applies to ALL routes except `/login`, `/api/auth/*`, and static assets
- Default user: `admin@example.com` / `Admin123!` (see [nextjs/prisma/seed.ts](nextjs/prisma/seed.ts#L13))
- Password hashing: bcrypt with 12 rounds (see [nextjs/app/api/auth/login/route.ts](nextjs/app/api/auth/login/route.ts))

### Database & Prisma Patterns
- **Custom Prisma client setup** ([nextjs/lib/prisma.ts](nextjs/lib/prisma.ts)) uses PostgreSQL adapter with connection pooling
- **Hierarchical task structure**: Tasks can have parent/subtasks via self-referential relation (`parentId` → `subtasks[]`)
- **Task statuses**: `TODO`, `IN_PROGRESS`, `REVIEW`, `BLOCKED`, `COMPLETED`, `CANCELLED`
- **Priorities**: `LOW`, `MEDIUM`, `HIGH`, `URGENT`
- **No user association yet**: Tasks lack `userId` FK (all users see all tasks - authentication is route-level only)

### Route Organization
- **Route groups for layouts**: 
  - `nextjs/app/(app)/*` → Authenticated pages with navigation (Home, Kanban, Calendar, Chat)
  - `nextjs/app/login/*` → Public login page with gradient background layout
- **Path alias**: `@/*` maps to nextjs project root in [nextjs/tsconfig.json](nextjs/tsconfig.json#L22) - use for imports like `@/lib/prisma`

## Development Workflows

### Docker-First Approach
**This project runs entirely in Docker** - always execute commands inside containers:
- App container: `content-planner-app`
- Database container: `content-planner-db`

```bash
# Start both PostgreSQL and Next.js app
docker compose up

# Run ANY npm/node commands inside the app container:
docker exec -it content-planner-app npm run dev
docker exec -it content-planner-app npm install <package>
docker exec -it content-planner-app npm run db:seed

# Prisma commands inside container:
docker exec -it content-planner-app npx prisma migrate dev
docker exec -it content-planner-app npx prisma generate
docker exec -it content-planner-app npx prisma studio

# Database access:
docker exec -it content-planner-db psql -U postgres -d content_planner
```

### Local Development (Without Docker)
```bash
# Only if running outside Docker (not recommended):
npm install
npm run dev  # Starts on localhost:3000
npm run db:seed  # Seed database
```

**Docker volumes**:
- `node_modules` volume prevents host/container conflicts
- `.next` cache volume for faster rebuilds
- App source mounted at `/app` with live reload (WATCHPACK_POLLING enabled)

### Database Management
```bash
# Run migrations (Prisma CLI must be available)
npx prisma migrate dev

# Generate Prisma Client after schema changes
npx prisma generate

# Open Prisma Studio
npx prisma studio
```

## Code Conventions

### API Route Structure
- **Standard pattern** for API routes (see [nextjs/app/api/tasks/route.ts](nextjs/app/api/tasks/route.ts)):
  ```typescript
  import { prisma } from '@/lib/prisma';
  export async function GET() {
    try {
      const data = await prisma.task.findMany({ /* ... */ });
      return NextResponse.json(data);
    } catch (error) {
      console.error('Context:', error);
      return NextResponse.json({ error: 'Message' }, { status: 500 });
    }
  }
  ```
- **No manual token verification in routes**: Middleware handles auth before routes execute
- **Email normalization**: Always lowercase emails (e.g., `email.toLowerCase()`) in auth logic

### Authentication Helpers
- **Server-side**: Use [nextjs/lib/auth/helpers.ts](nextjs/lib/auth/helpers.ts) → `verifyToken()`, `generateToken()`
- **Client-side**: Same file exports `getStoredToken()`, `getStoredUser()`, `clearAuth()` with `typeof window` checks
- **JWT payload structure**: `{ userId, email, name }` with 7-day expiration

### Component Patterns
- **Client components**: Needed for interactivity (LogoutButton, forms, drag-and-drop)
- **Server components by default**: Use for static pages and data fetching
- **Tailwind styling**: Dark mode support via `dark:` classes (gradient backgrounds common)

## Critical Context for AI Agents

### When Modifying Tasks
1. **Task relationships**: Updating parent tasks may require cascading changes to subtasks
2. **Status transitions**: Consider if `completedAt` should be set when status → `COMPLETED`
3. **Time tracking**: `estimatedHours` vs `actualHours` - maintain both fields for analytics

### When Adding Auth Features
1. **User model exists** but tasks aren't scoped per-user yet
2. **JWT_SECRET**: Currently defaults to `'your-secret-key-change-in-production'` - should use env var
3. **Token refresh**: Not implemented - tokens expire after 7 days without renewal

### Environment Variables Required
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # Required for Prisma
JWT_SECRET=<secure-random-string>                      # Used in middleware + auth routes
NODE_ENV=development|production                         # Affects Prisma client caching
```

### Common Pitfalls
- **Prisma client regeneration**: Always run `npx prisma generate` after schema changes
- **Migration state**: Migrations tracked in `nextjs/prisma/migrations/` - never edit committed migrations
- **Docker volume caching**: If deps aren't installing, delete `node_modules` volume and rebuild
- **Middleware matcher**: Be careful with pattern - excludes `_next/*`, images, favicons

## File Reference Quick Links
- Auth implementation: [nextjs/app/api/auth/login/route.ts](nextjs/app/api/auth/login/route.ts), [nextjs/middleware.ts](nextjs/middleware.ts)
- Database schema: [nextjs/prisma/schema.prisma](nextjs/prisma/schema.prisma)
- Seed data: [nextjs/prisma/seed.ts](nextjs/prisma/seed.ts) (20+ realistic content creator tasks)
- Prisma setup: [nextjs/lib/prisma.ts](nextjs/lib/prisma.ts) (uses `@prisma/adapter-pg`)
- Docker config: [docker-compose.yml](docker-compose.yml), [nextjs/Dockerfile](nextjs/Dockerfile)
- Auth docs: [docs/authentication.md](docs/authentication.md) (API specs + examples)
