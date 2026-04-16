# LIPI UI/UX Design Document
## Screen Map, Brand, Tone & Interaction Design

**Version**: 1.0  
**Status**: Design Phase  
**Last Updated**: April 14, 2026  
**Covers**: All screens, brand identity, tone system, gamification

---

## Core Design Principles

1. **Audio-first** — conversation is the product, UI gets out of the way
2. **Bilingual always** — Nepali leads, English follows
3. **Futuristic, not cultural** — high-tech aesthetic, no cultural appropriation
4. **One thing at a time** — onboarding, conversation, everything is single-focus
5. **Text is meaningful** — text only appears when LIPI learns something (corrections)
6. **Tone evolves** — LIPI adapts to each teacher's communication style over time

---

## Brand Identity

### Name
**LIPI (लिपि)** — Sanskrit/Nepali for *script* or *writing system*. The system through which language is recorded. LIPI is literally recording language.

### Tagline
```
"You speak. LIPI learns. Language lives."
```

### Brand Tone (A + B combined)
- **UI copy**: Minimal, clean, never wordy
- **LIPI's voice in conversation**: Genuinely curious, warm, humble
- **Error states**: Honest, never corporate
- **Onboarding**: Conversational, like meeting a friend

### Personality traits
```python
LIPI_PERSONALITY = {
    "curiosity":   9/10,   # Always asks follow-ups
    "humility":    9/10,   # "मलाई सिकाउनुस्" — teach me
    "warmth":      8/10,   # Feels like it cares
    "coolness":    7/10,   # UI is minimal, not loud
    "playfulness": 5/10,   # Mirrors teacher's humor level
}
```

### What LIPI is NOT
- Not a language teaching app
- Not a chatbot that answers questions
- Not a translation service
- Not a recording app

---

## Visual Design System

### Aesthetic
**Futuristic AI** — think Gemini aurora, iOS 18 AI glow, *Her* (2013 film). No ethnic patterns, no flags, no cultural symbols. Technology product first.

### Typography
- **Font**: Inter or Geist (both Devanagari + Latin)
- **Nepali script**: Same font family — Devanagari feels modern, not traditional
- **Hierarchy**: Nepali larger/bolder on top, English smaller below

### Themes (selectable in Settings)

#### 1. Dark Mode (default)
```
Background:  #0a0a0f
Orb:         Aurora — blue → purple → magenta shifting
Text:        #f0f0ff
Cards:       Frosted glass rgba(255,255,255,0.05)
Buttons:     Glowing border, no fill
```

#### 2. Bright Mode
```
Background:  #f8f8ff
Orb:         Soft blue + lavender, light glow
Text:        #0a0a1a
Cards:       White, subtle drop shadow
Buttons:     Solid fill, clean edges
```

#### 3. Cyber Punk
```
Background:  #000000
Orb:         Neon green + hot pink, crackling edges
Text:        #00ff9f
Cards:       Black + neon border glow
Grid:        Subtle perspective grid on background
Glitch:      Occasional text glitch animation
```

#### 4. Traditional
```
Background:  #1a0f00
Orb:         Warm gold → deep red, slow pulse
Text:        #ffd97d
Cards:       Warm amber frosted glass
Buttons:     Gold border
Note:        For users who prefer cultural warmth
```

### Implementation (CSS variables)
```css
[data-theme="dark"] {
  --bg:          #0a0a0f;
  --orb-a:       #6366f1;
  --orb-b:       #a855f7;
  --orb-c:       #ec4899;
  --text:        #f0f0ff;
  --card-bg:     rgba(255,255,255,0.05);
}

[data-theme="cyberpunk"] {
  --bg:          #000000;
  --orb-a:       #00ff9f;
  --orb-b:       #ff00ff;
  --orb-c:       #00ffff;
  --text:        #00ff9f;
  --card-bg:     rgba(0,255,159,0.05);
}
```

The orb reads `--orb-a/b/c` — theme change instantly recolors everything including animations. Theme picker shows **live animated orb preview** for each option (not static swatches).

**Theme selection**: Settings screen only. Not during onboarding.

---

## Complete Screen Map

