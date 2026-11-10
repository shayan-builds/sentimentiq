import { useState, type FormEvent } from 'react'
import {
  analyzeBatch,
  analyzeReview,
  type AnalysisResult,
  type AspectResult,
  type BatchOutcome,
  type Domain,
  type SentimentLabel,
  type SentimentValue,
} from './api'

type Mode = 'single' | 'batch'

const MAX_TEXT_LENGTH = 10_000
const MAX_BATCH_SIZE = 100

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  )
}

function App() {
  const [domain, setDomain] = useState<Domain>('product')
  const [mode, setMode] = useState<Mode>('single')
  const [singleText, setSingleText] = useState('')
  const [batchText, setBatchText] = useState('')
  const [singleResult, setSingleResult] = useState<AnalysisResult | null>(null)
  const [batchResults, setBatchResults] = useState<BatchOutcome[] | null>(null)
  const [submittedReviews, setSubmittedReviews] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const batchReviews = batchText
    .split(/\r?\n/)
    .map((review) => review.trim())
    .filter(Boolean)

  function resetResults() {
    setSingleResult(null)
    setBatchResults(null)
    setSubmittedReviews([])
    setError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    resetResults()

    if (mode === 'single') {
      const review = singleText.trim()
      if (!review) {
        setError('Enter a review before starting the analysis.')
        return
      }
      if (review.length > MAX_TEXT_LENGTH) {
        setError(`Reviews must be ${MAX_TEXT_LENGTH.toLocaleString()} characters or fewer.`)
        return
      }
      setLoading(true)
      try {
        setSingleResult(await analyzeReview({ text: review, domain }))
        setSubmittedReviews([review])
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : 'Analysis could not be completed.')
      } finally {
        setLoading(false)
      }
      return
    }

    if (batchReviews.length === 0) {
      setError('Add at least one review, with each review on its own line.')
      return
    }
    if (batchReviews.length > MAX_BATCH_SIZE) {
      setError(`A batch can contain at most ${MAX_BATCH_SIZE} reviews.`)
      return
    }
    const oversizedReview = batchReviews.findIndex((review) => review.length > MAX_TEXT_LENGTH)
    if (oversizedReview >= 0) {
      setError(`Review ${oversizedReview + 1} exceeds ${MAX_TEXT_LENGTH.toLocaleString()} characters.`)
      return
    }

    setLoading(true)
    try {
      setBatchResults(await analyzeBatch({ texts: batchReviews, domain }))
      setSubmittedReviews(batchReviews)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Batch analysis could not be completed.')
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = mode === 'single' ? Boolean(singleText.trim()) : batchReviews.length > 0

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#main" aria-label="SentimentIQ home">
          <BrandMark />
          <span>Sentiment<span className="brand-light">IQ</span></span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>
        <nav className="primary-nav" aria-label="Main navigation">
          <a className="nav-item active" href="#analyzer" aria-current="page">
            <NavGlyph />
            <span>Text analyzer</span>
            <span className="nav-indicator" />
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note-icon"><SparkGlyph /></div>
          <p>Clear signals from every voice.</p>
          <span>Live model inference</span>
        </div>
      </aside>

      <main className="main-area" id="main">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>Text analyzer</strong></div>
          <div className="api-indicator"><span /> Inference API</div>
        </header>

        <div className="content-wrap" id="analyzer">
          <section className="page-intro">
            <div className="intro-copy">
              <div className="eyebrow"><span className="eyebrow-mark" /> FEEDBACK INTELLIGENCE</div>
              <h1>Understand what people <em>really</em> think.</h1>
              <p>Analyze feedback with model-backed sentiment and aspect insights, one review or a batch at a time.</p>
            </div>
            <div className="intro-stamp" aria-hidden="true">
              <span className="stamp-orbit orbit-one" />
              <span className="stamp-orbit orbit-two" />
              <span className="stamp-core"><BrandMark /></span>
            </div>
          </section>

          <section className="workspace-grid" aria-label="Sentiment analysis workspace">
            <form className="card input-card" onSubmit={handleSubmit}>
              <div className="card-heading">
                <div>
                  <span className="step-label">01 <i /> INPUT</span>
                  <h2>Choose your analysis</h2>
                </div>
                <span className="card-heading-icon"><NavGlyph /></span>
              </div>

              <fieldset className="domain-fieldset" disabled={loading}>
                <legend>Analysis domain</legend>
                <div className="domain-options">
                  <DomainOption
                    selected={domain === 'product'}
                    title="Product reviews"
                    description="Product model"
                    symbol="P"
                    onClick={() => {
                      setDomain('product')
                      resetResults()
                    }}
                  />
                  <DomainOption
                    selected={domain === 'campus'}
                    title="Campus feedback"
                    description="VADER baseline"
                    symbol="C"
                    onClick={() => {
                      setDomain('campus')
                      resetResults()
                    }}
                  />
                </div>
              </fieldset>

              <div className="mode-switch" role="tablist" aria-label="Analysis mode">
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'single'}
                  className={mode === 'single' ? 'selected' : ''}
                  disabled={loading}
                  onClick={() => {
                    setMode('single')
                    resetResults()
                  }}
                >
                  Single review
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'batch'}
                  className={mode === 'batch' ? 'selected' : ''}
                  disabled={loading}
                  onClick={() => {
                    setMode('batch')
                    resetResults()
                  }}
                >
                  Batch analysis
                </button>
              </div>

              {mode === 'single' ? (
                <label className="review-field" htmlFor="single-review">
                  <span className="field-label">Review text</span>
                  <textarea
                    id="single-review"
                    value={singleText}
                    onChange={(event) => {
                      setSingleText(event.target.value)
                      resetResults()
                    }}
                    maxLength={MAX_TEXT_LENGTH}
                    disabled={loading}
                    placeholder="Paste a product review or campus comment to uncover its sentiment…"
                    rows={9}
                  />
                  <span className="textarea-footer">
                    <span>Be as detailed as you like</span>
                    <span>{singleText.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}</span>
                  </span>
                </label>
              ) : (
                <label className="review-field" htmlFor="batch-reviews">
                  <span className="field-label">Reviews <small>one per line</small></span>
                  <textarea
                    id="batch-reviews"
                    value={batchText}
                    onChange={(event) => {
                      setBatchText(event.target.value)
                      resetResults()
                    }}
                    disabled={loading}
                    placeholder={'The quality feels premium and the battery lasts all day.\nThe delivery was late and the packaging arrived damaged.'}
                    rows={9}
                  />
                  <span className="textarea-footer">
                    <span>Up to {MAX_BATCH_SIZE} reviews · {MAX_TEXT_LENGTH.toLocaleString()} characters each</span>
                    <span>{batchReviews.length} reviews</span>
                  </span>
                </label>
              )}

              {error && <div className="form-error" role="alert"><AlertGlyph />{error}</div>}

              <div className="form-actions">
                <span className="privacy-note"><LockGlyph /> Not saved to a database</span>
                <button className="primary-button" type="submit" disabled={loading || !canSubmit}>
                  {loading ? <Spinner /> : <SparkGlyph />}
                  {loading ? 'Analyzing…' : mode === 'single' ? 'Analyze review' : 'Analyze batch'}
                  {!loading && <span aria-hidden="true">↗</span>}
                </button>
              </div>
            </form>

            <section className={`card results-card ${loading ? 'is-loading' : ''}`} aria-live="polite">
              <div className="card-heading results-heading">
                <div>
                  <span className="step-label">02 <i /> INSIGHT</span>
                  <h2>Analysis results</h2>
                </div>
                {singleResult || batchResults ? <span className="live-badge"><span /> LIVE RESULT</span> : null}
              </div>

              {loading ? (
                <LoadingState mode={mode} />
              ) : singleResult ? (
                <SingleResult result={singleResult} review={submittedReviews[0] ?? ''} />
              ) : batchResults ? (
                <BatchResults outcomes={batchResults} reviews={submittedReviews} />
              ) : (
                <EmptyState mode={mode} />
              )}
            </section>
          </section>

          <footer className="page-footer">
            <span>SentimentIQ <b>·</b> Model-powered feedback analysis</span>
            <span>Scores are raw model outputs, not calibrated probabilities.</span>
          </footer>
        </div>
      </main>
    </div>
  )
}

