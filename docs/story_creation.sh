#!/bin/bash
set -euo pipefail
REPO="rahulsonar/content-creator-planner"
PROJECT=4
OWNER="rahulsonar"
STATUS="Backlog"

# Associative arrays to store epic and story issue numbers
declare -A EPIC_NUMBERS
declare -A STORY_NUMBERS

create_issue() {
  local title="$1"
  local body="$2"
  local label1="$3"
  local label2="$4"
  
  # Create the issue first
  issue_json=$(gh api repos/$REPO/issues \
    -f title="$title" \
    -f body="$body")
  
  number=$(echo "$issue_json" | jq -r .number)
  id=$(echo "$issue_json" | jq -r .id)
  
  # Add labels after creation
  gh issue edit "$number" --repo "$REPO" --add-label "$label1" --add-label "$label2" >/dev/null 2>&1 || true
  
  echo "Created issue #$number: $title"
  
  # Try to add to project
  gh project item-add "$PROJECT" --owner "$OWNER" --id "$id" --field "Status=$STATUS" >/dev/null 2>&1 || true
  
  echo "  Added to project $PROJECT with Status=$STATUS"
  echo "$number"
}

link_story_to_epic() {
  local story_number="$1"
  local epic_number="$2"
  echo "Linking story #$story_number to epic #$epic_number..."
  gh issue edit "$story_number" --repo "$REPO" --add-label "epic:$epic_number" >/dev/null 2>&1 || true
  echo "  Linked story #$story_number to epic #$epic_number"
}

# Epics
EPIC_NUMBERS["infrastructure"]=$(create_issue "Epic 1: Infrastructure & Python Agent Bootstrap" "Scope: Prisma AI models + migrations; python-agents FastAPI scaffold; docker-compose integration; Next.js proxy route; Python internal auth middleware.\nAcceptance: migrations run clean; python service boots in Docker; proxy authenticates with JWT+internal secret; services communicate end-to-end." "enhancement" "epic")
EPIC_NUMBERS["onboarding"]=$(create_issue "Epic 2: Onboarding Agent MVP" "Scope: onboarding agent flow with OpenAI; context markdown generation; proxy endpoints; onboarding UI; validation.\nAcceptance: conversational flow completes; context saved; UI sends/receives; redirect on completion; errors handled." "enhancement" "epic")
EPIC_NUMBERS["planning"]=$(create_issue "Epic 3: Planning Agent & Task Generation" "Scope: planning agent with Claude; dependency scheduling; bulk task endpoint; surface tasks to UI; performance and parsing validation.\nAcceptance: plans respect context; dependencies resolved; /api/tasks/bulk creates tasks with deps; tasks appear in boards; runs <10s for 20+ tasks." "enhancement" "epic")
EPIC_NUMBERS["hardening"]=$(create_issue "Epic 4: Production Hardening & Observability" "Scope: WebSocket streaming; rate limiting + token counting; structured logging + error handling; end-to-end/load/security tests; deployment checklist.\nAcceptance: streaming stable; limits enforced; errors logged with context; tests cover critical flows; launch checklist completed." "enhancement" "epic")

