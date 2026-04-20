// app.jsx — main prototype shell. Mobile + desktop, tweaks panel, screen routing.
const { useState: uSa, useEffect: uEa } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "themeKey": "bone",
  "register": "tapai",
  "platform": "mobile",
  "orbState": "idle",
  "screen": "teach"
}/*EDITMODE-END*/;

function App() {
  // Persistence
  const load = (k, d) => {
    try { return JSON.parse(localStorage.getItem('lipi.' + k)) ?? d; } catch { return d; }
  };
  const save = (k, v) => localStorage.setItem('lipi.' + k, JSON.stringify(v));

  const [themeKey, setThemeKey]   = uSa(() => load('themeKey', TWEAK_DEFAULTS.themeKey));
  const [register, setRegister]   = uSa(() => load('register', TWEAK_DEFAULTS.register));
  const [platform, setPlatform]   = uSa(() => load('platform', TWEAK_DEFAULTS.platform));
  const [orbState, setOrbState]   = uSa(() => load('orbState', TWEAK_DEFAULTS.orbState));
  const [screen, setScreen]       = uSa(() => load('screen', TWEAK_DEFAULTS.screen));
  const [tweaksOn, setTweaksOn]   = uSa(false);

  uEa(() => save('themeKey', themeKey), [themeKey]);
  uEa(() => save('register', register), [register]);
  uEa(() => save('platform', platform), [platform]);
  uEa(() => save('orbState', orbState), [orbState]);
  uEa(() => save('screen', screen), [screen]);

  // Tweaks host contract
  uEa(() => {
    const onMsg = (e) => {
      if (e.data?.type === '__activate_edit_mode') setTweaksOn(true);
      if (e.data?.type === '__deactivate_edit_mode') setTweaksOn(false);
    };
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);

  const persistEdit = (key, value) => {
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [key]: value } }, '*');
  };

  const theme = THEMES[themeKey];
  const user = { name: 'Raj', age: 28 };

  return (
    <div style={{
      minHeight: '100vh', background: theme.label === 'Ink' ? '#050508' : '#E5E2D9',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24, position: 'relative',
      fontFamily: FONTS.sans, color: theme.fg,
      transition: 'background 400ms ease',
    }}>
      {platform === 'mobile'
        ? <MobileFrame theme={theme}>
            <ScreenRouter screen={screen} setScreen={setScreen}
              theme={theme} themeKey={themeKey} setThemeKey={setThemeKey}
              register={register} setRegister={setRegister}
              orbState={orbState} setOrbState={setOrbState}
              user={user}/>
          </MobileFrame>
        : <DesktopShell theme={theme} screen={screen} setScreen={setScreen}
            themeKey={themeKey} setThemeKey={setThemeKey}
            register={register} setRegister={setRegister}
            orbState={orbState} setOrbState={setOrbState} user={user}/>
      }

      {tweaksOn && (
        <TweaksPanel
          themeKey={themeKey} setThemeKey={k => { setThemeKey(k); persistEdit('themeKey', k); }}
          register={register} setRegister={k => { setRegister(k); persistEdit('register', k); }}
          platform={platform} setPlatform={k => { setPlatform(k); persistEdit('platform', k); }}
          orbState={orbState} setOrbState={k => { setOrbState(k); persistEdit('orbState', k); }}
          screen={screen} setScreen={k => { setScreen(k); persistEdit('screen', k); }}
        />
      )}
    </div>
  );
}

