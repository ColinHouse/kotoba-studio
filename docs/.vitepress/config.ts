import { defineConfig } from 'vitepress'

// The site is served from https://colinhouse.github.io/kotoba-studio/, so every
// absolute asset path carries that prefix. It lives here alone: moving to a custom
// domain later is this one line plus a CNAME file in docs/public/.
const BASE = '/kotoba-studio/'

export default defineConfig({
  base: BASE,
  lang: 'zh-CN',
  title: 'Kotoba Studio',
  description: '会记住语境的日语伴读工具',
  cleanUrls: true,
  lastUpdated: true,

  // node_modules lives inside docs/ because the docs toolchain is self-contained;
  // without this VitePress would try to render every README it finds in there.
  srcExclude: ['**/node_modules/**'],

  head: [
    ['link', { rel: 'icon', href: `${BASE}favicon.png`, sizes: '32x32' }],
    ['meta', { name: 'theme-color', content: '#fcf1eb' }],
  ],

  themeConfig: {
    logo: '/mascot.png',

    nav: [
      { text: '安装', link: '/install' },
      { text: '使用', link: '/guide' },
      { text: '集成', link: '/integrations' },
      { text: '开发', link: '/architecture' },
      {
        text: '下载',
        link: 'https://github.com/ColinHouse/kotoba-studio/releases/latest',
      },
    ],

    sidebar: [
      {
        text: '开始',
        items: [
          { text: '安装', link: '/install' },
          { text: '头三件事', link: '/guide' },
          { text: '手机复习', link: '/mobile' },
          { text: '平台说明', link: '/platforms' },
        ],
      },
      {
        text: '集成',
        items: [
          { text: 'Hook 与导入导出', link: '/integrations' },
        ],
      },
      {
        text: '开发',
        items: [
          { text: '架构', link: '/architecture' },
          { text: '代码约定', link: '/conventions' },
          { text: '代码签名', link: '/CODE_SIGNING' },
          { text: '路线图', link: '/roadmap' },
        ],
      },
      {
        text: '决策记录',
        collapsed: true,
        items: [
          { text: '0001 技术栈', link: '/adr/0001-tech-stack' },
          { text: '0002 许可证', link: '/adr/0002-license' },
          { text: '0003 内容定位', link: '/adr/0003-content-locator' },
          { text: '0004 离线同步', link: '/adr/0004-offline-sync' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ColinHouse/kotoba-studio' },
    ],

    editLink: {
      pattern: 'https://github.com/ColinHouse/kotoba-studio/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页',
    },

    search: { provider: 'local' },

    outline: { label: '本页目录', level: [2, 3] },
    docFooter: { prev: '上一页', next: '下一页' },
    lastUpdatedText: '最后更新',
    darkModeSwitchLabel: '主题',
    returnToTopLabel: '回到顶部',

    footer: {
      message:
        '代码 AGPL-3.0-or-later · 词典数据 © EDRDG，CC BY-SA 4.0',
      copyright: 'Kotoba Studio',
    },
  },
})
