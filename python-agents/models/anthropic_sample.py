import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)

message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=20000,
    temperature=1,
    system="You are an expert user context manager. Your role is to manage user information in structured markdown files. You automatically have access to and operate inside a folder named agent_context/{userId}/ where you can create, read, update, and list context files. User will not interactive, so you cannot ask for clarifications or more information. To provide better service, try to list all files to begin while provide user information. Multiple iterations may be needed to gather all relevant context.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "attach label to task id 3"
                }
            ]
        }
    ],
    tools=[
        {
            "type": "custom",
            "name": "manage_tasks",
            "description": "Manage user's tasks with unified actions: create new tasks (with optional notes), search existing tasks (supports keywords, status, priority, project, and label/tag filters), update task details, add notes to existing tasks, or get specific task information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create",
                            "view",
                            "list"
                        ],
                        "description": "Project operation to perform"
                    },
                    "projects": {
                        "type": "array",
                        "description": "Array of new projects to create (for 'create' action)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Project name (concise, descriptive)"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Detailed project description"
                                },
                                "status": {
                                    "type": "string",
                                    "enum": [
                                        "ACTIVE",
                                        "ON_HOLD",
                                        "COMPLETED",
                                        "ARCHIVED",
                                        "CANCELLED"
                                    ],
                                    "description": "Project status (defaults to ACTIVE)"
                                },
                                "color": {
                                    "type": "string",
                                    "description": "Hex color code for UI (e.g., #FF5733)"
                                },
                                "icon": {
                                    "type": "string",
                                    "description": "Icon name or emoji for UI (e.g., 📹, 🎬)"
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "Project tags for categorization"
                                },
                                "startDate": {
                                    "type": "string",
                                    "description": "Project start date (ISO format: YYYY-MM-DD)"
                                },
                                "endDate": {
                                    "type": "string",
                                    "description": "Project end date (ISO format: YYYY-MM-DD)"
                                },
                                "dueDate": {
                                    "type": "string",
                                    "description": "Project due date (ISO format: YYYY-MM-DD)"
                                },
                                "isDefault": {
                                    "type": "boolean",
                                    "description": "Whether this project should be the default"
                                }
                            },
                            "required": [
                                "name"
                            ]
                        }
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID to view (for 'view' action)"
                    },
                    "status_filter": {
                        "type": "string",
                        "enum": [
                            "ACTIVE",
                            "ON_HOLD",
                            "COMPLETED",
                            "ARCHIVED",
                            "CANCELLED",
                            ""
                        ],
                        "description": "Optional: Filter projects by status (for 'list' action). Leave empty for no filter."
                    }
                },
                "required": [
                    "action"
                ]
            }
        }
    ]
)
print(message.content)