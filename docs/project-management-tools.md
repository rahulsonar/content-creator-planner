# Project Management Tools for Task Manager Agent

## Overview
The Task Manager Agent now includes project management capabilities alongside its existing task management features. This allows users to create, view, and list projects through natural language interactions.

## New Tool: `manage_projects`

### Actions

#### 1. Create Projects (`action: "create"`)
Create one or more projects with rich metadata.

**Parameters:**
- `projects` (array): List of project objects to create
  - `name` (string, required): Project name
  - `description` (string): Detailed project description
  - `status` (enum): ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED (default: ACTIVE)
  - `color` (string): Hex color code for UI (e.g., "#FF5733")
  - `icon` (string): Icon name or emoji (e.g., "📹", "🎬")
  - `tags` (array of strings): Project tags for categorization
  - `startDate` (string): ISO format date (YYYY-MM-DD)
  - `endDate` (string): ISO format date
  - `dueDate` (string): ISO format date

**Example Usage:**
```
User: "Create a new project called 'YouTube Channel Launch' for my tech review videos with icon 📹"
```

#### 2. View Project (`action: "view"`)
Get detailed information about a specific project including task statistics.

**Parameters:**
- `project_id` (string, required): ID of the project to view

**Returns:**
- Project details (name, description, status, dates)
- Task progress (completed/total tasks)
- Color, icon, and tags
- Creation and update timestamps

**Example Usage:**
```
User: "Show me details about the YouTube Channel Launch project"
```

#### 3. List Projects (`action: "list"`)
List all projects with optional status filtering.

**Parameters:**
- `status_filter` (enum, optional): Filter by ACTIVE, ON_HOLD, COMPLETED, ARCHIVED, CANCELLED

**Returns:**
- List of projects with summary information
- Task count and completion percentage for each project
- Status and metadata

**Example Usage:**
```
User: "List all my active projects"
User: "Show me all my projects"
```

## Database Schema

Projects are stored in the `Project` table with the following structure:

```sql
model Project {
  id          String   @id @default(cuid())
  name        String
  description String?  @db.Text
  status      ProjectStatus @default(ACTIVE)
  
  // Project timeline
  startDate   DateTime?
  endDate     DateTime?
  dueDate     DateTime?
  
  // User association
  userId      String
  user        User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  // Relations
  tasks       Task[]
  
  // Metadata
  color       String?  // Hex color code for UI
  icon        String?  // Icon name or emoji
  tags        String[]
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

enum ProjectStatus {
  ACTIVE
  ON_HOLD
  COMPLETED
  ARCHIVED
  CANCELLED
}
```

## Implementation Details

### Files Modified

1. **`agents/task_manager.py`**
   - Added `manage_projects` tool definition
   - Added project-related metadata counters (`projects_created`, `projects_viewed`, `projects_listed`)
   - Implemented handlers: `_handle_manage_projects`, `_create_projects`, `_view_project`, `_list_projects`
   - Updated system prompt to include project management capabilities

2. **`utils/project_manager.py`** (NEW)
   - `insert_projects_to_db()`: Insert projects into database
   - `get_project_by_id()`: Retrieve single project with task statistics
   - `list_projects()`: List projects with optional filtering

### Features

- **User Scoping**: All projects are associated with the authenticated user
- **Task Integration**: Projects can contain tasks (via `projectId` foreign key on tasks)
- **Progress Tracking**: Automatically calculates task completion statistics
- **Flexible Filtering**: List projects by status
- **Rich Metadata**: Support for colors, icons, tags, and dates

### Agent Metadata Tracking

New metadata counters added:
- `projects_created`: Number of projects created
- `projects_viewed`: Number of project detail views
- `projects_listed`: Number of project list operations

## Testing

Run the test script to verify functionality:

```bash
cd python-agents
python test_project_management.py
```

The test script covers:
1. Creating a single project
2. Listing all projects
3. Filtering projects by status
4. Creating multiple projects at once
5. Viewing project details

## Integration with Existing Features

- **Tasks**: Tasks can now be associated with projects via `projectId`
- **Task Manager**: Existing task management tools work alongside project tools
- **User Context**: Projects use the same user authentication flow as tasks
- **Logging**: All project operations are logged in `AgentCallLog`

## Example Conversation Flow

```
User: Create a project called "YouTube Channel" for my tech videos

Agent: ✓ Created 1 project(s) successfully (IDs: abc12345)

User: List all my projects

Agent: Found 1 project(s):
  📹 [ACTIVE] YouTube Channel (ID: abc12345...) [No tasks]

User: Show me details about the YouTube Channel project

Agent: Project Details:
  • ID: abc12345678...
  • Name: YouTube Channel
  • Status: ACTIVE
  • Description: Tech videos
  • Tasks: 0/0 completed
  • Color: Not set
  • Icon: Not set
  • Tags: None
  • Created: 2026-01-25T...
```

## Future Enhancements

Potential additions:
- Update project details (similar to task updates)
- Archive/delete projects
- Bulk operations
- Project templates
- Advanced analytics
- Timeline visualization support
