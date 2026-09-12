import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('CineSense frontend error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fatal-shell">
          <div className="fatal-card">
            <div className="logo-mark">C</div>
            <p className="overline">FRONTEND DIAGNOSTIC</p>
            <h1>CineSense hit a browser-side error</h1>
            <p>
              The backend can still be healthy. This panel is intentionally visible
              so a JavaScript error can never leave you with an unexplained black screen.
            </p>
            <pre>{String(this.state.error?.stack || this.state.error?.message || this.state.error)}</pre>
            <button onClick={() => window.location.reload()}>Reload CineSense</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
)
