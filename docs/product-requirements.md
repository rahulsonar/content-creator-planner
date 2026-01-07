# Product Requirements Document (PRD)
## Content Creator Planner - AI Agent Integration

**Version:** 1.0  
**Date:** January 7, 2026  
**Status:** Planning Phase

---

## 1. Executive Summary

### Vision
Transform the Content Creator Planner from a manual task management tool into an intelligent assistant that helps content creators onboard, plan, and execute their content strategy through conversational AI agents.

### Goals
- **Reduce onboarding time** from 30+ minutes (manual form filling) to 5-10 minutes (natural conversation)
- **Automate task generation** based on user context and goals
- **Provide personalized recommendations** using AI analysis of user's content strategy
- **Enable natural interaction** through chat-based interface with real-time streaming responses

### Target Users
- YouTube content creators (primary)
- Bloggers, podcasters, and multi-platform creators (secondary)
- Both individual creators and small content teams (2-5 people)

---

## 2. Problem Statement

### Current Pain Points
1. **Manual Onboarding**: Users must fill out long forms to set up their profile
2. **Task Creation Overhead**: Creating detailed task breakdown for content projects is time-consuming
3. **No Contextual Planning**: Existing systems don't understand creator's unique situation (channel size, niche, team structure)
4. **Static Experience**: No adaptive guidance based on user behavior

### Proposed Solution
Introduce AI agents that:
- Conduct conversational onboarding to gather user context naturally
- Generate comprehensive content plans with task breakdowns
- Provide ongoing assistance through chat interface
- Adapt recommendations based on user's profile and history

---

## 3. Feature Requirements

### 3.1 Conversational Onboarding Agent

**Priority:** P0 (Must Have)

**Description:**  
Replace traditional signup forms with a guided conversation that collects:
- Channel information (name, type, topic, existing vs. new)
- Demographics (age group, location)
- Content strategy (team size, upload frequency, goals)
- Thought process and preferences

**User Stories:**
- As a new user, I want to describe my channel in natural language so I don't have to fill out boring forms
- As a creator with an existing channel, I want the system to understand my context without repetitive questions
- As a team lead, I want to specify that I manage multiple creators

**Acceptance Criteria:**
- [ ] Conversation completes in 5-15 messages
- [ ] User can pause and resume onboarding
- [ ] System saves context to markdown file for future reference
- [ ] User.onboardingCompleted flag set upon completion
- [ ] Graceful handling of vague or incomplete answers

**Technical Notes:**
- Uses OpenAI GPT-4 for natural language understanding
- Stores conversation history in Conversation model
- Generates user_context/{userId}/context.md file

---

### 3.2 Content Planning Agent

**Priority:** P0 (Must Have)

**Description:**  
AI agent that analyzes user context and generates detailed content plans with task breakdowns.

**User Stories:**
- As a creator, I want AI to suggest video ideas based on my niche
- As a busy creator, I want a 6-month plan broken into actionable tasks
- As a team member, I want tasks assigned based on dependencies and skills

**Acceptance Criteria:**
- [ ] Generates 10-20 task suggestions per planning session
- [ ] Tasks include title, description, due date, priority, estimated hours
- [ ] Respects user's upload frequency preferences
- [ ] Identifies task dependencies (e.g., "Script writing" before "Video recording")
- [ ] Provides reasoning for each task suggestion
- [ ] User can approve/reject plan before committing to database

**Technical Notes:**
- Loads user_context/{userId}/context.md for personalization
- Uses Claude 3.5 for complex reasoning tasks
- Returns structured JSON for task creation

---

### 3.3 AI-Powered Script Writing & Content Ideas

**Priority:** P0 (Must Have)

**Description:**  
In-house AI agent that replaces the need for users to switch to ChatGPT or Claude for content creation. Provides context-aware script writing, content ideation, and creative assistance with integrated tools to take direct action on tasks.

