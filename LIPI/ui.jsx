// ui.jsx — shared primitives: mono labels, bilingual text, cards, buttons, bottom nav

const { useState: useState_ui, useEffect: useEffect_ui } = React;

// Mono caption used everywhere for labels, numerals, metadata
function Mono({ children, style = {}, color }) {
  return <span style={{
    fontFamily: FONTS.mono, fontSize: 10.5, letterSpacing: '0.14em',
    textTransform: 'uppercase', color: color || 'currentColor',
    fontWeight: 500, ...style,
  }}>{children}</span>;
}

// Numbered section marker: ⁄ 01
function SectionNumber({ n, style = {} }) {
  return <span style={{
    fontFamily: FONTS.mono, fontSize: 10.5, letterSpacing: '0.12em',
    opacity: 0.5, ...style,
  }}>⁄ {String(n).padStart(2, '0')}</span>;
}

// Bilingual: Nepali primary (serif, large), English secondary (sans, small muted)
function Bilingual({ np, en, size = 'md', align = 'left', theme, nowrap }) {
  const sizes = {
    xl: { np: 40, en: 15, gap: 10 },
    lg: { np: 28, en: 14, gap: 8 },
    md: { np: 20, en: 13, gap: 6 },
    sm: { np: 15, en: 11, gap: 4 },
  }[size];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: sizes.gap, textAlign: align }}>
      <div style={{
        fontFamily: FONTS.nepali, fontSize: sizes.np, color: theme.fg,
        lineHeight: 1.5, fontWeight: 400, letterSpacing: '-0.01em',
        whiteSpace: nowrap ? 'nowrap' : 'normal',
      }}>{np}</div>
      <div style={{
        fontFamily: FONTS.sans, fontSize: sizes.en, color: theme.fgMuted,
        lineHeight: 1.4, fontWeight: 400, fontStyle: 'italic',
      }}>{en}</div>
    </div>
  );
}

// Hairline divider
function Rule({ theme, soft, style = {} }) {
  return <div style={{
    height: 1, background: soft ? theme.ruleSoft : theme.rule,
    width: '100%', ...style,
  }} />;
}

// Primary CTA — pill
function PillButton({ children, onClick, theme, variant = 'primary', full, style = {}, small }) {
  const isPrim = variant === 'primary';
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      padding: small ? '10px 18px' : '14px 26px',
      background: isPrim ? theme.accent : 'transparent',
      color: isPrim ? theme.accentFg : theme.fg,
      border: isPrim ? 'none' : `1px solid ${theme.rule}`,
      borderRadius: 999,
      fontFamily: FONTS.sans, fontSize: small ? 13 : 14, fontWeight: 500,
      letterSpacing: '-0.005em',
      width: full ? '100%' : 'auto',
      cursor: 'pointer',
      transition: 'all 180ms ease',
      ...style,
    }}
    onMouseOver={e => e.currentTarget.style.transform = 'translateY(-1px)'}
    onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}
    >{children}</button>
  );
}

// Card
function Card({ children, theme, style = {}, tinted, frost, onClick }) {
  const bg = tinted ? theme[`tint${tinted}`] : (frost ? theme.bgFrost : theme.bgCard);
  return <div onClick={onClick} style={{
    background: bg,
    border: `1px solid ${theme.rule}`,
    borderRadius: 24,
    padding: 24,
    backdropFilter: frost ? 'blur(20px)' : undefined,
    cursor: onClick ? 'pointer' : 'default',
    transition: 'transform 220ms ease, box-shadow 220ms ease',
    ...style,
  }}
  onMouseOver={onClick ? e => { e.currentTarget.style.transform = 'translateY(-2px)'; } : undefined}
  onMouseOut={onClick ? e => { e.currentTarget.style.transform = 'translateY(0)'; } : undefined}
  >{children}</div>;
}

// Bottom tab nav for mobile
function BottomNav({ tab, setTab, theme }) {
  const tabs = [
    { id: 'home',     np: 'घर',     en: 'Home',       icon: iconHome },
    { id: 'teach',    np: 'सिकाऊ',  en: 'Teach',      icon: iconMic },
    { id: 'phraselab',np: 'शब्द',    en: 'Lab',        icon: iconBeaker },
    { id: 'heritage', np: 'सम्पदा', en: 'Heritage',   icon: iconBook },
    { id: 'ranks',    np: 'क्रम',   en: 'Ranks',      icon: iconAward },
  ];
  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0,
      padding: '10px 12px 34px',
      background: theme.bgFrost,
      backdropFilter: 'blur(24px) saturate(180%)',
      WebkitBackdropFilter: 'blur(24px) saturate(180%)',
      borderTop: `1px solid ${theme.rule}`,
      display: 'flex', justifyContent: 'space-around',
      zIndex: 40,
    }}>
      {tabs.map(t => {
        const active = tab === t.id;
        return (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
            padding: '6px 10px', background: 'transparent', border: 'none',
            color: active ? theme.fg : theme.fgSubtle,
            cursor: 'pointer', transition: 'color 180ms ease',
          }}>
            {t.icon(active ? theme.fg : theme.fgSubtle, active)}
            <span style={{
              fontFamily: FONTS.mono, fontSize: 9, letterSpacing: '0.12em',
              textTransform: 'uppercase', marginTop: 1,
            }}>{t.en}</span>
          </button>
        );
      })}
    </div>
  );
}