```
AUTH
└── Landing → Google / Phone login

ONBOARDING (one question per screen)
├── LIPI intro animation
├── Q1: Name
├── Q2: Age
├── Q3: Primary language (searchable single-select)
├── Q4: Other languages (searchable multi-select)
├── Q5: City / village (free text)
├── Q6: Education level (chips)
└── Q7: Gender (chips) → Home

MAIN APP (6 tabs)
├── [Home]        — Dashboard + stats
├── [Teach]       — Conversation (orb)
├── [Heritage]    — Long-form cultural stories and proverbs
├── [Phrase Lab]  — Targeted sentence translation and dialect tracking
├── [Ranks]       — Leaderboards
└── [Settings]    — Theme + prefs + consent

PROFILE (accessible from Home)
└── Stats, badges, contribution history
```

---

## Screen Designs

### 1. Auth / Landing

```
┌─────────────────────────────┐
│                             │
│         L I P I             │
│         लिपि                │
│                             │
│  You speak. LIPI learns.    │
│  Language lives.            │
│                             │
│  ┌─────────────────────┐    │
│  │  Continue with      │    │
│  │  Google             │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │  Continue with      │    │
│  │  Phone Number       │    │
│  └─────────────────────┘    │
│                             │
└─────────────────────────────┘
```

Clean, dark, minimal. No illustrations, no cultural imagery.

---

### 2. Onboarding

**Design rules:**
- One question per screen
- Nepali primary (larger, top), English secondary (smaller, below)
- Thin progress bar at top (no numbers — feels like a form)
- Auto-advance where possible (language selection → tap confirms)
- Smooth slide transitions between questions
- LIPI's orb visible but small — top center

**LIPI intro screen:**
```
┌─────────────────────────────┐
│                             │
│         ╭~~~~~╮             │
│       ~~  LIPI  ~~          │  ← small orb, gently pulsing
│         ╰~~~~~╯             │
│                             │
│  नमस्ते! म LIPI हुँ।        │
│  Hi! I'm LIPI.              │
│                             │
│  म भाषा सिक्दैछु —          │
│  तपाईंजस्ता शिक्षकहरूबाट।  │
│                             │
│  I'm learning languages —   │
│  from teachers like you.    │
│                             │
│  सुरु गर्नुअघि, केही        │
│  कुरा सोध्न सक्छु?          │
│  Before we begin, can I     │
│  ask you a few things?      │
│                             │
│         [ सुरु / Begin ]    │
└─────────────────────────────┘
```

**Question screens (example — Name):**
```
┌─────────────────────────────┐
│  ▓▓▓▓▓░░░░░░░░░             │  ← thin progress bar
│                             │
│         ╭~~~~~╮             │
│       ~~  LIPI  ~~          │
│         ╰~~~~~╯             │
│                             │
│  तपाईंको नाम के हो?         │  ← Nepali, large
│  What is your name?         │  ← English, smaller
│                             │
│  ┌─────────────────────┐    │
│  │                     │    │  ← text input
│  └─────────────────────┘    │
│                             │
│         [ अर्को / Next ]    │
└─────────────────────────────┘
```

**All 7 questions (bilingual):**

| # | Nepali | English | Input |
|---|--------|---------|-------|
| 1 | तपाईंको नाम के हो? | What is your name? | Text |
| 2 | तपाईंको उमेर कति हो? | How old are you? | Number |
| 3 | म कुन भाषा सिकूँ? | Which language will you help me learn? | Searchable single-select |
| 4 | अरू कुन भाषाहरू बोल्नुहुन्छ? | What other languages do you speak? | Searchable multi-select |
| 5 | तपाई कहाँ हुर्कनुभयो? | Where did you grow up? | Free text (geocoded later) |
| 6 | शैक्षिक योग्यता? | Education level? | Chips |
| 7 | लिंग? | Gender? | Chips |

**Gender chips (bilingual):**
```
[ पुरुष / Male ]        [ महिला / Female ]
[ अन्य / Other ]        [ भन्न मन छैन / Prefer not to say ]
```

**Education chips:**
```
[ प्राथमिक / Primary ]
[ माध्यमिक / Secondary ]
[ स्नातक / Bachelor's ]
[ स्नातकोत्तर / Master's ]
[ पिएचडी / PhD ]
[ भन्न मन छैन / Prefer not to say ]
```

