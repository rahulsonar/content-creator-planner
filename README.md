# Content Creator Planner

A Next.js application designed to help content creators plan, organize, and schedule their content creation journey.

## Project Structure

```
├── nextjs/            # Next.js 16 application (frontend, API routes & Prisma ORM)
├── python-agents/     # Python FastAPI service for AI agents
├── docs/             # Project documentation
└── docker-compose.yml # Docker orchestration
```

## Features

- 📅 **Plan Ahead** - Create content calendars and never miss a posting schedule
- 💡 **Organize Ideas** - Keep track of all your content ideas in one place
- 📊 **Track Progress** - Monitor your content performance and engagement
- 🤖 **AI Planning Agent** - Get AI-powered content planning assistance
- 🧪 **Dummy AI Mode** - Test without API costs (see [Dummy AI Mode docs](docs/dummy-ai-mode.md))

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# AI Configuration
USE_DUMMY_AI=false          # Set to true for testing without API costs
OPENAI_API_KEY=your_key     # Required when USE_DUMMY_AI=false


# Security
JWT_SECRET=your-secret-key
INTERNAL_API_SECRET=your-internal-secret
```

### Dummy AI Mode

For development and testing without incurring AI API costs, enable dummy mode:

```env
USE_DUMMY_AI=true
```

This will return predefined responses instead of calling OpenAI APIs. See [docs/dummy-ai-mode.md](docs/dummy-ai-mode.md) for details.

## Getting Started

### Using Docker (Recommended)

Start both PostgreSQL and Next.js app:

```bash
docker compose up
```

Run commands inside the container:

```bash
# Install dependencies
docker exec -it content-planner-app npm install

# Run development server
docker exec -it content-planner-app npm run dev

# Database operations
docker exec -it content-planner-app npx prisma migrate dev
docker exec -it content-planner-app npx prisma generate
docker exec -it content-planner-app npm run db:seed
```

### Local Development (Without Docker)

Navigate to the nextjs directory:

```bash
cd nextjs
npm install
```

Then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `nextjs/app/page.tsx`. The page auto-updates as you edit the file.

## Tech Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Turbopack** - Fast bundler for development

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