function DomainOption({
  selected,
  title,
  description,
  symbol,
  onClick,
}: {
  selected: boolean
  title: string
  description: string
  symbol: string
  onClick: () => void
}) {
  return (
    <button className={`domain-option ${selected ? 'selected' : ''}`} type="button" aria-pressed={selected} onClick={onClick}>
      <span className={`domain-symbol ${symbol === 'C' ? 'campus-symbol' : ''}`}>{symbol}</span>
      <span className="domain-copy"><b>{title}</b><small>{description}</small></span>
      <span className="radio-mark" aria-hidden="true" />
    </button>
  )
}

function SingleResult({ result, review }: { result: AnalysisResult; review: string }) {
  return (
    <div className="result-content">
      <div className="analyzed-quote"><span>ANALYZED REVIEW</span><p>“{review}”</p></div>
      <SentimentPanel sentiment={result.overall} />
      <AspectList aspects={result.aspects} />
    </div>
  )
}

function BatchResults({ outcomes, reviews }: { outcomes: BatchOutcome[]; reviews: string[] }) {
  if (!outcomes.length) {
    return <div className="empty-state compact-empty"><span className="empty-icon"><NavGlyph /></span><h3>No results returned</h3><p>The API returned an empty batch response.</p></div>
  }
  return (
    <div className="batch-list">
      <div className="batch-summary"><span>{outcomes.length} reviews processed</span><small>Results remain in input order</small></div>
      {outcomes.map((outcome) => (
        <article className="batch-item" key={outcome.input_index}>
          <div className="batch-item-head">
            <span className="batch-index">{String(outcome.input_index + 1).padStart(2, '0')}</span>
            <p>{reviews[outcome.input_index] ?? `Review ${outcome.input_index + 1}`}</p>
            <span className={`status-pill ${outcome.status}`}>{outcome.status === 'succeeded' ? 'Complete' : 'Failed'}</span>
          </div>
          {outcome.status === 'succeeded' && outcome.result ? (
            <>
              <SentimentPanel sentiment={outcome.result.overall} compact />
              <AspectList aspects={outcome.result.aspects} compact />
            </>
          ) : (
            <div className="item-error"><AlertGlyph />{outcome.error?.message ?? 'This review could not be analyzed.'}</div>
          )}
        </article>
      ))}
    </div>
  )
}