**User Stories:**
- As a creator, I want to generate video scripts without leaving the platform
- As a user brainstorming content ideas, I want AI that understands my channel's niche and past content
- As a busy creator, I want AI to draft outlines and take action (create tasks, set deadlines) in one conversation

**Acceptance Criteria:**
- [ ] AI agent has access to full user context (channel info, past content, goals)
- [ ] Supports script writing for various content types (tutorials, vlogs, reviews, etc.)
- [ ] Generates content ideas based on channel niche and audience
- [ ] Integrated tools allow AI to create tasks, update timelines, and manage calendar
- [ ] Responses include actionable next steps with automatic task creation option
- [ ] Context switching between planning and creative modes seamlessly

**Technical Notes:**
- Uses user_context/{userId}/context.md and task history for personalization
- Tool integration allows direct database operations (task creation, updates)
- Supports multi-turn conversations with memory of previous creative sessions

---

### 3.4 YouTube Analytics Integration

**Priority:** P1 (Should Have)

**Description:**  
Integration with YouTube analytics services (OutlierKit, VidIQ, or similar APIs) to fetch comprehensive performance data. AI agents analyze this data to provide actionable content suggestions.

**User Stories:**
- As a creator, I want AI to analyze which of my videos perform best and suggest similar topics
- As a growing channel, I want recommendations based on trending topics in my niche
- As a data-driven creator, I want AI to identify patterns in my audience engagement

**Acceptance Criteria:**
- [ ] Integration with at least one analytics service (OutlierKit or VidIQ)
- [ ] Fetches key metrics: views, watch time, CTR, engagement rate, audience retention
- [ ] AI agents can query analytics data when making content recommendations
- [ ] Automatic weekly summary of performance trends
- [ ] Content suggestions based on: top-performing videos, trending topics, competitor analysis
- [ ] Identifies underperforming content categories to avoid

**Technical Notes:**
- API credentials stored securely per user
- Analytics data cached to minimize API calls
- AI agents receive analytics summary in context, not raw data
- Fallback to YouTube native API if third-party service unavailable

**Data Points to Track:**
- Video performance metrics (views, likes, comments, shares)
- Audience demographics and growth trends
- Best posting times and frequencies
- Keyword performance and search rankings
- Competitor channel insights (if available via API)

---

### 3.5 Multi-Model Orchestrator

**Priority:** P1 (Should Have)

**Description:**  
Intelligent routing layer that selects optimal LLM model based on task complexity and cost.

**Routing Logic:**
- **OpenAI GPT-4**: Complex planning, nuanced conversations (onboarding final steps)
- **OpenAI GPT-3.5 Turbo**: Simple queries, follow-up questions (onboarding early steps)
- **Claude 3.5 Sonnet**: Research-heavy tasks, long context analysis

**Acceptance Criteria:**
- [ ] Automatically routes requests to appropriate model
- [ ] Tracks token usage per user per day
- [ ] Falls back to cheaper model if user exceeds daily limits
- [ ] Logs routing decisions for cost analysis

---

### 3.6 Real-Time Chat Interface

**Priority:** P0 (Must Have)

**Description:**  
WebSocket-based chat UI with streaming responses from AI agents.

**User Stories:**
- As a user, I want to see AI's response appear word-by-word like ChatGPT
- As a mobile user, I want chat to work on small screens
- As a returning user, I want to see my conversation history

**Acceptance Criteria:**
- [ ] Responses stream in real-time (no waiting for full response)
- [ ] Chat history persists across sessions
- [ ] Typing indicators during AI processing
- [ ] Support for markdown formatting in messages
- [ ] Mobile-responsive design

**Technical Notes:**
- WebSocket connection via Socket.io or native WebSockets
- Frontend React component (existing chat component to be adapted)
- Automatic reconnection on connection loss

---

### 3.7 User Context Management

**Priority:** P0 (Must Have)

