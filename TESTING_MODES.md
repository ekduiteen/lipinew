# Testing Modes — Teach Mode vs Regular LLM Mode

## Quick Toggle

You can now switch between two modes for testing:

### 1. **Teach Mode** (DEFAULT)
Full behavior policy engine active. LIPI uses all the sophisticated decision logic:
- Language steering toward target language
- Elicitation goals (word, phrase, sentence, variant, etc.)
- Unclear expression handling
- User resistance detection
- Full teach-mode system prompts

**Status:** This is production mode.

### 2. **Regular LLM Mode** (for testing)
Completely simplified chatbot behavior. LIPI acts like a standard conversational AI:
- NO steering toward target language
- NO language elicitation
- NO hidden learning extraction agenda
- Simple, friendly system prompts
- Just natural conversation on any topic

**Status:** Use for testing basic LLM responses without LIPI-specific behaviors.

---

## How to Enable Regular LLM Mode

### Option 1: Environment Variable (Recommended)

Set this before running the backend:

```bash
export LIPI_DISABLE_TEACH_BEHAVIORS=true
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

Or in `.env.local`:

```bash
# .env.local
LIPI_DISABLE_TEACH_BEHAVIORS=true
```

### Option 2: One-liner

```bash
LIPI_DISABLE_TEACH_BEHAVIORS=true docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

### Option 3: Docker Compose Override

Create `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  backend:
    environment:
      LIPI_DISABLE_TEACH_BEHAVIORS: "true"
```

Then restart:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

---

## What Changes When Teach Mode is Disabled

### ✅ Teach Mode ON (Default)

**System Prompt:**
- Full LIPI teacher model with multilingual support
- Register-specific communication rules
- Phase-based curriculum guidance
- Gamification awareness

**Turn Guidance:**
- Language-specific mode (code-switch handling)
- Teacher's teach language priority
- Elicitation strategies for target language
- One-question-per-turn limit
- Correction handling

**Example Response:**
```
User: "I'm tired today" (English)

LIPI: "Ah, one of those days... how would you say that in Newari?"
      ↑ STEERS toward target language learning
```

### ✅ Teach Mode OFF (Regular LLM Mode)

**System Prompt:**
```
You are a warm, helpful, and friendly conversational AI.
Engage naturally with the user on any topic they bring up.
Be concise, genuine, and interested in what they say.
Ask follow-up questions when it helps the conversation flow.
Don't have hidden agendas or try to extract information—
just be a good conversational partner.
```

**Turn Guidance:**
```
You are a helpful, friendly conversational AI assistant.
Have natural conversations on any topic the user brings up.
Be concise, warm, and engage naturally with what they say.
Ask questions when appropriate, but don't force it.
No structured learning goals or language extraction—
just be a good conversational partner.
```

**Example Response:**
```
User: "I'm tired today"

LIPI: "That sounds rough. Anything specific making it tough?"
      ↑ NORMAL conversation, no language steering
```

---

## Behavior Policy Comparison

| Aspect | Teach Mode | Regular Mode |
|--------|-----------|--------------|
| **Steering to target language** | ✅ Active | ❌ Disabled |
| **Language elicitation** | ✅ Dynamic | ❌ None |
| **Elicitation goals** | ✅ word/phrase/sentence/variant/meaning | ❌ none |
| **Hidden agenda** | ✅ Data extraction | ❌ None |
| **Question limits** | ✅ Max 1 per turn | ❌ Natural flow |
| **System prompt complexity** | ✅ 1000+ tokens | ❌ 150 tokens |
| **Behavior flags** | ✅ 40+ behavioral fields | ❌ Neutral defaults |

---

## Common Test Scenarios

### Test Scenario 1: Regular Chatting
**Goal:** Verify LIPI can chat naturally on any topic

```bash
LIPI_DISABLE_TEACH_BEHAVIORS=true docker compose restart backend
```

Now test conversations about:
- Movies, books, hobbies
- Weather, food, travel
- Current events, opinions
- Personal stories

LIPI should respond naturally without asking about languages.

### Test Scenario 2: Teach Mode Steering
**Goal:** Verify Teach Mode correctly extracts language data

```bash
# Leave as default (Teach Mode ON)
docker compose restart backend
```

Test conversations:
- English → LIPI steers to target language
- Mixed language → LIPI confirms and expands
- Target language teaching → LIPI confirms meaning

### Test Scenario 3: LLM Quality
**Goal:** Compare raw LLM output quality

```bash
# Test 1: Teach Mode OFF (regular)
LIPI_DISABLE_TEACH_BEHAVIORS=true docker compose restart backend
# Note LLM response quality

# Test 2: Teach Mode ON (with policies)
unset LIPI_DISABLE_TEACH_BEHAVIORS
docker compose restart backend
# Compare LLM response quality with behavior policies
```

---

## Backend Logs

When you disable teach mode, the backend logs will show on the first turn:

```
[INFO] ⚠️  TEACH MODE DISABLED — Running in regular LLM mode (testing)
```

This confirms the mode is active.

---

## Implementation Details

### Where the Changes Happen

**File: `backend/routes/sessions.py`**

1. **Early system prompt selection** (line ~413):
   ```python
   disable_teach_behaviors = os.getenv("LIPI_DISABLE_TEACH_BEHAVIORS", "").lower() == "true"
   teach_mode_enabled = not disable_teach_behaviors

   if teach_mode_enabled:
       system_prompt = build_system_prompt(profile) + cross_session_prompt_context
   else:
       system_prompt = "You are a warm, helpful, friendly conversational AI..."
   ```

2. **Per-turn guidance replacement** (line ~720):
   ```python
   if not teach_mode_enabled:
       turn_guidance = "You are a helpful, friendly conversational AI assistant..."
   ```

3. **Behavior policy neutral mode** (line ~663):
   ```python
   behavior_policy = behavior_policy_svc.choose_behavior_policy(
       ...,
       teach_mode_enabled=teach_mode_enabled,  # ← controls policy decision
   )
   ```

**File: `backend/services/behavior_policy.py`**

```python
def choose_behavior_policy(..., teach_mode_enabled: bool = True):
    # If disabled, return neutral policy (no steering, no elicitation)
    if not teach_mode_enabled:
        return _create_neutral_policy(...)
    # Otherwise, full behavior policy logic
```

---

## Verify It's Working

### Check Backend Logs

```bash
docker compose logs -f backend | grep -i "teach mode\|disable"
```

You should see:

```
⚠️  TEACH MODE DISABLED — Running in regular LLM mode (testing)
```

### Test in Frontend

**With Teach Mode OFF:**
1. Start a conversation in English
2. Talk about any topic (movies, weather, food, etc.)
3. LIPI should respond conversationally WITHOUT asking about target language
4. Example: "I like pizza" → "Nice! What's your favorite type?" (not "How do you say pizza in Newari?")

**With Teach Mode ON (default):**
1. Start a conversation in English
2. Talk about a concept
3. LIPI steers toward target language
4. Example: "I like pizza" → "That's great! How would you say pizza in Newari?"

---

## Reset to Default (Teach Mode)

```bash
unset LIPI_DISABLE_TEACH_BEHAVIORS
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

Or remove from `.env` / `docker-compose.override.yml`.

---

## Status

✅ Full LLM mode toggle implemented  
✅ System prompt replaced in regular mode  
✅ Per-turn guidance simplified in regular mode  
✅ Behavior policy neutralized in regular mode  
✅ No breaking changes (backward compatible)  
✅ All tests passing  
✅ Backend healthy with both modes

**Ready for unrestricted testing!**
