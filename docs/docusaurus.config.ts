import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const GITHUB_URL = 'https://github.com/bank2ai/bank2ai';
const EDIT_URL = `${GITHUB_URL}/edit/main/docs/`;

const config: Config = {
  title: 'bank2ai',
  tagline: 'The open standard for AI driven banking',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://bank2ai.com',
  baseUrl: '/',

  organizationName: 'bancony',
  projectName: 'bank2ai',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          editUrl: EDIT_URL,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      logo: {
        alt: 'bank2ai',
        src: 'img/logo.svg',
        srcDark: 'img/logo-dark.svg',
        width: 130,
        height: 30,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/specification/overview',
          label: 'Spec',
          position: 'left',
        },
        {
          to: '/docs/marketplace/overview',
          label: 'Marketplace',
          position: 'left',
        },
        {
          to: '/docs/enterprise/overview',
          label: 'Enterprise',
          position: 'left',
        },
        {
          href: GITHUB_URL,
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'bank2ai',
          items: [
            {label: 'Welcome', to: '/docs/getting-started/welcome'},
            {label: 'Quickstart', to: '/docs/getting-started/quickstart'},
            {label: 'Specification', to: '/docs/specification/overview'},
            {label: 'Marketplace', to: '/docs/marketplace/overview'},
          ],
        },
        {
          title: 'Bancony',
          items: [
            {label: 'Bancony', href: 'https://bancony.com'},
            {label: 'Enterprise overview', to: '/docs/enterprise/overview'},
            {label: 'Get in touch', to: '/docs/enterprise/contact'},
          ],
        },
        {
          title: 'Community',
          items: [
            {label: 'GitHub', href: GITHUB_URL},
            {label: 'Issues', href: `${GITHUB_URL}/issues`},
            {label: 'Contributing', to: '/docs/resources/contributing'},
          ],
        },
      ],
      copyright: `Bank2ai is an open standard stewarded by Bancony. © ${new Date().getFullYear()} Bancony.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