**Description:**  
System for storing and retrieving user context for AI personalization. **IMPORTANT:** User context is exclusively for AI agent consumption and should never be exposed to users through the UI. This context-aware intelligence is the platform's competitive advantage.

**Storage Strategy:**
- **Database (UserContext model)**: Structured fields (channelName, uploadFrequency, etc.)
- **Markdown files (AI-only)**: Human-readable context summaries for AI consumption, stored securely with no user access
- **Analytics cache (AI-only)**: YouTube performance data and insights for AI recommendations

**Markdown File Structure:**
```markdown
# User Context: [User Name]

## Channel Information
- **Name:** [Channel Name]
- **Type:** Existing/New
- **Topic:** [Topic/Niche]
- **Current Status:** [Subscriber count, video count if existing]

## Demographics
- **Age Group:** [Age range]
- **Location:** [Country/Region]

## Content Strategy
- **Team:** Solo/Team (Size: X)
- **Upload Frequency:** Weekly/Biweekly/Monthly
- **Goals:** [Short-term and long-term goals]
- **Challenges:** [Pain points mentioned during onboarding]

## Preferences
- [Additional preferences or notes from conversations]
```

**Acceptance Criteria:**
- [ ] Context file created after onboarding completion
- [ ] File updated when user modifies profile or new analytics data is fetched
- [ ] AI agents can read context file for personalization
- [ ] **Context files are stored in a secure directory with no API endpoints exposing them to users**
- [ ] **No UI components display raw context or internal AI reasoning**
- [ ] Admin-only access for debugging context files
- [ ] Context includes analytics insights and performance patterns

**Security Notes:**
- Context files stored in `/agent_context/{userId}/` (not publicly accessible)
- No export functionality for context files
- API routes must never return context.md content to client
- UI only shows results of AI processing, not the underlying context

---

### 3.8 Rate Limiting & Cost Control

**Priority:** P1 (Should Have)

**Description:**  
Prevent excessive API costs through user-level rate limiting.

**Initial Limits (Prototype Phase):**
- **Per User Per Day:**
  - 50 messages to AI agents
  - 100,000 input tokens (~75 pages of text)
  - 20,000 output tokens (~15 pages of AI responses)
- **Per Planning Session:**
  - Maximum 30 tasks generated at once
  - Maximum 3 planning sessions per week

**Acceptance Criteria:**
- [ ] User sees remaining quota in UI
- [ ] Graceful error message when limit exceeded
- [ ] Admin can adjust limits per user
- [ ] Metrics dashboard for cost monitoring

---

## 4. Non-Functional Requirements

### 4.1 Performance
- AI response latency: < 3 seconds for first token
- Task generation: < 10 seconds for 15-task plan
- WebSocket latency: < 100ms

### 4.2 Scalability
- Support 1,000 concurrent users (Phase 1)
- Support 10,000 users total (Phase 1)
- Independent scaling of Python agent service

### 4.3 Security
- Service-to-service authentication (Next.js ↔ Python)
- API key rotation support
- User data encryption at rest
- HTTPS/WSS for all connections

### 4.4 Reliability
- 99.5% uptime for chat service
- Automatic retry for failed LLM API calls
- Conversation state persistence (resume after crash)

---

## 5. Out of Scope (Phase 1)

- ❌ Voice input/output
- ❌ Image generation for thumbnails
- ❌ Multi-language support
- ❌ Mobile native apps
- ❌ Collaborative editing of plans
- ❌ Direct video upload/editing
- ❌ User-visible context files or internal AI reasoning logs

---

## 6. Success Metrics

### Primary KPIs
1. **Onboarding Completion Rate:** > 80% of users who start onboarding finish it
2. **Task Plan Acceptance Rate:** > 70% of generated plans get approved by users
3. **Time to First Plan:** < 15 minutes from signup to first generated plan
4. **Daily Active Users (DAU) with AI Interaction:** > 30% of total users
5. **Script/Content Creation Usage:** > 50% of active users use AI writing features weekly

