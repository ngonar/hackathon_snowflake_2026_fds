import React, { useState, useEffect } from 'react';
import { api, logout, getToken } from './services/api';
import LandingView from './components/LandingView';
import UserDashboard from './components/UserDashboard';
import AdminPanel from './components/AdminPanel';
import { 
  Globe, LogOut, LayoutDashboard, Shield, 
  CheckCircle, AlertTriangle, XCircle, Info 
} from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('landing'); // 'landing' | 'dashboard' | 'admin'
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState({ message: '', type: 'success' });
  const [toastTimeout, setToastTimeout] = useState(null);

  // Helper to trigger toast notification
  const showToast = (message, type = 'success') => {
    if (toastTimeout) {
      clearTimeout(toastTimeout);
    }
    setToast({ message, type });
    const timeout = setTimeout(() => {
      setToast({ message: '', type: 'success' });
    }, 4000);
    setToastTimeout(timeout);
  };

  // Fetch the logged in user profile
  const fetchUserProfile = async () => {
    try {
      const profile = await api.getMe();
      setUser(profile);
      if (profile.role === 'admin') {
        setView('admin');
      } else {
        setView('dashboard');
      }
    } catch (err) {
      console.error('Failed to restore session:', err);
      logout();
      setUser(null);
      setView('landing');
    } finally {
      setLoading(false);
    }
  };

  // Verify and load token on mount
  useEffect(() => {
    const token = getToken();
    if (token) {
      fetchUserProfile();
    } else {
      setLoading(false);
      setView('landing');
    }
  }, []);

  const handleLogout = () => {
    logout();
    setUser(null);
    setView('landing');
    showToast('Logged out successfully', 'info');
  };

  const handleLoginSuccess = () => {
    setLoading(true);
    fetchUserProfile();
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: '1rem',
        background: 'radial-gradient(circle at 50% 0%, #17153a 0%, #06060a 70%)'
      }}>
        <Globe size={48} className="text-primary" style={{ color: 'var(--primary)', animation: 'spin 2s linear infinite' }} />
        <h3 style={{ fontWeight: 500, letterSpacing: '0.05em' }}>Loading RemitApp...</h3>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header bar */}
      <header className="header">
        <div className="logo" style={{ cursor: 'pointer' }} onClick={() => setView(user ? (user.role === 'admin' ? 'admin' : 'dashboard') : 'landing')}>
          <Globe size={24} />
          <span>RemitApp</span>
        </div>

        <nav className="nav-links">
          {user ? (
            <>
              {/* Show client dashboard if not admin, or link if they are admin */}
              {user.role === 'admin' ? (
                <>
                  <button 
                    className={`btn btn-sm ${view === 'admin' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setView('admin')}
                  >
                    <Shield size={14} /> Admin Controls
                  </button>
                  <button 
                    className={`btn btn-sm ${view === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setView('dashboard')}
                  >
                    <LayoutDashboard size={14} /> Sender Panel
                  </button>
                </>
              ) : (
                <button 
                  className="btn btn-sm btn-primary"
                  onClick={() => setView('dashboard')}
                >
                  <LayoutDashboard size={14} /> Dashboard
                </button>
              )}

              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>
                Hello, <strong>{user.full_name}</strong> ({user.role})
              </span>
              
              <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
                <LogOut size={14} /> Log Out
              </button>
            </>
          ) : (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Secure 256-bit SSL Encryption
            </span>
          )}
        </nav>
      </header>

      {/* Main Section */}
      <main className="main-content">
        {view === 'landing' && (
          <LandingView 
            onLoginSuccess={handleLoginSuccess} 
            showToast={showToast} 
          />
        )}
        
        {view === 'dashboard' && user && (
          <UserDashboard 
            user={user} 
            onRefreshUser={fetchUserProfile} 
            showToast={showToast} 
          />
        )}

        {view === 'admin' && user && (
          <AdminPanel 
            showToast={showToast} 
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{
        padding: '2rem',
        textAlign: 'center',
        borderTop: '1px solid var(--border-color)',
        color: 'var(--text-muted)',
        fontSize: '0.8rem',
        marginTop: '3rem',
        background: 'rgba(8, 8, 12, 0.4)'
      }}>
        <div>&copy; {new Date().getFullYear()} RemitApp Inc. All rights reserved.</div>
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', opacity: 0.7 }}>
          Compliance: Registered Money Services Business (MSB). Rates provided for informational purposes only.
        </div>
      </footer>

      {/* Toast Alert */}
      {toast.message && (
        <div className={`toast toast-${toast.type} glass`}>
          {toast.type === 'success' && <CheckCircle size={20} className="text-success" />}
          {toast.type === 'warning' && <AlertTriangle size={20} className="text-warning" />}
          {toast.type === 'error' && <XCircle size={20} className="text-danger" />}
          {toast.type === 'info' && <Info size={20} style={{ color: 'var(--primary)' }} />}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}
