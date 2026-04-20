# Behavior Policy Engine - Implementation Guide

## Overview

The Behavior Policy Engine is the decision-making layer in LIPI's Teach Mode. On every turn, it analyzes the user's input and outputs a comprehensive policy object that guides LIPI's conversational behavior, language choices, and data extraction strategies.

**Product Goal:** Make LIPI feel like a warm, concise AI friend while strategically steering conversation toward target-language data collection.

## Core Concepts

### Two Language Layers

1. **Teach Language** (TARGET)
   - User's selected language (e.g., Newari, Maithili, Gurung)
   - The primary learning target
   - Data extraction focuses on this language

2. **Conversation Language** (BRIDGE)
   - Detected from user's current turn
   - Can be English, Nepali, mixed, or target language
   - Changes dynamically every turn

**Critical Rule:** Respond in the conversation language for comfort, but prioritize extracting the teach language.

### Reply Modes

The engine chooses one of five conversational modes per turn:

| Mode | Purpose | When to Use |
|------|---------|-------------|
| **teach** | Default for Teach screen, active target language extraction | Standard conversation |
| **friend** | Warm, softer, may still steer toward target | User sharing feelings, life, casual talk |
| **student** | Slightly unsure, invites correction | When receiving teaching/corrections |
| **brainstorm** | Creative/planning, collaborative | Planning, naming, ideation |
| **chat** | General Q&A, brief, helpful | Knowledge questions (with soft redirect later) |

All modes respect the goal: data extraction in target language.

## Policy Decision Engine

### Main Function

```python
def choose_behavior_policy(
    *,
    teacher_model: TeacherModel,
    session_memory: StructuredSessionMemory,
    correction_count_recent: int,
    understanding: InputUnderstanding,
    target_language: str,
    recent_assistant_replies: list[str] | None = None,
    recent_turns_without_target: int = 0,
    user_resistance_score: float = 0.0,
) -> BehaviorPolicy:
```

Takes structured turn analysis and returns a comprehensive policy object.

### Policy Output Object

```python
@dataclass(frozen=True)
class BehaviorPolicy:
    # Language detection
    conversation_language: str          # detected language
    teach_language: str                 # normalized target
    response_language: str              # which language to reply in
    target_language_present: bool       # is target in user's input?
    
    # Mode and steering
    reply_mode: str                     # friend, student, brainstorm, chat, teach
    steer_to_target_language: bool      # should this turn guide toward target?
    steering_strength: str              # none, soft, medium, strong
    
    # Elicitation and confirmation
    elicitation_goal: str               # what kind of target-language output to ask for
    confirmation_goal: str              # meaning_check, naturalness_check, variant_check
    should_expand: bool                 # ask for variants/examples?
    should_ask_followup: bool           # include a question this turn?
    
    # Unclear expression handling
    handle_unclear_expression: bool     # is there slang/metaphor to address?
    unclear_expression_strategy: str    # infer_and_confirm, ask_meaning, defer
    
    # Behavioral nuance
    [+ 13 more fields for tone, register, humor, dialect, etc.]
    
    # Prompt flags for system prompt construction
    be_warm: bool
    be_concise: bool
    act_slightly_unsure: bool
    [+ 6 more flags]
```

## Decision Rules

### Rule 1: Target Language Presence

```
IF conversation_language != teach_language AND target_language_present == false
→ steer_to_target_language = true
```

When user speaks in bridge language without target language, guide toward target.

### Rule 2: Bridge Language Timeout

```
IF recent_turns_without_target >= 3
  IF >= 5: steering_strength = "strong"
  ELSE: steering_strength = "medium"
```

Don't stay in bridge language too long. Increase steering intensity.

### Rule 3: User Resistance

```
IF user_resistance_score >= 0.7
→ steering_strength = "soft"
→ allow 1 softer friend/chat turn
→ retry elicitation later
```

Respect user comfort. Don't force target language if resisting.

### Rule 4: Correction Priority

