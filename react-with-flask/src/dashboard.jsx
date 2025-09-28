import { Link } from 'react-router-dom';
import { useAuthRedirect } from './useAuthRedirect.js';
import React, { useState, useEffect } from 'react';
import './dashboard.css';

function Dashboard() {
  // This hook handles automatic redirect on session expiry
  const auth = useAuthRedirect();

  // All state hooks must be declared before any early returns
  // Search/Add to Fridge state
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [searchError, setSearchError] = useState('');
  const [addingIds, setAddingIds] = useState({}); // map of id->boolean
  const [addMessage, setAddMessage] = useState('');
  const [hasSearched, setHasSearched] = useState(false); // track if search has been performed

  // Fridge items state
  const [fridgeItems, setFridgeItems] = useState([]);
  const [fridgeLoading, setFridgeLoading] = useState(false);
  const [fridgeError, setFridgeError] = useState('');
  const [deletingIds, setDeletingIds] = useState({}); // map of id->boolean for delete operations
  const [editingIds, setEditingIds] = useState({}); // map of id->boolean for edit operations
  const [editFormData, setEditFormData] = useState({}); // map of id->form data for editing

  // Configure API base (adjust if your Flask runs elsewhere)
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5001';

  const getAccessToken = () => auth.user?.access_token;

  // Fetch fridge items
  const fetchFridgeItems = async () => {
    setFridgeLoading(true);
    setFridgeError('');
    try {
      const token = getAccessToken();
      const resp = await fetch(`${API_BASE}/api/fridge`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Failed to fetch fridge items with status ${resp.status}`);
      }
      const data = await resp.json();
      setFridgeItems(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      console.error('Fetch fridge items error:', err);
      setFridgeError(err.message || 'Failed to load fridge items');
    } finally {
      setFridgeLoading(false);
    }
  };

  // Load fridge items on component mount
  useEffect(() => {
    fetchFridgeItems();
  }, []);

  // Helper function to get user's display name
  const getDisplayName = () => {
    if (!auth.user?.profile) return 'User';
    
    // Try name first, then given_name, then email as fallback
    return auth.user.profile.name || 
           auth.user.profile.given_name || 
           auth.user.profile.email || 
           'User';
  };

  // Debug logging removed - name display is working!

  // Handle OIDC errors that indicate session issues
  const hasOidcError = auth.error && auth.error.message?.includes('No matching state found in storage');
  
  // If not authenticated or has OIDC error, show appropriate state
  if (!auth.isAuthenticated || auth.isLoading || hasOidcError) {
    // If there's an OIDC error, the useAuthRedirect should handle redirect
    // But show a brief message in case it takes a moment
    if (hasOidcError) {
      return (
        <div className="dashboard-page">
          <div className="dashboard-container">
            <h1>Session expired, redirecting...</h1>
            <p>You will be redirected to the login page shortly.</p>
            {/* <p style={{fontSize: '12px', color: '#666'}}>Debug: OIDC Error detected</p> */}
          </div>
        </div>
      );
    }
    
    return (
      <div className="dashboard-page">
        <div className="dashboard-container">
          <h1>{auth.isLoading ? 'Loading...' : 'Redirecting...'}</h1>
          {/* <p style={{fontSize: '12px', color: '#666'}}>Debug: isAuthenticated={String(auth.isAuthenticated)}, isLoading={String(auth.isLoading)}</p> */}
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

  const handleSearch = async (e) => {
    e?.preventDefault();
    setSearching(true);
    setSearchError('');
    setResults([]);
    setHasSearched(true); // Mark that a search has been performed
    try {
      const token = getAccessToken();
      const resp = await fetch(`${API_BASE}/api/search?query=${encodeURIComponent(query)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Search failed with status ${resp.status}`);
      }
      const data = await resp.json();
      // Expecting array of items: [{ id, name, category, ... }]
      setResults(Array.isArray(data) ? data : (data.results || []));
    } catch (err) {
      console.error('Search error:', err);
      setSearchError(err.message || 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  // Reset search states when query changes
  const handleQueryChange = (e) => {
    setQuery(e.target.value);
    // Reset search-related states when user starts typing a new search
    if (hasSearched) {
      setHasSearched(false);
      setResults([]);
      setSearchError('');
    }
  };

  const handleAddToFridge = async (item) => {
    setAddingIds((prev) => ({ ...prev, [item.id || item.name]: true }));
    setAddMessage('');
    try {
      const token = getAccessToken();
      const resp = await fetch(`${API_BASE}/api/fridge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          item_id: item.id || null,
          name: item.name,
          category: item.category || null,
          // include any other metadata you want to persist
        }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Add failed with status ${resp.status}`);
      }
      setAddMessage(`${item.name} added to your fridge!`);
    } catch (err) {
      console.error('Add to fridge error:', err);
      setAddMessage(`Failed to add ${item.name}: ${err.message}`);
    } finally {
      setAddingIds((prev) => ({ ...prev, [item.id || item.name]: false }));
      // Clear message after a few seconds
      setTimeout(() => setAddMessage(''), 4000);
      // Refresh fridge items after adding
      fetchFridgeItems();
    }
  };


  // Delete item from fridge
  const handleDeleteFromFridge = async (itemId) => {
    setDeletingIds((prev) => ({ ...prev, [itemId]: true }));
    try {
      const token = getAccessToken();
      const resp = await fetch(`${API_BASE}/api/fridge/${itemId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Delete failed with status ${resp.status}`);
      }
      // Remove item from local state
      setFridgeItems(prev => prev.filter(item => item.id !== itemId));
    } catch (err) {
      console.error('Delete from fridge error:', err);
      alert(`Failed to remove item: ${err.message}`);
    } finally {
      setDeletingIds((prev) => ({ ...prev, [itemId]: false }));
    }
  };

  // Start editing an item
  const handleEditItem = (item) => {
    setEditingIds((prev) => ({ ...prev, [item.id]: true }));
    
    // Format dates for input fields (HTML date inputs need YYYY-MM-DD format)
    const createdDate = item.created_at ? new Date(item.created_at).toISOString().split('T')[0] : '';
    const expiryDate = item.expiry_date ? new Date(item.expiry_date).toISOString().split('T')[0] : '';
    
    setEditFormData((prev) => ({
      ...prev,
      [item.id]: {
        quantity: item.quantity || 1,
        unit: item.unit || 'items',
        created_at: createdDate,
        expiry_date: expiryDate,
      }
    }));
  };

  // Cancel editing an item
  const handleCancelEdit = (itemId) => {
    setEditingIds((prev) => ({ ...prev, [itemId]: false }));
    setEditFormData((prev) => {
      const newData = { ...prev };
      delete newData[itemId];
      return newData;
    });
  };

  // Update edit form data
  const handleEditFormChange = (itemId, field, value) => {
    setEditFormData((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value
      }
    }));
  };

  // Save edited item
  const handleSaveEdit = async (itemId) => {
    const formData = editFormData[itemId];
    if (!formData) return;

    try {
      const token = getAccessToken();
      
      // Prepare the update data
      const updateData = {
        quantity: parseFloat(formData.quantity),
        unit: formData.unit,
      };
      
      // Add dates if they exist
      if (formData.created_at) {
        updateData.created_at = new Date(formData.created_at).toISOString();
      }
      
      if (formData.expiry_date) {
        updateData.expiry_date = new Date(formData.expiry_date).toISOString();
      }
      
      const resp = await fetch(`${API_BASE}/api/fridge/${itemId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(updateData),
      });
      
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Update failed with status ${resp.status}`);
      }
      
      // Refresh fridge items to get updated data
      await fetchFridgeItems();
      
      // Clear edit state
      handleCancelEdit(itemId);
      
    } catch (err) {
      console.error('Update fridge item error:', err);
      alert(`Failed to update item: ${err.message}`);
    }
  };


  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <div className="nav-content">
          <div className="nav-left">
            <img className = "nav-logo" src = "ks.png"></img>
            <h2>KitchenSync</h2>
            <Link to="/" className="nav-link">← Back to Landing</Link>
          </div>
          <div className="nav-actions">
            <span className="user-info">
              Welcome, {getDisplayName()}!
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
            <h1>Welcome to Your Fridge</h1>
            {/* <p>This is a protected page only visible to authenticated users.</p> */}
          </div>

          <div className="dashboard-grid">
            {/* Add to Fridge - Search Card */}
            <div className="dashboard-card search-card">
              <div className="card-header">
                <h3>🧊 Add Items to Your Fridge</h3>
              </div>
              <div className="card-content">
                <form className="search-form" onSubmit={handleSearch}>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search ingredients (e.g., chicken, milk, broccoli)"
                    value={query}
                    onChange={handleQueryChange}
                  />
                  <button type="submit" className="btn btn-primary" disabled={searching || !query.trim()}>
                    {searching ? 'Searching...' : 'Search'}
                  </button>
                </form>

                {searchError && <p className="search-error">{searchError}</p>}
                {addMessage && <p className="search-message">{addMessage}</p>}

                {hasSearched && !searching && results.length === 0 && !searchError && (
                  <div className="no-results">
                    <p>No items found in database for "{query}"</p>
                    <p className="no-results-hint">Try searching for a different ingredient or check your spelling.</p>
                  </div>
                )}

                <ul className="search-results">
                  {results.map((item) => (
                    <li key={item.id || item.name} className="search-result-row">
                      <div className="search-result-main">
                        <span className="result-name">{item.name}</span>
                        {item.category && <span className="result-category">{item.category}</span>}
                      </div>
                      <div className="search-result-actions">
                        <button
                          className="btn btn-primary"
                          onClick={() => handleAddToFridge(item)}
                          disabled={!!addingIds[item.id || item.name]}
                        >
                          {addingIds[item.id || item.name] ? 'Adding...' : 'Add'}
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Your Fridge Items Card */}
            <div className="dashboard-card fridge-items-card">
              <div className="card-header">
                <h3>🧊 Your Fridge Items</h3>
                <button 
                  className="btn btn-secondary btn-sm refresh-btn" 
                  onClick={fetchFridgeItems}
                  disabled={fridgeLoading}
                >
                  {fridgeLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              <div className="card-content">
                {fridgeError && <p className="fridge-error">{fridgeError}</p>}
                
                {fridgeLoading ? (
                  <p className="loading-message">Loading your fridge items...</p>
                ) : fridgeItems.length === 0 ? (
                  <div className="empty-fridge">
                    <p>Your fridge is empty! Use the search above to add some items.</p>
                    <div className="empty-fridge-icon">🥺</div>
                  </div>
                ) : (
                  <ul className="fridge-items-list">
                    {fridgeItems.map((item) => (
                      <li key={item.id} className="fridge-item-row">
                        {editingIds[item.id] ? (
                          // Edit mode
                          <>
                            <div className="fridge-item-main">
                              <div className="fridge-item-info">
                                <span className="fridge-item-name">{item.name}</span>
                                {item.brand && <span className="fridge-item-brand">{item.brand}</span>}
                                {item.category && <span className="fridge-item-category">{item.category}</span>}
                              </div>
                              <div className="edit-form">
                                <div className="edit-row">
                                  <label className="edit-label">Quantity:</label>
                                  <input
                                    type="number"
                                    className="edit-input edit-quantity"
                                    value={editFormData[item.id]?.quantity || ''}
                                    onChange={(e) => handleEditFormChange(item.id, 'quantity', e.target.value)}
                                    min="0"
                                    step="0.1"
                                  />
                                  <input
                                    type="text"
                                    className="edit-input edit-unit"
                                    value={editFormData[item.id]?.unit || ''}
                                    onChange={(e) => handleEditFormChange(item.id, 'unit', e.target.value)}
                                    placeholder="unit (e.g., items, lbs, cups)"
                                  />
                                </div>
                                <div className="edit-row">
                                  <label className="edit-label">Added on:</label>
                                  <input
                                    type="date"
                                    className="edit-input edit-date"
                                    value={editFormData[item.id]?.created_at || ''}
                                    onChange={(e) => handleEditFormChange(item.id, 'created_at', e.target.value)}
                                  />
                                </div>
                                <div className="edit-row">
                                  <label className="edit-label">Expires on:</label>
                                  <input
                                    type="date"
                                    className="edit-input edit-date"
                                    value={editFormData[item.id]?.expiry_date || ''}
                                    onChange={(e) => handleEditFormChange(item.id, 'expiry_date', e.target.value)}
                                  />
                                </div>
                              </div>
                            </div>
                            <div className="fridge-item-actions edit-actions">
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => handleSaveEdit(item.id)}
                                title="Save changes"
                              >
                                Save
                              </button>
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => handleCancelEdit(item.id)}
                                title="Cancel editing"
                              >
                                Cancel
                              </button>
                            </div>
                          </>
                        ) : (
                          // View mode
                          <>
                            <div className="fridge-item-main">
                              <div className="fridge-item-info">
                                <span className="fridge-item-name">{item.name}</span>
                                {item.brand && <span className="fridge-item-brand">{item.brand}</span>}
                                {item.category && <span className="fridge-item-category">{item.category}</span>}
                              </div>
                              <div className="fridge-item-details">
                                {item.quantity && (
                                  <span className="fridge-item-quantity">
                                    {item.quantity} {item.unit || 'items'}
                                  </span>
                                )}
                                {item.expiry_date && (
                                  <span className="fridge-item-expiry">
                                    Expires: {new Date(item.expiry_date).toLocaleDateString()}
                                  </span>
                                )}
                                {item.created_at && (
                                  <span className="fridge-item-added">
                                    Added: {new Date(item.created_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="fridge-item-actions">
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => handleEditItem(item)}
                                title="Edit item"
                              >
                                Edit
                              </button>
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDeleteFromFridge(item.id)}
                                disabled={!!deletingIds[item.id]}
                                title="Remove from fridge"
                              >
                                {deletingIds[item.id] ? '...' : (
                                  <img 
                                    src="https://cdn-icons-png.flaticon.com/512/484/484662.png" 
                                    alt="Delete" 
                                    style={{ width: '20px', height: '20px' }}
                                  />
                                )}
                              </button>
                            </div>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* <div className="dashboard-card">
              
            </div> */}
          </div>

          <div className="user-profile-section">
            <h2>Your Profile Information</h2>
            <div className="profile-card">
              <div className="profile-details">
                <p><strong>Name:</strong> {auth.user?.profile?.name || auth.user?.profile?.given_name || 'Not available'}</p>
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
