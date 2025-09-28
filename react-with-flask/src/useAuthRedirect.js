import { useEffect, useState, useRef } from 'react';
import { useAuth } from 'react-oidc-context';
import { useNavigate, useLocation } from 'react-router-dom';

/**
 * Hook to handle automatic redirect when user loses authentication
 * while on a protected page (e.g., session timeout)
 */
export const useAuthRedirect = () => {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [wasAuthenticated, setWasAuthenticated] = useState(() => {
    // Initialize based on whether we're on a protected route
    // If we're on dashboard, we must have been authenticated to get here
    return location.pathname === '/dashboard';
  });
  const [forceRedirect, setForceRedirect] = useState(false);
  const hasRedirected = useRef(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    // Track if user was previously authenticated
    if (auth.isAuthenticated) {
      setWasAuthenticated(true);
      hasRedirected.current = false; // Reset redirect flag when authenticated
    }
  }, [auth.isAuthenticated]);

  // Monitor storage changes and periodically check auth state
  useEffect(() => {
    console.log('Storage monitoring effect - wasAuthenticated:', wasAuthenticated, 'hasRedirected:', hasRedirected.current);
    if (!wasAuthenticated || hasRedirected.current) {
      console.log('Skipping storage monitoring - not wasAuthenticated or already redirected');
      return;
    }

    // Check if critical OIDC storage keys exist
    const checkStorageIntegrity = () => {
      // Check all possible OIDC keys by iterating through all storage
      const findOidcKeys = (storage) => {
        const oidcKeys = [];
        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i);
          if (key && key.includes('oidc')) {
            oidcKeys.push(key);
          }
        }
        return oidcKeys;
      };
      
      const localOidcKeys = findOidcKeys(localStorage);
      const sessionOidcKeys = findOidcKeys(sessionStorage);
      const allOidcKeys = [...localOidcKeys, ...sessionOidcKeys];
      
      console.log('Current OIDC keys:', allOidcKeys);
      
      // Check if all storage is empty (indicating manual clearing)
      const localStorageEmpty = localStorage.length === 0;
      const sessionStorageEmpty = sessionStorage.length === 0;
      const noOidcKeys = allOidcKeys.length === 0;
      
      // Force redirect if:
      // 1. All storage is cleared, OR
      // 2. No OIDC keys but user claims to be authenticated, OR 
      // 3. User was authenticated but now has no OIDC data
      if ((localStorageEmpty && sessionStorageEmpty) || 
          (noOidcKeys && auth.isAuthenticated) ||
          (noOidcKeys && wasAuthenticated)) {
        console.log('Storage cleared detected - forcing redirect', {
          localStorageEmpty,
          sessionStorageEmpty,
          noOidcKeys,
          wasAuthenticated,
          isAuthenticated: auth.isAuthenticated
        });
        setForceRedirect(true);
      }
    };

    // Initial check
    checkStorageIntegrity();
    
    // Set up periodic checking
    intervalRef.current = setInterval(checkStorageIntegrity, 1000);

    // Listen for storage events (when storage is changed in other tabs)
    const handleStorageChange = (e) => {
      if (e.key === null || e.key.includes('oidc')) {
        console.log('Storage change detected:', e);
        checkStorageIntegrity();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [wasAuthenticated, auth.isAuthenticated]);

  useEffect(() => {
    // Check for OIDC errors that indicate session issues
    const hasOidcError = auth.error && auth.error.message?.includes('No matching state found in storage');
    
    // Debug all the conditions
    console.log('useAuthRedirect - Redirect conditions check:', {
      isLoading: auth.isLoading,
      isAuthenticated: auth.isAuthenticated,
      hasOidcError,
      forceRedirect,
      wasAuthenticated,
      pathname: location.pathname,
      hasRedirected: hasRedirected.current,
      error: auth.error?.message
    });
    
    // Only redirect if:
    // 1. Not loading (to avoid redirecting during initial auth check)
    // 2. Not authenticated OR has OIDC storage error OR forceRedirect is triggered
    // 3. User was previously authenticated (session expired vs never logged in) OR has OIDC error OR forceRedirect
    // 4. Not already on the landing page
    // 5. Haven't already redirected (prevent multiple redirects)
    if (!auth.isLoading && 
        (!auth.isAuthenticated || hasOidcError || forceRedirect) && 
        (wasAuthenticated || hasOidcError || forceRedirect) && 
        location.pathname !== '/' &&
        !hasRedirected.current) {
      
      console.log('🚀 REDIRECTING - User session expired, OIDC error, or storage cleared', {
        isAuthenticated: auth.isAuthenticated,
        hasOidcError,
        forceRedirect,
        wasAuthenticated,
        error: auth.error?.message
      });
      hasRedirected.current = true; // Mark as redirected
      
      // Clear any OAuth parameters from URL before redirect
      if (window.location.search) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
      
      // Clean up interval if redirecting
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      // Immediate redirect without delay
      navigate('/', { 
        replace: true,
        state: { sessionExpired: true } // Pass info about session expiry
      });
    } else {
      console.log('❌ NOT redirecting - conditions not met:', {
        condition1_notLoading: !auth.isLoading,
        condition2_notAuthOrErrorOrForce: (!auth.isAuthenticated || hasOidcError || forceRedirect),
        condition3_wasAuthOrErrorOrForce: (wasAuthenticated || hasOidcError || forceRedirect),
        condition4_notOnLandingPage: location.pathname !== '/',
        condition5_notAlreadyRedirected: !hasRedirected.current
      });
    }
  }, [auth.isAuthenticated, auth.isLoading, auth.error, forceRedirect, navigate, wasAuthenticated, location.pathname]);

  return auth;
};