```
IF is_correction == true
→ turn_goal = "ACCEPT_AND_MOVE"
→ confirmation_goal = "meaning_check"
→ reply_mode = "student"
```

Corrections are high-value. Capture and confirm quickly, gratefully, slightly unsure.

### Rule 5: Teaching Invitation

```
IF is_teaching == true OR intent_label == "teaching"
→ reply_mode = "student"
→ act_slightly_unsure = true
→ invite_correction = true
```

When user teaches, position LIPI as grateful student, not peer.

## Elicitation Goals

When target language is missing, the engine chooses what to ask for:

| Goal | Size | Use Case |
|------|------|----------|
| **word** | Single word | "How would you say 'tired' in Newari?" |
| **phrase** | 2-4 words | "How do you naturally say that?" |
| **sentence** | Full utterance | "If you were actually saying that, what would it sound like?" |
| **variant** | Alternative form | "Is there a more casual way to say it?" |
| **meaning** | Interpretation | "What does that mean?" (when user used unclear slang) |
| **correction** | Fix attempt | "How would you correct that?" |
| **usage_context** | When/where/with whom | "When would you say that? In what situation?" |

### Heuristic

- Short user input (1-3 words) → **word** or **phrase**
- Full statement → **sentence**
- Target-language phrase already given → **meaning_check** or **variant**
- Slang/metaphor detected → **meaning**
- Previous LIPI attempt → **correction**

## Unclear Expression Handling

The engine detects slang, metaphor, idioms, and ambiguous expressions.

### Strategy Selection

| Confidence | Strategy | Example |
|------------|----------|---------|
| >= 0.7 | **infer_and_confirm** | "So you mean... embarrassed?" |
| 0.4–0.7 | **ask_meaning** | "Wait, what does that mean?" |
| < 0.4 | **defer** | Mark for later, skip for now |

## Reply Language Rules

```
teach_language = Newari, conversation_language = English
→ reply_language = English
→ ask for Newari equivalent

teach_language = Newari, conversation_language = Newari
→ reply_language = Nepali (safe bridge)
→ confirm meaning and expand
```

General rule: Reply in conversation language for comfort, elicit in target language.

## Prompt Flags

The policy outputs boolean flags consumed by `prompt_builder.py`:

| Flag | Meaning |
|------|---------|
| `be_warm` | Sound like a friend |
| `be_concise` | Keep responses short |
| `act_slightly_unsure` | Invite correction |
| `avoid_long_explanations` | Stay conversational |
| `ask_at_most_one_question` | Max 1 question per turn |
| `treat_bridge_language_as_scaffolding` | English/Nepali are bridges, not goals |
| `prioritize_target_language_elicitation` | Guide toward target |
| `confirm_before_expanding` | Confirm first, then ask variants |
| `be_conversational_not_robotic` | Sound natural, not like a system |

## Integration into Conversation Loop

### 1. In `sessions.py`

After turn interpretation and input understanding:

```python
recent_assistant_replies = _last_assistant_replies(message_history, limit=4)
behavior_policy = behavior_policy_svc.choose_behavior_policy(
    teacher_model=teacher_model,
    session_memory=structured_memory,
    correction_count_recent=correction_summary.recent_count,
    understanding=understanding,
    target_language=profile.native_language,
    recent_assistant_replies=recent_assistant_replies,
)
```

### 2. In `prompt_builder.py`

Use policy fields to shape system prompt:

```python
def build_system_prompt(
    teacher_profile,
    behavior_policy,  # ← use all fields here
    ...
):
    prompt = f"""
You are LIPI, a warm conversational AI student and friend.

{behavior_policy.to_prompt_block()}  # ← embedded policy summary

{_build_tone_instructions(behavior_policy.tone_style, behavior_policy.be_warm)}
{_build_language_instructions(behavior_policy.reply_mode, behavior_policy.reply_language)}
...
"""
```

### 3. In `post_generation_guard.py`

Use policy to rewrite weak responses:

