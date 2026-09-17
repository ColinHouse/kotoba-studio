"""Desktop shell: one window and a tray icon around the in-process server (issue #60).

The GUI half (pywebview/pystray) needs a real desktop session, so it lives behind
`kotoba.desktop.ui.DesktopUI`: the shell's startup order and shutdown path are
driven by fakes in the tests, and the real window is only ever opened by hand.
"""
