# YouTube Content Planner

> AI-powered strategic content planning for YouTube creators

## Overview

YouTube Content Planner helps educational and niche content creators plan their content strategy 6-12 months in advance. Unlike tactical SEO tools, this platform focuses on long-term strategic planning: theme selection, series architecture, content balance, and niche-specific curriculum building.

## Problem We're Solving

Most YouTube creators struggle with:
- **Strategic planning** - Planning beyond the next 2-3 videos
- **Content architecture** - Designing series and thematic arcs
- **Balance** - Mixing evergreen content with trending topics
- **Consistency** - Maintaining regular uploads without burnout
- **Differentiation** - Standing out in competitive niches

Existing tools (VidIQ, TubeBuddy) focus on SEO and keywords. We focus on **strategic content planning**.

## Target Users

- Educational creators (history, science, tech)
- Tech review channels
- Tutorial/how-to channels
- 10k-500k subscriber range
- Solo creators or small teams

## Core Features

### Phase 1: MVP (Current)
- 📅 **Content Calendar** - Visual planning interface with drag-and-drop
- 📝 **Video Management** - Track ideas, planned, in-production, published
- 🎨 **Series Grouping** - Color-coded content series
- 💾 **Local Storage** - No backend required initially

### Phase 2: Intelligence Layer
- 🤖 **AI Strategy Assistant** - Multi-agent system for content suggestions
- 📊 **Performance Analytics** - YouTube data integration
- 🎯 **Context-Aware Planning** - Learns your channel's patterns
- 🔍 **Trend Detection** - Identifies opportunities in your niche

### Phase 3: Collaboration
- 👥 **Team Features** - Collaborate on content planning
- 📈 **Analytics Dashboard** - Performance insights
- 🔄 **Workflow Automation** - Recurring content templates
- 📤 **Export/Import** - Integration with other tools

## Tech Stack

- **Frontend**: Next.js 15 (App Router), React, TypeScript
- **UI Components**: Tailwind CSS
- **Calendar**: FullCalendar
- **AI Layer**: OpenAI GPT-4 / Anthropic Claude (multi-agent architecture)
- **Storage**: localStorage (MVP) → PostgreSQL (Production)
- **APIs**: YouTube Data API v3

## Project Structure

```
youtube-planner/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   ├── calendar/          # Calendar view
│   └── layout.tsx         # Root layout
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── calendar/         # Calendar components
│   ├── video-card.tsx    # Video card component
│   └── ai-panel.tsx      # AI suggestions panel
├── lib/                   # Utilities
│   ├── ai/               # AI agent system
│   │   ├── orchestrator.ts
│   │   ├── analytics-agent.ts
│   │   ├── strategy-agent.ts
│   │   └── context-manager.ts
│   ├── storage.ts        # Storage utilities
│   └── youtube-api.ts    # YouTube API wrapper
├── types/                 # TypeScript types
└── public/               # Static assets
```

## AI Agent Architecture

The platform uses a multi-agent system for intelligent suggestions:

```
Orchestrator Agent
├── Analytics Agent       # Analyzes channel performance data
├── Strategy Agent        # Generates content suggestions
├── Calendar Agent        # Optimizes scheduling and pacing
└── Trend Research Agent  # Monitors trends and opportunities
```

Each agent maintains **user context** including:
- Channel profile and positioning
- Historical performance patterns
- Content history and calendar
- Audience insights
- Production constraints

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- (Optional) YouTube API credentials
- (Optional) OpenAI or Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/rahulsonar/content-creator-planner.git
cd content-creator-planner

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your API keys

# Run development server
npm run dev
```

Visit `http://localhost:3000`

### Environment Variables

```bash
# Required for AI features
OPENAI_API_KEY=your_openai_key
# OR
ANTHROPIC_API_KEY=your_anthropic_key

# Required for YouTube integration
YOUTUBE_API_KEY=your_youtube_api_key

# Optional
DATABASE_URL=postgresql://...
```

## Development Roadmap

### ✅ Phase 0: Validation (Current)
- [x] User interviews with 15 creators
- [x] Problem validation
- [x] Feature prioritization
- [ ] Prototype testing

### 🚧 Phase 1: MVP (Weeks 1-4)
- [ ] Basic calendar interface
- [ ] Video management (CRUD)
- [ ] Series grouping
- [ ] localStorage persistence
- [ ] Single AI agent with comprehensive prompting

### 📋 Phase 2: Intelligence (Weeks 5-12)
- [ ] YouTube Analytics integration
- [ ] Context management system
- [ ] Multi-agent architecture
- [ ] Performance insights dashboard
- [ ] Backend database (Supabase/PostgreSQL)

### 🚀 Phase 3: Scale (Weeks 13-24)
- [ ] User authentication
- [ ] Team collaboration features
- [ ] Advanced analytics
- [ ] Payment integration ($30-50/month)
- [ ] Mobile app

## Validation Metrics

Target for initial validation (15 interviews):
- ✅ 7+ creators show genuine excitement
- ✅ 5+ express willingness to pay $30-50/month
- ✅ Clear pain point validation (not just "nice to have")

## Competitive Landscape

| Tool | Focus | Price | Our Differentiation |
|------|-------|-------|---------------------|
| VidIQ | SEO, keywords | $10-50/mo | Strategic vs tactical |
| TubeBuddy | Optimization | $9-50/mo | Long-term planning |
| OutlierKit | Competitor analysis | $9/mo | Content architecture |
| ChatGPT | General AI | $20/mo | Channel-specific context |
| **Us** | Strategic planning | $30-50/mo | 6-12 month strategy + AI |

## Contributing

We're currently in early development and not accepting external contributions yet. If you're a YouTube creator interested in testing early versions, please reach out!

## Business Model

**Target Pricing**: $30-50/month per creator

**Revenue Projections**:
- 100 users × $40/mo = $4,000 MRR
- 500 users × $40/mo = $20,000 MRR
- 1,000 users × $40/mo = $40,000 MRR

**Cost Structure** (per user/month):
- AI API calls: $5-15
- Infrastructure: $1-3
- YouTube API: Free (within quotas)
- **Gross margin**: ~60-70%

## Research & Validation

This project is informed by:
- 15 creator interviews (10k-500k subs)
- Competitive analysis of 10+ tools
- YouTube creator pain point research
- Content strategy best practices

Interview guide and findings available in `/docs/research/`

## License

Proprietary - All rights reserved (for now)

## Contact

- **Twitter**: [@yourhandle](https://twitter.com/yourhandle)
- **Email**: your@email.com
- **Website**: https://yourdomain.com

---

**Status**: 🚧 Early Development | 🎯 Validating Problem-Solution Fit

Last updated: January 2026