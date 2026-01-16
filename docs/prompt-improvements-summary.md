# Planning Agent Prompt Improvements

## Problem Analysis

### Conversation ID: f705a52a-3fc4-453b-afc9-8039a9fe6aeb

**User's Initial Message:**
```
"I am planning to start a youtube channel on history of deccan. I am not sure where to start."
```

**Agent's Response Issues:**
1. ❌ **Information Dump**: Immediately provided a 7-task detailed plan without asking any questions
2. ❌ **No Context Gathering**: Didn't ask about:
   - User's experience level with video creation
   - Available time/budget
   - Specific interests within Deccan history
   - Target audience
3. ❌ **No Follow-up Questions**: Didn't ask if user needed clarification or had concerns
4. ❌ **Prescriptive Rather Than Collaborative**: Told user what to do instead of exploring options together

## Solution: Enhanced Prompt Engineering

### Key Changes to `PLANNING_SYSTEM_PROMPT`

#### 1. **Conversation Flow Structure** (NEW)
Added explicit 4-step conversation flow:
- **Step 1**: ALWAYS ask clarifying questions first (2-4 targeted questions)
- **Step 2**: Provide strategic guidance before detailed plans
- **Step 3**: Generate detailed plan ONLY after sufficient context
- **Step 4**: ALWAYS end with follow-up questions

#### 2. **Specific Question Guidelines**
```
Ask 2-4 targeted questions to understand:
* What's their experience level with this type of content?
* What resources do they have (time, budget, equipment)?
* What's their timeline/deadline?
* Are there specific aspects they're most uncertain about?
```

#### 3. **Follow-up Examples**
```
- "Does this approach align with what you had in mind?"
- "Would you like me to break down any of these steps further?"
- "Any concerns about the timeline?"
```

#### 4. **Conversational Examples** (NEW)
Added `PLANNING_CONVERSATION_EXAMPLES` showing:
- ✅ GOOD: Asks questions, gathers context, offers choices
- ❌ BAD: Information dump, no questions

### Files Modified

1. **`python-agents/config/prompts.py`**
   - Enhanced `PLANNING_SYSTEM_PROMPT` with conversation flow
   - Added `PLANNING_CONVERSATION_EXAMPLES`

2. **`python-agents/agents/planner.py`**
   - Updated imports to include `PLANNING_CONVERSATION_EXAMPLES`
   - Added examples to agent initialization

## Expected Behavior After Changes

### Example: New Response Flow

**User:** "I am planning to start a youtube channel on history of deccan. I am not sure where to start."

**Improved Agent Response:**
```
That's a fascinating topic! The Deccan region has such rich history spanning multiple dynasties and eras. 

To help you create a solid foundation, I have a few questions:

1. **Experience Level**: Have you created video content before, or is this your first YouTube channel?

2. **Specific Focus**: The Deccan has a vast history - are you more interested in specific periods (Bahmani Sultanate, Maratha Empire), cultural aspects (architecture, art), or a broad chronological approach?

3. **Time Commitment**: How many hours per week can you dedicate to research, scripting, filming, and editing?

Understanding these will help me suggest a realistic starting point that matches your situation.
```

**User provides answers...**

**Agent continues:**
```
Great context! Based on what you've shared, here's what I'd recommend focusing on first...

[Provides strategic guidance]

Would you like me to create a detailed task breakdown for your first month, or would you prefer to discuss any specific concerns (like equipment, scripting format, etc.) first?
```

## Testing Recommendations

### 1. Restart Python Service
```bash
docker compose restart python-agents
```

### 2. Test Cases

#### Test Case 1: Vague Initial Request
**Input:** "I want to start a podcast"
**Expected:** Agent asks 2-4 clarifying questions about genre, experience, equipment

#### Test Case 2: Detailed Request
**Input:** "I want to create a 10-episode podcast series about medieval history for history students. I have basic audio equipment and some experience."
**Expected:** Agent acknowledges context, asks 1-2 follow-ups about timeline/specific topics, then offers to create plan

#### Test Case 3: After Plan Generation
**Expected:** Every agent response ends with a follow-up question like:
- "Would you like me to elaborate on any of these tasks?"
- "Any concerns about the approach?"
- "Should we adjust priorities based on your timeline?"

### 3. Monitor Conversation Quality

Check new conversations for:
- [ ] Agent asks questions before providing full plans
- [ ] Responses are collaborative, not prescriptive
- [ ] Every response includes a follow-up question
- [ ] Plans are tailored to user's stated context
- [ ] Tone is conversational, not robotic

## Additional Improvements to Consider

### Future Enhancements:

1. **Dynamic Question Selection**
   - Use user context from database to skip already-known information
   - Example: If user has completed onboarding, don't re-ask basic questions

2. **Progressive Disclosure**
   - Offer plans in stages (overview → details → implementation)
   - "Would you like me to break down Task 1 in more detail?"

3. **Confirmation Checkpoints**
   - Before generating 10+ tasks, confirm: "This plan has 12 tasks spanning 3 months. Does that scope work for you?"

4. **Context Retention**
   - Reference previous conversations: "Last time we discussed your podcast about X..."

5. **Proactive Follow-ups**
   - After 2-3 exchanges: "Before I create a detailed plan, is there anything else about your situation I should know?"

## Rollback Instructions

If changes cause issues, revert to previous prompt:

```bash
cd /var/www/html/content-creator-planner
git diff python-agents/config/prompts.py
git checkout HEAD -- python-agents/config/prompts.py python-agents/agents/planner.py
docker compose restart python-agents
```

## Metrics to Track

After deploying changes, monitor:
- **Average conversation length** (should increase slightly as agent asks questions)
- **User satisfaction indicators** (fewer abandoned conversations)
- **Task creation success rate** (plans should be more tailored)
- **Follow-up engagement** (users responding to agent's questions)

---

**Implementation Date:** January 15, 2026  
**Modified Files:** 2  
**Lines Changed:** ~100  
**Breaking Changes:** None (backward compatible)
