import { useAuth } from 'react-oidc-context';
import { Navigate, Link } from 'react-router-dom';
import './dashboard.css';

function Dashboard() {
  const auth = useAuth();

  // Redirect to home if not authenticated
  if (!auth.isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (auth.isLoading) {
    return (
      <div className="dashboard-page">
        <div className="dashboard-container">
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }

  const handleSignOut = async () => {
    try {
      await auth.removeUser();
      const clientId = "2v7frs8eeard997vkfaq1smslt";
      const logoutUri = "http://localhost:5173/";
      const cognitoDomain = "https://us-east-21qvpsnmpo.auth.us-east-2.amazoncognito.com";
      window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(logoutUri)}`;
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <div className="nav-content">
          <h2>My App Dashboard</h2>
          <div className="nav-actions">
            <span className="user-info">
              Welcome, {auth.user?.profile?.email || 'User'}!
            </span>
            <button onClick={handleSignOut} className="btn btn-outline">
              Sign Out
            </button>
          </div>
        </div>
      </nav>

      <main className="dashboard-main">
        <div className="dashboard-container">
          <div className="dashboard-header">
            <h1>Welcome to Your Dashboard</h1>
            <p>This is a protected page only visible to authenticated users.</p>
          </div>

          <div className="dashboard-grid">
            <div className="dashboard-card">
              <div className="card-header">
                <h3>📊 Analytics</h3>
              </div>
              <div className="card-content">
                <p>View your activity and insights</p>
                <div className="stat">
                  <span className="stat-number">42</span>
                  <span className="stat-label">Total Actions</span>
                </div>
              </div>
            </div>

            <div className="dashboard-card">
              <div className="card-header">
                <h3>⚙️ Settings</h3>
              </div>
              <div className="card-content">
                <p>Manage your account preferences</p>
                <button className="btn btn-secondary">Configure</button>
              </div>
            </div>

            <div className="dashboard-card">
              <div className="card-header">
                <h3>📝 Recent Activity</h3>
              </div>
              <div className="card-content">
                <p>Your latest actions and updates</p>
                <ul className="activity-list">
                  <li>Signed up successfully</li>
                  <li>Accessed dashboard</li>
                  <li>Profile created</li>
                </ul>
              </div>
            </div>

            <div className="dashboard-card">
              <div className="card-header">
                <h3>🔗 Quick Actions</h3>
              </div>
              <div className="card-content">
                <p>Common tasks and shortcuts</p>
                <div className="action-buttons">
                  <button className="btn btn-primary">New Project</button>
                  <button className="btn btn-secondary">Import Data</button>
                </div>
              </div>
            </div>
          </div>

          <div className="user-profile-section">
            <h2>Your Profile Information</h2>
            <div className="profile-card">
              <div className="profile-details">
                <p><strong>Email:</strong> {auth.user?.profile?.email || 'Not available'}</p>
                <p><strong>User ID:</strong> {auth.user?.profile?.sub || 'Not available'}</p>
                <p><strong>Email Verified:</strong> {auth.user?.profile?.email_verified ? 'Yes' : 'No'}</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
