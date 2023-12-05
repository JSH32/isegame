// import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

// StrictMode causes sockets to be messed up.
ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
  <App />
  // </React.StrictMode>,
)
