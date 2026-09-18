import type { Messages } from './types'

/**
 * zh-CN 是事实基准：这里的中文就是今天界面上的中文，逐字搬过来。
 * 改动这里之前先读 docs/conventions.md 的 i18n 约定。
 */
export const zhCN: Messages = {
  nav: {
    home: '首页',
    capture: '采集',
    inbox: '收件箱',
    review: '复习',
    stats: '统计',
    library: '词库',
    kanji: '汉字',
    sources: '作品',
    settings: '设置',
  },
  shell: {
    tagline: '会记住语境的伴读',
    activeSession: '进行中的会话',
    noSource: '未指定作品',
    lines: '句',
    offline: '无法连接 ことばこ 服务器。请确认桌面端正在运行，手机需与电脑在同一局域网。',
  },
  settings: {
    language: {
      title: '语言 / Language',
      zh: '简体中文',
      en: 'English',
    },
  },
  errors: {},
}
