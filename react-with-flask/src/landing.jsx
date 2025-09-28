import { useAuth } from 'react-oidc-context';
import { useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './landing.css';

function Landing() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showSessionExpiredMessage, setShowSessionExpiredMessage] = useState(false);

  // Helper function to get user's display name
  const getDisplayName = () => {
    if (!auth.user?.profile) return 'User';
    
    // Try name first, then given_name, then email as fallback
    return auth.user.profile.name || 
           auth.user.profile.given_name || 
           auth.user.profile.email || 
           'User';
  };

  // Check if user was redirected due to session expiry
  useEffect(() => {
    if (location.state?.sessionExpired) {
      setShowSessionExpiredMessage(true);
      // Clear the state to avoid showing message on subsequent visits
      window.history.replaceState({}, document.title);
      
      // Hide message after 5 seconds
      const timer = setTimeout(() => {
        setShowSessionExpiredMessage(false);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  // Redirect to dashboard only after OAuth callback (when URL has OAuth parameters)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const hasOAuthParams = urlParams.has('code') || urlParams.has('state');
    
    if (auth.isAuthenticated && !auth.isLoading && hasOAuthParams && !location.state?.sessionExpired) {
      console.log('User just signed in (OAuth callback detected), redirecting to dashboard...');
      // Clear OAuth parameters from URL and redirect to dashboard
      window.history.replaceState({}, document.title, window.location.pathname);
      navigate('/dashboard', { replace: true });
    }
  }, [auth.isAuthenticated, auth.isLoading, navigate, location.state]);
  

  const handleSignIn = () => {
    auth.signinRedirect();
  };

  const handleSignUp = () => {
    // Try direct signup endpoint
    const params = new URLSearchParams({
      client_id: "2v7frs8eeard997vkfaq1smslt",
      response_type: "code",
      scope: "openid email phone profile",
      redirect_uri: "http://localhost:5173/"
    });
    
    const cognitoDomain = "https://us-east-21qvpsnmpo.auth.us-east-2.amazoncognito.com";
    window.location.href = `${cognitoDomain}/signup?${params.toString()}`;
  };

  const handleSignOut = async () => {
    try {
      // Try the built-in logout first
      await auth.removeUser();
      // If that doesn't fully log out from Cognito, use the redirect method
      const clientId = "2v7frs8eeard997vkfaq1smslt";
      const logoutUri = "http://localhost:5173/";
      const cognitoDomain = "https://us-east-21qvpsnmpo.auth.us-east-2.amazoncognito.com";
      window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(logoutUri)}`;
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const handleDashboard = () => {
    navigate('/dashboard');
  };

  if (auth.isLoading) {
    return (
      <div className="landing-page">
        <div className="hero-section">
          <h1 className="hero-title">Loading...</h1>
        </div>
      </div>
    );
  }

  if (auth.error) {
    // Handle specific OIDC storage errors (common during session expiry simulation)
    if (auth.error.message?.includes('No matching state found in storage')) {
      console.log('OIDC state error detected - likely from session expiry simulation');
      // Clear the URL of any OAuth parameters and reload
      if (window.location.search) {
        window.history.replaceState({}, document.title, window.location.pathname);
        window.location.reload();
        return null;
      }
    }
    
    return (
      <div className="landing-page">
        <div className="hero-section">
          <h1 className="hero-title">Authentication Error</h1>
          <p className="hero-subtitle">
            {auth.error.message?.includes('No matching state found') 
              ? 'Session expired. Please try signing in again.' 
              : `Error: ${auth.error.message}`}
          </p>
          <div className="cta-buttons">
            <button onClick={handleSignIn} className="btn btn-primary">
              Sign In
            </button>
            <button onClick={() => window.location.reload()} className="btn btn-secondary">
              Refresh Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="landing-page">
      {/* Session Expired Message */}
      {showSessionExpiredMessage && (
        <div className="session-expired-banner">
          <div className="session-expired-content">
            <span>⚠️ Your session has expired. Please sign in again to continue.</span>
            <button 
              onClick={() => setShowSessionExpiredMessage(false)}
              className="close-banner"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Navigation Bar */}
      <nav className="landing-nav">
        <div className="nav-content">
          <div className="nav-left">
            <img className = "nav-logo" src = "ks.png"></img>
            <h2>basil</h2>
          </div>
          <div className="nav-actions">
            {auth.isAuthenticated ? (
              <>
                <span className="user-info">
                  Welcome, {getDisplayName()}!
                </span>
                <button onClick={handleSignOut} className="btn btn-outline">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <button onClick={handleSignUp} className="btn btn-nav-primary">
                  Sign Up
                </button>
                <button onClick={handleSignIn} className="btn btn-nav-secondary">
                  Log In
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="landing-main">
        <div className="hero-section">
          <h1 className="hero-title">
            {auth.isAuthenticated ? `Welcome back, ${getDisplayName()}!` : 'Welcome to basil'}
          </h1>
          <p className="hero-subtitle">
            {auth.isAuthenticated 
              ? 'You are successfully signed in. Let\'s get cooking.' 
              : 'Minimize waste, save money, and enjoy healthier meals with ease.'}
          </p>
          
          <div className="cta-buttons">
            {auth.isAuthenticated ? (
              <>
                {/* <button onClick={handleSignOut} className="btn btn-secondary">
                  Sign Out
                </button> */}
                <button onClick={handleDashboard} className="btn btn-primary">
                  Visit Fridge
                </button>
              </>
            ) : (
              <>
                <button onClick={handleSignUp} className="btn btn-primary">
                  Sign Up
                </button>
                <button onClick={handleSignIn} className="btn btn-secondary">
                  Log In
                </button>
              </>
            )}
          </div>
        </div>
        
        <div className="features-section">
          <h2>How can we help you?</h2>
          <h4>basil is built to help you waste less, save more, and eat better. Our goal is to minimize food waste by making sure every ingredient gets used, saving you money while encouraging creativity in the kitchen. We’re here to help you stay nourished and inspired, whether that means reaching protein goals, discovering new dishes, or making the most of what’s in your fridge.
          </h4>
          <div className="features-grid">
            <div className="feature-card">
              <h3>⏳Freshness Tracking</h3>
              <p>Keep tabs on your groceries and get reminders before items expire, so nothing goes to waste.</p>
            </div>
            <div className="feature-card">
              <h3>📝Smart Recipe Suggestions</h3>
              <p>Discover meals tailored to the ingredients that need to be used soon, turning potential waste into tasty dishes.</p>
            </div>
            <div className="feature-card">
              <h3>🥕Nutrition Insights</h3>
              <p>View macronutrient breakdowns for your meals to stay on top of your health and diet goals.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