**Language selector:**
- Searchable, flag emoji next to each language
- Popular languages shown first: नेपाली, हिन्दी, English, मैथिली, नेवारी
- Multi-select for "other languages" — selected languages show as chips

---

### 3. Home Screen

```
┌─────────────────────────────┐
│                             │
│  सुप्रभात, Raj!             │  ← time-based greeting
│  Good morning, Raj!         │     + age register (timi/tapai)
│                             │
│  ┌─────────────────────┐    │
│  │  LIPI ले सिक्यो     │    │
│  │  LIPI has learned   │    │
│  │                     │    │
│  │  389 शब्द  •  47h   │    │
│  │  389 words • 47hrs  │    │
│  └─────────────────────┘    │
│                             │
│  ┌──────────┐ ┌──────────┐  │
│  │  🔥 12   │ │  ✏️ 62  │  │
│  │  days    │ │  fixes   │  │
│  │  streak  │ │  made    │  │
│  └──────────┘ └──────────┘  │
│                             │
│  ┌─────────────────────┐    │
│  │  🏅 2,450 pts       │    │
│  │  📊 #3 this week    │    │
│  │  ─────────────────  │    │
│  │  🥇 Sita    3,200   │    │
│  │  🥈 Hari    2,890   │    │
│  │  🥉 Raj     2,450 ← │    │
│  │     Maya   2,100    │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │  सिकाउन सुरु गर्नु  │    │  ← primary CTA
│  │  Start Teaching     │    │
│  └─────────────────────┘    │
│                             │
│  आजको सिकाइ:                │
│  Today LIPI learned:        │
│  "खिचडी" — Sita             │
│  "दसैं" — Ram               │
│  "धन्यवाद" — You ✓          │  ← teacher sees their name
│                             │
│  ─────────────────────────  │
│  [Home] [Teach] [Ranks] [⚙] │
└─────────────────────────────┘
```

**Greeting logic:**
```python
def get_greeting(user: UserProfile, hour: int) -> str:
    time_greeting = {
        range(5, 12):  ("सुप्रभात", "Good morning"),
        range(12, 17): ("शुभ दिन",  "Good afternoon"),
        range(17, 21): ("शुभ साँझ", "Good evening"),
        range(21, 24): ("शुभ रात्रि","Good night"),
        range(0, 5):   ("शुभ रात्रि","Good night"),
    }

    # Register based on age
    if user.age < 30:
        name = user.first_name           # casual: just name
    else:
        name = f"{user.first_name} जी"  # respectful: name + ji

    nepali, english = time_greeting[hour]
    return f"{nepali}, {name}!\n{english}, {name}!"
```

---

### 4. Teach Screen (Conversation)

**The core screen. Minimal. Audio-first.**

```
┌─────────────────────────────┐
│                             │
│                             │
│                             │
│         ╭~~~~~~~╮           │
│      ~~~          ~~~       │
│    ~~    [LIPI orb]  ~~     │  ← full-screen orb
│      ~~~          ~~~       │
│         ╰~~~~~~~╯           │
│                             │
│                             │
│                             │
│                             │
└─────────────────────────────┘
```

**No text. No chat bubbles. Just the orb.**

Text appears ONLY when LIPI registers a correction:

```
┌─────────────────────────────┐
│                             │
│         ╭~~~~~~~╮           │
│      ~~~  LIPI   ~~~        │  ← orb shrinks slightly
│         ╰~~~~~~~╯           │
│                             │
│  ┌───────────────────────┐  │
│  │  मैले सिकेँ ✓         │  │
│  │  I learned:           │  │  ← slides up from bottom
│  │                       │  │
│  │  "नमस्ते"             │  │
│  │  nə-mə-STEY           │  │
│  └───────────────────────┘  │  ← fades after 3 seconds
│                             │
└─────────────────────────────┘
```

**Orb animation states:**

| State | Behavior |
|---|---|
| LIPI speaking | Pulses with audio amplitude |
| Listening (VAD active) | Ripples outward, warm glow, color shift |
| Processing / thinking | Slow morph, gentle rotation |
| Idle / waiting | Soft slow breathing |

