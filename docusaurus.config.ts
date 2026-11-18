import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import fs from 'node:fs';
import path from 'node:path';

// Serve the skill's own catalog pages from the canonical source without keeping a copy in docs/.
const motionCatalog = 'utils/skills/design/motion-catalog';
function motionCatalogPlugin() {
  return {
    name: 'motion-catalog-pages',
    async postBuild({outDir}: {outDir: string}) {
      const dest = path.join(outDir, 'catalogs/motion-catalog');
      for (const entry of ['catalog.html', 'shared', 'animations']) {
        fs.cpSync(path.join(motionCatalog, entry), path.join(dest, entry), {recursive: true});
      }
    },
  };
}

const config: Config = {
  title: 'Context — Skill・plugin活用ガイド',
  tagline: 'Skill・pluginを導入し、成果物を確かめる',
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
  plugins: ['./plugins/site-search', motionCatalogPlugin],
  themeConfig: {
    colorMode: {respectPrefersColorScheme: true},
    navbar: {
      title: 'Context',
      items: [
        {type: 'docSidebar', sidebarId: 'guideSidebar', label: '活用ガイド', position: 'left'},
        {href: 'https://github.com/yukihito-jokyu/context', label: 'GitHub', position: 'right'},
      ],
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula},
    footer: {style: 'dark', copyright: 'Context Repository · スキルの正本はGitHubで管理しています。'},
  } satisfies Preset.ThemeConfig,
};
export default config;
