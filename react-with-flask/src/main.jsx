import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from 'react-oidc-context'
import './index.css'
import App from './App.jsx'

// Cognito OIDC Configuration
const cognitoAuthConfig = {
  authority: "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_1QVpsNMpo",
  client_id: "2v7frs8eeard997vkfaq1smslt",
  redirect_uri: "http://localhost:5173/", // Fixed to match actual dev server port
  response_type: "code",
  scope: "openid email phone profile", // Added 'profile' scope to get name and other profile info
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider {...cognitoAuthConfig}>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