**Auto-detect voice (VAD) rules:**
- Uses faster-whisper's built-in VAD
- Silence threshold: 6 seconds → LIPI gently re-asks or simplifies question
- Background noise: confidence threshold before processing
- Teacher interrupts LIPI: LIPI stops immediately, starts listening

**Session end:**
After natural conversation pause or teacher navigates away:
```
┌─────────────────────────────┐
│  आजको सत्र / Today's session│
│                             │
│  ⏱  18 minutes              │
│  📚 23 words LIPI learned   │
│  ✏️  4 corrections made      │
│  🏅 +340 points earned      │
│                             │
│  [ घर / Home ]              │
└─────────────────────────────┘
```

---

### 5. Heritage Screen

```
┌─────────────────────────────┐
│  Stories & Heritage         │
│  Help preserve language     │
│                             │
│  [Story] [Word] [Culture]   │  ← mode selector
│                             │
│  ┌─────────────────────┐    │
│  │                     │    │
│  │ Tell a full story   │    │  ← dynamic prompt
│  │ about your childhood│    │
│  │                     │    │
│  └─────────────────────┘    │
│                             │
│          ╭~~~~~╮            │
│        ~~   🎤   ~~         │  ← hold to record
│          ╰~~~~~╯            │
│                             │
└─────────────────────────────┘
```

A calmer, slower-paced session compared to the main 'Teach' orb. Built for deep cultural preservation and long-form speech.

---

### 6. Ranks Screen

```
┌─────────────────────────────┐
│  Rankings / र्‍याङ्किङ        │
│                             │
│  [Weekly][Monthly][All-time]│  ← tabs
│  [Language][Category]       │
│                             │
│  This Week                  │
│  ─────────────────────────  │
│  🥇  Sita Sharma    3,200   │
│  🥈  Hari Thapa     2,890   │
│  🥉  Raj Kumar      2,450   │
│      Maya Rai       2,100   │
│      Deepak Pun     1,980   │
│      ...                    │
│  ─────────────────────────  │
│  #3  You            2,450   │  ← teacher's position always visible
│                             │
│  Weekly prize: Gift voucher │
│  Ends in: 3d 14h 22m        │
└─────────────────────────────┘
```

Teacher's rank is always pinned at the bottom even when they're not in top 5. They always know where they stand.

---

### 6. Settings Screen

```
┌─────────────────────────────┐
│  Settings / सेटिङ           │
│                             │
│  THEME                      │
│  ┌─────────────────────┐    │
│  │ [●dark][○bright]    │    │  ← live orb previews
│  │ [○cyber][○trad]     │    │
│  └─────────────────────┘    │
│                             │
│  LANGUAGE                   │
│  Teaching language  Nepali  │
│  App language       Auto    │
│                             │
│  PRIVACY & CONSENT          │
│  Use my audio for training  │ ●
│  Show my name in feed       │ ●
│  Show my name on leaderboard│ ●
│  Public teacher profile     │ ○
│                             │
│  NOTIFICATIONS              │
│  Daily teaching reminder    │ ●
│  Leaderboard updates        │ ●
│  Reward notifications       │ ●
│                             │
│  PROFILE                    │
│  Edit name, age, languages  │
│  Export my data             │
│  Delete my account          │
└─────────────────────────────┘
```

---

### 7. Profile Screen

```
┌─────────────────────────────┐
│                             │
│  [avatar]  Raj Kumar        │
│            Kathmandu        │
│                             │
│  🏅 GOLD TEACHER            │  ← milestone badge
│                             │
│  389 words  •  47h  •  12🔥 │
│                             │
│  BADGES                     │
│  🥇 Pioneer (first 100)     │
│  🌟 Gold Teacher (500 words)│
│  ✏️  Correction Master (50)  │
│                             │
│  WORDS I TAUGHT LIPI        │
│  "नमस्ते"  •  "खाना"  •  …  │
│  [View all 389 →]           │
│                             │
│  CONTRIBUTION HISTORY       │
│  Apr 14 — 23 words, 18 min  │
│  Apr 13 — 15 words, 12 min  │
│  Apr 12 — 31 words, 25 min  │
└─────────────────────────────┘
```

