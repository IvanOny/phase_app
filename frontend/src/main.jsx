import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import BurpeeChallenge from './components/Burpee/BurpeeChallenge.jsx'

const _token = new URLSearchParams(window.location.search).get('token');

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {_token ? <BurpeeChallenge token={_token} /> : <App />}
  </StrictMode>,
)
