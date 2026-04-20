// screens.jsx — all screens for the LIPI prototype
const { useState: uS, useEffect: uE, useRef: uR } = React;

// ═══════════════════════════════════════════════════════════════════
// AUTH / LANDING
// ═══════════════════════════════════════════════════════════════════
function AuthScreen({ theme, onContinue }) {
  return (
    <div style={{
      position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
      padding: '70px 28px 40px', justifyContent: 'space-between',
      background: theme.bg,
    }}>
      <StatusBar dark={theme.label === 'Ink'} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Mono color={theme.fgMuted}>⁄ 001 · Welcome</Mono>
        <Mono color={theme.fgMuted}>v 1.0</Mono>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <Orb state="idle" size={180} theme={theme} />
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            fontFamily: FONTS.serif, fontSize: 68, lineHeight: 0.9,
            color: theme.fg, letterSpacing: '-0.03em', fontWeight: 400,
          }}>लिपि</div>
          <div style={{
            fontFamily: FONTS.mono, fontSize: 11, letterSpacing: '0.3em',
            color: theme.fgMuted, textTransform: 'uppercase',
          }}>L · I · P · I</div>
        </div>
        <div style={{ maxWidth: 280, textAlign: 'center' }}>
          <div style={{
            fontFamily: FONTS.serif, fontSize: 22, lineHeight: 1.3,
            color: theme.fg, letterSpacing: '-0.01em',
          }}>
            You speak.<br/>
            <em style={{ color: theme.fgMuted }}>LIPI listens.</em><br/>
            Language lives.
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <PillButton theme={theme} full onClick={onContinue}>
          <svg width="16" height="16" viewBox="0 0 18 18"><path d="M17.6 9.2c0-.6 0-1.2-.1-1.7H9v3.3h4.8c-.2 1.1-.8 2-1.8 2.6v2.2h2.9c1.7-1.5 2.7-3.8 2.7-6.4z" fill="#4285F4"/><path d="M9 18c2.4 0 4.5-.8 6-2.2l-2.9-2.2c-.8.5-1.8.9-3.1.9-2.4 0-4.4-1.6-5.1-3.8H.9v2.3C2.4 15.9 5.5 18 9 18z" fill="#34A853"/><path d="M3.9 10.7c-.2-.5-.3-1.1-.3-1.7s.1-1.2.3-1.7V5H.9C.3 6.2 0 7.5 0 9s.3 2.8.9 4l3-2.3z" fill="#FBBC05"/><path d="M9 3.6c1.3 0 2.5.5 3.4 1.3l2.6-2.6C13.5.9 11.4 0 9 0 5.5 0 2.4 2.1.9 5l3 2.3C4.6 5.1 6.6 3.6 9 3.6z" fill="#EA4335"/></svg>
          Continue with Google
        </PillButton>
        <PillButton theme={theme} full variant="secondary" onClick={onContinue}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="3" y="1" width="10" height="14" rx="2" stroke="currentColor" strokeWidth="1.3"/><circle cx="8" cy="12.5" r="0.7" fill="currentColor"/></svg>
          Continue with Phone
        </PillButton>
        <div style={{ textAlign: 'center', marginTop: 6 }}>
          <Mono color={theme.fgSubtle}>by continuing you join 12,401 teachers</Mono>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ONBOARDING — multi-step