function ScreenRouter({ screen, setScreen, theme, themeKey, setThemeKey, register, setRegister, orbState, setOrbState, user, desktop }) {
  if (screen === 'auth')     return <AuthScreen theme={theme} onContinue={() => setScreen('onboarding')}/>;
  if (screen === 'onboarding') return <OnboardingScreen theme={theme} onDone={() => setScreen('home')}/>;
  const main = screen === 'home'     ? <HomeScreen theme={theme} user={user} register={register} onTeach={() => setScreen('teach')}/>
            : screen === 'teach'    ? <TeachScreen theme={theme} user={user} orbState={orbState} setOrbState={setOrbState}/>
            : screen === 'phraselab' ? <PhraseLabScreen theme={theme}/>
            : screen === 'heritage' ? <HeritageScreen theme={theme}/>
            : screen === 'ranks'    ? <RanksScreen theme={theme} user={user}/>
            : screen === 'settings' ? <SettingsScreen theme={theme} themeKey={themeKey} setThemeKey={setThemeKey} register={register} setRegister={setRegister}/>
            : <HomeScreen theme={theme} user={user} register={register} onTeach={() => setScreen('teach')}/>;
  return (
    <>
      {main}
      <BottomNav tab={screen} setTab={setScreen} theme={theme}/>
    </>
  );
}

// ───────────────────── Mobile frame
function MobileFrame({ children, theme }) {
  return (
    <div data-screen-label={`LIPI Mobile`} style={{
      width: 390, height: 844, borderRadius: 54, overflow: 'hidden',
      position: 'relative', background: theme.bg,
      boxShadow: '0 60px 120px rgba(0,0,0,0.28), 0 0 0 11px #1A1A20, 0 0 0 12px #2A2A34',
    }}>
      {/* dynamic island */}
      <div style={{
        position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
        width: 120, height: 34, borderRadius: 20, background: '#000', zIndex: 200,
      }}/>
      {children}
      {/* home indicator */}
      <div style={{
        position: 'absolute', bottom: 8, left: '50%', transform: 'translateX(-50%)',
        width: 134, height: 5, borderRadius: 999,
        background: theme.label === 'Ink' ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.28)',
        zIndex: 300,
      }}/>
    </div>
  );
}

