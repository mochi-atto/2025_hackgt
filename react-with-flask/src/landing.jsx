import { useAuth } from 'react-oidc-context';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import './landing.css';

function Landing() {
  const auth = useAuth();
  const navigate = useNavigate();
  
  // Auto-redirect to dashboard when user is authenticated
  useEffect(() => {
    if (auth.isAuthenticated && !auth.isLoading) {
      navigate('/dashboard');
    }
  }, [auth.isAuthenticated, auth.isLoading, navigate]);
  
  // Debug logging
  console.log('Auth state:', {
    isLoading: auth.isLoading,
    isAuthenticated: auth.isAuthenticated,
    error: auth.error,
    user: auth.user
  });

  const handleSignIn = () => {
    auth.signinRedirect();
  };

  const handleSignUp = () => {
    // Try direct signup endpoint
    const params = new URLSearchParams({
      client_id: "2v7frs8eeard997vkfaq1smslt",
      response_type: "code",
      scope: "openid email phone",
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
    return (
      <div className="landing-page">
        <div className="hero-section">
          <h1 className="hero-title">Error: {auth.error.message}</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="landing-page">
      <div className="hero-section">
        <h1 className="hero-title">
          {auth.isAuthenticated ? `Welcome back, ${auth.user?.profile?.email || 'User'}!` : 'Welcome to Our App'}
        </h1>
        <p className="hero-subtitle">
          {auth.isAuthenticated 
            ? 'You are successfully signed in. Explore all the amazing features we have to offer.' 
            : 'Discover amazing features and connect with others in a seamless experience.'}
        </p>
        
        <div className="cta-buttons">
          {auth.isAuthenticated ? (
            <>
              <button onClick={handleSignOut} className="btn btn-secondary">
                Sign Out
              </button>
              <button onClick={handleDashboard} className="btn btn-primary">
                Dashboard
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
        <h2>Why Choose Us?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <h3>🚀 Fast & Reliable</h3>
            <p>Built with modern React and Flask for optimal performance</p>
          </div>
          <div className="feature-card">
            <h3>🔒 Secure</h3>
            <p>Your data is protected with industry-standard security measures</p>
          </div>
          <div className="feature-card">
            <h3>📱 Responsive</h3>
            <p>Works seamlessly across all devices and screen sizes</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