// ═══════════════════════════════════════════════════════════════════
function OnboardingScreen({ theme, onDone }) {
  const [step, setStep] = uS(0);
  const [name, setName] = uS('');
  const [age, setAge] = uS(28);
  const [primary, setPrimary] = uS('नेपाली');
  const [others, setOthers] = uS(['English']);
  const [place, setPlace] = uS('');
  const [edu, setEdu] = uS('');
  const [gender, setGender] = uS('');

  const steps = [
    { type: 'intro' },
    { type: 'text', key: 'name', np: 'तपाईंको नाम के हो?', en: 'What should I call you?', value: name, set: setName, placeholder: 'Your name', mono: 'Q 01 · Name' },
    { type: 'number', key: 'age', np: 'तपाईंको उमेर कति हो?', en: 'How many years young?', value: age, set: setAge, mono: 'Q 02 · Age' },
    { type: 'select', key: 'primary', np: 'म कुन भाषा सिकूँ?', en: 'Which language will you teach me?',
      options: ['नेपाली · Nepali', 'हिन्दी · Hindi', 'नेवारी · Newari', 'मैथिली · Maithili', 'English', 'भोजपुरी · Bhojpuri'],
      value: primary, set: setPrimary, mono: 'Q 03 · Primary' },
    { type: 'multi', key: 'others', np: 'अरू कुन भाषाहरू बोल्नुहुन्छ?', en: 'Which others do you speak?',
      options: ['नेपाली', 'हिन्दी', 'English', 'नेवारी', 'मैथिली', 'भोजपुरी', 'तामाङ', 'मगर', 'Limbu', 'Urdu'],
      value: others, set: setOthers, mono: 'Q 04 · Others' },
    { type: 'text', key: 'place', np: 'तपाईं कहाँ हुर्कनुभयो?', en: 'Where did you grow up?', value: place, set: setPlace, placeholder: 'Kathmandu, Pokhara, ...', mono: 'Q 05 · Roots' },
    { type: 'chips', key: 'edu', np: 'शैक्षिक योग्यता?', en: 'Your education?',
      options: ['प्राथमिक · Primary', 'माध्यमिक · Secondary', 'स्नातक · Bachelor\u2019s', 'स्नातकोत्तर · Master\u2019s', 'पिएचडी · PhD', 'भन्न मन छैन · Skip'],
      value: edu, set: setEdu, mono: 'Q 06 · Education' },
    { type: 'chips', key: 'gender', np: 'लिंग?', en: 'Gender?',
      options: ['पुरुष · Male', 'महिला · Female', 'अन्य · Other', 'भन्न मन छैन · Skip'],
      value: gender, set: setGender, mono: 'Q 07 · Gender' },
  ];

  const s = steps[step];
  const progress = step / (steps.length - 1);

  return (
    <div style={{
      position: 'absolute', inset: 0, background: theme.bg,
      display: 'flex', flexDirection: 'column',
      padding: '70px 28px 40px',
    }}>
      <StatusBar dark={theme.label === 'Ink'} />

      {/* progress bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {step > 0 && (
          <button onClick={() => setStep(s => s - 1)} style={{
            background: 'transparent', border: 'none', color: theme.fgMuted, cursor: 'pointer', padding: 0,
          }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M11 4L6 9l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </button>
        )}
        <div style={{ flex: 1, height: 2, background: theme.rule, borderRadius: 1, overflow: 'hidden' }}>
          <div style={{ width: `${progress * 100}%`, height: '100%', background: theme.fg, transition: 'width 400ms cubic-bezier(.4,0,.2,1)' }} />
        </div>
        <Mono color={theme.fgMuted}>{String(step).padStart(2, '0')} / {String(steps.length - 1).padStart(2, '0')}</Mono>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 32, marginTop: 20 }}>
        {s.type === 'intro' ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
            <Orb state="listening" size={140} theme={theme} />
            <div style={{ textAlign: 'center', maxWidth: 300 }}>
              <div style={{ fontFamily: FONTS.serif, fontSize: 32, color: theme.fg, lineHeight: 1.2, letterSpacing: '-0.02em' }}>
                नमस्ते!<br/>म LIPI हुँ।
              </div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 15, color: theme.fgMuted, marginTop: 14, lineHeight: 1.5, fontStyle: 'italic' }}>
                Hi — I'm LIPI. I'm learning languages from teachers like you.<br/><br/>
                Before we begin, can I ask you a few things?
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div>
              <Mono color={theme.fgMuted}>⁄ {s.mono}</Mono>
              <div style={{ marginTop: 14 }}>
                <Bilingual np={s.np} en={s.en} size="lg" theme={theme}/>
              </div>
            </div>

            {s.type === 'text' && (
              <input value={s.value} onChange={e => s.set(e.target.value)} placeholder={s.placeholder}
                style={{
                  fontFamily: FONTS.serif, fontSize: 28, color: theme.fg,
                  background: 'transparent', border: 'none', borderBottom: `1.5px solid ${theme.rule}`,
                  padding: '10px 0', width: '100%', outline: 'none',
                }}/>
            )}

            {s.type === 'number' && (
              <div>
                <div style={{
                  fontFamily: FONTS.serif, fontSize: 72, color: theme.fg, textAlign: 'center',
                  lineHeight: 1, letterSpacing: '-0.03em',
                }}>{s.value}</div>
                <input type="range" min="13" max="90" value={s.value} onChange={e => s.set(+e.target.value)}
                  style={{ width: '100%', marginTop: 16, accentColor: theme.fg }}/>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                  <Mono color={theme.fgSubtle}>13</Mono><Mono color={theme.fgSubtle}>90</Mono>
                </div>
              </div>
            )}

            {s.type === 'select' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {s.options.map(o => (
                  <button key={o} onClick={() => s.set(o)} style={{
                    textAlign: 'left', padding: '14px 18px',
                    background: s.value === o ? theme.accent : 'transparent',
                    color: s.value === o ? theme.accentFg : theme.fg,
                    border: `1px solid ${s.value === o ? theme.accent : theme.rule}`,
                    borderRadius: 16, fontFamily: FONTS.nepaliUi, fontSize: 15, cursor: 'pointer',
                    transition: 'all 180ms ease',
                  }}>{o}</button>
                ))}
              </div>
            )}

            {s.type === 'multi' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {s.options.map(o => {
                  const on = s.value.includes(o);
                  return (
                    <Chip key={o} theme={theme} active={on} onClick={() =>
                      s.set(on ? s.value.filter(x => x !== o) : [...s.value, o])
                    }>{o}</Chip>
                  );
                })}
              </div>
            )}

            {s.type === 'chips' && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {s.options.map(o => (
                  <Chip key={o} theme={theme} active={s.value === o} onClick={() => s.set(o)}>{o}</Chip>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <PillButton theme={theme} full onClick={() => step === steps.length - 1 ? onDone({ name, age }) : setStep(s => s + 1)}>
        {step === 0 ? 'Begin · सुरु गर्नु' : step === steps.length - 1 ? 'Start teaching' : 'Continue'}
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8m0 0L7 3m4 4L7 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </PillButton>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// HOME
// ═══════════════════════════════════════════════════════════════════
function HomeScreen({ theme, user, register, onTeach }) {
  const hour = new Date().getHours();
  const greet = hour < 12 ? REGISTERS[register].greetingMorning
              : hour < 17 ? REGISTERS[register].greetingAfternoon
              : REGISTERS[register].greetingEvening;
  const greetEn = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const displayName = user.name + REGISTERS[register].nameSuffix;

  return (
    <div style={{
      position: 'absolute', inset: 0, overflow: 'auto', background: theme.bg,
      padding: '60px 20px 120px',
    }}>
      <StatusBar dark={theme.label === 'Ink'} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0 4px' }}>
        <div>
          <Mono color={theme.fgMuted}>⁄ 042 · TODAY</Mono>
          <div style={{ marginTop: 14 }}>
            <Bilingual np={`${greet}, ${displayName}`} en={`${greetEn}, ${user.name}`} size="lg" theme={theme} nowrap/>
          </div>
        </div>
        <div style={{
          width: 40, height: 40, borderRadius: 999, background: theme.tintLavender,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: FONTS.serif, fontSize: 16, color: theme.fg, border: `1px solid ${theme.rule}`,
        }}>{user.name[0]}</div>
      </div>

      {/* LIPI learned hero */}
      <Card theme={theme} style={{ marginTop: 24, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '22px 22px 4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Mono color={theme.fgMuted}>LIPI HAS LEARNED</Mono>
          <Mono color={theme.fgMuted}>↗ +23 today</Mono>
        </div>
        <div style={{ padding: '12px 22px 18px' }}>
          <div style={{ fontFamily: FONTS.nepali, fontSize: 16, color: theme.fgMuted, lineHeight: 1.4 }}>शब्दहरू <span style={{ fontFamily: FONTS.sans, fontSize: 12, fontStyle: 'italic' }}>· words from you</span></div>
          <div style={{
            fontFamily: FONTS.serif, fontSize: 96, lineHeight: 1,
            color: theme.fg, letterSpacing: '-0.04em', fontWeight: 400,
            marginTop: 8,
          }}>389</div>
        </div>
        <div style={{ position: 'relative', height: 64, margin: '0 22px 18px', borderTop: `1px solid ${theme.rule}` }}>
          {/* mini sparkline */}
          <svg viewBox="0 0 320 60" width="100%" height="60" preserveAspectRatio="none">
            <path d="M0,50 C40,40 60,30 90,32 C120,34 140,20 170,22 C200,24 230,10 260,14 C290,18 310,8 320,10"
              fill="none" stroke={theme.fg} strokeWidth="1.2" opacity="0.6"/>
            <path d="M0,50 C40,40 60,30 90,32 C120,34 140,20 170,22 C200,24 230,10 260,14 C290,18 310,8 320,10 L320,60 L0,60 Z"
              fill={theme.tintLavender}/>
          </svg>
        </div>
        <div style={{
          display: 'flex', borderTop: `1px solid ${theme.rule}`,
        }}>
          {[
            { val: '47.2', unit: 'hrs', label: 'Taught' },
            { val: '12', unit: 'day', label: 'Streak' },
            { val: '62', unit: 'fx', label: 'Corrections' },
          ].map((s, i, arr) => (
            <div key={s.label} style={{
              flex: 1, padding: '16px 18px',
              borderRight: i < arr.length - 1 ? `1px solid ${theme.rule}` : 'none',
            }}>
              <Mono color={theme.fgSubtle}>{s.label}</Mono>
              <div style={{
                fontFamily: FONTS.serif, fontSize: 28, color: theme.fg,
                marginTop: 4, letterSpacing: '-0.02em',
              }}>{s.val}<span style={{ fontSize: 13, fontFamily: FONTS.mono, color: theme.fgMuted, marginLeft: 4 }}>{s.unit}</span></div>
            </div>
          ))}
        </div>
      </Card>

      {/* Teach CTA */}
      <button onClick={onTeach} style={{
        marginTop: 14, width: '100%', padding: '22px 22px',
        background: theme.accent, color: theme.accentFg,
        border: 'none', borderRadius: 24, cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontFamily: FONTS.sans, textAlign: 'left',
      }}>
        <div style={{ minWidth: 0 }}>
          <Mono color={`${theme.accentFg}99`}>NOW · READY · सिकाउनु</Mono>
          <div style={{ fontFamily: FONTS.serif, fontSize: 26, marginTop: 8, letterSpacing: '-0.01em', lineHeight: 1.2 }}>
            Start teaching LIPI
          </div>
        </div>
        <div style={{
          width: 52, height: 52, borderRadius: 999, background: `${theme.accentFg}18`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 10h10m0 0l-5-5m5 5l-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </div>
      </button>

      {/* Rank / position */}
      <Card theme={theme} style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Mono color={theme.fgMuted}>⁄ RANK · WEEKLY</Mono>
          <Mono color={theme.fgMuted}>ends in 3d 14h</Mono>
        </div>
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { r: 1, n: 'Sita Sharma',   p: 3200, tag: 'GOLD' },
            { r: 2, n: 'Hari Thapa',    p: 2890 },
            { r: 3, n: user.name,       p: 2450, you: true },
            { r: 4, n: 'Maya Rai',      p: 2100 },
          ].map(r => (
            <div key={r.r} style={{
              display: 'grid', gridTemplateColumns: '28px 1fr auto auto',
              gap: 10, alignItems: 'center',
              padding: '10px 12px', borderRadius: 12,
              background: r.you ? theme.tintButter : 'transparent',
              border: r.you ? `1px solid ${theme.rule}` : '1px solid transparent',
            }}>
              <Mono color={theme.fgSubtle}>{String(r.r).padStart(2, '0')}</Mono>
              <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fg }}>
                {r.n}{r.you && <span style={{ color: theme.fgMuted, marginLeft: 8 }}>· you</span>}
              </div>
              {r.tag && <Mono color={theme.fgMuted}>{r.tag}</Mono>}
              <div style={{ fontFamily: FONTS.mono, fontSize: 13, color: theme.fg, fontWeight: 500 }}>{r.p.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Today's learnings feed */}
      <div style={{ marginTop: 24, padding: '0 4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <Mono color={theme.fgMuted}>⁄ TODAY LIPI LEARNED</Mono>
          <Mono color={theme.fgMuted}>LIVE ●</Mono>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {[
            { w: 'खिचडी',     tr: 'a rice-lentil dish', by: 'Sita S.',      place: 'Kathmandu' },
            { w: 'दसैं',      tr: 'Dashain festival',   by: 'Ram T.',       place: 'Pokhara' },
            { w: 'धन्यवाद',   tr: 'thank you',          by: 'You',          place: 'Kathmandu', you: true },
            { w: 'मिठास',     tr: 'sweetness',          by: 'Anjali K.',    place: 'Lalitpur' },
            { w: 'झर्‍यो',     tr: 'it fell',            by: 'Deepak P.',    place: 'Biratnagar' },
          ].map((r, i) => (
            <div key={i} style={{
              padding: '14px 4px', borderBottom: i < 4 ? `1px solid ${theme.ruleSoft}` : 'none',
              display: 'grid', gridTemplateColumns: '1fr auto', gap: 10, alignItems: 'center',
            }}>
              <div>
                <div style={{ fontFamily: FONTS.nepali, fontSize: 20, color: theme.fg }}>
                  {r.w}
                  {r.you && <span style={{
                    fontFamily: FONTS.mono, fontSize: 10, color: theme.fg,
                    marginLeft: 8, padding: '2px 8px', background: theme.tintButter,
                    borderRadius: 999, letterSpacing: '0.12em',
                  }}>YOU ✓</span>}
                </div>
                <div style={{ fontFamily: FONTS.sans, fontSize: 12, color: theme.fgMuted, fontStyle: 'italic', marginTop: 1 }}>
                  {r.tr}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: FONTS.sans, fontSize: 12, color: theme.fg }}>{r.by}</div>
                <Mono color={theme.fgSubtle}>{r.place}</Mono>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TEACH — the signature screen
// ═══════════════════════════════════════════════════════════════════
function TeachScreen({ theme, user, orbState, setOrbState }) {
  const [subtitles, setSubtitles] = uS([]);
  const [showLearned, setShowLearned] = uS(false);
  const [elapsed, setElapsed] = uS(0);

  // Timer
  uE(() => {
    const id = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // Fake conversation ticker
  uE(() => {
    const loop = [
      { state: 'speaking',  text: { np: 'नमस्ते! आज तपाईंले मलाई के सिकाउनुहुन्छ?', en: "Namaste! What will you teach me today?" }, wait: 3800, who: 'lipi' },
      { state: 'listening', text: null, wait: 2500 },
      { state: 'listening', text: { np: '…"दसैं" भन्ने शब्द…', en: "…the word 'Dashain'…" }, wait: 2400, who: 'user' },
      { state: 'thinking',  text: null, wait: 1600 },
      { state: 'speaking',  text: { np: 'दसैं — नेपालको सबैभन्दा ठूलो पर्व, हो?', en: "Dashain — Nepal's biggest festival, right?" }, wait: 3600, who: 'lipi' },
      { state: 'listening', text: null, wait: 2000 },
    ];
    let i = 0;
    let t;
    const run = () => {
      const step = loop[i % loop.length];
      setOrbState(step.state);
      if (step.text) {
        setSubtitles(prev => [{ ...step.text, who: step.who, id: Date.now() + Math.random() }, ...prev].slice(0, 3));
      }
      if (step.state === 'thinking') setShowLearned(true);
      else if (step.state === 'listening') setShowLearned(false);
      i++;
      t = setTimeout(run, step.wait);
    };
    run();
    return () => clearTimeout(t);
  }, []);

  const min = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const sec = String(elapsed % 60).padStart(2, '0');

  return (
    <div style={{
      position: 'absolute', inset: 0, background: theme.bg, overflow: 'hidden',
    }}>
      <StatusBar dark={theme.label === 'Ink'} />

      {/* top chrome */}
      <div style={{
        position: 'absolute', top: 56, left: 20, right: 20, zIndex: 10,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{
          padding: '8px 14px', borderRadius: 999,
          background: theme.bgFrost, border: `1px solid ${theme.rule}`,
          backdropFilter: 'blur(20px)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: 999,
            background: orbState === 'listening' ? '#E85B5B' : theme.fgMuted,
            animation: orbState === 'listening' ? 'pulse 1.4s ease-in-out infinite' : 'none',
          }}/>
          <Mono>{orbState}</Mono>
          <span style={{ color: theme.fgSubtle }}>·</span>
          <Mono color={theme.fgMuted}>{min}:{sec}</Mono>
        </div>
        <div style={{
          padding: '8px 14px', borderRadius: 999,
          background: theme.bgFrost, border: `1px solid ${theme.rule}`,
          backdropFilter: 'blur(20px)',
        }}>
          <Mono color={theme.fgMuted}>NE · ↔ · EN</Mono>
        </div>
      </div>

      {/* Orb centered */}
      <div style={{
        position: 'absolute', inset: 0, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 40,
      }}>
        <Orb state={orbState} size={260} theme={theme}/>

        {/* "mistakes learned" chip */}
        {showLearned && (
          <div style={{
            position: 'absolute', top: '58%',
            padding: '12px 18px', borderRadius: 16,
            background: theme.bgCard, border: `1px solid ${theme.rule}`,
            boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
            animation: 'rise 300ms cubic-bezier(.4,0,.2,1) both',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: 999, background: theme.tintSage,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>✓</div>
            <div>
              <Mono color={theme.fgMuted}>LEARNED</Mono>
              <div style={{ fontFamily: FONTS.nepali, fontSize: 18, color: theme.fg, marginTop: 2 }}>दसैं</div>
            </div>
            <div style={{
              fontFamily: FONTS.mono, fontSize: 10, color: theme.fgMuted,
              padding: '3px 8px', background: theme.tintLavender, borderRadius: 6, letterSpacing: '0.1em',
            }}>də-SAĨ</div>
          </div>
        )}
      </div>

      {/* subtitles stack — bottom */}
      <div style={{
        position: 'absolute', bottom: 160, left: 20, right: 20,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {subtitles.slice(0, 2).reverse().map((s, i, arr) => {
          const latest = i === arr.length - 1;
          return (
            <div key={s.id} style={{
              padding: '14px 18px', borderRadius: 18,
              background: s.who === 'lipi' ? theme.bgCard : theme.tintLavender,
              border: `1px solid ${theme.rule}`,
              opacity: latest ? 1 : 0.5, transform: latest ? 'scale(1)' : 'scale(0.97)',
              transition: 'all 300ms ease',
              animation: latest ? 'rise 280ms cubic-bezier(.4,0,.2,1) both' : 'none',
              backdropFilter: 'blur(20px)',
              alignSelf: s.who === 'lipi' ? 'flex-start' : 'flex-end',
              maxWidth: '90%',
            }}>
              <Mono color={theme.fgMuted}>{s.who === 'lipi' ? 'LIPI' : user.name.toUpperCase()}</Mono>
              <div style={{ fontFamily: FONTS.nepali, fontSize: 16, color: theme.fg, marginTop: 2, lineHeight: 1.4 }}>{s.np}</div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 11.5, color: theme.fgMuted, fontStyle: 'italic', marginTop: 1 }}>{s.en}</div>
            </div>
          );
        })}
      </div>

      {/* bottom controls */}
      <div style={{
        position: 'absolute', bottom: 80, left: 0, right: 0,
        display: 'flex', justifyContent: 'center', gap: 12,
      }}>
        <button style={ctrlBtnStyle(theme)}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4 9h10m-4-4l4 4-4 4" stroke={theme.fg} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
        <button onClick={() => setOrbState(orbState === 'idle' ? 'listening' : 'idle')} style={{
          ...ctrlBtnStyle(theme),
          width: 64, height: 64,
          background: theme.accent, color: theme.accentFg, border: 'none',
        }}>
          {orbState === 'idle'
            ? <svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M5 4l14 7-14 7V4z" fill="currentColor"/></svg>
            : <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><rect x="5" y="4" width="4" height="12" rx="1"/><rect x="11" y="4" width="4" height="12" rx="1"/></svg>
          }
        </button>
        <button style={ctrlBtnStyle(theme)}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="4" y="4" width="10" height="10" rx="1.5" stroke={theme.fg} strokeWidth="1.4"/></svg>
        </button>
      </div>
    </div>
  );
}

function ctrlBtnStyle(theme) {
  return {
    width: 48, height: 48, borderRadius: 999,
    background: theme.bgCard, border: `1px solid ${theme.rule}`,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', backdropFilter: 'blur(20px)',
    boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
  };
}

// ═══════════════════════════════════════════════════════════════════
// HERITAGE
// ═══════════════════════════════════════════════════════════════════
function HeritageScreen({ theme }) {
  const [mode, setMode] = uS('story');
  const [recording, setRecording] = uS(false);
  const prompts = {
    story: { np: 'आफ्नो बाल्यकालको कुनै एउटा कथा सुनाउनुस्।', en: 'Tell a story from your childhood.' },
    word:  { np: 'तपाईंको गाउँमा "ढिकी" भन्नाले के बुझिन्छ?', en: 'What does "dhiki" mean in your village?' },
    culture: { np: 'दसैंमा टीका लगाउने परम्पराबारे बताउनुस्।', en: 'Tell me about the Dashain tika tradition.' },
  };
  return (
    <div style={{ position: 'absolute', inset: 0, background: theme.bg, padding: '60px 24px 120px', overflow: 'auto' }}>
      <StatusBar dark={theme.label === 'Ink'}/>
      <Mono color={theme.fgMuted}>⁄ 03 · HERITAGE</Mono>
      <div style={{ marginTop: 14, marginBottom: 20 }}>
        <Bilingual np="सम्पदा · कथा" en="Stories, idioms, rituals — the long-form archive" size="lg" theme={theme}/>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {[['story', 'Story', 'कथा'], ['word', 'Word', 'शब्द'], ['culture', 'Culture', 'संस्कृति']].map(([k, en, np]) => (
          <button key={k} onClick={() => setMode(k)} style={{
            flex: 1, padding: '12px 10px', borderRadius: 14,
            background: mode === k ? theme.accent : 'transparent',
            color: mode === k ? theme.accentFg : theme.fg,
            border: `1px solid ${mode === k ? theme.accent : theme.rule}`,
            cursor: 'pointer', textAlign: 'center',
          }}>
            <div style={{ fontFamily: FONTS.nepali, fontSize: 14 }}>{np}</div>
            <Mono style={{ opacity: 0.7 }}>{en}</Mono>
          </button>
        ))}
      </div>

      <Card theme={theme} tinted="Butter" style={{ padding: 28 }}>
        <Mono color={theme.fgMuted}>PROMPT · 14 OF 200</Mono>
        <div style={{ fontFamily: FONTS.serif, fontSize: 26, color: theme.fg, marginTop: 14, lineHeight: 1.3, letterSpacing: '-0.01em' }}>
          {prompts[mode].np}
        </div>
        <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fgMuted, fontStyle: 'italic', marginTop: 8 }}>
          {prompts[mode].en}
        </div>
      </Card>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, marginTop: 32 }}>
        <button onMouseDown={() => setRecording(true)} onMouseUp={() => setRecording(false)}
          onTouchStart={() => setRecording(true)} onTouchEnd={() => setRecording(false)}
          style={{
            width: 96, height: 96, borderRadius: 999,
            background: recording ? theme.orbA : theme.accent, color: theme.accentFg,
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: recording
              ? `0 0 0 12px ${theme.orbGlow}, 0 8px 32px rgba(0,0,0,0.12)`
              : `0 8px 32px rgba(0,0,0,0.14)`,
            transition: 'all 220ms ease', transform: recording ? 'scale(1.04)' : 'scale(1)',
          }}>
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="11" y="4" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M7 12a7 7 0 0014 0M14 19v4M10 23h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        </button>
        <Mono color={theme.fgMuted}>HOLD TO RECORD · {recording ? 'CAPTURING' : 'READY'}</Mono>
        {recording && (
          <div style={{ display: 'flex', gap: 2, marginTop: 4 }}>
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} style={{
                width: 2, height: 8 + Math.random() * 28, background: theme.fg,
                borderRadius: 2, animation: `wave 0.6s ease-in-out ${i * 30}ms infinite alternate`,
              }}/>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 32 }}>
        <Mono color={theme.fgMuted}>⁄ YOUR ARCHIVE</Mono>
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { t: 'Childhood story · Pokhara', d: '4:23', date: 'Apr 16' },
            { t: 'Word: जाँड', d: '0:48', date: 'Apr 14' },
            { t: 'Tihar bhai tika ritual', d: '6:12', date: 'Apr 11' },
          ].map((r, i) => (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 12, alignItems: 'center',
              padding: '14px 16px', borderRadius: 14,
              background: theme.bgCard, border: `1px solid ${theme.rule}`,
            }}>
              <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fg }}>{r.t}</div>
              <Mono color={theme.fgMuted}>{r.d}</Mono>
              <Mono color={theme.fgSubtle}>{r.date}</Mono>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// RANKS
// ═══════════════════════════════════════════════════════════════════
function RanksScreen({ theme, user }) {
  const [tab, setTab] = uS('week');
  const leaders = [
    { r: 1, n: 'Sita Sharma',   p: 3200, pl: 'Kathmandu',   lang: 'Nepali',  streak: 24 },
    { r: 2, n: 'Hari Thapa',    p: 2890, pl: 'Pokhara',     lang: 'Newari',  streak: 18 },
    { r: 3, n: user.name,       p: 2450, pl: 'Kathmandu',   lang: 'Nepali',  streak: 12, you: true },
    { r: 4, n: 'Maya Rai',      p: 2100, pl: 'Biratnagar',  lang: 'Maithili',streak: 8 },
    { r: 5, n: 'Deepak Pun',    p: 1980, pl: 'Lalitpur',    lang: 'Nepali',  streak: 14 },
    { r: 6, n: 'Anjali Khadka', p: 1740, pl: 'Butwal',      lang: 'Bhojpuri',streak: 6 },
    { r: 7, n: 'Bikash Lama',   p: 1680, pl: 'Dharan',      lang: 'Tamang',  streak: 11 },
    { r: 8, n: 'Priya Rana',    p: 1520, pl: 'Nepalgunj',   lang: 'Awadhi',  streak: 5 },
  ];
  return (
    <div style={{ position: 'absolute', inset: 0, background: theme.bg, padding: '60px 20px 120px', overflow: 'auto' }}>
      <StatusBar dark={theme.label === 'Ink'}/>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Mono color={theme.fgMuted}>⁄ 05 · RANKS</Mono>
        <Mono color={theme.fgMuted}>RESETS 3D 14H</Mono>
      </div>
      <div style={{ marginTop: 14 }}>
        <Bilingual np="क्रम तालिका" en="The teachers keeping LIPI alive" size="lg" theme={theme}/>
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 20 }}>
        {['week', 'month', 'all-time'].map(k => (
          <button key={k} onClick={() => setTab(k)} style={{
            padding: '8px 16px', borderRadius: 999,
            background: tab === k ? theme.accent : 'transparent',
            color: tab === k ? theme.accentFg : theme.fgMuted,
            border: `1px solid ${tab === k ? theme.accent : theme.rule}`,
            fontFamily: FONTS.mono, fontSize: 10.5, letterSpacing: '0.14em', textTransform: 'uppercase',
            cursor: 'pointer',
          }}>{k}</button>
        ))}
      </div>

      {/* Top 3 podium */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr 1fr', gap: 10, marginTop: 24, alignItems: 'end' }}>
        {[leaders[1], leaders[0], leaders[2]].map((l, i) => {
          const heights = [120, 150, 100];
          return (
            <div key={l.r} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 50, height: 50, borderRadius: 999,
                background: l.r === 1 ? theme.tintButter : l.r === 2 ? theme.tintSky : theme.tintPeach,
                border: `1px solid ${theme.rule}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: FONTS.serif, fontSize: 20, color: theme.fg,
              }}>{l.n[0]}</div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 12, color: theme.fg, textAlign: 'center', lineHeight: 1.2 }}>
                {l.n.split(' ')[0]}
              </div>
              <div style={{
                width: '100%', height: heights[i], borderRadius: '14px 14px 0 0',
                background: l.you ? theme.tintButter : theme.bgCard,
                border: `1px solid ${theme.rule}`, borderBottom: 'none',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4,
              }}>
                <div style={{ fontFamily: FONTS.serif, fontSize: 32, color: theme.fg, letterSpacing: '-0.02em' }}>{l.r}</div>
                <div style={{ fontFamily: FONTS.mono, fontSize: 11, color: theme.fgMuted }}>{l.p.toLocaleString()}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* List */}
      <div style={{ marginTop: 24 }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '30px 1fr auto auto', gap: 10,
          padding: '8px 14px', borderBottom: `1px solid ${theme.rule}`,
        }}>
          <Mono color={theme.fgSubtle}>#</Mono>
          <Mono color={theme.fgSubtle}>TEACHER</Mono>
          <Mono color={theme.fgSubtle}>LANG</Mono>
          <Mono color={theme.fgSubtle}>PTS</Mono>
        </div>
        {leaders.map(l => (
          <div key={l.r} style={{
            display: 'grid', gridTemplateColumns: '30px 1fr auto auto', gap: 10,
            padding: '13px 14px', borderBottom: `1px solid ${theme.ruleSoft}`,
            background: l.you ? theme.tintButter : 'transparent',
            alignItems: 'center',
          }}>
            <Mono color={theme.fgMuted}>{String(l.r).padStart(2, '0')}</Mono>
            <div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fg }}>
                {l.n}{l.you && <span style={{ color: theme.fgMuted }}> · you</span>}
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 2 }}>
                <Mono color={theme.fgSubtle}>{l.pl}</Mono>
                <Mono color={theme.fgSubtle}>🔥 {l.streak}d</Mono>
              </div>
            </div>
            <Mono color={theme.fgMuted}>{l.lang}</Mono>
            <div style={{ fontFamily: FONTS.mono, fontSize: 13, color: theme.fg, fontWeight: 500 }}>{l.p.toLocaleString()}</div>
          </div>
        ))}
      </div>

      <Card theme={theme} tinted="Butter" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Mono color={theme.fgMuted}>WEEKLY PRIZE</Mono>
            <div style={{ fontFamily: FONTS.serif, fontSize: 20, marginTop: 4, color: theme.fg }}>Gift voucher · ₨ 2,500</div>
          </div>
          <Mono color={theme.fgMuted}>3D 14H 22M</Mono>
        </div>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════════════
function SettingsScreen({ theme, themeKey, setThemeKey, register, setRegister }) {
  const [consents, setConsents] = uS({ training: true, feed: true, board: true, profile: false });
  const [notifs, setNotifs] = uS({ daily: true, leader: true, rewards: true });
  const toggle = (o, k) => ({ ...o, [k]: !o[k] });

  return (
    <div style={{ position: 'absolute', inset: 0, background: theme.bg, padding: '60px 24px 120px', overflow: 'auto' }}>
      <StatusBar dark={theme.label === 'Ink'}/>
      <Mono color={theme.fgMuted}>⁄ 06 · SETTINGS</Mono>
      <div style={{ marginTop: 14 }}>
        <Bilingual np="सेटिङ" en="Themes, privacy, and how LIPI talks to you" size="lg" theme={theme}/>
      </div>

      <Section title="Theme" theme={theme}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          {Object.entries(THEMES).map(([k, t]) => (
            <button key={k} onClick={() => setThemeKey(k)} style={{
              padding: 10, borderRadius: 14, cursor: 'pointer',
              background: t.bgCard, border: `1.5px solid ${themeKey === k ? theme.accent : t.rule}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: 999,
                background: `radial-gradient(circle at 30% 30%, ${t.orbC}, ${t.orbA} 50%, ${t.orbB})`,
              }}/>
              <Mono style={{ fontSize: 8.5, color: themeKey === k ? theme.fg : theme.fgMuted }}>{t.label}</Mono>
            </button>
          ))}
        </div>
      </Section>

      <Section title="How LIPI addresses you" theme={theme}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {Object.entries(REGISTERS).map(([k, r]) => (
            <button key={k} onClick={() => setRegister(k)} style={{
              textAlign: 'left', padding: '14px 16px', borderRadius: 14,
              background: register === k ? theme.accent : theme.bgCard,
              color: register === k ? theme.accentFg : theme.fg,
              border: `1px solid ${register === k ? theme.accent : theme.rule}`,
              cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ fontFamily: FONTS.nepali, fontSize: 16 }}>{r.label}</div>
                <Mono style={{ opacity: 0.7, marginTop: 2 }}>AGE {r.age}</Mono>
              </div>
              {register === k && <svg width="18" height="18" viewBox="0 0 18 18"><path d="M4 9l3 3 7-7" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Privacy & consent" theme={theme}>
        {[
          ['training', 'Use my audio for LIPI training'],
          ['feed',     'Show my name in community feed'],
          ['board',    'Show my name on leaderboard'],
          ['profile',  'Public teacher profile'],
        ].map(([k, label]) => (
          <Toggle key={k} theme={theme} label={label} on={consents[k]} onChange={() => setConsents(o => toggle(o, k))}/>
        ))}
      </Section>

      <Section title="Notifications" theme={theme}>
        {[
          ['daily',  'Daily teaching reminder'],
          ['leader', 'Leaderboard updates'],
          ['rewards','Reward notifications'],
        ].map(([k, label]) => (
          <Toggle key={k} theme={theme} label={label} on={notifs[k]} onChange={() => setNotifs(o => toggle(o, k))}/>
        ))}
      </Section>

      <Section title="Profile" theme={theme}>
        <Row theme={theme} label="Edit profile" value="Name, age, languages"/>
        <Row theme={theme} label="Export my data" value="ZIP archive"/>
        <Row theme={theme} label="Delete my account" value="Permanent" danger/>
      </Section>
    </div>
  );
}

function Section({ title, children, theme }) {
  return (
    <div style={{ marginTop: 28 }}>
      <Mono color={theme.fgMuted} style={{ marginBottom: 12, display: 'block' }}>⁄ {title.toUpperCase()}</Mono>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>{children}</div>
    </div>
  );
}
function Toggle({ label, on, onChange, theme }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '14px 16px', borderRadius: 14,
      background: theme.bgCard, border: `1px solid ${theme.rule}`,
    }}>
      <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fg }}>{label}</div>
      <button onClick={onChange} style={{
        width: 44, height: 26, borderRadius: 999,
        background: on ? theme.accent : theme.rule,
        border: 'none', cursor: 'pointer', position: 'relative',
        transition: 'background 220ms ease',
      }}>
        <div style={{
          position: 'absolute', top: 3, left: on ? 21 : 3,
          width: 20, height: 20, borderRadius: 999, background: theme.accentFg,
          transition: 'left 220ms cubic-bezier(.4,0,.2,1)',
          boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
        }}/>
      </button>
    </div>
  );
}
function Row({ label, value, danger, theme }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '14px 16px', borderRadius: 14,
      background: theme.bgCard, border: `1px solid ${theme.rule}`, cursor: 'pointer',
    }}>
      <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: danger ? '#C44' : theme.fg }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Mono color={theme.fgMuted}>{value}</Mono>
        <svg width="12" height="12" viewBox="0 0 12 12"><path d="M4 2l4 4-4 4" stroke={theme.fgSubtle} strokeWidth="1.3" fill="none" strokeLinecap="round"/></svg>
      </div>
    </div>
  );
}

// ───────────────────── Phrase Lab — focused micro-task tool
// "Lipi needs help with ___" — bite-sized prompts, hold to record, see corpus grow.
function PhraseLabScreen({ theme }) {
  const [active, setActive] = React.useState('food');
  const [recIdx, setRecIdx] = React.useState(null); // index of prompt being recorded
  const [holding, setHolding] = React.useState(false);
  const [done, setDone] = React.useState({}); // { 'food-0': true, ... }
  const [amp, setAmp] = React.useState(0);

  React.useEffect(() => {
    if (!holding) return;
    const id = setInterval(() => setAmp(0.5 + Math.random() * 0.5), 90);
    return () => clearInterval(id);
  }, [holding]);

  const categories = [
    { id: 'food',     np: 'खाना',      en: 'Food & cooking',    count: 24, need: 6 },
    { id: 'family',   np: 'परिवार',     en: 'Family terms',       count: 18, need: 4 },
    { id: 'festival', np: 'पर्व',        en: 'Festivals',          count: 9,  need: 11 },
    { id: 'idiom',    np: 'उखान',       en: 'Idioms & sayings',  count: 12, need: 8 },
    { id: 'place',    np: 'ठाउँ',       en: 'Places in Nepal',    count: 31, need: 3 },
  ];

  const prompts = {
    food:     [
      { np: 'खिचडी', en: 'a comforting rice + lentil porridge', hint: 'How would you describe khichadi to someone who has never had it?' },
      { np: 'अचार', en: 'pickle / chutney', hint: 'What does achar add to a meal? When do you eat it?' },
      { np: 'सेल रोटी', en: 'sweet ring-shaped fried bread', hint: 'When is sel roti made — what occasion?' },
      { np: 'ढिँडो', en: 'thick buckwheat porridge', hint: 'Tell Lipi about dhindo — texture, how to eat it.' },
    ],
    family:   [
      { np: 'दाजु', en: 'older brother', hint: 'How do you address dāju? Is it different in different regions?' },
      { np: 'भाउजू', en: "older brother's wife", hint: 'How would you greet bhauju when visiting?' },
    ],
    festival: [
      { np: 'दसैं', en: 'Dashain — biggest Hindu festival', hint: 'Tell Lipi one memory from Dashain.' },
      { np: 'तिहार', en: 'festival of lights', hint: 'How is Tihar different from Diwali?' },
    ],
    idiom:    [
      { np: 'हात्तीको दाँत', en: '"elephant\'s teeth" — show vs reality', hint: 'When would you use this phrase?' },
    ],
    place:    [
      { np: 'पाटन', en: 'Patan — old city near Kathmandu', hint: 'Describe Patan in one sentence.' },
    ],
  };

  const list = prompts[active] || [];
  const cat = categories.find(c => c.id === active);
  const doneCount = Object.keys(done).filter(k => k.startsWith(active + '-')).length;

  return (
    <div style={{ position: 'absolute', inset: 0, background: theme.bg, padding: '60px 0 120px', overflow: 'auto' }}>
      <StatusBar dark={theme.label === 'Ink'}/>

      {/* Header */}
      <div style={{ padding: '0 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Mono color={theme.fgMuted}>⁄ 04 · PHRASE LAB</Mono>
          <Mono color={theme.fgMuted}>{doneCount}/{list.length} TODAY</Mono>
        </div>
        <div style={{ marginTop: 14 }}>
          <Bilingual np="लिपिलाई के सिकाउने?" en="What should Lipi learn next?" size="lg" theme={theme}/>
        </div>
        <div style={{
          marginTop: 14, padding: '12px 14px', borderRadius: 12,
          background: theme.tintLavender, border: `1px solid ${theme.rule}`,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{ width: 6, height: 6, borderRadius: 999, background: theme.fg }}/>
          <Mono color={theme.fg}>BITE-SIZED · 30 SEC EACH</Mono>
        </div>
      </div>

      {/* Category strip */}
      <div style={{
        display: 'flex', gap: 8, padding: '20px 24px 4px',
        overflowX: 'auto', scrollbarWidth: 'none',
      }}>
        {categories.map(c => {
          const isActive = c.id === active;
          return (
            <button key={c.id} onClick={() => { setActive(c.id); setRecIdx(null); }} style={{
              flex: '0 0 auto', padding: '10px 14px', borderRadius: 999,
              background: isActive ? theme.accent : theme.bgCard,
              color: isActive ? theme.accentFg : theme.fg,
              border: `1px solid ${isActive ? theme.accent : theme.rule}`,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ fontFamily: FONTS.nepali, fontSize: 14 }}>{c.np}</span>
              <span style={{
                fontFamily: FONTS.mono, fontSize: 9.5, letterSpacing: '0.1em',
                opacity: 0.7,
              }}>{c.need}↓</span>
            </button>
          );
        })}
      </div>

      {/* Category meta */}
      <div style={{ padding: '12px 24px 4px', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: FONTS.sans, fontSize: 13, color: theme.fgMuted, fontStyle: 'italic' }}>
          {cat.en} — {cat.count} contributed, {cat.need} still needed
        </div>
      </div>

      {/* Prompt cards */}
      <div style={{ padding: '12px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {list.map((p, i) => {
          const k = `${active}-${i}`;
          const isDone = done[k];
          const isRec = recIdx === i;
          return (
            <div key={k} style={{
              padding: '18px 18px 16px', borderRadius: 16,
              background: isDone ? theme.tintSage : theme.bgCard,
              border: `1px solid ${isDone ? theme.tintSage : theme.rule}`,
              transition: 'all 220ms ease',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Mono color={theme.fgMuted}>PROMPT · {String(i + 1).padStart(2, '0')}</Mono>
                  <div style={{ fontFamily: FONTS.nepali, fontSize: 26, color: theme.fg, marginTop: 8, lineHeight: 1.3 }}>{p.np}</div>
                  <div style={{ fontFamily: FONTS.sans, fontSize: 12, color: theme.fgMuted, fontStyle: 'italic', marginTop: 4 }}>{p.en}</div>
                </div>
                {isDone && (
                  <div style={{
                    width: 26, height: 26, borderRadius: 999, background: theme.fg, color: theme.bg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <svg width="12" height="12" viewBox="0 0 12 12"><path d="M2 6l3 3 5-6" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                )}
              </div>

              {!isDone && (
                <>
                  <div style={{
                    marginTop: 12, padding: '10px 12px', borderRadius: 10,
                    background: theme.bg, border: `1px dashed ${theme.rule}`,
                    fontFamily: FONTS.serif, fontSize: 14, fontStyle: 'italic', color: theme.fg, lineHeight: 1.4,
                  }}>“{p.hint}”</div>

                  <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <button
                      onMouseDown={() => { setRecIdx(i); setHolding(true); }}
                      onMouseUp={() => {
                        setHolding(false);
                        setTimeout(() => { setDone(d => ({ ...d, [k]: true })); setRecIdx(null); }, 250);
                      }}
                      onMouseLeave={() => { if (isRec) { setHolding(false); setRecIdx(null); } }}
                      onTouchStart={() => { setRecIdx(i); setHolding(true); }}
                      onTouchEnd={() => {
                        setHolding(false);
                        setTimeout(() => { setDone(d => ({ ...d, [k]: true })); setRecIdx(null); }, 250);
                      }}
                      style={{
                        flex: 1, padding: '12px 16px', borderRadius: 999,
                        background: isRec && holding ? '#E85B5B' : theme.fg,
                        color: theme.bg,
                        border: 'none', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                        fontFamily: FONTS.sans, fontSize: 13, fontWeight: 500,
                        transition: 'background 160ms',
                      }}>
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <rect x="5" y="2" width="4" height="7" rx="2" stroke="currentColor" strokeWidth="1.4"/>
                        <path d="M3.5 7.5a3.5 3.5 0 007 0M7 11v2M5 13h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                      </svg>
                      {isRec && holding ? 'Recording — release to save' : 'Hold to record'}
                    </button>
                    <button onClick={() => setDone(d => ({ ...d, [k]: 'skip' }))} style={{
                      padding: '12px 14px', borderRadius: 999, background: 'transparent',
                      color: theme.fgMuted, border: `1px solid ${theme.rule}`, cursor: 'pointer',
                      fontFamily: FONTS.sans, fontSize: 12,
                    }}>Skip</button>
                  </div>

                  {isRec && holding && (
                    <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 3, height: 28 }}>
                      {[...Array(28)].map((_, w) => (
                        <div key={w} style={{
                          width: 2.5, height: `${20 + Math.sin((w + Date.now() / 100) * 0.5) * 8 * amp + Math.random() * 12 * amp}px`,
                          background: theme.fg, borderRadius: 2, opacity: 0.7,
                          transition: 'height 90ms',
                        }}/>
                      ))}
                    </div>
                  )}
                </>
              )}

              {isDone && (
                <div style={{
                  marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  paddingTop: 10, borderTop: `1px solid ${theme.rule}`,
                }}>
                  <Mono color={theme.fg}>SAVED · +25 PTS</Mono>
                  <Mono color={theme.fgMuted}>0:14 · 12 KB</Mono>
                </div>
              )}
            </div>
          );
        })}

        {/* Streak / motivator */}
        <div style={{
          marginTop: 8, padding: '20px 18px', borderRadius: 16,
          background: theme.tintButter, border: `1px solid ${theme.rule}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <Mono color={theme.fgMuted}>SESSION REWARD</Mono>
            <div style={{ fontFamily: FONTS.serif, fontSize: 22, color: theme.fg, marginTop: 6, letterSpacing: '-0.01em' }}>
              {doneCount === 0 ? 'Start with one' : doneCount < list.length ? `${list.length - doneCount} more for +200 pts` : 'Daily set complete ✓'}
            </div>
          </div>
          <div style={{ fontFamily: FONTS.serif, fontSize: 38, color: theme.fg, letterSpacing: '-0.04em' }}>
            {doneCount * 25}<span style={{ fontFamily: FONTS.mono, fontSize: 11, color: theme.fgMuted, marginLeft: 4 }}>pts</span>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, {
  AuthScreen, OnboardingScreen, HomeScreen, TeachScreen,
  HeritageScreen, RanksScreen, SettingsScreen, PhraseLabScreen,
});