# Stories for Epic 1
STORY_NUMBERS["prisma_models"]=$(create_issue "1.1 Story: Prisma AI models and migration" "Add Conversation, UserContext, task AI fields, dependencies; run migrate/generate; preserve data." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["prisma_models"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["python_scaffold"]=$(create_issue "1.2 Story: Scaffold python-agents FastAPI service" "Create python-agents skeleton with env config, logging, health check, requirements, Dockerfile." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["python_scaffold"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["python_compose"]=$(create_issue "1.3 Story: Add python-agent to docker-compose" "Wire python-agent service, env vars, volumes; verify compose up with db/app; hot reload works." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["python_compose"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["proxy_setup"]=$(create_issue "1.4 Story: Next.js proxy to python-agent with JWT" "Implement /api/agent/[...path] proxy, token verification, header forwarding, error passthrough." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["proxy_setup"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["python_auth"]=$(create_issue "1.5 Story: Python internal auth middleware" "Add internal secret check + user context headers validation in python-agent middleware." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["python_auth"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["ci_cd_pipeline"]=$(create_issue "1.6 Story: GitHub Actions CI/CD pipeline" "Set up automated testing, linting, and Docker image build on push; deploy staging on PR; production on release tag." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["ci_cd_pipeline"]}" "${EPIC_NUMBERS["infrastructure"]}"

STORY_NUMBERS["dev_documentation"]=$(create_issue "1.7 Story: Developer onboarding documentation" "Create comprehensive dev guide covering local setup, Docker workflows, Prisma patterns, Python agent architecture, API endpoints." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["dev_documentation"]}" "${EPIC_NUMBERS["infrastructure"]}"

# Stories for Epic 2
STORY_NUMBERS["onboarding_flow"]=$(create_issue "2.1 Story: Onboarding agent flow and persistence" "Implement onboarding agent class with stepwise flow, OpenAI calls, conversation storage." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["onboarding_flow"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["context_generator"]=$(create_issue "2.2 Story: Context markdown generator" "Generate markdown context files + UserContext persistence; ensure readable by agents." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["context_generator"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["onboarding_endpoints"]=$(create_issue "2.3 Story: Onboarding proxy endpoints" "Expose onboarding start/message endpoints via proxy; forward user headers; handle auth errors." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["onboarding_endpoints"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["onboarding_ui"]=$(create_issue "2.4 Story: Onboarding chat UI" "Build onboarding chat UI in app/(app)/onboarding with loading states and completion redirect." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["onboarding_ui"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["onboarding_validation"]=$(create_issue "2.5 Story: Onboarding validation & errors" "Test onboarding scenarios, handle edge cases, ensure acceptance criteria met." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["onboarding_validation"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["context_caching"]=$(create_issue "2.6 Story: User context caching and invalidation" "Cache parsed user context, implement smart invalidation on profile updates, reduce agent processing time." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["context_caching"]}" "${EPIC_NUMBERS["onboarding"]}"

STORY_NUMBERS["collaboration_agent"]=$(create_issue "2.7 Story: Team collaboration agent" "Enable team task assignment, approval workflows, comment-based agent interactions, mention-to-ping agents." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["collaboration_agent"]}" "${EPIC_NUMBERS["onboarding"]}"

# Stories for Epic 3
STORY_NUMBERS["planning_agent"]=$(create_issue "3.1 Story: Planning agent with Claude" "Planning agent reads user context, builds prompt, returns structured plan JSON." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["planning_agent"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["dependency_scheduling"]=$(create_issue "3.2 Story: Dependency scheduling utility" "Topological sort + due-date calculation respecting upload cadence and dependencies." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["dependency_scheduling"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["bulk_tasks"]=$(create_issue "3.3 Story: /api/tasks/bulk with deps" "Batch insert tasks, enforce <=50, link dependencies, transaction safety." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["bulk_tasks"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["surface_tasks"]=$(create_issue "3.4 Story: Surface AI tasks to UI" "Persist AI reasoning/plan metadata; show generated tasks in Kanban and Calendar." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["surface_tasks"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["plan_performance"]=$(create_issue "3.5 Story: Plan performance & parsing tests" "Validate 20+ task plans parse reliably and complete in <10s." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["plan_performance"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["agent_fallbacks"]=$(create_issue "3.6 Story: Agent fallback and retry logic" "Implement exponential backoff, fallback models, graceful degradation when services unavailable." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["agent_fallbacks"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["multi_step_planning"]=$(create_issue "3.7 Story: Multi-step collaborative planning" "Enable users to refine plans with agents, version planning history, compare plan variations." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["multi_step_planning"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["template_management"]=$(create_issue "3.8 Story: Plan templates and library" "Save successful plans as reusable templates, categorized by content type and channel size." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["template_management"]}" "${EPIC_NUMBERS["planning"]}"

STORY_NUMBERS["content_calendar_ai"]=$(create_issue "3.9 Story: AI-powered content calendar insights" "Agent analyzes calendar patterns, suggests optimal posting times, identifies content gaps." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["content_calendar_ai"]}" "${EPIC_NUMBERS["planning"]}"

# Stories for Epic 4
STORY_NUMBERS["websocket_streaming"]=$(create_issue "4.1 Story: WebSocket streaming path" "Implement Python WebSocket handler, Next.js server hookup, UI streaming rendering." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["websocket_streaming"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["rate_limiting"]=$(create_issue "4.2 Story: Rate limiting and token counting" "Enforce daily message/token limits with adjustable settings and admin overrides." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["rate_limiting"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["structured_logging"]=$(create_issue "4.3 Story: Structured logging and error handling" "Global error handler, contextual logs, recovery for transient failures." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["structured_logging"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["comprehensive_tests"]=$(create_issue "4.4 Story: E2E, load, and security tests" "End-to-end journeys, load (100 users, 50-task plans), JWT/internal secret, SQL/XSS checks." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["comprehensive_tests"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["deployment_checklist"]=$(create_issue "4.5 Story: Deployment checklist completion" "Finalize envs, SSL, monitoring/alerts, backups; verify prod endpoints and launch readiness." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["deployment_checklist"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["usage_analytics"]=$(create_issue "4.6 Story: Agent usage analytics dashboard" "Track conversations, plan generations, task creations, user engagement, cost insights (tokens, API calls)." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["usage_analytics"]}" "${EPIC_NUMBERS["hardening"]}"

STORY_NUMBERS["error_monitoring"]=$(create_issue "4.7 Story: Error tracking and alerting" "Integrate Sentry/DataDog for error monitoring, real-time alerts for critical failures, error aggregation dashboard." "enhancement" "story")
link_story_to_epic "${STORY_NUMBERS["error_monitoring"]}" "${EPIC_NUMBERS["hardening"]}"

echo ""
echo "=========================================="
echo "Story creation complete!"
echo "=========================================="
echo "Epic Numbers:"
echo "  Infrastructure: #${EPIC_NUMBERS["infrastructure"]}"
echo "  Onboarding: #${EPIC_NUMBERS["onboarding"]}"
echo "  Planning: #${EPIC_NUMBERS["planning"]}"
echo "  Hardening: #${EPIC_NUMBERS["hardening"]}"
echo "=========================================="