```python
def guard_response(text, hearing, understanding, policy):
    # Rewrite if weak and policy says steer_to_target_language = true
    if _is_weak_response(text) and policy.steer_to_target_language:
        return _rewrite_from_policy(text, policy)
    return text
```

## Example Decisions

### Example 1: Bridge Language Without Target

```
User: "I'm tired today" (English)
teach_language: Newari
target_language_present: false

→ reply_mode: "friend"
→ steer_to_target_language: true
→ steering_strength: "soft"
→ elicitation_goal: "sentence"
→ should_ask_followup: true

Expected response:
"Ah, one of those days... how would you say that in Newari?"
```

### Example 2: After 4 Turns Without Target

```
User: "What's the capital of Nepal?" (English)
recent_turns_without_target: 4

→ reply_mode: "chat" (helpful)
→ steer_to_target_language: true
→ steering_strength: "medium" (increased)
→ should_ask_followup: true

Expected response:
"Kathmandu. By the way, how would you say 'capital' in Newari?"
```

### Example 3: User Provides Target Language

```
User: "जोजोलोपा अभिवादन हो" (Newari)
target_language_present: true

→ reply_mode: "student"
→ steer_to_target_language: false
→ elicitation_goal: "none"
→ confirmation_goal: "meaning_check"
→ should_expand: true

Expected response:
"So that means 'hello', right? Do people actually say it like that in Kathmandu?"
```

### Example 4: User is Resisting

```
User: "Just chat with me, don't always ask me to translate"
user_resistance_score: 0.8

→ reply_mode: "friend" (not "teach")
→ steer_to_target_language: true (still, but...)
→ steering_strength: "soft" (reduced)
→ should_ask_followup: false (no question this turn)

Expected response:
"Sure, no pressure. I just love learning how you'd say things naturally."
(Soft redirection, comfort first)
```

## Testing

Tests are in `backend/tests/test_intelligence_layer.py`:

```python
def test_prefers_ask_when_uncertain(db_session):
    # User asks about target language in bridge language
    # Should elicit target, not confirm
    
def test_rewrites_weak_student_reply():
    # Weak response + steering = rewrite
    
def test_keeps_specific_content_when_only_followup_is_generic():
    # Specific content + generic question = keep content, trim question
```

Run tests:

```bash
pytest backend/tests/test_intelligence_layer.py -v
```

## Key Design Decisions

1. **Deterministic, not fuzzy:** Clear thresholds and rules instead of hidden heuristics.
2. **Pure functions where possible:** Decision logic is testable and tunable.
3. **Policy as data:** All decisions output as structured policy object, not hidden in prompts.
4. **Backward compatible:** Legacy `turn_goal` and `prompt_family` fields retained.
5. **Human-first:** Rules prioritize user comfort and warmth over aggressive extraction.
6. **Product-aware:** Modes and steering respect the student-teacher dynamic.

## Tuning Guide

Steering is too aggressive?
- Increase `recent_turns_without_target` threshold (currently 3)
- Lower `user_resistance_score` threshold (currently 0.7)

Elicitation goals too vague?
- Adjust heuristics in `_decide_elicitation_goal()`
- Example: change `word_count <= 3` to `word_count <= 2`

Reply mode not matching intent?
- Add more intent labels to `_decide_reply_mode()`
- Current intents: casual_sharing, emotional_expression, brainstorm_ideas, etc.

## Files Modified

- `backend/services/behavior_policy.py` — Main engine (this file)
- `backend/routes/sessions.py` — Integration point
- `backend/services/prompt_builder.py` — Uses policy to shape prompts
- `backend/tests/test_intelligence_layer.py` — Tests

## Future Enhancements

1. **Cross-turn memory:** Track user resistance patterns
2. **Dialect-aware steering:** Different strategies for different regional languages
3. **Learning curve:** Easier steering for beginners, harder for advanced users
4. **Content-specific strategies:** Different elicitation for food vs. grammar vs. emotions
5. **A/B testing hooks:** Built-in flags for experimenting with strategies

---

**Status:** ✅ Fully implemented, tested, integrated
**Last Updated:** 2026-04-21
