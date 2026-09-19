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
  capture: {
    hook: {
      title: 'Hook 文本源',
      state: {
        idle: '未检测到',
        connecting: '正在连接',
        connected: '已连接',
      },
      lastHeard: '最后收到',
      connect: '连接',
      disconnect: '断开',
      test: '测试连接',
      advanced: '高级',
      address: 'WebSocket 地址',
      saveAndConnect: '保存并连接',
      lastError: '最近一次错误',
      helpTextractor:
        '连不上通常是因为 Textractor 还缺 WebSocket 扩展：它不随 Textractor 自带，要单独安装一次。',
      helpTextractorLink: '查看安装方法',
      helpOther: '请先启动这个工具，并打开它的 WebSocket 服务。',
      inboundHint: '也可以让 Hook 工具主动连到 ことばこ：',
      testOk: '连接正常',
      testFail: '还是连不上，按下面的说明检查一下。',
    },
  },
  errors: {},
}
