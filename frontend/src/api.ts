export type Domain = 'product' | 'campus'
export type SentimentLabel = 'positive' | 'negative' | 'neutral' | 'mixed'
export type ConfidenceKind = 'raw_score' | 'calibrated_probability'

export interface SentimentValue {
  sentiment_label: SentimentLabel
  sentiment_score: number
  confidence_value: number
  confidence_kind: ConfidenceKind
}

export interface AspectResult extends SentimentValue {
  aspect_text: string
  aspect_category: string | null
  start_offset: number | null
  end_offset: number | null
}

export interface AnalysisResult {
  overall: SentimentValue
  aspects: AspectResult[]
}

export interface AnalysisError {
  code: string
  message: string
}

export interface BatchOutcome {
  input_index: number
  status: 'succeeded' | 'failed'
  result: AnalysisResult | null
  error: AnalysisError | null
}

export interface AnalyzeRequest {
  text: string
  domain: Domain
}

export interface BatchAnalyzeRequest {
  texts: string[]
  domain: Domain
}

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_URL?.trim() || 'http://localhost:8000').replace(
  /\/+$/,
  '',
)

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSentiment(value: unknown): value is SentimentValue {
  if (!isRecord(value)) return false
  return (
    ['positive', 'negative', 'neutral', 'mixed'].includes(String(value.sentiment_label)) &&
    typeof value.sentiment_score === 'number' &&
    Number.isFinite(value.sentiment_score) &&
    value.sentiment_score >= -1 &&
    value.sentiment_score <= 1 &&
    typeof value.confidence_value === 'number' &&
    Number.isFinite(value.confidence_value) &&
    value.confidence_value >= 0 &&
    value.confidence_value <= 1 &&
    ['raw_score', 'calibrated_probability'].includes(String(value.confidence_kind))
  )
}

function isAspect(value: unknown): value is AspectResult {
  if (!isRecord(value) || !isSentiment(value)) return false
  const start = value.start_offset
  const end = value.end_offset
  const validOffsets =
    (start === null && end === null) ||
    (typeof start === 'number' &&
      Number.isInteger(start) &&
      start >= 0 &&
      typeof end === 'number' &&
      Number.isInteger(end) &&
      end > start)
  return (
    typeof value.aspect_text === 'string' &&
    value.aspect_text.length > 0 &&
    (typeof value.aspect_category === 'string' || value.aspect_category === null) &&
    validOffsets
  )
}

function isAnalysisResult(value: unknown): value is AnalysisResult {
  return (
    isRecord(value) &&
    isSentiment(value.overall) &&
    Array.isArray(value.aspects) &&
    value.aspects.every(isAspect)
  )
}

function isBatchOutcome(value: unknown): value is BatchOutcome {
  if (!isRecord(value) || !Number.isInteger(value.input_index) || Number(value.input_index) < 0) {
    return false
  }
  if (value.status === 'succeeded') {
    return value.error === null && isAnalysisResult(value.result)
  }
  if (value.status === 'failed') {
    return (
      value.result === null &&
      isRecord(value.error) &&
      typeof value.error.code === 'string' &&
      typeof value.error.message === 'string'
    )
  }
  return false
}

function describeApiError(body: unknown, status: number): string {
  if (isRecord(body)) {
    const detail = body.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => {
        if (!isRecord(item) || typeof item.msg !== 'string') return []
        const location = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : ''
        return [location ? `${location}: ${item.msg}` : item.msg]
      })
      if (messages.length) return messages.join(' · ')
    }
    if (typeof body.message === 'string') return body.message
  }
  return `The API request failed with status ${status}.`
}

async function postJson(path: string, payload: unknown): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new ApiError('Could not reach the SentimentIQ API. Check the API URL and try again.')
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    if (!response.ok) throw new ApiError(`The API request failed with status ${response.status}.`, response.status)
    throw new ApiError('The API returned an unreadable response.', response.status)
  }
  if (!response.ok) throw new ApiError(describeApiError(body, response.status), response.status)
  return body
}

export async function analyzeReview(request: AnalyzeRequest): Promise<AnalysisResult> {
  const response = await postJson('/api/v1/analyze', request)
  if (!isAnalysisResult(response)) {
    throw new ApiError('The API returned an invalid single-analysis response.')
  }
  return response
}

export async function analyzeBatch(request: BatchAnalyzeRequest): Promise<BatchOutcome[]> {
  const response = await postJson('/api/v1/analyze/batch', request)
  if (
    !Array.isArray(response) ||
    response.length !== request.texts.length ||
    !response.every(isBatchOutcome) ||
    response.some((outcome, index) => outcome.input_index !== index)
  ) {
    throw new ApiError('The API returned an invalid batch-analysis response.')
  }
  return response
}
