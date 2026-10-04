import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'

const MOODS = ['Happy', 'Relaxed', 'Sad/Cathartic', 'Thrilled', 'Romantic', 'Nostalgic']
const GENRES = ['Comedy','Drama','Thriller','Romance','Science Fiction','Animation','Adventure','Mystery']
const COMPARISON_COLORS = ['#ef4055', '#8b5cf6', '#22c55e', '#f59e0b']

const cleanAssistantText = value => String(value || '')
  .replace(/```[\s\S]*?```/g, block => block.replace(/```[a-z]*\n?/gi, '').replace(/```/g, ''))
  .replace(/\*\*(.*?)\*\*/g, '$1')
  .replace(/__(.*?)__/g, '$1')
  .replace(/`([^`]+)`/g, '$1')
  .replace(/^#{1,6}\s+/gm, '')
  .replace(/^[-*]\s+/gm, '• ')
  .replace(/\n{3,}/g, '\n\n')
  .trim()

const moodClass = mood => {
  const value = (mood || '').toLowerCase()
  if (value.includes('happy')) return 'poster-happy'
  if (value.includes('relax')) return 'poster-relaxed'
  if (value.includes('thrill')) return 'poster-thrilled'
  if (value.includes('romantic')) return 'poster-romantic'
  if (value.includes('sad')) return 'poster-cathartic'
  return 'poster-nostalgic'
}

function Icon({ children }) {
  return <span className="icon">{children}</span>
}

function Modal({ open, onClose, title, eyebrow, wide = false, children, lock = false }) {
  if (!open) return null
  return (
    <div
      className="modal-backdrop"
      onMouseDown={e => {
        if (!lock && e.target === e.currentTarget) onClose?.()
      }}
    >
      <div className={`modal ${wide ? 'modal-wide' : ''}`}>
        {!lock && <button className="modal-close" onClick={onClose}>×</button>}
        {eyebrow && <div className="overline">{eyebrow}</div>}
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

function Poster({ movie, compact = false }) {
  if (movie?.poster_url) {
    return <img className={`poster-img ${compact ? 'compact' : ''}`} src={movie.poster_url} alt={`${movie.title} poster`} />
  }
  return (
    <div className={`poster-fallback ${moodClass(movie?.moods?.[0])} ${compact ? 'compact' : ''}`}>
      <span className="poster-film">◉</span>
      <strong>{movie?.title || 'Movie'}</strong>
      <small>{movie?.year || ''}</small>
    </div>
  )
}

function MovieCard({ movie, selected, onCompare, onNeedAuth, user, onOpen }) {
  const [flagged, setFlagged] = useState(false)

  const markWatched = async () => {
    if (!user) {
      onNeedAuth()
      return
    }
    try {
      await api.watched({ movie_id: movie.id, watched: true, rating: null })
    } catch (e) {
      console.warn(e)
    }
  }

  const flag = async () => {
    if (!user) {
      onNeedAuth()
      return
    }
    try {
      await api.flag({
        movie_id: movie.id,
        reason: 'Recommendation did not feel right',
        details: ''
      })
      setFlagged(true)
    } catch (e) {
      console.warn(e)
    }
  }

  return (
    <article className={`movie-card ${selected ? 'selected' : ''}`} onClick={() => onOpen?.(movie)} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') onOpen?.(movie) }}>
      <div className="poster-wrap">
        <Poster movie={movie} />
        <span className="rating-badge">★ {movie.rating}</span>
      </div>

      <div className="movie-card-caption">
        <h3>{movie.title}</h3>
        <span>{movie.year}</span>
      </div>

      <div className="movie-hover-panel">
        <div className="card-actions">
          <button title="Mark as watched" onClick={e => { e.stopPropagation(); markWatched() }}>▶</button>
          <button
            className={selected ? 'selected-btn' : ''}
            title="Add to comparison"
            onClick={e => { e.stopPropagation(); onCompare(movie.id) }}
          >
            {selected ? '✓' : '+'}
          </button>
          <button title="Flag recommendation" onClick={e => { e.stopPropagation(); flag() }}>
            {flagged ? '✓' : '⚑'}
          </button>
        </div>
        <div className="movie-meta">
          <span>{movie.runtime} min</span>
          <span>{movie.pace}</span>
        </div>
        <div className="chip-line">
          {movie.moods?.slice(0, 2).map(m => <span key={m}>{m}</span>)}
        </div>
        <p>{movie.overview}</p>
      </div>
    </article>
  )
}

function MovieRow({ title, subtitle, movies, compareIds, toggleCompare, user, onNeedAuth, onOpenMovie }) {
  const row = useRef(null)

  return (
    <section className="movie-section">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <button onClick={() => row.current?.scrollBy({ left: 700, behavior: 'smooth' })}>
          Explore →
        </button>
      </div>

      <div className="movie-row" ref={row}>
        {movies.map(movie => (
          <MovieCard
            key={movie.id}
            movie={movie}
            user={user}
            selected={compareIds.includes(movie.id)}
            onCompare={toggleCompare}
            onNeedAuth={onNeedAuth}
            onOpen={onOpenMovie}
          />
        ))}
      </div>
    </section>
  )
}

function MovieDetailModal({ movie, open, onClose, onCompare, onFindSimilar, selected, user, onNeedAuth }) {
  const [summary, setSummary] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setSummary('')
  }, [movie?.id])

  if (!movie) return null

  const summarize = async () => {
    if (!user) { onNeedAuth(); return }
    setBusy(true)
    try {
      const result = await api.summarize(movie.id)
      setSummary(result.summary || movie.overview)
    } catch {
      setSummary(movie.overview)
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={onClose} title={movie.title} eyebrow={`${movie.year} · ${movie.runtime} MIN · ★ ${movie.rating}`} wide>
      <div className="movie-detail-layout">
        <div className="movie-detail-poster"><Poster movie={movie} /></div>
        <div className="movie-detail-copy">
          <div className="detail-chip-row">
            {movie.genres?.map(g => <span key={g}>{g}</span>)}
            {movie.moods?.slice(0, 3).map(m => <span key={m}>{m}</span>)}
          </div>
          <p className="movie-detail-overview">{summary || movie.overview}</p>
          <dl className="movie-facts">
            <div><dt>Director</dt><dd>{movie.director || 'Not listed'}</dd></div>
            <div><dt>Cast</dt><dd>{Array.isArray(movie.cast) ? movie.cast.slice(0, 6).join(', ') : (movie.cast || 'Not listed')}</dd></div>
            <div><dt>Language</dt><dd>{movie.language || 'Not listed'}</dd></div>
            <div><dt>Pace</dt><dd>{movie.pace || 'Not listed'}</dd></div>
            <div><dt>Studio</dt><dd>{movie.studio || 'Not listed'}</dd></div>
          </dl>
          <div className="detail-actions">
            <button className="btn-primary" onClick={() => onCompare(movie.id)}>{selected ? '✓ Added to compare' : '+ Add to compare'}</button>
            <button className="btn-secondary" disabled={busy} onClick={summarize}>{busy ? 'Summarising…' : 'Short plot summary'}</button>
            <button className="btn-secondary similar-launch-btn" onClick={()=>onFindSimilar?.(movie)}>◎ Find Similar Movies</button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

function SimilarityModal({ movie, open, onClose, user, onNeedAuth, compareIds, toggleCompare, onOpenCompare }) {
  const MODES=[
    ['story','Similar story / plot'],['genre','Similar genres'],['cast','Same actors'],['year','Similar release period'],
    ['title','Similar title'],['director','Same director'],['studio','Same studio'],['producer','Same producer'],['mood','Similar mood']
  ]
  const [modes,setModes]=useState(['story','genre','cast','year','title','director','studio'])
  const [result,setResult]=useState(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')

  useEffect(()=>{
    if(open&&movie){setResult(null);setError('');setModes(['story','genre','cast','year','title','director','studio'])}
  },[open,movie?.id])

  if(!movie) return null
  const toggleMode=m=>setModes(current=>current.includes(m)?current.filter(x=>x!==m):[...current,m])
  const run=async()=>{
    if(!user){onNeedAuth();return}
    if(!modes.length){setError('Choose at least one similarity type.');return}
    setBusy(true);setError('')
    try{
      setResult(await api.similar({
        movie_id:movie.id,modes,weights:{},preset:'overall',required_genre:null,
        year_mode:'within_5',custom_year_min:null,custom_year_max:null,
        mood:null,free_minutes:null,limit:12
      }))
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const addCompare=id=>{if(!compareIds.includes(id))toggleCompare(id)}
  const compareOriginal=id=>{addCompare(movie.id);addCompare(id);setTimeout(()=>{onClose();onOpenCompare?.()},0)}
  const compLabel={story:'Story',genre:'Genre',cast:'Cast',year:'Era',title:'Title',director:'Director',studio:'Studio',producer:'Producer',mood:'Mood'}
  return <Modal open={open} onClose={onClose} title={`Find movies similar to ${movie.title}`} eyebrow="EXPLAINABLE MULTI-FACTOR SIMILARITY" wide>
    <div className="similarity-shell">
      <section className="similarity-source-card"><Poster movie={movie} compact/><div><strong>{movie.title}</strong><span>{movie.year} · {movie.runtime} min · ★ {movie.rating}</span><small>{movie.genres?.slice(0,4).join(' · ')}</small></div></section>
      <div className="similarity-builder-grid">
        <section className="similarity-controls">
          <div className="section-kicker">1 · Choose similarity types</div>
          <div className="similar-mode-grid">{MODES.map(([key,label])=><button key={key} className={modes.includes(key)?'active':''} onClick={()=>toggleMode(key)}>{label}</button>)}</div>
          <button className="btn-primary full" disabled={busy} onClick={run}>{busy?'Calculating similarity…':'Find similar movies'}</button>
          {error&&<div className="error-box">{error}</div>}
        </section>
        <section className="similarity-results-panel">
          {!result&&!busy&&<div className="empty-card similarity-empty"><div className="big-symbol">◎</div><h3>Choose how “similar” should be defined.</h3><p>CineSense can combine semantic story similarity, genres, cast, creators, era, title patterns, studio and mood. Every result includes a score breakdown and a grounded reason.</p></div>}
          {result&&<>
            <div className="similar-results-head"><div><div className="section-kicker">RANKED RESULTS</div><h3>{result.results?.length||0} explainable matches</h3></div><div className="semantic-badge">{result.semantic_backend==='sentence-transformers'?'Sentence Transformers':'384-d semantic hash vectors'}</div></div><div className="similar-weight-summary">{Object.entries(result.weights||{}).map(([k,v])=><span key={k}>{compLabel[k]||k} {Math.round(v)}%</span>)}</div>
            {!result.producer_data_available&&modes.includes('producer')&&<div className="info-box">Verified producer data is not yet available for the selected movie. Same-studio similarity still works immediately; producer matching activates automatically for movies enriched from TMDB credits.</div>}
            <div className="similar-result-list">{result.results?.map((r,index)=><article className="similar-result-card" key={r.id}>
              <div className="similar-rank">#{index+1}</div><Poster movie={r} compact/>
              <div className="similar-result-main"><div className="similar-title-row"><div><h4>{r.title}</h4><span>{r.year} · {r.runtime} min · ★ {r.rating}</span></div><b>{r.similarity}%</b></div>
                <p>{r.why_similar}</p>
                <div className="similar-breakdown">{modes.map(m=><span key={m}><small>{compLabel[m]||m}</small><strong>{Math.round(r.components?.[m]||0)}%</strong></span>)}</div>
                <div className="similar-match-line">{r.matches?.actors?.length>0&&<span>Cast: {r.matches.actors.join(', ')}</span>}{r.matches?.genres?.length>0&&<span>Genres: {r.matches.genres.join(', ')}</span>}{r.matches?.director&&<span>Director: {r.matches.director}</span>}{r.matches?.studio&&<span>Studio: {r.matches.studio}</span>}{typeof r.year_difference==='number'&&<span>Year difference: {r.year_difference}</span>}</div>
                <div className="similar-actions"><button className="btn-secondary" onClick={()=>addCompare(r.id)}>{compareIds.includes(r.id)?'✓ In shortlist':'+ Add to shortlist'}</button><button className="btn-secondary" onClick={()=>compareOriginal(r.id)}>Compare with original</button></div>
              </div>
            </article>)}</div>
          </>}
        </section>
      </div>
    </div>
  </Modal>
}

function AuthModal({ open, onClose, onUser }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ display_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const user = mode === 'login'
        ? await api.login({ email: form.email, password: form.password })
        : await api.register(form)
      onUser(user)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const demo = async () => {
    setError('')
    setBusy(true)
    try {
      const user = await api.demo()
      onUser(user)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={mode === 'login' ? 'Welcome back' : 'Create your CineSense profile'}
      eyebrow="PRIVATE · PERSONAL · EXPLAINABLE"
    >
      <form className="stack-form" onSubmit={submit}>
        {mode === 'register' && (
          <label>
            Name
            <input
              value={form.display_name}
              onChange={e => setForm({ ...form, display_name: e.target.value })}
              required
            />
          </label>
        )}
        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            required
          />
        </label>

        {error && <div className="error-box">{error}</div>}

        <button className="btn-primary full" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
        <button className="btn-secondary full" type="button" onClick={demo} disabled={busy}>
          Continue as demo
        </button>

        <p className="form-switch">
          {mode === 'login' ? 'New here? ' : 'Already registered? '}
          <button
            type="button"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? 'Create account' : 'Sign in'}
          </button>
        </p>
      </form>
    </Modal>
  )
}

function ConsentModal({ user, onUser }) {
  if (!user || user.consented) return null

  const accept = async () => {
    try {
      onUser(await api.consent())
    } catch (e) {
      alert(e.message)
    }
  }

  return (
    <Modal
      open
      lock
      title="Before your first AI recommendation"
      eyebrow="TRANSPARENCY & CONSENT"
    >
      <div className="consent-copy">
        <p>
          CineSense uses AI-assisted analysis to infer signals such as mood,
          genre and available time. You remain in control of those signals.
        </p>
        <ul>
          <li>Movie facts are grounded in the CineSense catalogue.</li>
          <li>Short-term chat memory is encrypted and limited.</li>
          <li>Diagnostic activity logs use safe summaries instead of raw chat text.</li>
          <li>You can dismiss a mood or flag an unsuitable recommendation.</li>
        </ul>
        <button className="btn-primary full" onClick={accept}>
          ✓ I understand — continue
        </button>
      </div>
    </Modal>
  )
}

function MovieSearch({ movies, onOpenMovie, onCatalogueExpand }) {
  const [query,setQuery]=useState('')
  const [genre,setGenre]=useState('')
  const [results,setResults]=useState([])
  const [busy,setBusy]=useState(false)
  const [external,setExternal]=useState(false)
  const [error,setError]=useState('')
  const normalized=query.trim()
  const moviesRef=useRef(movies)
  const requestSequence=useRef(0)
  moviesRef.current=movies
  const genres=useMemo(()=>Array.from(new Set(movies.flatMap(movie=>movie.genres||[]))).sort((a,b)=>a.localeCompare(b)),[movies])

  useEffect(()=>{
    const applyGenre=rows=>genre?rows.filter(movie=>(movie.genres||[]).some(g=>g.toLowerCase()===genre.toLowerCase())):rows
    const sequence=++requestSequence.current
    setError('')
    setExternal(false)

    if(normalized.length===1){
      setBusy(false)
      setResults([])
      return
    }
    if(!normalized&&!genre){
      setBusy(false)
      setResults([])
      return
    }

    const controller=new AbortController()
    const timer=setTimeout(async()=>{
      setBusy(true)
      try{
        const payload=await api.searchMovies(normalized,{genre,signal:controller.signal})
        if(sequence!==requestSequence.current)return
        const rows=payload.results||[]
        const filtered=applyGenre(rows)
        setResults(filtered)
        setExternal(Boolean(payload.external_search))
        if(payload.external_search)onCatalogueExpand?.(rows)
      }catch(e){
        if(e.name==='AbortError'||sequence!==requestSequence.current)return
        const n=normalized.toLowerCase()
        const local=moviesRef.current.filter(movie=>(!n||[movie.title,movie.year,movie.language,movie.director,movie.studio,...(movie.cast||[]),...(movie.genres||[]),...(movie.moods||[]),...(movie.keywords||[])].filter(Boolean).join(' ').toLowerCase().includes(n)))
        setResults(applyGenre(local).slice(0,24))
        setError(`Live catalogue search is unavailable. Showing matches already loaded on this page. ${e.message}`)
      }finally{if(sequence===requestSequence.current)setBusy(false)}
    },300)
    return ()=>{clearTimeout(timer);controller.abort()}
  },[normalized,genre,onCatalogueExpand])

  const searching=Boolean(normalized.length>=2||genre)
  const hasInput=Boolean(normalized||genre)
  return <section className="movie-search-section" aria-label="Movie search" role="search">
    <div className="movie-search-row">
      <div className="search-shell cinematic-search" aria-busy={busy}>
        <span className="search-icon">⌕</span>
        <input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')setQuery('')}} placeholder="Search by title, actor, director, mood or keyword…" role="combobox" aria-autocomplete="list" aria-label="Search movies" aria-controls="movie-search-results" aria-expanded={hasInput} autoComplete="off" />
        {busy&&<span className="searching-dot">Searching…</span>}
        {query&&<button type="button" className="search-clear" onClick={()=>setQuery('')} aria-label="Clear search">×</button>}
      </div>
      <label className="genre-filter-shell">
        <span>Genre</span>
        <select value={genre} onChange={e=>setGenre(e.target.value)} aria-label="Filter movies by genre">
          <option value="">All genres</option>
          {genres.map(item=><option value={item} key={item}>{item}</option>)}
        </select>
      </label>
    </div>
    {hasInput&&<div className="search-results-panel" id="movie-search-results" aria-live="polite">
      {normalized.length===1?<p className="search-hint">Type one more character to search the catalogue.</p>:<>
      <div className="search-results-head"><strong>{busy?'Searching movie catalogue…':results.length?`${results.length} ${results.length===1?'match':'matches'}`:'No matches found'}</strong><span>{genre?`${genre} filter · `:''}{external?'Expanded from TMDB and saved to CineSense':'CineSense catalogue'}</span></div>
      {error&&<div className="search-error" role="status">{error}</div>}
      {results.length>0&&<div className="search-results-grid" role="listbox">{results.map(movie=><button type="button" className="search-result" role="option" aria-selected="false" key={movie.id} onClick={()=>onOpenMovie(movie)}><div className="search-poster"><Poster movie={movie} compact /></div><div><strong>{movie.title}</strong><span>{movie.year} · {movie.runtime} min · ★ {movie.rating}</span><small>{movie.genres?.slice(0,3).join(' · ')} · {movie.source==='tmdb'?'TMDB':'Curated'}</small></div></button>)}</div>}
      {!busy&&!error&&searching&&results.length===0&&<p className="muted">No catalogue matches. Try a full title, an actor or director, a mood, or a different genre.</p>}
      </>}
    </div>}
  </section>
}

function ChatDrawer({
  open, onClose, user, onNeedAuth, detected, setDetected, messages, setMessages
}) {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const end = useRef(null)

  useEffect(() => {
    try {
      end.current?.scrollIntoView?.({ block: 'nearest' })
    } catch {}
  }, [messages, busy])

  const send = async supplied => {
    const message = (supplied ?? input).trim()
    if (!message || busy) return

    if (!user) {
      onNeedAuth()
      return
    }

    if (!user.consented) return

    setMessages(current => [...current, { role: 'user', content: message }])
    setInput('')
    setBusy(true)

    try {
      const response = await api.chat({
        message,
        mood_override: detected.mood || null,
        dismissed_moods: []
      })

      setMessages(current => [
        ...current,
        {
          role: 'assistant',
          content: cleanAssistantText(response.reply),
          movies: response.movies?.slice(0, 4) || []
        }
      ])

      setDetected({
        mood: response.preferences?.mood || null,
        genres: response.preferences?.genres || [],
        time_available: response.preferences?.time_available || null
      })
    } catch (e) {
      setMessages(current => [
        ...current,
        {
          role: 'assistant',
          content:
            `I couldn't complete that request: ${e.message}. ` +
            `You can refine the request without starting over.`
        }
      ])
    } finally {
      setBusy(false)
    }
  }

  const startVoice = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setMessages(current => [
        ...current,
        {
          role: 'assistant',
          content:
            'Voice input is not available in this browser. ' +
            'Type the same request and I can handle it normally.'
        }
      ])
      return
    }

    const recognizer = new SpeechRecognition()
    recognizer.lang = 'en-US'
    recognizer.interimResults = false
    recognizer.onstart = () => setListening(true)
    recognizer.onend = () => setListening(false)
    recognizer.onerror = () => setListening(false)
    recognizer.onresult = e => setInput(e.results[0][0].transcript)
    recognizer.start()
  }

  const prompts = [
    'I’m stressed — something warm under 110 minutes',
    'I want something tense under 100 minutes',
    'Something romantic and gentle',
    'Give me a nostalgic comfort movie'
  ]

  if (!open) return null

  return (
    <aside className="chat-drawer">
      <div className="chat-head">
        <div className="chat-brand">
          <span className="ai-orb">✦</span>
          <div>
            <strong>CineSense</strong>
            <small>Your mood-aware movie assistant</small>
          </div>
        </div>
        <button className="round-btn" onClick={onClose}>×</button>
      </div>

      <div className="ai-notice">
        <span>✓</span>
        Movie facts come from the CineSense catalogue. You can adjust detected preferences at any time.
      </div>

      {(detected.mood || detected.genres?.length || detected.time_available) && (
        <div className="detected-line">
          <small>Detected</small>
          {detected.mood && (
            <button
              className="signal-chip"
              onClick={() => setDetected({ ...detected, mood: null })}
            >
              {detected.mood} ×
            </button>
          )}
          {detected.genres?.map(g => <span className="signal-chip" key={g}>{g}</span>)}
          {detected.time_available && (
            <span className="signal-chip">{detected.time_available} min</span>
          )}
        </div>
      )}

      <div className="chat-messages">
        {messages.map((message, i) => (
          <div className={`chat-message ${message.role}`} key={`${message.role}-${i}`}>
            <div className="chat-bubble">{message.role === 'assistant' ? cleanAssistantText(message.content) : message.content}</div>
            {message.movies?.length > 0 && (
              <div className="chat-movies">
                {message.movies.map(movie => (
                  <div className="chat-movie" key={movie.id}>
                    <Poster movie={movie} compact />
                    <div>
                      <strong>{movie.title}</strong>
                      <small>{movie.runtime} min · ★ {movie.rating}</small>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="typing-dots"><span/><span/><span/></div>}
        <div ref={end} />
      </div>

      {messages.length < 3 && (
        <div className="quick-prompts">
          {prompts.map(p => <button key={p} onClick={() => send(p)}>{p}</button>)}
        </div>
      )}

      <div className="chat-input">
        <button
          className={`round-btn ${listening ? 'listening' : ''}`}
          onClick={startVoice}
          title="Voice input"
        >
          {listening ? '■' : '🎙'}
        </button>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Tell me your mood, taste, or free time…"
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
        />
        <button className="send-btn" disabled={!input.trim() || busy} onClick={() => send()}>
          ➤
        </button>
      </div>
    </aside>
  )
}

function PlannerModal({ open, onClose, user, onNeedAuth }) {
  const moodEmoji = { Happy:'😊', Relaxed:'😌', 'Sad/Cathartic':'🥲', Thrilled:'⚡', Romantic:'💗', Nostalgic:'✨' }
  const [tab, setTab] = useState('plan')
  const [genre, setGenre] = useState('Comedy')
  const [mood, setMood] = useState('Relaxed')
  const [moodText, setMoodText] = useState('')
  const [moodNote, setMoodNote] = useState('')
  const [minutes, setMinutes] = useState(120)
  const [finishBy, setFinishBy] = useState('I need to finish by 11:00 PM')
  const [bufferMinutes, setBufferMinutes] = useState(10)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [insights, setInsights] = useState(null)
  const [weekly, setWeekly] = useState(null)
  const [calendar, setCalendar] = useState(null)
  const [slots, setSlots] = useState([])
  const [windows, setWindows] = useState([])
  const [selectedWindow, setSelectedWindow] = useState(null)
  const [calendarMessage, setCalendarMessage] = useState('')
  const [reminderMinutes, setReminderMinutes] = useState(15)
  const [slotForm, setSlotForm] = useState({ title:'Busy', start_at:'', end_at:'' })

  const nowForDate = new Date()
  const today = `${nowForDate.getFullYear()}-${String(nowForDate.getMonth()+1).padStart(2,'0')}-${String(nowForDate.getDate()).padStart(2,'0')}`

  const refreshPersonal = async () => {
    if (!user) return
    const [i,w,c] = await Promise.allSettled([api.plannerInsights(), api.weeklySummary(), api.calendarStatus()])
    if (i.status === 'fulfilled') setInsights(i.value)
    if (w.status === 'fulfilled') setWeekly(w.value)
    if (c.status === 'fulfilled') setCalendar(c.value)
  }

  const refreshSlots = async () => {
    if (!user) return
    try { setSlots(await api.calendarBusySlots()) } catch { setSlots([]) }
  }

  useEffect(() => {
    if (open && user) {
      refreshPersonal()
      refreshSlots()
    }
  }, [open, user?.id])

  const checkMood = async (selectedMood = null) => {
    if (!user) { onNeedAuth(); return }
    try {
      const response = await api.moodCheck({ text:moodText, selected_mood:selectedMood })
      if (response.mood) setMood(response.mood)
      if (response.genres?.length) setGenre(response.genres[0])
      if (response.time_available) setMinutes(response.time_available)
      setMoodNote(response.message || '')
    } catch (e) { setMoodNote(e.message) }
  }

  const quickPlan = value => {
    if (busy) return
    const safeValue = Math.max(30, Math.min(600, Number(value) || 120))
    setMinutes(safeValue)
    setSelectedWindow(null)
    if (user) setTimeout(() => run(safeValue), 0)
  }

  const run = async (minutesOverride = null) => {
    if (!user) { onNeedAuth(); return }
    if (busy) return
    const safeMinutes = Math.max(30, Math.min(600, Number(minutesOverride ?? minutes) || 120))
    const safeBuffer = Math.max(0, Math.min(60, Number(bufferMinutes) || 0))
    setBusy(true)
    setResult(null)
    try {
      const response = await api.plan({
        genres: genre ? [genre] : [],
        mood: mood || null,
        free_minutes: safeMinutes,
        finish_by: finishBy?.trim() || null,
        buffer_minutes: safeBuffer,
        query: moodText?.trim().slice(0, 500) || null
      })
      setResult(response)
      refreshPersonal()
    } catch (e) {
      const friendly = e.status === 429
        ? `${e.message} Subscribe to Premium or Family from Plans to use the full Mood & Time Planner.`
        : e.message
      setResult({ error: friendly })
    } finally { setBusy(false) }
  }

  const save = async () => {
    try {
      await api.savePlan('My CineSense watch plan', result)
      setCalendarMessage('Watch plan saved to CineSense.')
    } catch (e) { setCalendarMessage(e.message) }
  }

  const connectLocal = async () => {
    if (!user) { onNeedAuth(); return }
    try {
      const response = await api.connectLocalCalendar()
      setCalendar({ ...(calendar || {}), connected:true, provider:'local' })
      setCalendarMessage(response.message)
      refreshSlots()
    } catch (e) { setCalendarMessage(e.message) }
  }

  const connectGoogle = async () => {
    if (!user) { onNeedAuth(); return }
    if (!calendar?.google_available) {
      setCalendarMessage('Google Calendar needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env before it can connect.')
      return
    }
    try {
      const response = await api.googleCalendarConnect()
      if (response.auth_url) window.location.href = response.auth_url
    } catch (e) { setCalendarMessage(e.message) }
  }

  const addBusy = async () => {
    if (!user) { onNeedAuth(); return }
    if (!slotForm.start_at || !slotForm.end_at) { setCalendarMessage('Choose both a start and end time.'); return }
    try {
      await api.addCalendarBusySlot({
        ...slotForm,
        start_at:new Date(slotForm.start_at).toISOString(),
        end_at:new Date(slotForm.end_at).toISOString()
      })
      setSlotForm({ title:'Busy', start_at:'', end_at:'' })
      setCalendarMessage('Busy time added. CineSense will avoid it when finding free windows.')
      refreshSlots()
    } catch (e) { setCalendarMessage(e.message) }
  }

  const findWindows = async () => {
    if (!user) { onNeedAuth(); return }
    try {
      const response = await api.calendarFreeWindows({
        date: today,
        window_start:'18:00',
        window_end:'23:59',
        min_minutes:30,
        timezone_offset_minutes:new Date().getTimezoneOffset()
      })
      setWindows(response.windows || [])
      setCalendarMessage(response.windows?.length ? 'Here are your free windows for tonight.' : 'No free evening window of at least 30 minutes was found.')
    } catch (e) { setCalendarMessage(e.message) }
  }

  const useWindow = windowItem => {
    setSelectedWindow(windowItem)
    setMinutes(windowItem.minutes)
    const end = new Date(windowItem.end_at)
    const h = String(end.getHours()).padStart(2,'0')
    const m = String(end.getMinutes()).padStart(2,'0')
    setFinishBy(`${h}:${m}`)
    setTab('plan')
    setCalendarMessage(`Using your ${windowItem.label} free window.`)
  }

  const eventTimes = () => {
    const now = new Date()
    const ymd = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
    let start = null
    if (selectedWindow) start = new Date(selectedWindow.start_at)
    if (!start || Number.isNaN(start.getTime())) {
      if (result?.suggested_start) start = new Date(`${ymd}T${result.suggested_start}:00`)
      else start = new Date(Date.now() + 5 * 60000)
    }
    const end = new Date(start.getTime() + Number(result?.used_minutes || 0) * 60000)
    return { start, end }
  }

  const addToCalendar = async () => {
    if (!user) { onNeedAuth(); return }
    if (!result?.movies?.length) return
    try {
      const { start, end } = eventTimes()
      const title = result.movies.length > 1 ? `Movie night: ${result.movies.map(m=>m.title).join(' + ')}` : `Watch ${result.movies[0].title}`
      const description = result.movies.map(m => `${m.title} — ${m.runtime} min`).join('\n')
      const response = await api.addPlanToCalendar({
        title,
        start_at:start.toISOString(),
        end_at:end.toISOString(),
        description,
        reminder_minutes:Number(reminderMinutes)
      })
      setCalendarMessage(response.message)
      if (response.ics) {
        const blob = new Blob([response.ics], { type:'text/calendar;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'cinesense-watch-plan.ics'
        a.click()
        URL.revokeObjectURL(url)
      }
      refreshSlots()
    } catch (e) { setCalendarMessage(e.message) }
  }

  return (
    <Modal open={open} onClose={onClose} title="Mood & Time Watch Planner" eyebrow="PERSONALISED WATCH PLANNING" wide>
      <div className="planner-tabs" role="tablist">
        <button className={tab==='plan'?'active':''} onClick={()=>setTab('plan')}>Plan tonight</button>
        <button className={tab==='insights'?'active':''} onClick={()=>setTab('insights')}>My insights</button>
        <button className={tab==='calendar'?'active':''} onClick={()=>setTab('calendar')}>Calendar</button>
      </div>

      {tab === 'plan' && <div className="planner-grid planner-grid-v2">
        <div className="control-panel planner-controls-v2">
          <section className="planner-section">
            <div className="section-kicker">1 · Smart mood check-in</div>
            <h3>How are you feeling right now?</h3>
            <div className="mood-buttons">
              {MOODS.map(m => <button key={m} className={mood===m?'active':''} onClick={()=>{ setMood(m); checkMood(m) }}><span>{moodEmoji[m]}</span>{m}</button>)}
            </div>
            <div className="mood-free-text">
              <input value={moodText} onChange={e=>setMoodText(e.target.value)} placeholder="Or tell CineSense in your own words…" />
              <button className="btn-secondary" onClick={()=>checkMood()}>Detect</button>
            </div>
            {moodNote && <p className="helper-success">{moodNote}</p>}
          </section>

          <section className="planner-section">
            <div className="section-kicker">2 · I have X minutes</div>
            <div className="quick-time-grid">
              {[30,60,90,120,180,240].map(v => <button key={v} className={Number(minutes)===v?'active':''} onClick={()=>quickPlan(v)}><strong>{v===120?'2 hours':v===180?'3+ hours':v===240?'4 hours':`${v} min`}</strong><small>{v<60?'Quick gap':v<100?'One movie':v<180?'Movie night':'Room for a double feature'}</small></button>)}
            </div>
            <label className="range-label">
              <span className="label-between"><span>Custom free time</span><b>{minutes} minutes</b></span>
              <input type="range" min="30" max="360" step="5" value={Number(minutes) || 120} onChange={e=>{setMinutes(Number(e.target.value));setSelectedWindow(null)}} />
            </label>
          </section>

          <section className="planner-section two-col-fields">
            <label>Genre<select value={genre} onChange={e=>setGenre(e.target.value)}>{GENRES.map(g=><option key={g}>{g}</option>)}</select></label>
            <label>Confirmed mood<select value={mood} onChange={e=>setMood(e.target.value)}>{MOODS.map(m=><option key={m}>{m}</option>)}</select></label>
          </section>

          <section className="planner-section">
            <div className="section-kicker">3 · Smart finish-time planner</div>
            <label>Finish-time request<input value={finishBy} onChange={e=>setFinishBy(e.target.value)} placeholder="e.g. I need to sleep by 11:30 PM" /></label>
            <div className="buffer-row"><span>Wind-down buffer</span>{[0,10,15,20,30].map(v=><button key={v} className={bufferMinutes===v?'active':''} onClick={()=>setBufferMinutes(v)}>{v} min</button>)}</div>
          </section>

          <button className="btn-primary full planner-build-btn" onClick={run} disabled={busy}>{busy ? 'Finding the best fit…' : 'Create my smart watch plan'}</button>
        </div>

        <div className="planner-result planner-result-v2">
          {!result && <div className="empty-card planner-hero-empty"><div className="big-symbol">◷</div><h3>Your evening, fitted around you.</h3><p>Confirm your mood, choose how much time you have, and CineSense will fit one movie or a double feature around your real schedule.</p><button className="calendar-inline-link" onClick={()=>setTab('calendar')}>Check my calendar availability →</button></div>}
          {result?.error && <div className="error-box">{result.error}</div>}
          {result?.movies && result.movies.length > 0 && <>
            <div className="plan-intro"><div className="overline">{result.type==='double'?'DOUBLE FEATURE':'SMART MOVIE PLAN'}</div><p>{result.message}</p>{result.why_this_plan&&<div className="personal-why"><b>Why this plan fits you</b><p>{result.why_this_plan}</p></div>}</div>
            {result.suggested_start && <div className="schedule-card"><div><small>Suggested start</small><strong>{result.suggested_start}</strong></div><div><small>Movie time ends</small><strong>{result.planned_finish || result.finish_by}</strong></div><div><small>Finish by</small><strong>{result.finish_by}</strong></div><div><small>Buffer</small><strong>{result.buffer_minutes} min</strong></div></div>}
            <div className="plan-list">{result.movies.map((movie,i)=><div className="plan-item" key={movie.id}><span className="plan-number">{i+1}</span><Poster movie={movie} compact/><div><strong>{movie.title}</strong><small>{movie.runtime} min · ★ {movie.rating}</small><p>{movie.personal_reason || movie.reason}</p></div></div>)}</div>
            <div className="stat-line"><span><b>{result.used_minutes}</b> min watch time</span><span><b>{result.remaining_minutes}</b> min spare</span><span><b>{result.buffer_minutes || 0}</b> min buffer</span></div>
            <div className="plan-calendar-actions"><label>Reminder<select value={reminderMinutes} onChange={e=>setReminderMinutes(e.target.value)}><option value={0}>None</option><option value={5}>5 min</option><option value={15}>15 min</option><option value={30}>30 min</option><option value={60}>1 hour</option></select></label><div className="plan-actions">{user?.plan!=='free'&&<button className="btn-secondary" onClick={save}>Save plan</button>}<button className="btn-primary" onClick={addToCalendar}>Add to Calendar</button></div></div>
            {calendarMessage && <p className="helper-success">{calendarMessage}</p>}
          </>}
          {result?.movies && result.movies.length===0 && !result.error && <div className="empty-card"><h3>No full movie fits yet</h3><p>{result.message}</p><p>Try 90 minutes or more, or change your genre. CineSense won’t pretend a full movie fits when it doesn’t.</p></div>}
        </div>
      </div>}

      {tab === 'insights' && <div className="insights-dashboard">
        <div className="insight-heading"><div><div className="section-kicker">4 · Mood history & personal insights</div><h3>Your CineSense patterns</h3></div><button className="btn-secondary" onClick={refreshPersonal}>Refresh</button></div>
        <div className="weekly-summary-grid">
          <div><span>🎬</span><strong>{weekly?.movies_watched ?? 0}</strong><small>Movies watched</small></div>
          <div><span>⏱</span><strong>{weekly?.watch_time_label || '0h 00m'}</strong><small>Watch time</small></div>
          <div><span>🙂</span><strong>{weekly?.most_common_mood || '—'}</strong><small>Most common mood</small></div>
          <div><span>🍿</span><strong>{weekly?.favourite_genre || '—'}</strong><small>Favourite genre</small></div>
          <div><span>◷</span><strong>{weekly?.average_movie_length || 0} min</strong><small>Average movie length</small></div>
        </div>
        <div className="insight-cards">{(insights?.insights || ['Create a few plans to unlock personalised patterns.']).map((text,i)=><article key={i}><span>✦</span><p>{text}</p></article>)}</div>
        <div className="insight-note"><b>Weekly Mood & Watch Summary</b><p>These insights use your own saved planner activity and watched titles. They are designed to help you notice patterns, not to label how you feel.</p></div>
      </div>}

      {tab === 'calendar' && <div className="calendar-dashboard">
        <div className="calendar-connect-card">
          <div><div className="section-kicker">6 · Calendar-aware planning</div><h3>{calendar?.connected ? `${calendar.provider==='google'?'Google':'CineSense'} Calendar connected` : 'Connect a calendar'}</h3><p>Let CineSense find evening gaps and turn them into a watch plan. Google Calendar works when OAuth credentials are configured; the built-in CineSense Calendar works immediately for the university demo.</p></div>
          <div className="calendar-connect-actions">{!calendar?.connected&&<button className="btn-primary" onClick={connectLocal}>Connect CineSense Calendar</button>}{calendar?.provider!=='google'&&<button className="btn-secondary" onClick={connectGoogle}>{calendar?.google_available?'Connect Google Calendar':'Google setup needed'}</button>}{calendar?.connected&&<button className="btn-secondary" onClick={async()=>{await api.disconnectCalendar();setCalendar({...calendar,connected:false,provider:null});setCalendarMessage('Calendar disconnected.')}}>Disconnect</button>}</div>
        </div>

        <div className="calendar-two-col">
          <section className="calendar-panel"><h4>Add a busy time</h4><p>Use this for classes, work, dinner, or anything CineSense should avoid.</p><input value={slotForm.title} onChange={e=>setSlotForm({...slotForm,title:e.target.value})} placeholder="What are you doing?"/><label>Start<input type="datetime-local" value={slotForm.start_at} onChange={e=>setSlotForm({...slotForm,start_at:e.target.value})}/></label><label>End<input type="datetime-local" value={slotForm.end_at} onChange={e=>setSlotForm({...slotForm,end_at:e.target.value})}/></label><button className="btn-secondary full" onClick={addBusy}>Add busy time</button></section>
          <section className="calendar-panel"><h4>Find free time tonight</h4><p>Search 6:00 PM–11:59 PM for gaps of at least 30 minutes.</p><button className="btn-primary full" onClick={findWindows}>Find my free windows</button><div className="free-window-list">{windows.map((w,i)=><button key={i} onClick={()=>useWindow(w)}><strong>{w.label}</strong><small>Use this window for a watch plan →</small></button>)}</div></section>
        </div>

        {slots.length>0&&<section className="calendar-slot-list"><div className="label-between"><h4>Saved calendar times</h4><span>{slots.length} items</span></div>{slots.slice(0,8).map(slot=><div key={slot.id}><span><b>{slot.title}</b><small>{new Date(slot.start_at).toLocaleString()} – {new Date(slot.end_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</small></span><button onClick={async()=>{await api.deleteCalendarBusySlot(slot.id);refreshSlots()}}>Remove</button></div>)}</section>}
        {calendarMessage&&<p className="helper-success calendar-message">{calendarMessage}</p>}
      </div>}
    </Modal>
  )
}

function CompareModal({ open, onClose, movies, compareIds, toggleCompare, user, onNeedAuth }) {
  const MODES = [
    ['best_mood','Best for My Mood'],['best_quality','Best Quality'],['shortest','Shortest Option'],
    ['most_exciting','Most Exciting'],['safest_group','Safest Group Choice'],['different','Something Different']
  ]
  const [mood, setMood] = useState('Relaxed')
  const [mode, setMode] = useState('best_mood')
  const [freeMinutes, setFreeMinutes] = useState(120)
  const [scenario, setScenario] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const selected = movies.filter(m => compareIds.includes(m.id))
  const movieColor = id => {
    const selectedIndex = compareIds.findIndex(movieId => String(movieId) === String(id))
    return COMPARISON_COLORS[(selectedIndex < 0 ? 0 : selectedIndex) % COMPARISON_COLORS.length]
  }

  useEffect(() => {
    if (!open) { setResult(null); setScenario('') }
  }, [open])

  const run = async (scenarioOverride = scenario) => {
    if (!user) { onNeedAuth(); return }
    if (selected.length < 2) return
    setBusy(true)
    try {
      const response=await api.compare({
        movie_ids: selected.map(m => m.id), mood, mode,
        free_minutes: Number(freeMinutes) || null,
        scenario: scenarioOverride?.trim() || null,
        user_note: null
      })
      setResult(response)
    } catch (e) { setResult({ error:e.message }) }
    finally { setBusy(false) }
  }

  const Radar = ({rows}) => {
    const criteria=[['mood_fit','Mood'],['genre_fit','Genre'],['rating_fit','Rating'],['time_fit','Time'],['pace_fit','Pace'],['history_fit','Personal']]
    const size=300,c=150,r=104
    const point=(i,val=100)=>{const a=-Math.PI/2+i*2*Math.PI/criteria.length;const rr=r*(val/100);return [c+Math.cos(a)*rr,c+Math.sin(a)*rr]}
    return <div className="radar-wrap"><svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Multi-criteria radar comparison">
      {[25,50,75,100].map(level=><polygon key={level} className="radar-grid" points={criteria.map((_,i)=>point(i,level).join(',')).join(' ')}/>) }
      {criteria.map(([,label],i)=>{const [x,y]=point(i,116);return <text key={label} x={x} y={y} textAnchor="middle" dominantBaseline="middle">{label}</text>})}
      {rows.slice(0,4).map(row=><polygon key={row.id} className="radar-shape" style={{fill:movieColor(row.id),stroke:movieColor(row.id)}} points={criteria.map(([key],i)=>point(i,row[key]).join(',')).join(' ')}/>) }
    </svg><div className="radar-legend" aria-label="Radar chart movie colours">{rows.slice(0,4).map(r=><span key={r.id}><i className="radar-dot" style={{backgroundColor:movieColor(r.id)}} aria-hidden="true"/><strong>{r.title}</strong></span>)}</div></div>
  }

  const RatingMoodComparison = ({rows}) => <div className="rating-mood-list">
    {rows.map(row=><article key={row.id} style={{'--series-color':movieColor(row.id)}}>
      <header><i aria-hidden="true"/><strong>{row.title}</strong></header>
      <div className="rating-mood-metric"><div><span>Catalogue rating</span><b>{row.rating}/10</b></div><div className="rating-mood-track"><i style={{width:`${Math.max(0,Math.min(100,Number(row.rating)*10))}%`,backgroundColor:movieColor(row.id)}}/></div></div>
      <div className="rating-mood-metric"><div><span>Mood match · {mood}</span><b>{row.mood_fit}%</b></div><div className="rating-mood-track"><i style={{width:`${Math.max(0,Math.min(100,row.mood_fit))}%`,backgroundColor:movieColor(row.id)}}/></div></div>
    </article>)}
  </div>

  return (
    <Modal open={open} onClose={onClose} title="Compare your shortlist"  wide>
      <div className="compare-control-grid">
        <label>Decision mode<select value={mode} onChange={e=>setMode(e.target.value)}>{MODES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        <label>Current mood<select value={mood} onChange={e=>setMood(e.target.value)}>{MOODS.map(m=><option key={m}>{m}</option>)}</select></label>
        <label>Available time<input type="number" min="30" max="600" value={freeMinutes} onChange={e=>setFreeMinutes(e.target.value)} /><span className="input-suffix">min</span></label>
      </div>
      <p className="compare-intro">Select 2–4 films to compare. CineSense evaluates them using catalogue facts and your preferences (mood, time, group safety) and recommends the best fit for your situation.</p>

      <div className="selected-strip">
        {selected.length===0?<div className="empty-inline">No movies selected. Use the + button on movie cards.</div>:selected.map(movie=><button key={movie.id} onClick={()=>toggleCompare(movie.id)}><Poster movie={movie} compact/><span>{movie.title}</span><b>×</b></button>)}
      </div>
      <div className="compare-primary-actions"><button className="btn-primary" disabled={selected.length<2||busy} onClick={()=>run('')}>{busy?'Comparing…':`Compare ${selected.length || ''} movies`}</button></div>

      {result?.error&&<div className="error-box">{result.error}</div>}
      {result?.rows&&<div className="comparison-output comparison-v2">
        <div className="comparison-summary"><div><div className="section-kicker">{result.mode_label}</div><h3>{result.rows.find(r=>r.id===result.winner_id)?.title} is the best fit</h3><p>{cleanAssistantText(result.explanation)}</p></div></div>
        {result.scenario&&<div className="ranking-change-box"><strong>What changed?</strong>{result.ranking_changes?.length?result.ranking_changes.map((x,i)=><p key={i}>↕ {x}</p>):<p>The new condition did not change the ranking, but the suitability and risk scores were recalculated.</p>}</div>}

        <div className="comparison-quick-list">{result.rows.map(row=>{const minutes=Number(result.free_minutes||freeMinutes);const difference=minutes-row.runtime;return <article className={row.id===result.winner_id?'quick-winner':''} style={{'--series-color':movieColor(row.id)}} key={row.id}>
          <span className="quick-rank">#{row.rank}</span><Poster movie={row} compact/><div className="quick-copy"><div className="quick-title"><h4>{row.title}</h4><strong>{row.overall_score}% fit</strong></div><p>{row.runtime} min · ★ {row.rating} · {row.tone}</p><div className="quick-metrics"><span>Mood {row.mood_fit}%</span><span>Genre {row.genre_fit}%</span><span>{difference>=0?`Fits with ${difference} min spare`:`${Math.abs(difference)} min over your time`}</span></div><small>{row.risk_reasons?.[0]}</small></div><span className={`risk-badge risk-${row.risk_level.toLowerCase()}`}>{row.risk_level} risk</span>
        </article>})}</div>

        <section className="what-if-box">
          <div><div className="section-kicker">TRY ANOTHER SITUATION</div><h3>Change one condition. Keep the same movies.</h3><p>For example: “What if I only have 90 minutes?”, “less intense”, “rating matters more than mood”, or “remove horror”.</p></div>
          <div className="what-if-input"><input value={scenario} onChange={e=>setScenario(e.target.value)} placeholder="What if I only have 90 minutes?" aria-label="Describe a different comparison situation" onKeyDown={e=>{if(e.key==='Enter')run()}}/><button disabled={selected.length<2||busy||!scenario.trim()} onClick={()=>run()}>Update result</button></div>
        </section>

        <div className="comparison-details">
        <div className="comparison-weight-explainer"><strong>How CineSense weighted this decision</strong><div className="weight-pills">{Object.entries(result.weights||{}).map(([k,v])=><span key={k}>{k} {v}%</span>)}</div></div>
        <div className="table-scroll"><table><thead><tr><th>Rank</th><th>Movie</th><th>Suitability</th><th>Mood</th><th>Genre</th><th>Time</th><th>Rating</th><th>Risk</th></tr></thead><tbody>{result.rows.map(row=><tr className={row.id===result.winner_id?'winner-row':''} style={{'--series-color':movieColor(row.id)}} key={row.id}><td>#{row.rank}{row.rank_change?` (${row.rank_change>0?'↑':'↓'}${Math.abs(row.rank_change)})`:''}</td><td>{row.id===result.winner_id?'✦ ':''}{row.title}</td><td><b>{row.overall_score}%</b></td><td>{row.mood_fit}%</td><td>{row.genre_fit}%</td><td>{row.time_fit}%</td><td>{row.rating}</td><td><span className={`risk-badge risk-${row.risk_level.toLowerCase()}`}>{row.risk_level}</span></td></tr>)}</tbody></table></div>

        <div className="comparison-chart-grid">
          <section className="chart-card"><h3>Overall suitability</h3><p>Weighted by the selected AI decision mode.</p><div className="suitability-bars">{result.rows.map(r=><div key={r.id}><span>{r.title}</span><div><i style={{width:`${r.overall_score}%`,backgroundColor:movieColor(r.id)}}/></div><b>{r.overall_score}%</b></div>)}</div></section>
          <section className="chart-card"><h3>Mood compatibility</h3><p>How closely catalogue mood tags match {mood}.</p><div className="mood-bars">{result.rows.map(r=><div key={r.id}><span>{r.title}</span><div><i style={{width:`${r.mood_fit}%`,backgroundColor:movieColor(r.id)}}/></div><b>{r.mood_fit}%</b></div>)}</div></section>
          <section className="chart-card"><h3>Runtime comparison</h3><p>Bar colours identify each movie; the label shows whether it fits within {result.free_minutes||freeMinutes} minutes.</p><div className="runtime-bars">{result.rows.map(r=>{const left=(result.free_minutes||freeMinutes)-r.runtime;return <div key={r.id}><span>{r.title}</span><div><i style={{width:`${Math.min(100,(r.runtime/Math.max(Number(result.free_minutes||freeMinutes),r.runtime))*100)}%`,backgroundColor:movieColor(r.id)}}/></div><b>{left>=0?`${left}m left`:`${Math.abs(left)}m over`}</b></div>})}</div></section>
          <section className="chart-card"><h3>Disadvantages</h3><p>Potential disadvantages before you commit.</p><div className="risk-list">{result.rows.map(r=><article key={r.id} style={{'--series-color':movieColor(r.id)}}><div><strong>{r.title}</strong><span className={`risk-badge risk-${r.risk_level.toLowerCase()}`}>{r.risk_level} · {r.risk_score}%</span></div><p>{r.risk_reasons.join(' ')}</p></article>)}</div></section>
        </div>

        <div className="comparison-chart-grid chart-wide"><section className="chart-card"><h3>Multi-criteria radar</h3><p>Six grounded factors, limited to four shortlisted movies for readability.</p><Radar rows={result.rows}/></section></div>
        </div>
      </div>}
    </Modal>
  )
}


function FamilyModal({ open, onClose, user }) {
  const genreOptions=['Action','Adventure','Animation','Comedy','Crime','Drama','Fantasy','Horror','Romance','Science Fiction','Thriller']
  const moodOptions=['Happy','Relaxed','Sad/Cathartic','Thrilled','Romantic','Nostalgic']
  const emptyEditor={id:null,name:'',preferred_genres:[],disliked_genres:[],preferred_moods:[]}
  const [profiles,setProfiles]=useState([])
  const [editor,setEditor]=useState(emptyEditor)
  const [selected,setSelected]=useState([])
  const [requestText,setRequestText]=useState('')
  const [groupMood,setGroupMood]=useState('')
  const [minutes,setMinutes]=useState(180)
  const [group,setGroup]=useState(null)
  const [compareIds,setCompareIds]=useState([])
  const [comparison,setComparison]=useState(null)
  const [votes,setVotes]=useState({})
  const [result,setResult]=useState(null)
  const [history,setHistory]=useState(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [household,setHousehold]=useState(null)
  const [inviteEmail,setInviteEmail]=useState('')
  const [inviteRole,setInviteRole]=useState('member')
  const [inviteLink,setInviteLink]=useState('')

  const load=async()=>{
    if(!open||!user)return
    try{const [rows,home]=await Promise.all([api.profiles(),api.familyHousehold()]);setProfiles(rows);setHousehold(home);setError('')}catch(e){setError(e.message)}
  }
  useEffect(()=>{if(open){load();setGroup(null);setComparison(null);setResult(null);setCompareIds([]);setVotes({});setHistory(null);setNotice('');const token=new URLSearchParams(window.location.search).get('family_invite');if(token){api.acceptFamilyInvite(token).then(r=>{setNotice(r.message);window.history.replaceState({},'',window.location.pathname);load()}).catch(e=>setError(e.message))}}},[open,user?.id])

  const inviteMember=async()=>{
    if(!inviteEmail.trim()){setError('Enter the family member email address.');return}
    setBusy(true);try{const r=await api.inviteFamilyMember({email:inviteEmail.trim(),role:inviteRole});setInviteLink(`${window.location.origin}${r.invite_path}`);setInviteEmail('');setNotice('Invitation created. Copy and share the link below.');await load()}catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const changeMemberRole=async(id,role)=>{setBusy(true);try{await api.updateFamilyMemberRole(id,role);setNotice('Family member role updated.');await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const removeMember=async id=>{if(!confirm('Remove this user from the Family plan?'))return;setBusy(true);try{await api.removeFamilyMember(id);setNotice('Family member removed.');await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const copyInvite=async()=>{try{await navigator.clipboard.writeText(inviteLink);setNotice('Invite link copied.')}catch{setNotice('Copy the invite link shown below.')}}

  const toggleList=(key,value)=>setEditor(e=>({...e,[key]:e[key].includes(value)?e[key].filter(x=>x!==value):[...e[key],value]}))
  const startNew=()=>{setEditor(emptyEditor);setHistory(null)}
  const editProfile=p=>{setEditor({id:p.id,name:p.name,preferred_genres:p.preferences?.preferred_genres||[],disliked_genres:p.preferences?.disliked_genres||[],preferred_moods:p.preferences?.preferred_moods||[]});setHistory(null)}
  const saveProfile=async()=>{
    if(!editor.name.trim()){setError('Enter a profile display name.');return}
    setBusy(true)
    try{
      const body={name:editor.name.trim(),preferred_genres:editor.preferred_genres,disliked_genres:editor.disliked_genres,preferred_moods:editor.preferred_moods}
      if(editor.id) await api.updateProfile(editor.id,body); else await api.createProfile(body)
      setEditor(emptyEditor);setNotice(editor.id?'Profile updated.':'Profile created.');await load()
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const switchTo=async id=>{setBusy(true);try{await api.switchProfile(id);setNotice('Active profile switched. Recommendations and watch history now use this profile.');await load()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const remove=async id=>{if(!confirm('Delete this family profile and its private watch history?'))return;setBusy(true);try{await api.deleteProfile(id);setSelected(x=>x.filter(v=>v!==id));if(editor.id===id)setEditor(emptyEditor);await load();setNotice('Profile removed.')}catch(e){setError(e.message)}finally{setBusy(false)}}
  const showHistory=async p=>{setBusy(true);try{const [prefs,rows]=await Promise.all([api.profilePreferences(p.id),api.profileHistory(p.id)]);setHistory({profile:p,prefs,rows});setError('')}catch(e){setError(e.message)}finally{setBusy(false)}}
  const toggleMember=id=>setSelected(x=>x.includes(id)?x.filter(v=>v!==id):[...x,id].slice(0,5))

  const createChoice=async()=>{
    if(selected.length<2){setError('Choose at least two participating family profiles.');return}
    setBusy(true)
    try{
      const response=await api.groupChoice({profile_ids:selected,free_minutes:Number(minutes)||180,mood:groupMood||null,request_text:requestText})
      setGroup(response);setComparison(null);setResult(null);setCompareIds([]);setVotes({});setError('');setNotice('Group session created. Consensus scores consider every selected member.')
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const toggleCompare=id=>setCompareIds(x=>x.includes(id)?x.filter(v=>v!==id):(x.length<4?[...x,id]:x))
  const compare=async()=>{
    if(!group?.session_id||compareIds.length<2){setError('Select 2–4 group recommendations to compare.');return}
    setBusy(true);try{setComparison(await api.groupCompare(group.session_id,compareIds));setError('')}catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const castVote=async(profileId)=>{
    const movieId=Number(votes[profileId]);if(!movieId){setError('Choose a movie before voting.');return}
    setBusy(true);try{const r=await api.groupVote(group.session_id,profileId,movieId);setResult(r);setError('')}catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const participants=household?.participants||[]
  const managedIds=new Set(participants.filter(p=>p.participant_type==='managed_profile').map(p=>p.id))
  const managedProfiles=profiles.filter(p=>managedIds.has(p.id))

  return <Modal open={open} onClose={onClose} title="Family profiles & group choice" eyebrow="5 PRIVATE PROFILES · CONSENSUS SCORING · HUMAN VOTING" wide>
    {user?.plan!=='family'&&!household?<div className="empty-card"><div className="big-symbol">⌂</div><h3>Family plan feature</h3><p>Upgrade to Family or accept a household invitation to use shared profiles, preferences, and group decisions.</p></div>:<>
      {error&&<div className="error-box">{error}</div>}{notice&&<div className="success-box">{notice}</div>}
      {household&&<section className="family-household family-panel">
        <div className="family-section-head"><div><span className="overline">FAMILY HOUSEHOLD</span><h3>Plan owner & members</h3><p>{household.members.length}/{household.max_members} places used · Your role: {household.current_role}</p></div>{household.current_role==='owner'&&<span className="owner-badge">Owner</span>}</div>
        <div className="household-members">{household.members.map(m=><div className="household-member" key={m.id}><div><strong>{m.email}</strong><small>{m.role}</small></div>{m.is_owner?<span className="owner-badge">Owner</span>:household.can_manage?<><select value={m.role} onChange={e=>changeMemberRole(m.id,e.target.value)} disabled={busy}><option value="member">Member</option><option value="child">Child</option></select><button className="danger-link" onClick={()=>removeMember(m.id)} disabled={busy}>Remove</button></>:null}</div>)}</div>
        {household.can_manage&&<div className="household-invite"><input type="email" value={inviteEmail} onChange={e=>setInviteEmail(e.target.value)} placeholder="family.member@example.com"/><select value={inviteRole} onChange={e=>setInviteRole(e.target.value)}><option value="member">Member</option><option value="child">Child</option></select><button className="btn-primary" onClick={inviteMember} disabled={busy||household.members.length+household.pending_invites.length>=household.max_members}>Send invite</button></div>}
        {inviteLink&&<div className="invite-link"><code>{inviteLink}</code><button className="btn-secondary" onClick={copyInvite}>Copy link</button></div>}
        {!!household.pending_invites.length&&<div className="pending-invites"><strong>Pending invitations</strong>{household.pending_invites.map(i=><span key={i.id}>{i.email} · expires {new Date(i.expires_at).toLocaleDateString()}</span>)}</div>}
      </section>}
      <div className="family-layout">
        <section className="family-panel">
          <div className="family-section-head"><div><span className="overline">01 · MANAGED PROFILES</span><h3>Children & guests</h3><p>Real members use their own accounts. Profiles are only for children or guests without a login.</p></div>{household?.can_manage&&<button className="btn-secondary" onClick={startNew}>+ Child / guest</button>}</div>
          {!household?.can_manage&&<div className="account-profile-note"><strong>Your account is your profile</strong><p>Your preferences, mood history, watch history, and votes stay attached to your own CineSense login. You do not need another profile.</p></div>}
          {household?.can_manage&&<><div className="profile-grid enhanced">{managedProfiles.map(p=><article className={`family-profile ${p.active?'active':''}`} key={p.id}>
            <button className="profile-main" onClick={()=>switchTo(p.id)} disabled={busy}><span>{p.name?.[0]?.toUpperCase()||'P'}</span><strong>{p.name}</strong><small>{p.active?'✓ Active profile':'Use this profile'}</small></button>
            <div className="profile-mini-stats"><span>{p.history_count||0} watched</span><span>{p.preferences?.preferred_genres?.slice(0,2).join(' · ')||'No saved genres'}</span></div>
            <div className="profile-actions"><button onClick={()=>editProfile(p)}>Edit</button><button onClick={()=>showHistory(p)}>History</button><button className="danger-link" onClick={()=>remove(p.id)}>Delete</button></div>
          </article>)}{!managedProfiles.length&&<div className="empty-managed-profile"><span>Optional</span><p>Add a child or guest only when they will not have their own CineSense login.</p></div>}</div>

          <div className="profile-editor">
            <div className="family-section-head compact"><div><span className="overline">PROFILE SETTINGS</span><h4>{editor.id?'Edit profile':'Create profile'}</h4></div></div>
            <label>Display name<input value={editor.name} onChange={e=>setEditor({...editor,name:e.target.value})} maxLength={50} placeholder="e.g. Kids, Guest"/></label>
            <div className="preference-block"><strong>Preferred genres</strong><div className="choice-chips">{genreOptions.map(g=><button type="button" className={editor.preferred_genres.includes(g)?'active':''} onClick={()=>toggleList('preferred_genres',g)} key={g}>{g}</button>)}</div></div>
            <div className="preference-block"><strong>Disliked genres</strong><div className="choice-chips danger">{genreOptions.map(g=><button type="button" className={editor.disliked_genres.includes(g)?'active':''} onClick={()=>toggleList('disliked_genres',g)} key={g}>{g}</button>)}</div></div>
            <div className="preference-block"><strong>Favourite moods</strong><div className="choice-chips">{moodOptions.map(m=><button type="button" className={editor.preferred_moods.includes(m)?'active':''} onClick={()=>toggleList('preferred_moods',m)} key={m}>{m}</button>)}</div></div>
            <div className="form-actions"><button className="btn-primary" disabled={busy} onClick={saveProfile}>{editor.id?'Save profile changes':'Create profile'}</button>{editor.id&&<button className="btn-secondary" onClick={startNew}>Cancel</button>}</div>
          </div>

          {history&&<div className="profile-history-card"><div className="family-section-head compact"><div><span className="overline">PRIVATE HISTORY</span><h4>{history.profile.name}</h4></div><button className="panel-close" onClick={()=>setHistory(null)}>×</button></div><p>Learned genres: {history.prefs.learned_genres?.join(', ')||'Not enough history yet'} · Learned moods: {history.prefs.learned_moods?.join(', ')||'Not enough history yet'}</p><div className="history-list">{history.rows.slice(0,8).map((x,i)=><div key={`${x.movie.id}-${i}`}><strong>{x.movie.title}</strong><span>{x.rating?`${x.rating}/5`:'Watched'}</span></div>)}{!history.rows.length&&<small>No watched movies recorded for this profile yet.</small>}</div></div>}
          </>}
        </section>

        <section className="family-panel group-panel">
          <div className="family-section-head"><div><span className="overline">02 · GROUP SESSION</span><h3>Who is watching?</h3><p>Choose from one combined list of real accounts and optional managed profiles.</p></div></div>
          <div className="participant-list">{participants.map(p=><label className={`participant-choice ${selected.includes(p.id)?'selected':''}`} key={p.id}><input type="checkbox" checked={selected.includes(p.id)} onChange={()=>toggleMember(p.id)}/><span>{p.name?.[0]?.toUpperCase()||'P'}</span><div><strong>{p.name}</strong><small>{p.participant_type==='account'?`${p.role} account`:p.subtitle}</small></div></label>)}</div>
          <div className="group-controls"><label>What do you want tonight?<input value={requestText} onChange={e=>setRequestText(e.target.value)} placeholder="Something funny but not too intense"/></label><div className="two-col"><label>Mood<select value={groupMood} onChange={e=>setGroupMood(e.target.value)}><option value="">Use family pattern</option>{moodOptions.map(m=><option key={m}>{m}</option>)}</select></label><label>Available time<input type="number" min="30" max="600" value={minutes} onChange={e=>setMinutes(e.target.value)}/><small>minutes</small></label></div><button className="btn-primary full" disabled={busy||selected.length<2} onClick={createChoice}>Find group recommendations for {selected.length||0} participants</button></div>

          {group?.results?.length>0&&<div className="group-results advanced"><div className="family-section-head compact"><div><span className="overline">03 · CONSENSUS RESULTS</span><h4>Best compromises</h4></div><span className="session-pill">Session {group.session_id.slice(0,7)}</span></div>{group.results.slice(0,8).map(m=><div className="group-pick scored" key={m.id}><Poster movie={m} compact/><div className="group-pick-main"><div className="group-pick-title"><strong>{m.title}</strong><b>{m.group_score}% consensus</b></div><p>{m.reason}</p><div className="member-score-row">{m.consensus?.member_scores?.map(ms=><span className={ms.conflicts?.length?'conflict':ms.score>=60?'good':''} key={ms.profile_id}>{ms.profile_name} {Math.round(ms.score)}%</span>)}</div></div><label className="compare-check"><input type="checkbox" checked={compareIds.includes(m.id)} onChange={()=>toggleCompare(m.id)}/> Compare</label></div>)}<button className="btn-secondary full" disabled={compareIds.length<2||compareIds.length>4||busy} onClick={compare}>Compare selected ({compareIds.length}/4)</button></div>}

          {comparison&&<div className="group-comparison"><span className="overline">04 · EXPLAINABLE DECISION</span><h4>Why this works for the group</h4><p>{comparison.explanation}</p><div className="consensus-table">{comparison.group_consensus?.map(r=><div className={r.movie_id===comparison.winner_id?'winner':''} key={r.movie_id}><strong>{r.title}</strong><span>{r.group_score}% consensus</span><span>{r.satisfied_members}/{r.member_count} satisfied</span><span>{r.conflict_count} conflicts</span></div>)}</div></div>}

          {group?.results?.length>0&&<div className="family-voting"><span className="overline">05 · FAMILY VOTING</span><h4>Everyone gets a say</h4><p>Each participating profile can cast or change one vote. Final ranking combines 65% compatibility and 35% human vote share.</p>{group.members?.map(member=><div className="vote-row" key={member.id}><strong>{member.name}</strong><select value={votes[member.id]||''} onChange={e=>setVotes({...votes,[member.id]:e.target.value})}><option value="">Choose a movie</option>{group.results.slice(0,8).map(m=><option value={m.id} key={m.id}>{m.title}</option>)}</select><button className="btn-secondary" disabled={busy||!votes[member.id]} onClick={()=>castVote(member.id)}>Cast vote</button></div>)}</div>}

          {result?.winner&&<div className="final-winner"><span className="overline">CURRENT FAMILY WINNER</span><h3>✦ {result.winner.title}</h3><div className="winner-metrics"><span>{result.winner.votes} votes</span><span>{result.winner.group_score}% consensus</span><span>{result.winner.final_score}% final score</span></div><p>{result.explanation}</p><small>{result.votes_cast}/{result.members} participating profiles have voted · Status: {result.status}</small></div>}
        </section>
      </div>
    </>}
  </Modal>
}

function BillingModal({ open, onClose, user, onUser, initialPlan = 'premium' }) {
  const empty = {cardholder_name:'',card_number:'',expiry_month:'',expiry_year:'',cvv:'',billing_address:'',billing_city:'',billing_country:''}
  const [status,setStatus]=useState(null)
  const [profile,setProfile]=useState(null)
  const [form,setForm]=useState(empty)
  const [plan,setPlan]=useState(initialPlan)
  const [error,setError]=useState('')
  const [notice,setNotice]=useState('')
  const [busy,setBusy]=useState(false)
  const [successPlan,setSuccessPlan]=useState('')

  const load=async()=>{
    if(!open||!user)return
    try{
      const [s,p]=await Promise.all([api.billingStatus(),api.paymentProfile()])
      setStatus(s); setProfile(p.payment_profile); setError('')
      if(p.payment_profile){
        setForm(f=>({...f,cardholder_name:p.payment_profile.cardholder_name||'',expiry_month:String(p.payment_profile.expiry_month||''),expiry_year:String(p.payment_profile.expiry_year||''),billing_address:p.payment_profile.billing_address||'',billing_city:p.payment_profile.billing_city||'',billing_country:p.payment_profile.billing_country||''}))
      }
    }catch(e){setError(e.message)}
  }
  useEffect(()=>{setPlan(initialPlan||'premium');setSuccessPlan('');load()},[open,user?.id,initialPlan])

  const cardDigits=form.card_number.replace(/\D/g,'')
  const validCard=cardDigits.length===16
  const save=async e=>{
    e?.preventDefault();setBusy(true);setError('');setNotice('')
    try{
      const r=await api.savePaymentProfile({...form,card_number:cardDigits,expiry_month:Number(form.expiry_month),expiry_year:Number(form.expiry_year)})
      setProfile(r.payment_profile);setForm(f=>({...f,card_number:'',cvv:''}));setNotice('Billing details saved securely for this simulation. Full card numbers and CVV are not stored.')
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const subscribe=async()=>{
    setBusy(true);setError('');setNotice('')
    try{
      if(!profile){setError('Save your billing details first.');return}
      const r=await api.simulateSubscribe(plan);setNotice(`Subscription activated: ${r.plan}. This is a simulated university-project payment.`)
      setStatus(await api.billingStatus());onUser(await api.me());setSuccessPlan(r.plan)
      setTimeout(()=>{onClose?.();window.scrollTo({top:0,behavior:'smooth'})},1800)
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  const remove=async()=>{setBusy(true);try{await api.deletePaymentProfile();setProfile(null);setForm(empty);setNotice('Saved billing profile deleted.')}catch(e){setError(e.message)}finally{setBusy(false)}}
  const cancel=async()=>{setBusy(true);try{await api.simulateCancel();setStatus(await api.billingStatus());onUser(await api.me());setNotice('Subscription cancelled. Your account is now on the Free plan.')}catch(e){setError(e.message)}finally{setBusy(false)}}
  const price=plan==='family'?'$8.99 / month':'$4.99 / month'

  return <Modal open={open} onClose={onClose} title="Subscription & billing" eyebrow="SIMULATED PAYMENT · UNIVERSITY PROJECT" wide>
    {successPlan&&<div className="subscription-success-pop" role="status"><div className="subscription-success-icon">✓</div><h3>Subscription successful!</h3><p>Thank you for choosing CineSense. Your <b>{successPlan.toUpperCase()}</b> plan is now active.</p><small>Taking you back to the home page…</small></div>}
    {!user?<div className="empty-card"><h3>Sign in to subscribe</h3><p>Create or sign in to an account before choosing a plan.</p></div>:<>
      <div className="subscription-summary">
        <div><span>Current plan</span><strong>{user.plan?.toUpperCase()}</strong><small>{status?.status||'No active paid subscription'}</small></div>
        <div className="plan-toggle"><button className={plan==='premium'?'active':''} onClick={()=>setPlan('premium')}>Premium · $4.99</button><button className={plan==='family'?'active':''} onClick={()=>setPlan('family')}>Family · $8.99</button></div>
      </div>
      {error&&<div className="error-box">{error}</div>}{notice&&<div className="success-box">{notice}</div>}
      <div className="billing-grid">
        <form className="billing-form" onSubmit={save}>
          <div className="form-title"><div><h3>Billing details</h3><p>Simulation only. Enter a Luhn-valid 16-digit test card, for example 4242 4242 4242 4242.</p></div>{profile&&<span className="saved-badge">Saved · {profile.card_brand} •••• {profile.card_last4}</span>}</div>
          <label>Cardholder name<input value={form.cardholder_name} onChange={e=>setForm({...form,cardholder_name:e.target.value})} required placeholder="Name on card"/></label>
          <label>Card number<input inputMode="numeric" value={form.card_number} onChange={e=>setForm({...form,card_number:e.target.value.replace(/[^\d ]/g,'').slice(0,19)})} required placeholder={profile?`Re-enter card to update (saved ${profile.card_brand} •••• ${profile.card_last4})`:'4242 4242 4242 4242'}/><small className={form.card_number&&!validCard?'field-error':'field-help'}>{form.card_number&&!validCard?'Enter exactly 16 digits.':'16 digits; validated before saving.'}</small></label>
          <div className="field-pair"><label>Expiry month<input type="number" min="1" max="12" value={form.expiry_month} onChange={e=>setForm({...form,expiry_month:e.target.value})} required/></label><label>Expiry year<input type="number" min="2026" max="2100" value={form.expiry_year} onChange={e=>setForm({...form,expiry_year:e.target.value})} required/></label><label>CVV<input inputMode="numeric" value={form.cvv} onChange={e=>setForm({...form,cvv:e.target.value.replace(/\D/g,'').slice(0,4)})} required placeholder="123"/></label></div>
          <label>Billing address<input value={form.billing_address} onChange={e=>setForm({...form,billing_address:e.target.value})} required placeholder="Street address"/></label>
          <div className="field-pair two"><label>City<input value={form.billing_city} onChange={e=>setForm({...form,billing_city:e.target.value})} required/></label><label>Country<input value={form.billing_country} onChange={e=>setForm({...form,billing_country:e.target.value})} required/></label></div>
          <div className="billing-form-actions"><button className="btn-secondary" disabled={busy||!validCard||form.cvv.length<3}>{profile?'Update billing details':'Save billing details'}</button>{profile&&<button className="danger-link" type="button" disabled={busy} onClick={remove}>Delete saved details</button>}</div>
        </form>
        <aside className="checkout-card">
          <span className="overline">SELECTED PLAN</span><h3>{plan==='family'?'Family':'Premium'}</h3><div className="checkout-price">{price}</div>
          <ul>{(plan==='family'?['Up to 5 family profiles','Per-profile viewing preferences','Shared group movie choice','Unlimited AI features']:['Unlimited AI conversations','Mood & time planner','Movie comparisons','Saved watch plans']).map(x=><li key={x}>✓ {x}</li>)}</ul>
          <button className="btn-primary full" disabled={busy||!profile} onClick={subscribe}>{busy?'Processing…':`Simulate ${plan==='family'?'Family':'Premium'} subscription`}</button>
          <p>No money is charged. This flow validates input, stores only masked card metadata and billing information, and persists your selected subscription in the database.</p>
          {user.plan!=='free'&&<button className="danger-link full-link" disabled={busy} onClick={cancel}>Cancel current subscription</button>}
        </aside>
      </div>
    </>}
  </Modal>
}

function AdminModal({ open, onClose, onCatalogueChanged }) {
  const [tab,setTab]=useState('overview'),[overview,setOverview]=useState(null),[movies,setMovies]=useState([]),[users,setUsers]=useState([]),[security,setSecurity]=useState(null)
  const [events,setEvents]=useState([]),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[trailer,setTrailer]=useState(''),[featured,setFeatured]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const load=async()=>{if(!open)return;setError('');try{const [o,m,u,sec,ev]=await Promise.all([api.adminOverview(),api.adminMovies(''),api.adminUsers(),api.adminSecurity(),api.adminSecurityEvents()]);setOverview(o);setMovies(m);setUsers(u);setSecurity(sec);setEvents(ev)}catch(e){setError(e.message)}}
  useEffect(()=>{load()},[open])
  const find=async()=>{setBusy(true);try{setMovies(await api.adminMovies(query))}catch(e){setError(e.message)}finally{setBusy(false)}}
  const importPopular=async()=>{setBusy(true);setError('');setNotice('');try{const r=await api.adminImportPopular(5);setNotice(`Catalogue updated: ${r.added} new popular movies imported. Total ${r.total}.`);await load();onCatalogueChanged?.()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const enrichProducers=async()=>{setBusy(true);setError('');setNotice('');try{const r=await api.adminEnrichProducers(120);setNotice(`Producer enrichment complete: ${r.movies_with_verified_producers} of ${r.movies_checked} checked movies now have verified producer credits.`)}catch(e){setError(e.message)}finally{setBusy(false)}}
  const choose=m=>{setSelected(m);setTrailer(m.trailer_youtube_url||'');setFeatured(Boolean(m.featured));setNotice('');setError('')}
  const saveMedia=async()=>{if(!selected)return;setBusy(true);try{await api.adminUpdateMovie(selected.id,{trailer_youtube_url:trailer,featured});setNotice('Movie media settings saved.');const m=await api.adminMovies(query);setMovies(m);const refreshed=m.find(x=>x.id===selected.id);if(refreshed)setSelected(refreshed);onCatalogueChanged?.()}catch(e){setError(e.message)}finally{setBusy(false)}}
  const upload=async(kind,file)=>{if(!selected||!file)return;setBusy(true);try{const r=await api.adminUploadMovieImage(selected.id,kind,file);setNotice(`${kind==='poster'?'Poster':'Backdrop'} uploaded successfully.`);setSelected(x=>({...x,...r.movie}));setMovies(await api.adminMovies(query));onCatalogueChanged?.()}catch(e){setError(e.message)}finally{setBusy(false)}}
  return <Modal open={open} onClose={onClose} title="CineSense administration" eyebrow="CATALOGUE · MEDIA · USERS · SECURITY" wide>
    <div className="admin-tabs"><button className={tab==='overview'?'active':''} onClick={()=>setTab('overview')}>Overview</button><button className={tab==='movies'?'active':''} onClick={()=>setTab('movies')}>Movie media</button><button className={tab==='users'?'active':''} onClick={()=>setTab('users')}>Users</button><button className={tab==='security'?'active':''} onClick={()=>setTab('security')}>Security</button></div>
    {error&&<div className="error-box">{error}</div>}{notice&&<div className="success-box">{notice}</div>}
    {tab==='overview'&&overview&&<><div className="admin-overview-grid"><div><span>Users</span><strong>{overview.users}</strong></div><div><span>Movies</span><strong>{overview.movies}</strong></div><div><span>Family profiles</span><strong>{overview.family_profiles}</strong></div><div><span>Media uploads</span><strong>{overview.uploads}</strong></div><div><span>TMDB search</span><strong>{overview.tmdb_configured?'Connected':'Needs API key'}</strong></div><div><span>Environment</span><strong>{overview.environment}</strong></div></div><div className="admin-catalogue-action"><div><h3>Expand the movie catalogue</h3><p>With TMDB_API_KEY configured, CineSense can import popular titles in bulk and automatically import search results that are not already local.</p></div><button className="btn-primary" disabled={busy||!overview.tmdb_configured} onClick={importPopular}>{overview.tmdb_configured?'Import popular movies':'Add TMDB key first'}</button></div><div className="admin-catalogue-action"><div><h3>Enrich verified producer credits</h3><p>Producer similarity uses TMDB crew credits stored in a separate table. Run enrichment in batches so “Same producer” can use verified people rather than guessing from studio names.</p></div><button className="btn-secondary" disabled={busy||!overview.tmdb_configured} onClick={enrichProducers}>{overview.tmdb_configured?'Enrich producer data':'Add TMDB key first'}</button></div></>}
    {tab==='movies'&&<div className="admin-movie-layout">
      <div className="admin-movie-list"><div className="admin-search"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find movie to manage" onKeyDown={e=>e.key==='Enter'&&find()}/><button onClick={find}>Search</button></div>{movies.map(m=><button className={selected?.id===m.id?'active':''} key={m.id} onClick={()=>choose(m)}><Poster movie={m} compact/><span><strong>{m.title}</strong><small>{m.year} · {m.poster_url?'Poster ready':'No poster'}</small></span></button>)}</div>
      <div className="admin-media-editor">{selected?<><div className="admin-preview" style={{backgroundImage:selected.backdrop_url?`linear-gradient(180deg,rgba(5,7,11,.15),#0d1017),url(${selected.backdrop_url})`:undefined}}><Poster movie={selected}/><div><span className="overline">MOVIE MEDIA</span><h3>{selected.title}</h3><p>Upload eye-catching artwork and choose the trailer used on the home hero.</p></div></div><label>Poster image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload('poster',e.target.files?.[0])}/></label><label>Backdrop image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>upload('backdrop',e.target.files?.[0])}/></label><label>YouTube trailer URL<input value={trailer} onChange={e=>setTrailer(e.target.value)} placeholder="https://www.youtube.com/watch?v=..."/></label><label className="feature-check"><input type="checkbox" checked={featured} onChange={e=>setFeatured(e.target.checked)}/> Use this movie/trailer as the home-page hero background</label><button className="btn-primary" disabled={busy} onClick={saveMedia}>Save media settings</button><p className="fine-print">Uploads accept JPG, PNG or WebP only and are size/signature validated by the backend.</p></>:<div className="empty-card"><h3>Select a movie</h3><p>Choose a catalogue movie to upload its poster/backdrop or attach a YouTube trailer.</p></div>}</div>
    </div>}
    {tab==='users'&&<div className="admin-user-table">{users.map(u=><div key={u.id}><span className="profile-avatar">{u.display_name?.[0]||'U'}</span><div><strong>{u.display_name}</strong><small>{u.email}</small></div><span>{u.plan}</span><b>{u.is_admin?'ADMIN':'USER'}</b></div>)}</div>}
    {tab==='security'&&security&&<div className="security-dashboard"><div className="security-score"><strong>{security.score}%</strong><span>security controls passing</span></div><div className="security-checks">{security.checks.map(c=><article className={c.passed?'pass':'warn'} key={c.area}><b>{c.passed?'✓':'!'} {c.area}</b><p>{c.detail}</p></article>)}</div><h3>Prompt attack regression tests</h3><div className="prompt-tests">{security.prompt_tests.map((t,i)=><div key={i}><span>{t.blocked?'Blocked':'Allowed'}</span><code>{t.input}</code><small>{t.risk} · score {t.risk_score}</small></div>)}</div><h3>Recent security events</h3><div className="security-event-list">{events.slice(0,20).map((e,i)=><div key={i}><b>{e.category}</b><span>{e.detail}</span><small>{new Date(e.created_at).toLocaleString()}</small></div>)}</div></div>}
  </Modal>
}

function PricingModal({ open, onClose, onChoosePlan }) {
  const [details,setDetails]=useState(null)
  const tiers = [
    {name:'Free',price:'$0',tag:'Start here',features:['Unlimited browsing and movie search','10 AI chat/comparison requests per day','Standard recommendations'],description:'Explore the catalogue and try CineSense before subscribing.'},
    {name:'Premium',price:'$4.99 / month',tag:'Most popular',features:['Unlimited AI chat and comparisons','Mood scheduler and double features','Saved watch plans'],description:'For frequent viewers who want the complete individual CineSense experience.'},
    {name:'Family',price:'$8.99 / month',tag:'Households',features:['Up to 5 profiles','Separate preference history','Group movie-choice tools'],description:'Separate experiences for household members plus shared movie decisions.'},
    {name:'B2B API',price:'$49 / month concept',tag:'For platforms',features:['Recommendation API access','Usage tracking','10,000 included recommendation calls'],description:'A commercial API concept for smaller streaming and OTT providers.'}
  ]
  const choose=tier=>{
    setDetails(tier)
  }
  return <Modal open={open} onClose={onClose} title="Choose the CineSense plan that fits you" eyebrow="SIMPLE · TRANSPARENT · UNIVERSITY-PROJECT BILLING" wide>
    <div className="pricing-grid">
      {tiers.map((tier,index)=><button className={`price-card price-card-button ${index===1?'featured':''}`} key={tier.name} onClick={()=>choose(tier)}>
        <small className="plan-tag">{tier.tag}</small><h3>{tier.name}</h3><div className="price">{tier.price}</div>{tier.features.map(item=><p key={item}>✓ {item}</p>)}<span className="plan-more">View plan details →</span>
      </button>)}
    </div>
    {details&&<div className="plan-detail-panel"><button className="panel-close" onClick={()=>setDetails(null)}>×</button><div><span className="overline">{details.tag}</span><h3>{details.name}</h3><p>{details.description}</p></div><div className="plan-detail-price"><strong>{details.price}</strong>{['Premium','Family'].includes(details.name)&&<button className="btn-primary" onClick={()=>{onClose();onChoosePlan(details.name.toLowerCase())}}>Subscribe to {details.name}</button>}</div></div>}
    <p className="fine-print">Payments are simulated for this university project. Subscription status is still persisted so plan-gated features can be demonstrated end-to-end.</p>
  </Modal>
}

function ResponsibleModal({ open, onClose }) {
  const [fairness, setFairness] = useState(null)
  useEffect(() => { if (open) api.fairness().then(setFairness).catch(console.warn) }, [open])
  return (
    <Modal open={open} onClose={onClose} title="How CineSense uses AI responsibly" eyebrow="PRIVACY · EXPLAINABILITY · FAIRNESS · USER CONTROL" wide>
      <div className="responsible-grid">
        <div><span>🔐</span><h3>Your privacy</h3><p>Sensitive profile and conversation data is protected, and only limited recent conversation context is retained.</p></div>
        <div><span>✦</span><h3>Clear recommendations</h3><p>CineSense explains why a movie fits instead of presenting a recommendation without context.</p></div>
        <div><span>⚑</span><h3>You stay in control</h3><p>You can adjust detected preferences, ignore suggestions, and flag recommendations that do not feel right.</p></div>
        <div><span>◎</span><h3>More balanced choices</h3><p>Recommendations are diversified where possible so one studio or category does not dominate your shortlist.</p></div>
      </div>
      {fairness&&<div className="catalogue-snapshot"><h3>Catalogue diversity snapshot</h3><p>CineSense currently includes {fairness.total_movies || fairness.total || 0} catalogue movies across multiple languages, studios and release periods.</p><p className="muted">This summary is shown to explain the recommendation catalogue without exposing internal system logs or developer metadata.</p></div>}
    </Modal>
  )
}

export default function App() {
  const [movies, setMovies] = useState([])
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [bootError, setBootError] = useState('')
  const [compareIds, setCompareIds] = useState([])
  const [chatOpen, setChatOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [plannerOpen, setPlannerOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)
  const [pricingOpen, setPricingOpen] = useState(false)
  const [responsibleOpen, setResponsibleOpen] = useState(false)
  const [familyOpen, setFamilyOpen] = useState(false)
  const [billingOpen, setBillingOpen] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)
  const [heroData, setHeroData] = useState(null)
  const [billingPlan, setBillingPlan] = useState('premium')
  const [selectedMovie, setSelectedMovie] = useState(null)
  const [similarityMovie, setSimilarityMovie] = useState(null)
  const [detected, setDetected] = useState({ mood: null, genres: [], time_available: null })
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hi — I’m CineSense. Tell me how you feel, what kind of movie you want, ' +
        'or how much free time you have. I’ll keep the conversation natural and explain why each suggestion fits.'
    }
  ])

  const loadApp = async () => {
    setLoading(true)
    setBootError('')

    try {
      const catalogue = await api.movies()
      if (!Array.isArray(catalogue)) throw new Error('Movie catalogue returned an unexpected format.')
      setMovies(catalogue)
      api.siteHero().then(setHeroData).catch(()=>{})
    } catch (e) {
      setBootError(`The frontend could not load the movie catalogue: ${e.message}`)
    }

    try {
      const current = await api.me()
      setUser(current)
    } catch {
      // 401 is expected before the user signs in.
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadApp()
  }, [])

  const logout = async () => {
    try { await api.logout() } catch {}
    setUser(null)
    setMessages([{role:'assistant',content:'You are signed out. Sign in again whenever you want personalised recommendations and saved history.'}])
    setDetected({ mood: null, genres: [], time_available: null })
    setCompareIds([])
  }

  const toggleCompare = id => {
    setCompareIds(current => {
      if (current.includes(id)) return current.filter(x => x !== id)
      return [...current, id].slice(-4)
    })
  }

  const mergeCatalogue = useCallback(rows => {
    setMovies(current => {
      const known=new Set(current.map(movie=>movie.id))
      const additions=(rows||[]).filter(movie=>!known.has(movie.id))
      return additions.length?[...current,...additions]:current
    })
  },[])

  const groups = useMemo(() => {
    const byMood = mood => movies.filter(movie => movie.moods?.includes(mood))
    return [
      ['Top picks right now', 'Strong catalogue ratings across different moods', movies.slice(0, 14)],
      ['Lighten the mood', 'Funny, hopeful and easy to settle into', byMood('Happy')],
      ['Need to decompress?', 'Calmer pacing and warm emotional energy', byMood('Relaxed')],
      ['Keep me on edge', 'Suspense, tension and faster momentum', byMood('Thrilled')],
      ['Date-night energy', 'Romantic stories with different levels of intensity', byMood('Romantic')],
      ['A little nostalgic', 'Comfort, memory and familiar emotional textures', byMood('Nostalgic')],
      ['Let me feel something', 'Emotionally heavier, cathartic choices', byMood('Sad/Cathartic')]
    ]
  }, [movies])

  if (loading) {
    return (
      <div className="splash">
        <div className="logo-mark large">C</div>
        <h1>CineSense AI</h1>
        <p>Connecting the six-agent movie companion…</p>
        <div className="loader"><span/><span/><span/></div>
      </div>
    )
  }

  if (bootError) {
    return (
      <div className="fatal-shell">
        <div className="fatal-card">
          <div className="logo-mark">C</div>
          <div className="overline">STARTUP CONNECTION CHECK</div>
          <h1>CineSense could not finish loading</h1>
          <p>{bootError}</p>
          <p>
            Confirm the backend window still says
            <code> Uvicorn running on http://127.0.0.1:8000 </code>.
          </p>
          <button onClick={loadApp}>Try again</button>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <button className="brand-button" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <span className="logo-mark">C</span>
          <span>CineSense <b>AI</b></span>
        </button>

        <div className="nav-links">
          <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>Home</button>
          <button onClick={() => setPlannerOpen(true)}>Watch planner</button>
          <button onClick={() => setCompareOpen(true)}>Compare <i>{compareIds.length}</i></button>
          <button onClick={() => setResponsibleOpen(true)}>Responsible AI</button>
          <button onClick={() => setFamilyOpen(true)}>Family</button>
          <button onClick={() => setPricingOpen(true)}>Plans</button>
          {user?.is_admin&&<button className="admin-nav-link" onClick={()=>setAdminOpen(true)}>Admin</button>}
        </div>

        <div className="nav-actions">
          <button className="round-btn" onClick={() => setChatOpen(true)}>✦</button>
          {user ? (
            <div className="account-actions">
              <button className="profile-chip" onClick={() => setBillingOpen(true)} title="Manage subscription">
                <span>{user.display_name?.[0] || 'U'}</span><strong>{user.display_name}</strong><small>{user.plan}</small>
              </button>
              <button className="logout-btn" onClick={logout}>Logout</button>
            </div>
          ) : (
            <button className="btn-primary compact-btn" onClick={() => setAuthOpen(true)}>
              Sign in
            </button>
          )}
        </div>
      </nav>

      <header className="hero">
        {heroData?.trailer_youtube_url&&<div className="hero-video-wrap"><iframe title={`${heroData?.movie?.title||'Featured movie'} trailer`} src={`${heroData.trailer_youtube_url}?autoplay=1&mute=1&controls=0&loop=1&playlist=${heroData.trailer_youtube_url.split('/').pop()}&modestbranding=1&rel=0&playsinline=1`} allow="autoplay; encrypted-media; picture-in-picture" tabIndex="-1" /></div>}
        {!heroData?.trailer_youtube_url&&heroData?.movie?.backdrop_url&&<div className="hero-backdrop" style={{backgroundImage:`url(${heroData.movie.backdrop_url})`}}/>}
        <div className="hero-media-overlay" />
        <div className="hero-glow hero-glow-one" />
        <div className="hero-glow hero-glow-two" />
        <div className="hero-content">
          <div className="overline">✦ MOOD-AWARE MOVIE COMPANION</div>
          <h1>Stop browsing.<br/><span>Start feeling.</span></h1>
          <p>
            Tell CineSense what kind of night you’re having. Six specialised agents
            turn your mood, taste and free time into grounded movie choices—with
            reasons you can actually understand.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => setChatOpen(true)}>✦ Talk to CineSense</button>
            <button className="btn-secondary" onClick={() => setPlannerOpen(true)}>◷ Plan my movie night</button>
          </div>
          <div className="hero-facts">
            <span>✓ Explainable recommendations</span>
            <span>•</span>
            <span>Personalised movie discovery</span>
            <span>•</span>
            <span>You control your mood preferences</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        <section className="conversation-banner">
          <div className="banner-copy">
            <span className="ai-orb">✦</span>
            <div>
              <strong>Not sure what to search for?</strong>
              <p>
                Describe your day instead: “I’m exhausted, need something funny,
                and only have 90 minutes.”
              </p>
            </div>
          </div>
          <button className="btn-primary" onClick={() => setChatOpen(true)}>
            ✦ Start a natural conversation
          </button>
        </section>

        <MovieSearch movies={movies} onOpenMovie={setSelectedMovie} onCatalogueExpand={mergeCatalogue} />

        {groups.map(([title, subtitle, list]) =>
          list.length > 0 ? (
            <MovieRow
              key={title}
              title={title}
              subtitle={subtitle}
              movies={list}
              compareIds={compareIds}
              toggleCompare={toggleCompare}
              user={user}
              onNeedAuth={() => setAuthOpen(true)}
              onOpenMovie={setSelectedMovie}
            />
          ) : null
        )}
      </main>

      <footer>
        <div className="brand-button">
          <span className="logo-mark">C</span>
          <span>CineSense AI</span>
        </div>
        <p>
          Educational multi-agent movie discovery platform · AI recommendations can be corrected or flagged.
        </p>
      </footer>

      <button className="floating-chat" onClick={() => setChatOpen(true)}>
        ✦ <span>Ask CineSense</span>
      </button>

      <ChatDrawer
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        user={user}
        onNeedAuth={() => setAuthOpen(true)}
        detected={detected}
        setDetected={setDetected}
        messages={messages}
        setMessages={setMessages}
      />

      <MovieDetailModal
        movie={selectedMovie}
        open={Boolean(selectedMovie)}
        onClose={() => setSelectedMovie(null)}
        selected={selectedMovie ? compareIds.includes(selectedMovie.id) : false}
        onCompare={toggleCompare}
        onFindSimilar={movie=>{setSimilarityMovie(movie);setSelectedMovie(null)}}
        user={user}
        onNeedAuth={() => setAuthOpen(true)}
      />

      <SimilarityModal
        movie={similarityMovie}
        open={Boolean(similarityMovie)}
        onClose={() => setSimilarityMovie(null)}
        user={user}
        onNeedAuth={() => setAuthOpen(true)}
        compareIds={compareIds}
        toggleCompare={toggleCompare}
        onOpenCompare={() => setCompareOpen(true)}
      />

      <AuthModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        onUser={setUser}
      />

      <ConsentModal user={user} onUser={setUser} />

      <PlannerModal
        open={plannerOpen}
        onClose={() => setPlannerOpen(false)}
        user={user}
        onNeedAuth={() => setAuthOpen(true)}
      />

      <CompareModal
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        movies={movies}
        compareIds={compareIds}
        toggleCompare={toggleCompare}
        user={user}
        onNeedAuth={() => setAuthOpen(true)}
      />

      <FamilyModal open={familyOpen} onClose={() => setFamilyOpen(false)} user={user} />

      <BillingModal open={billingOpen} onClose={() => setBillingOpen(false)} user={user} onUser={setUser} initialPlan={billingPlan} />

      <PricingModal
        open={pricingOpen}
        onClose={() => setPricingOpen(false)}
        onChoosePlan={plan => { setBillingPlan(plan); setBillingOpen(true) }}
      />

      <AdminModal open={adminOpen} onClose={()=>setAdminOpen(false)} onCatalogueChanged={()=>{api.movies().then(setMovies);api.siteHero().then(setHeroData)}} />

      <ResponsibleModal
        open={responsibleOpen}
        onClose={() => setResponsibleOpen(false)}
      />
    </div>
  )
}
