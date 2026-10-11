import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Context — スキル活用ガイド',
  tagline: '目的からスキルを選び、成果物を確かめる',
  url: 'https://yukihito-jokyu.github.io',
  baseUrl: '/context/',
  organizationName: 'yukihito-jokyu',
  projectName: 'context',
  trailingSlash: true,
  staticDirectories: ['docs/artifacts'],
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  onDuplicateRoutes: 'throw',
  markdown: {
    format: 'md',
    mermaid: true,
    hooks: {onBrokenMarkdownLinks: 'throw', onBrokenMarkdownImages: 'throw'},
  },
  i18n: {defaultLocale: 'ja', locales: ['ja']},
  presets: [['classic', {
    docs: {
      path: 'docs',
      exclude: ['artifacts/**'],
      routeBasePath: '/',
      sidebarPath: './sidebars.ts',
      editUrl: 'https://github.com/yukihito-jokyu/context/edit/main/',
    },
    blog: false,
    theme: {customCss: './src/css/custom.css'},
  } satisfies Preset.Options]],
  themes: ['@docusaurus/theme-mermaid'],
  plugins: ['./plugins/site-search'],
  themeConfig: {
    colorMode: {respectPrefersColorScheme: true},
    navbar: {
      title: 'Context',
      items: [
        {type: 'docSidebar', sidebarId: 'guideSidebar', label: 'スキル活用ガイド', position: 'left'},
        {href: 'https://github.com/yukihito-jokyu/context', label: 'GitHub', position: 'right'},
      ],
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula},
    footer: {style: 'dark', copyright: 'Context Repository · スキルの正本はGitHubで管理しています。'},
  } satisfies Preset.ThemeConfig,
};
export default config;
