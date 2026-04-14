# LLM Benchmark Plan: Qwen 3.5 vs Gemma 4
## Focus: Question Generation & Student Behavior

**Status**: Ready to Execute  
**Timeline**: 2-3 weeks  
**Hardware**: Single GPU testing (can iterate quickly)  
**Models**: Qwen 3.5 70B vs Gemma 4

---

## Core Insight

LIPI LLM role:
- ❌ NOT to be accurate at Nepali (users teach this)
- ✅ Generate diverse, engaging questions
- ✅ Ask like a curious student, not a teacher
- ✅ Naturally incorporate user corrections
- ✅ Respond in <2 seconds

---

## Test Suite 1: Question Generation Quality (15 tests)

**Prompt Pattern**: "Generate 5 different ways to ask about: [topic]"

### Test Cases

```
1. Greetings
   Prompt: "नेपालीमा नमस्कार गर्ने 5 फरक तरिका बनाउनुहोस्"
   Scoring: Diversity (no repeats), grammatical soundness, naturalness
   
2. Food/Eating
   Prompt: "खाना खाने बारे पूछ्ने 5 फरक तरिका बनाउनुहोस्"
   
3. Family relationships
   Prompt: "परिवार सदस्यहरु बारे पूछ्ने 5 तरिका"
   
4. Daily activities
   Prompt: "दैनिक गतिविधि बारे सोध्ने 5 तरिका"
   
5. Colors & objects
   Prompt: "रुङ्ग र वस्तु बारे पूछ्ने 5 प्रश्न"
   
6. Numbers & time
   Prompt: "संख्या र समय बारे पूछ्ने 5 तरिका"
   
7. Emotions
   Prompt: "भावना बारे पूछ्ने 5 फरक तरिका"
   
8. Occupations
   Prompt: "पेशा बारे पूछ्ने 5 सवाल"
   
9. Travel & places
   Prompt: "यात्रा र ठाउँ बारे सोध्ने 5 प्रश्न"
   
10. Weather
    Prompt: "मौसम बारे पूछ्ने 5 तरिका"
    
11. Health & body parts
    Prompt: "स्वास्थ्य बारे पूछ्ने 5 भिन्न प्रश्न"
    
12. Sports & hobbies
    Prompt: "खेल र शौक बारे सोध्ने 5 सवाल"
    
13. Education & learning
    Prompt: "शिक्षा बारे पूछ्ने 5 फरक तरिका"
    
14. Shopping & money
    Prompt: "किनमेल र पैसा बारे पूछ्ने 5 सवाल"
    
15. Holidays & festivals
    Prompt: "पर्व र त्योहार बारे सोध्ने 5 तरिका"
```

**Scoring Rubric** (0-5 per test):
- 5: All 5 unique, grammatical, natural, varied structures
- 4: 4-5 unique, minor grammar issues, mostly natural
- 3: 3-4 unique, some repetition, acceptable
- 2: Heavy repetition, grammatical errors, awkward phrasing
- 1: Mostly broken, unusable

**Target**: Average score >4.0/5

---

## Test Suite 2: Student Behavior (10 tests)

**Pattern**: Present a teaching scenario. Does model respond like a curious student?

### Test Cases

```
1. Name introduction
   Teacher: "मेरो नाम राज हो"
   Expected LIPI response: Ask name back (नमस्ते! मेरो नाम के हो?)
   Score: Does it ask a question? (Yes=1, No=0)

2. Correction acceptance
   Teacher: "नेपालीमा 'water' को लागि पानी भन्छन्, जल नभन्छन्"
   Expected: Acknowledge, ask for clarification or use in context
   Score: Shows gratitude? Shows curiosity? (0-2)

3. Grammar teaching moment
   Teacher: "नेपालीमा verb को अन्त -छु, -छौ, -छ, -छौं हुन्छ"
   Expected: Ask for example or acknowledge learning
   Score: Student-like (curious, not explaining back) (0-1)

4. Cultural fact
   Teacher: "नेपालको राष्ट्रिय फुल लालीगुराँस हो"
   Expected: Show curiosity ("Where does it grow?" etc.)
   Score: Asks follow-up question (Yes=1, No=0)

5. Dialect variation
   Teacher: "मेरो क्षेत्रमा हामी 'भन्छु' भन्दा 'भनु' प्रयोग गरु"
   Expected: Ask about region/context
   Score: Shows interest in learning variation (0-1)

6. Idiomatic expression
   Teacher: "नेपालीमा 'सधैन' को मतलब 'हमेशा' हो"
   Expected: Ask for example sentence
   Score: Seeks application (0-1)

7. Word origin
   Teacher: "यो शब्द संस्कृतबाट आयो"
   Expected: Curious about meaning difference
   Score: Asks clarifying question (0-1)

8. Pronunciation correction
   Teacher: "यो शब्द 'ता' नभन्दा 'ड' को साथ बोल्छन्"
   Expected: Repeat back for confirmation or ask for more
   Score: Acknowledges & seeks practice (0-1)

9. Usage context
   Teacher: "यो शब्द औपचारिक अवस्थामा प्रयोग हुन्छ"
   Expected: Ask for informal equivalent or example
   Score: Shows context awareness (0-1)

10. Multi-turn teaching
    Turn 1: Teacher: "नेपालीमा 'hello' को लागि नमस्ते भन्छन्"
    LIPI: [responds]
    Turn 2: Teacher: "अनि रात्रिमा 'शुभ रात्रि' भन्छन्"
    LIPI: [should connect to previous teaching]
    Score: References previous lesson or asks connected question (0-2)
```

**Scoring**: Total /13 points per model  
**Target**: >10/13 (77% student behavior)

---

## Test Suite 3: Feedback Incorporation (8 tests)

