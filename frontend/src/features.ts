/**
 * Switches for work that exists but is not offered to users yet.
 *
 * A flag rather than deleted markup: these paths work, they are just not ready to
 * be supported. Deleting them would mean rewriting the same screens to bring them
 * back, and would leave the components behind as orphans nobody dares touch.
 */

/**
 * Screen capture as a text source.
 *
 * Off for the first release. OCR needs a capture experience that does not exist
 * yet (#179) and accuracy work that has not happened; shipping it in its current
 * state would make the whole application look unreliable. The hook sources
 * (Textractor / Agent / LunaTranslator, or Textractor's clipboard output) are what
 * v1 supports.
 *
 * Nothing on the backend is disabled: the engines, the endpoints and the lines
 * already captured through OCR all keep working. Turning this back on is this one
 * line -- see #192 for what should be true before it is.
 */
export const OCR_ENABLED = false
