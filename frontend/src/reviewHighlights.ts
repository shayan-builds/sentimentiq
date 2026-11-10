import type { AspectResult } from './api'

export interface ReviewSegment {
  text: string
  highlighted: boolean
}

/**
 * Highlight only aspect offsets that point to their exact mention in the
 * submitted text. API offsets are zero-based Unicode code-point offsets,
 * while JavaScript string slices use UTF-16 code units. Invalid, stale, and
 * overlapping spans are omitted rather than guessed.
 */
export function buildReviewSegments(
  text: string,
  aspects: readonly AspectResult[],
): ReviewSegment[] {
  const codePointToCodeUnit = [0]
  let codeUnitOffset = 0
  for (const codePoint of text) {
    codeUnitOffset += codePoint.length
    codePointToCodeUnit.push(codeUnitOffset)
  }

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
        end >= codePointToCodeUnit.length ||
        !aspect.aspect_text ||
        text
          .slice(codePointToCodeUnit[start], codePointToCodeUnit[end])
          .toLowerCase() !== aspect.aspect_text.toLowerCase()
      ) {
        return []
      }
      return [{ start: codePointToCodeUnit[start], end: codePointToCodeUnit[end] }]
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
