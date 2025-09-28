import { Link } from 'react-router-dom';
import { useAuthRedirect } from './useAuthRedirect.js';
import React, { useState, useEffect } from 'react';
import { marked } from 'marked';
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
  const [favoritingIds, setFavoritingIds] = useState({}); // map of id->boolean for favorite operations
  const [showFavorites, setShowFavorites] = useState(false); // toggle to show favorites instead of search
  
  // Favorites state
  const [favorites, setFavorites] = useState([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoritesError, setFavoritesError] = useState('');

  // Fridge items state
  const [fridgeItems, setFridgeItems] = useState([]);
  const [fridgeLoading, setFridgeLoading] = useState(false);
  const [fridgeError, setFridgeError] = useState('');
  const [deletingIds, setDeletingIds] = useState({}); // map of id->boolean for delete operations
  const [editingIds, setEditingIds] = useState({}); // map of id->boolean for edit operations
  const [editFormData, setEditFormData] = useState({}); // map of id->form data for editing

  // Recipe generation state
  const [recipeQuery, setRecipeQuery] = useState('');
  const [generatingRecipe, setGeneratingRecipe] = useState(false);
  const [recipeResponse, setRecipeResponse] = useState(null);
  const [recipeError, setRecipeError] = useState('');
  const [showRecipeCard, setShowRecipeCard] = useState(false);

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

  // Fetch favorites
  const fetchFavorites = async () => {
    setFavoritesLoading(true);
    setFavoritesError('');
    try {
      const token = getAccessToken();
      const userId = auth.user?.profile?.sub || 'demo_user';
      const resp = await fetch(`${API_BASE}/api/favorites?user_id=${userId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Failed to fetch favorites with status ${resp.status}`);
      }
      const data = await resp.json();
      setFavorites(Array.isArray(data) ? data : (data.favorites || []));
    } catch (err) {
      console.error('Fetch favorites error:', err);
      setFavoritesError(err.message || 'Failed to load favorites');
    } finally {
      setFavoritesLoading(false);
    }
  };

  // Load fridge items and favorites on component mount
  useEffect(() => {
    fetchFridgeItems();
    fetchFavorites();
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
      const userId = auth.user?.profile?.sub || 'demo_user';
      
      // Build query parameters
      const params = new URLSearchParams({
        query: query,
        user_id: userId
      });
      
      const resp = await fetch(`${API_BASE}/api/search?${params.toString()}`, {
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

  // Recipe generation functions
  const handleGenerateRecipe = async (e) => {
    e?.preventDefault();
    setGeneratingRecipe(true);
    setRecipeError('');
    setRecipeResponse(null);
    
    try {
      const token = getAccessToken();
      const userId = auth.user?.profile?.sub || 'demo_user'; // Use actual user ID
      
      const resp = await fetch(`${API_BASE}/api/ai/recipe-suggestions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: recipeQuery || 'What can I cook with my available groceries?',
          user_id: userId
        }),
      });
      
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Recipe generation failed with status ${resp.status}`);
      }
      
      const data = await resp.json();
      setRecipeResponse(data);
      setShowRecipeCard(true);
      
    } catch (err) {
      console.error('Recipe generation error:', err);
      setRecipeError(err.message || 'Failed to generate recipe');
    } finally {
      setGeneratingRecipe(false);
    }
  };

  const handleRecipeQueryChange = (e) => {
    setRecipeQuery(e.target.value);
  };

  const resetRecipe = () => {
    setRecipeResponse(null);
    setRecipeError('');
    setShowRecipeCard(false);
    setRecipeQuery('');
  };

  // Favorites functionality
  const handleToggleFavorite = async (item) => {
    const itemKey = item.id || item.name;
    setFavoritingIds((prev) => ({ ...prev, [itemKey]: true }));
    
    try {
      const token = getAccessToken();
      const userId = auth.user?.profile?.sub || 'demo_user';
      
      if (item.is_favorite && item.favorite_id) {
        // Remove from favorites
        const resp = await fetch(`${API_BASE}/api/favorites/${item.favorite_id}?user_id=${userId}`, {
          method: 'DELETE',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `Failed to remove from favorites with status ${resp.status}`);
        }
        
        // Update item in results
        setResults(prev => prev.map(r => r.id === item.id ? 
          { ...r, is_favorite: false, favorite_id: null } : r
        ));
        
        // Refresh favorites list
        fetchFavorites();
      } else {
        // Add to favorites
        const favoriteData = {
          user_id: userId,
          display_name: item.name
        };
        
        // Determine if it's a USDA item or local item
        if (item.source === 'usda' && item.fdc_id) {
          // For USDA items, we need to create a local FoodItem first or reference existing one
          favoriteData.food_item_id = null; // The backend should handle USDA item creation
        } else if (item.food_item_id) {
          favoriteData.food_item_id = item.food_item_id;
        } else if (item.custom_food_id) {
          favoriteData.custom_food_id = item.custom_food_id;
        }
        
        const resp = await fetch(`${API_BASE}/api/favorites`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(favoriteData),
        });
        
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `Failed to add to favorites with status ${resp.status}`);
        }
        
        const data = await resp.json();
        
        // Update item in results
        setResults(prev => prev.map(r => r.id === item.id ? 
          { ...r, is_favorite: true, favorite_id: data.id } : r
        ));
        
        // Refresh favorites list
        fetchFavorites();
      }
    } catch (err) {
      console.error('Toggle favorite error:', err);
      alert(`Failed to ${item.is_favorite ? 'remove from' : 'add to'} favorites: ${err.message}`);
    } finally {
      setFavoritingIds((prev) => ({ ...prev, [itemKey]: false }));
    }
  };
  
  // Remove favorite from favorites list
  const handleRemoveFavorite = async (favoriteId, itemName) => {
    setFavoritingIds((prev) => ({ ...prev, [favoriteId]: true }));
    
    try {
      const token = getAccessToken();
      const userId = auth.user?.profile?.sub || 'demo_user';
      
      const resp = await fetch(`${API_BASE}/api/favorites/${favoriteId}?user_id=${userId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Failed to remove from favorites with status ${resp.status}`);
      }
      
      // Remove item from favorites list
      setFavorites(prev => prev.filter(fav => fav.id !== favoriteId));
      
      // Update any search results that might show this item
      setResults(prev => prev.map(r => 
        (r.favorite_id === favoriteId) ? 
        { ...r, is_favorite: false, favorite_id: null } : r
      ));
      
    } catch (err) {
      console.error('Remove favorite error:', err);
      alert(`Failed to remove ${itemName} from favorites: ${err.message}`);
    } finally {
      setFavoritingIds((prev) => ({ ...prev, [favoriteId]: false }));
    }
  };

  // Function to render Markdown content safely
  const renderMarkdown = (text) => {
    try {
      // Remove the MACROS_JSON block from the text before rendering
      let cleanText = text.replace(/<MACROS_JSON>.*?<\/MACROS_JSON>/gs, '').trim();
      
      // Remove common AI preamble patterns
      cleanText = cleanText.replace(/^I'd love to help you create.*?\n\n/s, ''); // Remove "I'd love to help" intros
      cleanText = cleanText.replace(/^Here's a.*?recipe.*?:\n\n/si, ''); // Remove "Here's a recipe" intros
      cleanText = cleanText.replace(/^Let me suggest.*?:\n\n/si, ''); // Remove "Let me suggest" intros
      cleanText = cleanText.replace(/^Based on.*?here's.*?:\n\n/si, ''); // Remove "Based on your ingredients" intros
      cleanText = cleanText.replace(/^Perfect! I can help.*?\n\n/si, ''); // Remove "Perfect! I can help" intros
      cleanText = cleanText.replace(/^Great! Using your.*?\n\n/si, ''); // Remove "Great! Using your" intros
      
      // Clean up any remaining standalone introductory sentences
      cleanText = cleanText.replace(/^.*allows you to use up items that may be expiring soon\.\s*\n\n/si, '');
      cleanText = cleanText.replace(/^.*This recipe is versatile.*?\n\n/si, '');
      
      // Clean up extra whitespace
      cleanText = cleanText.replace(/\n\s*\n\s*\n/g, '\n\n').trim();
      
      // Split text into lines to extract title and serving info
      const lines = cleanText.split('\n');
      let title = '';
      let servingInfo = '';
      let remainingContent = cleanText;
      
      // Extract first line as title if it doesn't start with common recipe section indicators
      if (lines.length > 0 && lines[0].trim() && 
          !lines[0].toLowerCase().startsWith('ingredients') &&
          !lines[0].toLowerCase().startsWith('instructions') &&
          !lines[0].toLowerCase().startsWith('directions') &&
          !lines[0].toLowerCase().includes('step ')) {
        
        // Clean the title by removing markdown formatting and list indicators
        let rawTitle = lines[0].trim();
        // Remove numbered list indicators (e.g., "1) ", "2) ", etc.)
        rawTitle = rawTitle.replace(/^\d+[.)\]\s]+/, '');
        // Remove markdown bold formatting
        rawTitle = rawTitle.replace(/\*\*(.*?)\*\*/g, '$1');
        // Remove other markdown formatting
        rawTitle = rawTitle.replace(/[*_`]/g, '');
        title = rawTitle;
        
        // Check if second line contains serving/time info
        if (lines.length > 1 && lines[1].trim()) {
          const secondLine = lines[1].trim().toLowerCase();
          if ((secondLine.includes('serving') || secondLine.includes('time') || 
               secondLine.includes('prep') || secondLine.includes('cook') ||
               secondLine.includes('total') || secondLine.includes('yield')) &&
              !secondLine.startsWith('ingredients') &&
              !secondLine.startsWith('instructions') &&
              !secondLine.startsWith('directions')) {
            
            // Clean the serving info by removing markdown formatting and list indicators
            let rawServingInfo = lines[1].trim();
            // Remove numbered list indicators
            rawServingInfo = rawServingInfo.replace(/^\d+[.)\]\s]+/, '');
            // Remove markdown bold formatting
            rawServingInfo = rawServingInfo.replace(/\*\*(.*?)\*\*/g, '$1');
            // Remove other markdown formatting
            rawServingInfo = rawServingInfo.replace(/[*_`]/g, '');
            servingInfo = rawServingInfo;
            
            // Remove title and serving info from remaining content
            remainingContent = lines.slice(2).join('\n').trim();
          } else {
            // Remove just the title from remaining content
            remainingContent = lines.slice(1).join('\n').trim();
          }
        } else {
          // Remove just the title from remaining content
          remainingContent = lines.slice(1).join('\n').trim();
        }
      }
      
      // Configure marked options for safety
      marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: true,
        smartLists: true,
        smartypants: true
      });
      
      // Convert remaining markdown to HTML
      const htmlContent = remainingContent ? marked(remainingContent) : '';
      
      // Return JSX with special formatting for title and serving info
      return (
        <div className="markdown-content">
          {title && <h1 className="recipe-title">{title}</h1>}
          {servingInfo && <div className="recipe-serving-info">{servingInfo}</div>}
          {htmlContent && <div dangerouslySetInnerHTML={{ __html: htmlContent }} />}
        </div>
      );
    } catch (error) {
      console.error('Markdown rendering error:', error);
      // Fallback to plain text display (also clean the text)
      let cleanText = text.replace(/<MACROS_JSON>.*?<\/MACROS_JSON>/gs, '').trim();
      
      // Apply same cleaning to fallback
      cleanText = cleanText.replace(/^I'd love to help you create.*?\n\n/s, '');
      cleanText = cleanText.replace(/^Here's a.*?recipe.*?:\n\n/si, '');
      cleanText = cleanText.replace(/^Let me suggest.*?:\n\n/si, '');
      cleanText = cleanText.replace(/^Based on.*?here's.*?:\n\n/si, '');
      cleanText = cleanText.replace(/^Perfect! I can help.*?\n\n/si, '');
      cleanText = cleanText.replace(/^Great! Using your.*?\n\n/si, '');
      cleanText = cleanText.replace(/^.*allows you to use up items that may be expiring soon\.\s*\n\n/si, '');
      cleanText = cleanText.replace(/^.*This recipe is versatile.*?\n\n/si, '');
      cleanText = cleanText.replace(/\n\s*\n\s*\n/g, '\n\n').trim();
      
      return (
        <div className="recipe-text">
          {cleanText.split('\n').map((line, index) => (
            <p key={index} className={line.trim() === '' ? 'recipe-blank-line' : 'recipe-line'}>
              {line.trim() || '\u00A0'}
            </p>
          ))}
        </div>
      );
    }
  };


  return (
    <div className="dashboard-page">
      <nav className="dashboard-nav">
        <div className="nav-content">
          <div className="nav-left">
            <img className = "nav-logo" src = "ks.png"></img>
            <h2>basil</h2>
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
            <p>Feeling chilly?</p>
          </div>

          <div className="dashboard-grid">
            {/* Add to Fridge - Search Card */}
            <div className="dashboard-card search-card">
              <div className="card-header">
                <h3>🧊 Add Items to Your Fridge</h3>
              </div>
              <div className="card-content">
                <div className="search-controls">
                  <div className="toggle-container">
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={showFavorites}
                        onChange={(e) => setShowFavorites(e.target.checked)}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                    <span className="toggle-label">
                      {showFavorites ? 'Showing Favorites' : 'Show Favorites'}
                    </span>
                  </div>
                </div>
                
                {!showFavorites && (
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
                )}

                {!showFavorites && searchError && <p className="search-error">{searchError}</p>}
                {showFavorites && favoritesError && <p className="search-error">{favoritesError}</p>}
                {addMessage && <p className="search-message">{addMessage}</p>}

                {!showFavorites && hasSearched && !searching && results.length === 0 && !searchError && (
                  <div className="no-results">
                    <p>No items found in database for "{query}"</p>
                    <p className="no-results-hint">Try searching for a different ingredient or check your spelling.</p>
                  </div>
                )}

                {showFavorites && favoritesLoading && (
                  <p className="loading-message">Loading your favorites...</p>
                )}

                {showFavorites && !favoritesLoading && favorites.length === 0 && !favoritesError && (
                  <div className="no-results">
                    <p>You haven't favorited any items yet.</p>
                    <p className="no-results-hint">Search for ingredients and click the star (☆) to add them to your favorites!</p>
                  </div>
                )}

                <ul className="search-results">
                  {/* Show search results when not showing favorites */}
                  {!showFavorites && results.map((item) => (
                    <li key={item.id || item.name} className="search-result-row">
                      <div className="search-result-main">
                        <span className="result-name">{item.name}</span>
                        {item.category && <span className="result-category">{item.category}</span>}
                      </div>
                      <div className="search-result-actions">
                        <button
                          className={`favorite-btn ${item.is_favorite ? 'favorited' : ''}`}
                          onClick={() => handleToggleFavorite(item)}
                          disabled={!!favoritingIds[item.id || item.name]}
                          title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                        >
                          {favoritingIds[item.id || item.name] ? '⏳' : (item.is_favorite ? '⭐' : '☆')}
                        </button>
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
                  
                  {/* Show favorites when toggle is on */}
                  {showFavorites && favorites.map((favorite) => (
                    <li key={favorite.id} className="search-result-row">
                      <div className="search-result-main">
                        <span className="result-name">{favorite.display_name}</span>
                        {favorite.category && <span className="result-category">{favorite.category}</span>}
                      </div>
                      <div className="search-result-actions">
                        <button
                          className="favorite-btn favorited"
                          onClick={() => handleRemoveFavorite(favorite.id, favorite.display_name)}
                          disabled={!!favoritingIds[favorite.id]}
                          title="Remove from favorites"
                        >
                          {favoritingIds[favorite.id] ? '⏳' : '⭐'}
                        </button>
                        <button
                          className="btn btn-primary"
                          onClick={() => {
                            // Create an item object that matches the expected format
                            const item = {
                              id: favorite.food_item_id || favorite.custom_food_id || favorite.id,
                              name: favorite.display_name,
                              category: favorite.category
                            };
                            handleAddToFridge(item);
                          }}
                          disabled={!!addingIds[favorite.food_item_id || favorite.custom_food_id || favorite.id]}
                        >
                          {addingIds[favorite.food_item_id || favorite.custom_food_id || favorite.id] ? 'Adding...' : 'Add'}
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

            {/* AI Recipe Generation Card */}
            <div className="dashboard-card recipe-generation-card">
              <div className="card-header">
                <h3>🤖 AI Recipe Suggestions</h3>
                <small>Powered by Mosaic AI • Uses your fridge items</small>
              </div>
              <div className="card-content">
                {!showRecipeCard ? (
                  // Recipe generation form
                  <>
                    <form className="recipe-form" onSubmit={handleGenerateRecipe}>
                      <input
                        type="text"
                        className="recipe-input"
                        placeholder="What would you like to cook?"
                        value={recipeQuery}
                        onChange={handleRecipeQueryChange}
                      />
                      <button 
                        type="submit" 
                        className="btn btn-primary recipe-generate-btn" 
                        disabled={generatingRecipe || fridgeItems.length === 0}
                      >
                        {generatingRecipe ? '🧠 Generating...' : '✨ Generate Recipe'}
                      </button>
                    </form>
                    <p className="recipe-examples">
                      e.g., "Something quick for dinner", "Use my expiring ingredients", "Healthy meal with chicken"
                    </p>
                    
                    {fridgeItems.length === 0 && (
                      <p className="recipe-hint">
                        💡 Add some items to your fridge first to get personalized recipe suggestions!
                      </p>
                    )}
                    
                    {fridgeItems.length > 0 && (
                      <div className="fridge-preview">
                        <p className="fridge-preview-title">Your available ingredients:</p>
                        <div className="fridge-preview-items">
                          {fridgeItems.slice(0, 6).map((item, index) => (
                            <span key={item.id} className="fridge-preview-item">
                              {item.name}{index < Math.min(fridgeItems.length, 6) - 1 ? ', ' : ''}
                            </span>
                          ))}
                          {fridgeItems.length > 6 && <span className="fridge-preview-more">+{fridgeItems.length - 6} more</span>}
                        </div>
                      </div>
                    )}
                    
                    {recipeError && <p className="recipe-error">{recipeError}</p>}
                  </>
                ) : (
                  // Recipe response display
                  <div className="recipe-response">
                    <div className="recipe-response-header">
                      <button className="btn btn-secondary btn-sm" onClick={resetRecipe}>
                        ← Generate New Recipe
                      </button>
                    </div>
                    
                    <div className="recipe-content">
                      {recipeResponse?.recipe_suggestions && (
                        <div className="recipe-text">
                          {renderMarkdown(recipeResponse.recipe_suggestions)}
                        </div>
                      )}
                      
                      {recipeResponse?.macros && (
                        <div className="recipe-macros">
                          <h4>Nutritional Information (per serving)</h4>
                          <div className="macros-grid">
                            <div className="macro-item">
                              <span className="macro-label">Calories</span>
                              <span className="macro-value">{recipeResponse.macros.macros_per_serving?.calories || 'N/A'}</span>
                            </div>
                            <div className="macro-item">
                              <span className="macro-label">Protein</span>
                              <span className="macro-value">{recipeResponse.macros.macros_per_serving?.protein_g || 'N/A'}g</span>
                            </div>
                            <div className="macro-item">
                              <span className="macro-label">Carbs</span>
                              <span className="macro-value">{recipeResponse.macros.macros_per_serving?.carbs_g || 'N/A'}g</span>
                            </div>
                            <div className="macro-item">
                              <span className="macro-label">Fat</span>
                              <span className="macro-value">{recipeResponse.macros.macros_per_serving?.fat_g || 'N/A'}g</span>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div className="recipe-footer">
                        <p className="powered-by">
                          🚀 Powered by {recipeResponse?.powered_by || 'Mosaic AI'}
                        </p>
                        {recipeResponse?.timestamp && (
                          <p className="generated-time">
                            Generated at {new Date(recipeResponse.timestamp * 1000).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="user-profile-section">
            <h2>Your Profile Information</h2>
            <div className="profile-card">
              <div className="profile-details">
                <p><strong>Name:</strong> {auth.user?.profile?.name || auth.user?.profile?.given_name || 'Not available'}</p>
                <p><strong>Email:</strong> {auth.user?.profile?.email || 'Not available'}</p>
                {/* <p><strong>User ID:</strong> {auth.user?.profile?.sub || 'Not available'}</p> */}
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