**Pattern**: Teacher corrects LIPI. Does LIPI naturally incorporate it?

### Test Cases

```
1. Grammar correction
   LIPI: "मैं जान्छु"
   Teacher: "सही छ, तर 'हामी जान्छौं' plural हो"
   LIPI Expected: Next question uses plural or acknowledges distinction
   Score: Natural incorporation (0-2)

2. Vocabulary swap
   LIPI: "सधैन कहाँ जान्छु?"
   Teacher: "बरु 'कहिले' भन्छन्, 'कहाँ' नभन्छन्"
   LIPI Expected: "तब कहिले जान्छु?" (uses corrected form)
   Score: Uses feedback in next turn (0-2)

3. Pronunciation guidance
   LIPI: "नमस्कार"
   Teacher: "सही हो, तर 'नमस्ते' अधिक सामान्य"
   LIPI Expected: Acknowledges and adjusts
   Score: Shows learning (0-2)

4. Cultural correction
   LIPI: "नेपालको राजधानी काठमाडौँ हो"
   Teacher: "सही छ। अनि यो 'Kathmandu Valley' को केन्द्र हो"
   LIPI Expected: Asks follow-up about valley or geography
   Score: Builds on correction (0-2)

5. Dialect note
   LIPI: "तपाई कहाँ छन्?"
   Teacher: "मेरो क्षेत्रमा हामी 'तँ कहाँ छौ?' भन्छु"
   LIPI Expected: Acknowledges dialect variation
   Score: Shows interest (0-2)

6. Idiomatic correction
   LIPI: "यो कहिले हुन्छ?"
   Teacher: "वरु 'कहिले भेट हुन्छ?' भन्छन्"
   LIPI Expected: Thanks and uses corrected phrasing
   Score: Natural response (0-2)

7. Tense correction
   LIPI: "मैं खान्छु (present)"
   Teacher: "भोलि को लागि: मैं खान्छु (future expected)"
   LIPI Expected: Clarifies or asks about tense usage
   Score: Shows understanding (0-2)

8. Multiple corrections in one turn
   Teacher: "Actually, it's 'खान्छु' not 'जान्छु', and plural is 'खान्छौं'"
   LIPI Expected: Acknowledges both corrections naturally
   Score: Handles multiple corrections (0-2)
```

**Scoring**: Total /16 points  
**Target**: >12/16 (75% incorporation quality)

---

## Test Suite 4: Speed Test (1 test)

**Metric**: Response latency

```
Scenario: Real chat with 5 rapid questions
1. "नमस्ते! तपाई को हुनुहुन्छ?"
2. "आज कस्तो दिन छ?"
3. "तपाईको मनपर्ने खाना कुन हो?"
4. "नेपालमा कहिले बर्षात हुन्छ?"
5. "मेरो नाम के लिनु?"

Measurement: Time from question to first token (STT→LLM→TTS pipeline)
Target: <2 seconds per response
```

---

## Execution Plan

### Week 1: Setup

- [ ] Install vLLM + Qwen 3.5 weights
- [ ] Install vLLM + Gemma 4 weights
- [ ] Create test harness (Python script to run tests)
- [ ] Prepare system prompt in Nepali (student roleplay)

### Week 2: Test Qwen 3.5

- [ ] Run 15 question generation tests
- [ ] Run 10 student behavior tests
- [ ] Run 8 feedback incorporation tests
- [ ] Run speed benchmarks
- [ ] Document scores

### Week 3: Test Gemma 4 + Decide

- [ ] Run all tests for Gemma 4
- [ ] Compare scores
- [ ] Pick winner (or hybrid approach)
- [ ] Document decision

---

## Scoring Summary Template

```
╔═══════════════════════════════════════════════════════════════╗
║          LLM Question Generation Benchmark Results            ║
╚═══════════════════════════════════════════════════════════════╝

MODEL: Qwen 3.5 70B
HARDWARE: Single L40S GPU

┌───────────────────────────────────────────────────────────────┐
│ TEST SUITE RESULTS                                            │
├───────────────────────────────────────────────────────────────┤
│ 1. Question Generation    │ 14.2/15    │ 94.7% ✓✓           │
│ 2. Student Behavior       │ 11/13      │ 84.6% ✓            │
│ 3. Feedback Incorporation │ 13/16      │ 81.3% ✓            │
│ 4. Speed                  │ 1.8s avg   │ Good               │
└───────────────────────────────────────────────────────────────┘

OVERALL SCORE: 88.2/100

RECOMMENDATION: ✓ APPROVED for Phase 1

NOTES:
- Question generation excellent (very diverse)
- Student behavior strong (asks follow-ups naturally)
- Speed adequate for real-time chat
- Handles corrections smoothly

COMPARISON vs Gemma 4:
  [Gemma 4 scores to be filled in after testing]
```

---

## Decision Framework

**If Qwen wins**:
```
Score: Qwen 94 vs Gemma 87
Decision: Use Qwen 3.5 for production
GPU allocation: 1× GPU (not 5), frees 4 GPUs for training
```

**If Gemma wins**:
```
Score: Gemma 92 vs Qwen 88
Decision: Use Gemma 4 for production
Benefit: Faster (256 tok/s vs 128)
```

**If very close**:
```
Score: Qwen 91 vs Gemma 90
Decision: Use Qwen (cheaper inference, proven)
Or: A/B test in Phase 1 with users
```

---

## Next Actions

1. **Source test environment** — Single GPU or cloud instance
2. **Write test harness** — Python script to automate scoring
3. **Confirm Nepali prompts** — Have native speaker review test cases
4. **Execute Week 1-3 plan** — 3 weeks to decision
5. **Document winner** — Update docker-compose.yml with chosen model
