/**
 * Whether new content should pull the viewport along.
 *
 * A capture session can run for hours; if the user scrolled up to read an
 * earlier line, a new line must not yank them back to the bottom. Only when the
 * viewport is already at (or very near) the bottom does following make sense.
 */
export const FOLLOW_TOLERANCE_PX = 48

export function followsNewest(
  scrollTop: number,
  clientHeight: number,
  scrollHeight: number,
  tolerance: number = FOLLOW_TOLERANCE_PX,
): boolean {
  return scrollHeight - scrollTop - clientHeight <= tolerance
}
