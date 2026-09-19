import type { ErrorCode } from './errors'
import type { Messages } from './types'

/**
 * English. `errors` covers every code the backend can send; where the code is
 * known but the value that produced the message is not (53 raise sites put one
 * into the text), the sentence stays general on purpose — the message-envelope
 * `params` field that would fix this is deliberately not added yet.
 */
export const en: Messages & { errors: Record<ErrorCode, string> } = {
  nav: {
    home: 'Home',
    capture: 'Capture',
    inbox: 'Inbox',
    review: 'Review',
    stats: 'Stats',
    library: 'Library',
    kanji: 'Kanji',
    sources: 'Sources',
    settings: 'Settings',
  },
  shell: {
    tagline: 'A reading companion that remembers context',
    activeSession: 'Session in progress',
    noSource: 'No source selected',
    lines: 'lines',
    offline:
      'Cannot reach the ことばこ server. Make sure the desktop app is running; the phone must be on the same network.',
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
      title: 'Hook text source',
      state: {
        idle: 'Not detected',
        connecting: 'Connecting',
        connected: 'Connected',
      },
      lastHeard: 'Last heard',
      connect: 'Connect',
      disconnect: 'Disconnect',
      test: 'Test connection',
      advanced: 'Advanced',
      address: 'WebSocket address',
      saveAndConnect: 'Save and connect',
      lastError: 'Last error',
      helpTextractor:
        'The usual cause is the missing WebSocket extension: Textractor does not ship one, so it has to be installed separately.',
      helpTextractorLink: 'How to install it',
      helpOther: 'Start the tool first and turn on its WebSocket server.',
      inboundHint: 'Hook tools can also connect to Kotobako themselves:',
      testOk: 'The connection works',
      testFail: 'Still cannot connect — check the steps below.',
      idleHint: 'This game may not be hookable — screen recognition still works.',
      idleHintLink: 'Use screen recognition →',
    },
    source: {
      title: 'Text source',
      recommended: 'Recommended',
      prefer: 'Prefer this',
      hookTitle: 'Hook text source',
      hookReason:
        'Text is read straight from the game memory, with no recognition error; not every game can be hooked.',
      hookLink: 'Connect a hook tool →',
      ocrTitle: 'Screen recognition (OCR)',
      ocrReason:
        'It reads whatever is visible on screen — the fallback for games that cannot be hooked.',
      ocrLink: 'Use screen recognition →',
    },
    ocr: {
      result: 'OCR result',
      copied: 'Copied',
      copyHint: 'Click a box to copy that block of text',
      noBlocks: 'This engine returns one block of text and no per-block boxes.',
      noImage: 'No screenshot is available to draw the boxes on; showing the plain text.',
    },
  },
  errors: {
    ai_failed: 'The AI explanation failed. You can retry, or keep working without it.',
    anki_error: 'AnkiConnect reported an error. Check that Anki is running with the add-on.',
    bad_dictionary: 'This dictionary file is not in the expected format.',
    bad_encoding: 'The file could not be decoded as text.',
    bad_epub: 'This EPUB could not be parsed.',
    bad_import: 'The import could not be read. Check the file and try again.',
    bad_mokuro: 'This .mokuro file is not in the expected format.',
    bad_subtitle: 'No dialogue could be read from this subtitle file.',
    buffer_miss: 'That moment is no longer in the rolling buffer, so no screenshot could be added.',
    busy: 'Another job is running. Try again when it finishes.',
    capture_failed: 'The screen capture failed.',
    capture_paused: 'Capture is paused while a restore finishes.',
    capture_unavailable: 'Screen capture is not available on this system.',
    database_busy: 'The database is busy (a dictionary import?). Try again in a moment.',
    database_error: 'The database operation failed.',
    device_required: 'This request needs a registered device.',
    empty_text: 'There is no text to save after normalization.',
    ffmpeg_unavailable: 'ffmpeg was not found. Install it to use audio and video features.',
    http_error: 'The request was rejected by the server.',
    invalid_backup: 'This backup file cannot be used.',
    invalid_card_type: 'Unknown card type.',
    invalid_kind: 'Unknown source kind.',
    invalid_mode: 'Unknown session or review mode.',
    invalid_rating: 'The rating must be 1 (Again) to 4 (Easy).',
    invalid_region: 'That screen region is not valid.',
    invalid_status: 'Unknown status.',
    invalid_term: 'That term could not be found.',
    invalid_value: 'A value in the request is not acceptable.',
    method_not_allowed: 'That action is not allowed here.',
    network: 'Cannot reach the server.',
    no_line: 'That line no longer exists.',
    no_timeline: 'This work has no lines with timing yet.',
    not_found: 'Not found.',
    nothing_to_export: 'There is nothing to export yet.',
    ocr_failed: 'The OCR engine failed on this image.',
    ocr_unavailable:
      'No OCR engine is available. Install the Japanese language pack, or the ocr-onnx extra (RapidOCR).',
    restoring: 'A backup is being restored. Try again when it finishes.',
    too_many: 'Too many items in one request.',
    unknown_device: 'That device is not registered.',
    unknown_hook: 'Unknown hook tool.',
    unknown_setting: 'Unknown setting.',
    validation_error: 'The request was not valid.',
    video_not_found: 'The video file could not be found.',
  },
}
