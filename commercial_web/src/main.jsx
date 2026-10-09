import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthProvider } from './AuthShell'
import './styles.css'
import { installZenithNativeApiBridge } from './nativeApiBridge.js'

// Before React effects: native bundles route backend requests to trusted HTTPS.
// The existing website keeps original same-origin requests unchanged.
installZenithNativeApiBridge()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