### Secondary Metrics
- Average conversation length (target: 8-12 messages)
- Token cost per user per month (target: < $3 including analytics processing)
- Task completion rate for AI-generated tasks (target: > 60%)
- User retention after 30 days (target: > 50%)
- Analytics-driven content acceptance rate (target: > 65%)
- User engagement with AI-suggested topics vs. self-created (track ratio)

---

## 7. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM API cost overrun | High | Medium | Implement strict rate limits, use cheaper models for simple tasks |
| OpenAI/Claude API outage | High | Low | Implement fallback models, queue system for retry |
| Poor AI suggestions (users reject plans) | Medium | Medium | Collect feedback, fine-tune prompts, allow manual editing |
| WebSocket connection issues | Medium | Medium | Fallback to HTTP polling, auto-reconnect logic |
| Slow Python service response | Medium | Low | Implement caching, optimize prompts, use streaming |
| Context file exposure to users | High | Low | Strict API route validation, no export endpoints, security audits |
| Analytics API rate limits or costs | Medium | Medium | Cache data aggressively, batch requests, use free tier limits wisely |
| Inaccurate analytics-based recommendations | Medium | Medium | Combine multiple data sources, allow user feedback to retrain |

---

## 8. Dependencies

### External Services
- OpenAI API (GPT-4, GPT-3.5 Turbo)
- Anthropic API (Claude 3.5 Sonnet)
- OutlierKit API or VidIQ API (YouTube analytics)
- YouTube Data API v3 (fallback for basic analytics)

### Technical Dependencies
- Next.js 16 (existing)
- FastAPI (new - Python agent service)
- PostgreSQL (existing)
- WebSocket library (Socket.io or native)

### Development Dependencies
- Docker (for Python service containerization)
- Prisma (schema updates required)

---

## 9. Timeline

See [implementation-plan.md](./implementation-plan.md) for detailed week-by-week breakdown.

**High-Level Milestones:**
- **Week 1:** Infrastructure setup (Prisma schema, Python project, proxy routes)
- **Week 2:** Onboarding agent MVP
- **Week 3:** Planning agent MVP
- **Week 4:** Polish, testing, rate limiting

**Target Launch:** End of January 2026 (4 weeks)

---

## 10. Open Questions

1. **Context file sections:** With analytics data, what's the optimal structure for AI consumption vs. file size?
2. **Rate limit numbers:** 50 messages/day per user - is this too restrictive with script writing features?
3. **Task approval UI:** Should users approve tasks one-by-one or as a batch?
4. **Conversation branching:** Should users be able to have multiple concurrent conversations (planning + script writing)?
5. **Analytics service selection:** Start with OutlierKit, VidIQ, or build direct YouTube API integration first?
6. **Analytics refresh frequency:** Daily, weekly, or on-demand? Balance API costs vs. data freshness
7. **Context visibility debugging:** How do admins troubleshoot AI behavior without exposing context to users?
8. **Script templates:** Should we provide genre-specific templates (tutorial, vlog, review) or pure freeform?

---

## Appendix A: User Personas

### Persona 1: Solo Tech YouTuber
- **Name:** Alex
- **Channel:** 5,000 subscribers, coding tutorials
- **Pain Point:** Spends hours planning video series, wants AI to suggest logical progression
- **Upload Frequency:** Weekly
- **Key Feature:** Task dependencies for tutorial series

### Persona 2: Lifestyle Vlogger Team
- **Name:** Sarah (Manager)
- **Channel:** 50,000 subscribers, travel & food
- **Pain Point:** Coordinating 3-person team (videographer, editor, social media manager)
- **Upload Frequency:** 2-3 times per week
- **Key Feature:** Team task assignment

### Persona 3: New Creator
- **Name:** Jordan
- **Channel:** Not yet created
- **Pain Point:** Overwhelmed by all the steps to start a channel
- **Upload Frequency:** Planning to do monthly
- **Key Feature:** Onboarding that builds confidence with actionable first steps