// ───────────────────── Desktop shell
function DesktopShell({ theme, screen, setScreen, themeKey, setThemeKey, register, setRegister, orbState, setOrbState, user }) {
  const items = [
    ['home', 'Home', 'घर'],
    ['teach', 'Teach', 'सिकाऊ'],
    ['phraselab', 'Phrase Lab', 'शब्द'],
    ['heritage', 'Heritage', 'सम्पदा'],
    ['ranks', 'Ranks', 'क्रम'],
    ['settings', 'Settings', 'सेटिङ'],
  ];
  return (
    <div data-screen-label="LIPI Desktop" style={{
      width: 1280, height: 800, borderRadius: 16, overflow: 'hidden',
      background: theme.bg, position: 'relative', display: 'flex',
      boxShadow: '0 40px 100px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.1)',
    }}>
      {/* window chrome */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 38,
        background: theme.bgFrost, borderBottom: `1px solid ${theme.rule}`,
        display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8, zIndex: 500,
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {['#FF5F56', '#FFBD2E', '#27C93F'].map(c => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 999, background: c }}/>
          ))}
        </div>
        <div style={{ flex: 1, textAlign: 'center' }}>
          <Mono color={theme.fgMuted}>teacher.lipi.ai</Mono>
        </div>
      </div>

      {/* Sidebar */}
      <div style={{
        width: 240, marginTop: 38, padding: '28px 20px',
        borderRight: `1px solid ${theme.rule}`, background: theme.bgCard,
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 999,
            background: `radial-gradient(circle at 30% 30%, ${theme.orbC}, ${theme.orbA} 50%, ${theme.orbB})`,
            boxShadow: `0 0 18px ${theme.orbGlow}`,
          }}/>
          <div>
            <div style={{ fontFamily: FONTS.serif, fontSize: 22, color: theme.fg, lineHeight: 1 }}>लिपि</div>
            <Mono color={theme.fgMuted}>LIPI · v1.0</Mono>
          </div>
        </div>

        {items.map(([k, en, np]) => {
          const active = screen === k;
          return (
            <button key={k} onClick={() => setScreen(k)} style={{
              textAlign: 'left', padding: '10px 12px', borderRadius: 10,
              background: active ? theme.accent : 'transparent',
              color: active ? theme.accentFg : theme.fg,
              border: 'none', cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              transition: 'all 160ms ease',
            }}>
              <div>
                <div style={{ fontFamily: FONTS.sans, fontSize: 14 }}>{en}</div>
                <div style={{ fontFamily: FONTS.nepali, fontSize: 12, opacity: 0.6, marginTop: 1 }}>{np}</div>
              </div>
              {active && <svg width="14" height="14" viewBox="0 0 14 14"><path d="M4 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/></svg>}
            </button>
          );
        })}

        <div style={{ marginTop: 'auto', paddingTop: 20, borderTop: `1px solid ${theme.rule}` }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '8px 4px' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 999, background: theme.tintLavender,
              border: `1px solid ${theme.rule}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: FONTS.serif, fontSize: 14, color: theme.fg,
            }}>{user.name[0]}</div>
            <div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 13, color: theme.fg }}>{user.name}</div>
              <Mono color={theme.fgMuted}>RANK #3 · 2,450 PTS</Mono>
            </div>
          </div>
        </div>
      </div>

      {/* Main content — we reuse mobile screens inside a framed viewport */}
      <div style={{ flex: 1, marginTop: 38, position: 'relative', background: theme.bg, overflow: 'hidden' }}>
        <DesktopContent screen={screen} theme={theme} user={user}
          themeKey={themeKey} setThemeKey={setThemeKey}
          register={register} setRegister={setRegister}
          orbState={orbState} setOrbState={setOrbState}
          setScreen={setScreen}/>
      </div>
    </div>
  );
}

function DesktopContent({ screen, theme, user, themeKey, setThemeKey, register, setRegister, orbState, setOrbState, setScreen }) {
  if (screen === 'teach') {
    return <DesktopTeach theme={theme} user={user} orbState={orbState} setOrbState={setOrbState}/>;
  }
  if (screen === 'home') {
    return <DesktopHome theme={theme} user={user} register={register} onTeach={() => setScreen('teach')}/>;
  }
  // For other screens, embed the mobile layout in a centered panel
  const inner = screen === 'heritage' ? <HeritageScreen theme={theme}/>
              : screen === 'phraselab' ? <PhraseLabScreen theme={theme}/>
              : screen === 'ranks'    ? <RanksScreen theme={theme} user={user}/>
              : screen === 'settings' ? <SettingsScreen theme={theme} themeKey={themeKey} setThemeKey={setThemeKey} register={register} setRegister={setRegister}/>
              : null;
  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 40,
    }}>
      <div style={{
        width: 480, height: '95%', position: 'relative',
        background: theme.bg, borderRadius: 24, overflow: 'hidden',
        border: `1px solid ${theme.rule}`,
      }}>{inner}</div>
    </div>
  );
}

function DesktopHome({ theme, user, register, onTeach }) {
  const hour = new Date().getHours();
  const greet = hour < 12 ? REGISTERS[register].greetingMorning : hour < 17 ? REGISTERS[register].greetingAfternoon : REGISTERS[register].greetingEvening;
  return (
    <div style={{ padding: '40px 56px', overflow: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Mono color={theme.fgMuted}>⁄ 042 · TODAY · 18 APR 2026</Mono>
          <div style={{ marginTop: 18 }}>
            <Bilingual np={`${greet}, ${user.name}${REGISTERS[register].nameSuffix}`} en="Let's keep teaching LIPI today" size="xl" theme={theme} nowrap/>
          </div>
        </div>
        <button onClick={onTeach} style={{
          padding: '14px 22px', borderRadius: 999,
          background: theme.accent, color: theme.accentFg, border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 10, fontFamily: FONTS.sans, fontSize: 14, fontWeight: 500,
        }}>Start teaching
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8m0 0L7 3m4 4L7 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, marginTop: 32 }}>
        <Card theme={theme} style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '24px 26px 4px', display: 'flex', justifyContent: 'space-between' }}>
            <Mono color={theme.fgMuted}>LIPI HAS LEARNED</Mono>
            <Mono color={theme.fgMuted}>↗ +23 TODAY</Mono>
          </div>
          <div style={{ padding: '12px 26px 22px' }}>
            <div style={{ fontFamily: FONTS.nepali, fontSize: 18, color: theme.fgMuted, lineHeight: 1.4 }}>शब्दहरू <span style={{ fontFamily: FONTS.sans, fontSize: 13, fontStyle: 'italic' }}>· words from you</span></div>
            <div style={{ fontFamily: FONTS.serif, fontSize: 144, lineHeight: 1, color: theme.fg, letterSpacing: '-0.04em', marginTop: 8 }}>389</div>
          </div>
          <svg viewBox="0 0 600 100" width="100%" height="100" preserveAspectRatio="none" style={{ marginTop: 18 }}>
            <path d="M0,80 C60,70 100,40 150,45 C210,50 240,20 290,28 C340,36 400,8 460,14 C510,20 550,4 600,10 L600,100 L0,100 Z" fill={theme.tintLavender}/>
            <path d="M0,80 C60,70 100,40 150,45 C210,50 240,20 290,28 C340,36 400,8 460,14 C510,20 550,4 600,10" fill="none" stroke={theme.fg} strokeWidth="1.2" opacity="0.7"/>
          </svg>
          <div style={{ display: 'flex', borderTop: `1px solid ${theme.rule}` }}>
            {[['47.2', 'hrs', 'Taught'], ['12', 'day', 'Streak'], ['62', 'fx', 'Corrections'], ['#3', 'rank', 'Weekly']].map((s, i, a) => (
              <div key={s[2]} style={{ flex: 1, padding: '18px 22px', borderRight: i < a.length - 1 ? `1px solid ${theme.rule}` : 'none' }}>
                <Mono color={theme.fgSubtle}>{s[2]}</Mono>
                <div style={{ fontFamily: FONTS.serif, fontSize: 30, color: theme.fg, marginTop: 4, letterSpacing: '-0.02em' }}>
                  {s[0]}<span style={{ fontSize: 13, fontFamily: FONTS.mono, color: theme.fgMuted, marginLeft: 4 }}>{s[1]}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card theme={theme}>
          <Mono color={theme.fgMuted}>⁄ WEEKLY RANK</Mono>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 16 }}>
            {[{ r: 1, n: 'Sita Sharma', p: 3200 }, { r: 2, n: 'Hari Thapa', p: 2890 }, { r: 3, n: user.name, p: 2450, you: true }, { r: 4, n: 'Maya Rai', p: 2100 }].map(r => (
              <div key={r.r} style={{
                display: 'grid', gridTemplateColumns: '28px 1fr auto', gap: 10, alignItems: 'center',
                padding: '10px 12px', borderRadius: 10,
                background: r.you ? theme.tintButter : 'transparent',
              }}>
                <Mono color={theme.fgSubtle}>{String(r.r).padStart(2, '0')}</Mono>
                <div style={{ fontFamily: FONTS.sans, fontSize: 14, color: theme.fg }}>{r.n}{r.you && ' · you'}</div>
                <div style={{ fontFamily: FONTS.mono, fontSize: 13, color: theme.fg }}>{r.p.toLocaleString()}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 28 }}>
        <Mono color={theme.fgMuted}>⁄ TODAY LIPI LEARNED · LIVE ●</Mono>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 14 }}>
          {[
            { w: 'खिचडी', tr: 'a rice-lentil dish', by: 'Sita S.', tint: 'Lavender' },
            { w: 'दसैं', tr: 'Dashain festival', by: 'Ram T.', tint: 'Butter' },
            { w: 'धन्यवाद', tr: 'thank you', by: 'You', you: true, tint: 'Sage' },
            { w: 'मिठास', tr: 'sweetness', by: 'Anjali K.', tint: 'Peach' },
          ].map((r, i) => (
            <Card key={i} theme={theme} tinted={r.tint} style={{ padding: 18 }}>
              <Mono color={theme.fgMuted}>NEW · {i + 1}/23</Mono>
              <div style={{ fontFamily: FONTS.nepali, fontSize: 28, color: theme.fg, marginTop: 10 }}>{r.w}</div>
              <div style={{ fontFamily: FONTS.sans, fontSize: 12, color: theme.fgMuted, fontStyle: 'italic', marginTop: 2 }}>{r.tr}</div>
              <div style={{ marginTop: 14, paddingTop: 10, borderTop: `1px solid ${theme.rule}`, fontFamily: FONTS.sans, fontSize: 12, color: theme.fg }}>
                {r.by}{r.you && ' ✓'}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function DesktopTeach({ theme, user, orbState, setOrbState }) {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div style={{
        position: 'absolute', top: 32, left: 56, right: 56, zIndex: 10,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{
          padding: '10px 16px', borderRadius: 999,
          background: theme.bgFrost, border: `1px solid ${theme.rule}`,
          backdropFilter: 'blur(20px)', display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 7, height: 7, borderRadius: 999,
            background: orbState === 'listening' ? '#E85B5B' : theme.fgMuted,
            animation: orbState === 'listening' ? 'pulse 1.4s ease-in-out infinite' : 'none',
          }}/>
          <Mono>{orbState}</Mono>
          <span style={{ color: theme.fgSubtle }}>·</span>
          <Mono color={theme.fgMuted}>SESSION 08:42</Mono>
        </div>
        <Mono color={theme.fgMuted}>NE · ↔ · EN</Mono>
      </div>

      <div style={{
        position: 'absolute', inset: 0, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 56,
      }}>
        <Orb state={orbState} size={380} theme={theme}/>
        <div style={{ textAlign: 'center', maxWidth: 560 }}>
          <Mono color={theme.fgMuted}>LIPI SAYS</Mono>
          <div style={{ fontFamily: FONTS.nepali, fontSize: 32, color: theme.fg, marginTop: 12, lineHeight: 1.3 }}>
            दसैं — नेपालको सबैभन्दा ठूलो पर्व, हो?
          </div>
          <div style={{ fontFamily: FONTS.sans, fontSize: 16, color: theme.fgMuted, fontStyle: 'italic', marginTop: 6 }}>
            Dashain — Nepal's biggest festival, right?
          </div>
        </div>
      </div>

      <div style={{
        position: 'absolute', bottom: 32, left: '50%', transform: 'translateX(-50%)',
        display: 'flex', gap: 12,
      }}>
        {['idle', 'listening', 'thinking', 'speaking'].map(s => (
          <button key={s} onClick={() => setOrbState(s)} style={{
            padding: '10px 16px', borderRadius: 999,
            background: orbState === s ? theme.accent : theme.bgFrost,
            color: orbState === s ? theme.accentFg : theme.fg,
            border: `1px solid ${orbState === s ? theme.accent : theme.rule}`,
            fontFamily: FONTS.mono, fontSize: 10.5, letterSpacing: '0.14em', textTransform: 'uppercase',
            cursor: 'pointer', backdropFilter: 'blur(20px)',
          }}>{s}</button>
        ))}
      </div>
    </div>
  );
}

function DesktopFrame({ children, theme }) {
  return (
    <div data-screen-label="LIPI Desktop" style={{
      width: 1280, height: 800, borderRadius: 16, overflow: 'hidden',
      background: theme.bg,
      boxShadow: '0 40px 100px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.1)',
      position: 'relative', display: 'flex',
    }}>
      {/* window chrome */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 38,
        background: theme.bgFrost, borderBottom: `1px solid ${theme.rule}`,
        display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8, zIndex: 500,
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {['#FF5F56', '#FFBD2E', '#27C93F'].map(c => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 999, background: c }}/>
          ))}
        </div>
        <div style={{ flex: 1, textAlign: 'center' }}>
          <Mono color={theme.fgMuted}>LIPI · लिपि · teacher.lipi.ai</Mono>
        </div>
      </div>

      {/* push content below chrome */}
      <div style={{ marginTop: 38, display: 'flex', width: '100%', height: 'calc(100% - 38px)' }}>
        {children}
      </div>
    </div>
  );
}

// ───────────────────── Desktop-aware screen router
// For desktop, we render a two-pane layout: sidebar nav + content.
function DesktopRouter({ screen, setScreen, theme, themeKey, setThemeKey, register, setRegister, orbState, setOrbState, user }) {
  // (We compose differently for desktop — see App above.)
  return null;
}

// ───────────────────── Tweaks Panel
function TweaksPanel({ themeKey, setThemeKey, register, setRegister, platform, setPlatform, orbState, setOrbState, screen, setScreen }) {
  return (
    <div style={{
      position: 'fixed', right: 20, bottom: 20, width: 300,
      background: '#FDFBF5', border: '1px solid rgba(0,0,0,0.12)',
      borderRadius: 20, padding: 18, zIndex: 9999,
      boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      fontFamily: FONTS.sans, color: '#141413',
    }}>
      <div style={{ fontFamily: FONTS.serif, fontSize: 20, marginBottom: 4 }}>Tweaks</div>
      <Mono color="#6E6B63" style={{ marginBottom: 14, display: 'block' }}>LIVE DESIGN CONTROLS</Mono>

      <TweakBlock label="Platform">
        {['mobile', 'desktop'].map(p => (
          <TweakChip key={p} active={platform === p} onClick={() => setPlatform(p)}>{p}</TweakChip>
        ))}
      </TweakBlock>

      <TweakBlock label="Screen">
        {['auth', 'onboarding', 'home', 'teach', 'phraselab', 'heritage', 'ranks', 'settings'].map(s => (
          <TweakChip key={s} active={screen === s} onClick={() => setScreen(s)}>{s}</TweakChip>
        ))}
      </TweakBlock>

      <TweakBlock label="Theme">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, width: '100%' }}>
          {Object.entries(THEMES).map(([k, t]) => (
            <button key={k} onClick={() => setThemeKey(k)} style={{
              padding: 6, borderRadius: 10, cursor: 'pointer',
              background: t.bgCard, border: `1.5px solid ${themeKey === k ? '#141413' : 'rgba(0,0,0,0.08)'}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
            }}>
              <div style={{
                width: 22, height: 22, borderRadius: 999,
                background: `radial-gradient(circle at 30% 30%, ${t.orbC}, ${t.orbA} 50%, ${t.orbB})`,
              }}/>
              <span style={{ fontFamily: FONTS.mono, fontSize: 8, letterSpacing: '0.1em', textTransform: 'uppercase' }}>{t.label}</span>
            </button>
          ))}
        </div>
      </TweakBlock>

      <TweakBlock label="Orb state (in Teach)">
        {['idle', 'listening', 'thinking', 'speaking'].map(s => (
          <TweakChip key={s} active={orbState === s} onClick={() => setOrbState(s)}>{s}</TweakChip>
        ))}
      </TweakBlock>

      <TweakBlock label="Register">
        {Object.entries(REGISTERS).map(([k, r]) => (
          <TweakChip key={k} active={register === k} onClick={() => setRegister(k)}>{k}</TweakChip>
        ))}
      </TweakBlock>
    </div>
  );
}

function TweakBlock({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontFamily: FONTS.mono, fontSize: 9.5, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#6E6B63', marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{children}</div>
    </div>
  );
}
function TweakChip({ children, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: '6px 10px', borderRadius: 999,
      background: active ? '#141413' : 'transparent',
      color: active ? '#FDFBF5' : '#141413',
      border: `1px solid ${active ? '#141413' : 'rgba(0,0,0,0.12)'}`,
      fontFamily: FONTS.mono, fontSize: 10, letterSpacing: '0.1em',
      textTransform: 'uppercase', cursor: 'pointer',
    }}>{children}</button>
  );
}

Object.assign(window, { App });