---

## Language Strategy

### Phase 1 — Nepali ↔ English (interchangeable)
LIPI mirrors the teacher's active language. No toggle, no button.

```
Teacher speaks Nepali  → LIPI replies in Nepali
Teacher speaks English → LIPI replies in English
Teacher mixes both     → LIPI mirrors the mix
```

**Display rule:** Both languages shown until teacher establishes a pattern. LIPI drops the secondary language after ~3 consistent exchanges.

### Phase 2 — Native language conversations
Once enough teachers from a language group exist:
- Maithili teachers → LIPI converses in Maithili
- Newari teachers → LIPI converses in Newari
- Platform language (Nepali) always present as secondary

### Future language pairs
Not English + Nepali forever. Long-term:
- Hindi speaker sees Hindi + Nepali (not Hindi + English)
- Nepali is the platform identity, always present

---

## Tone & Address System

### Age-based register (default)

| Age | Register | Example |
|-----|----------|---------|
| < 30 | तिमी (timi) | "तिमी कहाँ हुर्कियौ?" |
| ≥ 30 | तपाई (tapai) | "तपाईं कहाँ हुर्कनुभयो?" |
| ≥ 60 | हजुर (hajur) | "हजुर कहाँ बस्नुहुन्छ?" |

### Teacher override (natural speech, any time)
Teacher can tell LIPI to switch register mid-conversation:

```
Teacher: "मलाई तिमी भनेर बोल"
LIPI:    Switches to तिमी immediately, no awkward confirmation

Teacher: "तँ भनेर बोल"
LIPI:    Switches to तँ — most intimate register

Teacher: "formal राख्नुस्"
LIPI:    Returns to तपाई/हजुर
```

LIPI switches naturally — no meta-commentary. Just starts using the new register.

### Tone evolution over time

LIPI learns the teacher's full communication style across sessions:

```
Session 1-3:    Register (timi/tapai/tan)
Session 4-10:   Energy level (fast/slow, short/long)
Session 10-20:  Humor level (does teacher joke? LIPI mirrors)
Session 20+:    Vocabulary preferences
                Code-switching ratio
                Favorite topics
                How they like to be acknowledged
```

**Stored per teacher:**

```python
class TeacherToneProfile:
    register: str            # "tapai" | "timi" | "ta"
    energy: str              # "high" | "medium" | "low"
    humor_level: float       # 0.0 to 1.0
    code_switch_ratio: float # 0.0 = pure Nepali, 1.0 = pure English
    avg_response_length: int # short vs elaborate
    preferred_topics: list
    override_set_by_user: bool
```

**Dynamic system prompt (generated each session):**

```python
def build_system_prompt(user, tone):
    register_note = {
        "tapai": "Use तपाई — formal, respectful",
        "timi":  "Use तिमी — casual, peer-like",
        "ta":    "Use तँ — very informal, close friend"
    }[tone.register]

    humor_note = (
        "Mirror teacher's humor naturally"
        if tone.humor_level > 0.5
        else "Warm but straightforward"
    )

    return f"""
तपाई LIPI हुनुहुन्छ — {user.primary_language} सिक्दै गरेको AI विद्यार्थी।

शिक्षक: {user.name}, {user.age} वर्ष
{register_note}
Energy: {tone.energy}
{humor_note}
Code-switch: {tone.code_switch_ratio:.0%} Nepali
Topics they enjoy: {', '.join(tone.preferred_topics[:3])}

नियम: सधैं सवाल सोध्नुस्। शिक्षा दिनु होइन।
If teacher says "मलाई तँ भन" — switch register immediately.
"""
```

**The relationship arc:**
```
Day 1:    LIPI speaks carefully, learns your register
Week 1:   LIPI picks up your rhythm and energy
Month 1:  LIPI sounds like it knows you
Month 3:  LIPI feels like a close student you've taught for years
```

---

## Points & Gamification System

### Earning points

| Action | Points |
|--------|--------|
| Teaching session (5 min) | 10 |
| Each word LIPI learns from you | 5 |
| Correction accepted by LIPI | 15 |
| Daily streak bonus | 5× multiplier |
| Rare dialect / minority language | 3× multiplier |
| Audio quality bonus (clear audio) | +2 per utterance |
| First teacher of a new word | +25 (pioneer bonus) |

