# Planner Agent Flow Diagram

```mermaid
flowchart TD
    A["Chat (User Input)"] --> B["API Endpoint /api/chat/"]
    B --> C["Orchestrator Agent"]
    C --> D["Planner Agent"]
    D --> E["Task Planning & Breakdown"]
    E --> F["Context Manager / Storage"]
    F --> G["Response Generation"]
    G --> H["API Response"]
    H --> I["Chat (User Sees Output)"]

    D -- "May call" --> J["Other Agents (e.g., Context Manager, Task Inserter)"]
    F -- "Logs/Updates" --> K["Database"]
```

**Description:**
- The flow starts with a user message in Chat.
- The message is sent to the API endpoint, which invokes the Orchestrator Agent.
- The Orchestrator delegates planning to the Planner Agent.
- The Planner Agent breaks down tasks, interacts with context/storage, and may call other agents.
- Results are logged/updated in the database, and a response is generated and returned to the user.