function SentimentPanel({ sentiment, compact = false }: { sentiment: SentimentValue; compact?: boolean }) {
  return (
    <div className={`sentiment-panel ${compact ? 'compact' : ''}`}>
      <div className="sentiment-overview">
        <span className="result-label">OVERALL SENTIMENT</span>
        <div className="sentiment-line">
          <SentimentBadge label={sentiment.sentiment_label} />
          <span className="score-value">{formatScore(sentiment.sentiment_score)}</span>
        </div>
        <span className="score-caption">Raw sentiment score <i>·</i> range −1 to +1</span>
      </div>
      <div className="confidence-box">
        <span className="result-label">CONFIDENCE VALUE</span>
        <b>{sentiment.confidence_value.toFixed(3)}</b>
        <span className="confidence-kind">{sentiment.confidence_kind.replace('_', ' ')}</span>
      </div>
    </div>
  )
}

function SentimentBadge({ label }: { label: SentimentLabel }) {
  return <span className={`sentiment-badge ${label}`}><i />{capitalize(label)}</span>
}

function AspectList({ aspects, compact = false }: { aspects: AspectResult[]; compact?: boolean }) {
  return (
    <section className={`aspect-section ${compact ? 'compact' : ''}`}>
      <div className="section-title-row">
        <div><span className="result-label">ASPECT BREAKDOWN</span><h3>What stood out</h3></div>
        <span className="aspect-count">{aspects.length} {aspects.length === 1 ? 'aspect' : 'aspects'}</span>
      </div>
      {aspects.length ? (
        <div className="aspect-list">
          {aspects.map((aspect, index) => (
            <AspectRow aspect={aspect} key={`${aspect.aspect_text}-${aspect.start_offset ?? index}`} />
          ))}
        </div>
      ) : (
        <p className="no-aspects">No known aspects were detected in this review.</p>
      )}
    </section>
  )
}

function AspectRow({ aspect }: { aspect: AspectResult }) {
  return (
    <div className="aspect-row">
      <span className="aspect-icon"><AspectGlyph /></span>
      <span className="aspect-name"><b>{aspect.aspect_text}</b><small>{aspect.aspect_category?.replace(/_/g, ' ') ?? 'Uncategorized'}</small></span>
      <SentimentBadge label={aspect.sentiment_label} />
      <span className="aspect-score" title="Raw sentiment score">{formatScore(aspect.sentiment_score)}</span>
    </div>
  )
}

function EmptyState({ mode }: { mode: Mode }) {
  return (
    <div className="empty-state">
      <div className="empty-illustration"><span /><span /><span /><i><BrandMark /></i></div>
      <span className="result-label">YOUR NEXT INSIGHT STARTS HERE</span>
      <h3>Ready when you are</h3>
      <p>{mode === 'single' ? 'Add a review and run the analysis to see its overall sentiment and the aspects behind it.' : 'Paste multiple reviews, one per line, to compare their sentiment in a single run.'}</p>
      <div className="empty-note"><span /> Results come directly from the SentimentIQ inference API</div>
    </div>
  )
}

function LoadingState({ mode }: { mode: Mode }) {
  return (
    <div className="loading-state" role="status">
      <Spinner />
      <h3>{mode === 'single' ? 'Reading between the lines' : 'Analyzing your batch'}</h3>
      <p>Sending feedback to the selected sentiment model…</p>
      <div className="loading-lines"><i /><i /><i /></div>
    </div>
  )
}

function NavGlyph() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 5.5A2.5 2.5 0 0 1 7.5 3h9A2.5 2.5 0 0 1 19 5.5v13a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 5 18.5v-13Z" /><path d="M8.5 8h7M8.5 12h3M8.5 16h2" /><path d="m14 14 1.2 1.2L18 12.5" /></svg>
}

function SparkGlyph() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 2 1.7 6.3L20 10l-6.3 1.7L12 18l-1.7-6.3L4 10l6.3-1.7L12 2Z" /><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></svg>
}

function AlertGlyph() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 2.8 19h18.4L12 3Z" /><path d="M12 9v4m0 3h.01" /></svg>
}

function LockGlyph() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3" /></svg>
}

function AspectGlyph() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 5h16M4 12h10M4 19h7" /><circle cx="18" cy="12" r="2" /><circle cx="14" cy="19" r="2" /></svg>
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function formatScore(score: number): string {
  return `${score >= 0 ? '+' : ''}${score.toFixed(3)}`
}

export default App
