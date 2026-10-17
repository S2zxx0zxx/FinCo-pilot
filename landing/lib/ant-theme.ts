/** Shared by Ant static CSS generation and the public runtime. */
export const marketingTheme = {
  cssVar: { key: 'finco-marketing' },
  hashed: false,
  zeroRuntime: true,
  token: {
    colorPrimary: '#165dff',
    colorInfo: '#165dff',
    colorText: '#17212e',
    colorTextSecondary: '#536171',
    colorTextDescription: '#536171',
    colorTextTertiary: '#536171',
    colorBorder: '#cdd5df',
    colorBorderSecondary: '#e1e6ed',
    colorBgLayout: '#f5f7fa',
    borderRadius: 12,
    fontSize: 16,
    fontFamily: 'var(--font-finco), system-ui, sans-serif',
    controlHeight: 44,
    motionDurationSlow: '0.24s',
  },
  components: {
    Button: {
      fontWeight: 600,
      primaryShadow: 'none',
      controlHeightLG: 50,
    },
    Card: { paddingLG: 28, headerFontSize: 18 },
    Tabs: { horizontalItemGutter: 28, titleFontSize: 16 },
    Collapse: { headerBg: '#ffffff', contentBg: '#ffffff' },
  },
}
