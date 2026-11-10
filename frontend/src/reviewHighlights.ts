import type { AspectResult } from './api'

export interface ReviewSegment {
  text: string
  highlighted: boolean
}

/**
 * Highlight only aspect offsets that point to their exact mention in the
 * submitted JavaScript string. Offsets are zero-based and end-exclusive.
 * Invalid, stale, and overlapping spans are omitted rather than guessed.
 */
export function buildReviewSegments(
  text: string,
  aspects: readonly AspectResult[],
): ReviewSegment[] {
  const spans = aspects
    .flatMap((aspect) => {
      const { start_offset: start, end_offset: end } = aspect
      if (
        typeof start !== 'number' ||
        typeof end !== 'number' ||
        !Number.isFinite(start) ||
        !Number.isInteger(start) ||
        !Number.isFinite(end) ||
        !Number.isInteger(end) ||
        start < 0 ||
        start >= end ||
        end > text.length ||
        !aspect.aspect_text ||
        text.slice(start, end).toLowerCase() !== aspect.aspect_text.toLowerCase()
      ) {
        return []
      }
      return [{ start, end }]
    })
    .sort((left, right) => left.start - right.start || left.end - right.end)

  const segments: ReviewSegment[] = []
  let cursor = 0

  for (const span of spans) {
    if (span.start < cursor) continue
    if (span.start > cursor) {
      segments.push({ text: text.slice(cursor, span.start), highlighted: false })
    }
    segments.push({ text: text.slice(span.start, span.end), highlighted: true })
    cursor = span.end
  }

  if (cursor < text.length || segments.length === 0) {
    segments.push({ text: text.slice(cursor), highlighted: false })
  }

  return segments
}