// Icons — minimal line style
const iconHome = (c) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M3 8.5L10 3l7 5.5V16a1 1 0 01-1 1h-4v-5H8v5H4a1 1 0 01-1-1V8.5z"
      stroke={c} strokeWidth="1.3" strokeLinejoin="round"/>
  </svg>
);
const iconMic = (c, active) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <rect x="7.5" y="2.5" width="5" height="9" rx="2.5" stroke={c} strokeWidth="1.3"/>
    <path d="M4.5 9.5a5.5 5.5 0 0011 0M10 14.5v3M7 17.5h6" stroke={c} strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
);
const iconBook = (c) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M3.5 3.5h5a2 2 0 012 2V17a2 2 0 00-2-2h-5V3.5zM16.5 3.5h-5a2 2 0 00-2 2V17a2 2 0 012-2h5V3.5z"
      stroke={c} strokeWidth="1.3" strokeLinejoin="round"/>
  </svg>
);
const iconBeaker = (c) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M8 2.5h4M8.5 2.5v5L4.5 15a1.5 1.5 0 001.3 2.3h8.4A1.5 1.5 0 0015.5 15l-4-7.5v-5"
      stroke={c} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="9" cy="13" r="0.8" fill={c}/>
    <circle cx="11.5" cy="14.5" r="0.6" fill={c}/>
  </svg>
);
const iconAward = (c) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <circle cx="10" cy="8" r="5" stroke={c} strokeWidth="1.3"/>
    <path d="M7 12.5L5.5 17l4.5-2 4.5 2-1.5-4.5" stroke={c} strokeWidth="1.3" strokeLinejoin="round"/>
  </svg>
);
const iconGear = (c) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <circle cx="10" cy="10" r="2.5" stroke={c} strokeWidth="1.3"/>
    <path d="M10 2.5v2M10 15.5v2M2.5 10h2M15.5 10h2M4.7 4.7l1.4 1.4M13.9 13.9l1.4 1.4M4.7 15.3l1.4-1.4M13.9 6.1l1.4-1.4"
      stroke={c} strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
);

// Chip
function Chip({ children, theme, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '10px 16px',
      background: active ? theme.accent : 'transparent',
      color: active ? theme.accentFg : theme.fg,
      border: `1px solid ${active ? theme.accent : theme.rule}`,
      borderRadius: 999,
      fontFamily: FONTS.sans, fontSize: 13, fontWeight: 450,
      cursor: 'pointer', transition: 'all 180ms ease',
    }}>{children}</button>
  );
}

// Status bar for iOS
function StatusBar({ dark, time = '9:41' }) {
  const c = dark ? '#F2F0E8' : '#141413';
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0,
      height: 50, display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', padding: '14px 28px 0',
      pointerEvents: 'none', zIndex: 100,
    }}>
      <span style={{ fontFamily: FONTS.sans, fontSize: 15, fontWeight: 600, color: c }}>{time}</span>
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <svg width="17" height="11" viewBox="0 0 17 11" fill={c}>
          <rect x="0" y="7" width="3" height="4" rx="0.6"/>
          <rect x="4.5" y="5" width="3" height="6" rx="0.6"/>
          <rect x="9" y="2.5" width="3" height="8.5" rx="0.6"/>
          <rect x="13.5" y="0" width="3" height="11" rx="0.6"/>
        </svg>
        <svg width="24" height="11" viewBox="0 0 24 11" fill="none">
          <rect x="0.5" y="0.5" width="20" height="10" rx="3" stroke={c} strokeOpacity="0.4"/>
          <rect x="2" y="2" width="17" height="7" rx="1.5" fill={c}/>
          <path d="M22 4v3a1.2 1.2 0 000-3z" fill={c} fillOpacity="0.5"/>
        </svg>
      </div>
    </div>
  );
}

Object.assign(window, {
  Mono, SectionNumber, Bilingual, Rule, PillButton, Card, BottomNav, Chip, StatusBar,
});
