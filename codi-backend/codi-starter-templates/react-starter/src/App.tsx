import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-container">
          <span className="logo">🚀</span>
          <h1> {"{{PROJECT_TITLE}}"}</h1>
        </div>
        <p className="subtitle">Built with <span className="highlight">Codi</span></p>
      </header>

      <main className="main-content">
        <div className="card">
          <button onClick={() => setCount((count) => count + 1)}>
            Count is {count}
          </button>
          <p className="hint">Click the button to test state management</p>
        </div>

        <div className="features">
          <div className="feature">
            <span className="feature-icon">⚛️</span>
            <h3>React 19</h3>
            <p>Latest React with Concurrent Features</p>
          </div>
          <div className="feature">
            <span className="feature-icon">📘</span>
            <h3>TypeScript</h3>
            <p>Full type safety out of the box</p>
          </div>
          <div className="feature">
            <span className="feature-icon">⚡</span>
            <h3>Vite</h3>
            <p>Lightning fast HMR and builds</p>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Created with ❤️ by Codi AI</p>
      </footer>
    </div>
  )
}

export default App