Corrections worth more than volume — prevents spam, rewards quality.

### Anti-gaming rules
- Points confirmed only after LIPI quality check passes
- Minimum audio quality threshold before points awarded
- Troll score system blocks bad actors (see STUDENT_CHARACTER_DESIGN.md)
- Community corrections can flag bad teachings

### Leaderboard tiers

| Board | Reset | Prize |
|-------|-------|-------|
| Weekly | Every Monday | Gift voucher |
| Monthly | 1st of month | Cash prize + badge |
| All-time | Never | Permanent Hall of Fame |
| By language | Monthly | Language-specific prize |
| By category | Weekly | Category badge |

### Milestone badges

| Milestone | Badge |
|-----------|-------|
| 100 words taught | 🥉 Bronze Teacher |
| 500 words taught | 🥈 Silver Teacher |
| 1,000 words taught | 🥇 Gold Teacher |
| 5,000 words taught | ⭐ LIPI Legend |
| First to teach a word | 🏴 Pioneer |
| 50 corrections made | ✏️ Correction Master |
| 7-day streak | 🔥 On Fire |
| 30-day streak | 💎 Dedicated |
| 100-day streak | 🎖️ LIPI Elder |

### Streak rewards
- 7 days → Bonus points multiplier
- 30 days → Exclusive theme unlocked
- 100 days → Physical gift (merch, certificate)

### Monthly winner rewards
- Cash prize or gift voucher
- Permanent "Top Teacher [Month Year]" badge
- Featured on community page
- Certificate of language contribution

---

## Community Feed

Shows what LIPI learned today from the whole community.
Only shows names of teachers who have consented (opt-in).

```
आजको सिकाइ / Today LIPI learned:
"खिचडी" — Sita Sharma, Kathmandu
"दसैं"  — Ram Thapa, Pokhara
"धन्यवाद" — You ✓
```

Seeing "You" in the feed with a checkmark is the dopamine hit — your contribution is public, named, permanent.

---

## Session Summary Card

Shown after each teaching session ends:

```
आजको सत्र / Today's session

⏱  18 minutes
📚 23 words LIPI learned
✏️  4 corrections you made
🏅 +340 points earned
📊 Now ranked #3 this week

[ घर जानु / Go Home ]
```

---

## Copy Guidelines

### Bilingual rules
- Nepali always on top, larger
- English always below, smaller
- Never English-only anywhere in the app
- Exception: Settings labels can be English-first for technical terms

### LIPI's voice examples

**Greeting:**
```
नमस्ते! म LIPI हुँ।
Hi! I'm LIPI.
```

**Learning something:**
```
मैले सिकेँ। धन्यवाद!
I learned. Thank you!
```

**Confused:**
```
मलाई अलि गाह्रो भयो।
अर्को उदाहरण दिनुस् न।

I'm a bit confused.
Can you give me another example?
```

**Correction received:**
```
ओहो! त्यसरी भन्दो रहेछ।
मैले गलत बुझेको थिएँ।

Oh! So that's how it's said.
I had misunderstood.
```

**After a long session:**
```
आज धेरै सिकेँ।
तपाईं राम्रो शिक्षक हुनुहुन्छ।

I learned a lot today.
You are a good teacher.
```

### Error states (honest, not corporate)
```
❌ Never: "An unexpected error occurred. Please try again."
✓  Use:   "LIPI ले सुन्न सकेन। फेरि भन्नुस्।"
           "LIPI couldn't hear. Please say that again."

❌ Never: "Service temporarily unavailable."
✓  Use:   "LIPI अहिले सोच्दैछ। एक छिन पर्खनुस्।"
           "LIPI is thinking. Wait a moment."
```

---

## Next Steps

- [ ] Create Figma mockups for all screens
- [ ] Define Lottie animation specs for the orb (4 states)
- [ ] Write all onboarding copy in Nepali + English
- [ ] Write full system prompt templates (all registers)
- [ ] Design language selector component (searchable, 200+ languages)
- [ ] Define points calculation logic in detail
- [ ] Build Next.js component library with theme system
