import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ArrowRight, RefreshCw, LogIn, UserPlus, Info, TrendingUp } from 'lucide-react';

export default function LandingView({ onLoginSuccess, showToast }) {
  const [activeTab, setActiveTab] = useState('login'); // 'login' | 'register'
  
  // Auth Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerName, setRegisterName] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Calculator State
  const [rates, setRates] = useState([]);
  const [calcSourceCurrency, setCalcSourceCurrency] = useState('USD');
  const [calcTargetCurrency, setCalcTargetCurrency] = useState('EUR');
  const [calcSourceAmount, setCalcSourceAmount] = useState('100');
  const [estimate, setEstimate] = useState(null);
  const [calcLoading, setCalcLoading] = useState(false);

  // Fetch available rates on load
  useEffect(() => {
    fetchRates();
  }, []);

  const fetchRates = async () => {
    try {
      const data = await api.getRates();
      setRates(data);
      if (data.length > 0) {
        // Set default target currency to first available rate
        setCalcTargetCurrency(data[0].target_currency);
      }
    } catch (err) {
      showToast(err.message || 'Failed to fetch exchange rates', 'error');
    }
  };

  // Run estimation when inputs change
  useEffect(() => {
    if (!calcSourceAmount || parseFloat(calcSourceAmount) <= 0) {
      setEstimate(null);
      return;
    }
    const delayDebounce = setTimeout(() => {
      runEstimation();
    }, 400);

    return () => clearTimeout(delayDebounce);
  }, [calcSourceAmount, calcTargetCurrency]);

  const runEstimation = async () => {
    setCalcLoading(true);
    try {
      const amount = parseFloat(calcSourceAmount);
      if (isNaN(amount) || amount <= 0) return;
      const data = await api.estimateTransfer(calcSourceCurrency, calcTargetCurrency, amount);
      setEstimate(data);
    } catch (err) {
      console.error(err);
      setEstimate(null);
    } finally {
      setCalcLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      showToast('Please fill in all fields', 'warning');
      return;
    }
    setAuthLoading(true);
    try {
      await api.login(loginEmail, loginPassword);
      showToast('Logged in successfully', 'success');
      onLoginSuccess();
    } catch (err) {
      showToast(err.message || 'Login failed. Check your credentials.', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!registerEmail || !registerName || !registerPassword) {
      showToast('Please fill in all fields', 'warning');
      return;
    }
    if (registerPassword.length < 6) {
      showToast('Password must be at least 6 characters long', 'warning');
      return;
    }
    setAuthLoading(true);
    try {
      await api.register(registerEmail, registerName, registerPassword);
      showToast('Account registered successfully! Please log in.', 'success');
      setActiveTab('login');
      // Autofill email for user convenience
      setLoginEmail(registerEmail);
      setLoginPassword('');
    } catch (err) {
      showToast(err.message || 'Registration failed.', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  return (
    <div className="landing-grid">
      <div className="hero-text">
        <h1>Global Remittance, <br />Simplified.</h1>
        <p>
          Send money internationally with zero hassle. Experience lightning-fast transfers,
          real-time exchange rates, and bank-grade security. Track your transactions end-to-end.
        </p>

        <div className="glass calc-card">
          <div className="card-title-icon" style={{ marginBottom: '1.25rem' }}>
            <TrendingUp size={22} className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Live Transfer Estimator</h3>
          </div>

          <div className="calc-row">
            <div className="form-group">
              <label>You Send (USD)</label>
              <input
                type="number"
                className="input-control"
                value={calcSourceAmount}
                onChange={(e) => setCalcSourceAmount(e.target.value)}
                placeholder="100.00"
                min="1"
              />
            </div>
            <div className="form-group">
              <label>To Currency</label>
              <select
                className="input-control calc-select"
                value={calcTargetCurrency}
                onChange={(e) => setCalcTargetCurrency(e.target.value)}
              >
                {rates.map((r) => (
                  <option key={r.id} value={r.target_currency}>
                    {r.target_currency}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {calcLoading && (
            <div style={{ display: 'flex', justifyContent: 'center', margin: '1rem 0' }}>
              <RefreshCw size={24} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          )}

          {estimate && !calcLoading && (
            <div className="calc-details">
              <div className="calc-detail-item">
                <span>Exchange Rate</span>
                <span>1 USD = {estimate.exchange_rate} {estimate.target_currency}</span>
              </div>
              <div className="calc-detail-item">
                <span>Transfer Fee</span>
                <span>${estimate.fee.toFixed(2)} USD</span>
              </div>
              <div className="calc-detail-item">
                <span>Recipient Gets</span>
                <span style={{ fontWeight: 600, color: 'var(--success)' }}>
                  {estimate.target_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {estimate.target_currency}
                </span>
              </div>
              <div className="calc-detail-item total">
                <span>Total Required</span>
                <span>${estimate.total_required.toFixed(2)} USD</span>
              </div>
            </div>
          )}

          {!estimate && !calcLoading && (
            <div className="empty-state" style={{ padding: '1.5rem 0' }}>
              <Info size={18} />
              <span style={{ fontSize: '0.85rem' }}>Enter an amount to see live estimates and fees</span>
            </div>
          )}
        </div>

        {/* Live Rates Grid */}
        <div style={{ marginTop: '2rem' }}>
          <h4>Supported Exchange Rates</h4>
          <div className="rates-grid">
            {rates.map((r) => (
              <div key={r.id} className="glass rate-card" style={{ padding: '1rem' }}>
                <div className="rate-pair">
                  <div className="currency-flag-mock">{r.target_currency.slice(0, 2)}</div>
                  <div>
                    <div style={{ fontWeight: 600 }}>USD / {r.target_currency}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Fee: {r.fee_percentage}%</div>
                  </div>
                </div>
                <div className="rate-values">
                  <div className="rate-number">{r.rate}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="glass auth-card">
          <div className="auth-tabs">
            <div
              className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
              onClick={() => setActiveTab('login')}
            >
              Sign In
            </div>
            <div
              className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`}
              onClick={() => setActiveTab('register')}
            >
              Sign Up
            </div>
          </div>

          {activeTab === 'login' ? (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  className="input-control"
                  placeholder="name@example.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  className="input-control"
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '1rem' }}
                disabled={authLoading}
              >
                {authLoading ? (
                  <>
                    <RefreshCw size={18} style={{ animation: 'spin 1s linear infinite' }} /> Signing In...
                  </>
                ) : (
                  <>
                    <LogIn size={18} /> Sign In
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  className="input-control"
                  placeholder="Jane Doe"
                  value={registerName}
                  onChange={(e) => setRegisterName(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  className="input-control"
                  placeholder="name@example.com"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password (Min 6 chars)</label>
                <input
                  type="password"
                  className="input-control"
                  placeholder="••••••••"
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  required
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '1rem' }}
                disabled={authLoading}
              >
                {authLoading ? (
                  <>
                    <RefreshCw size={18} style={{ animation: 'spin 1s linear infinite' }} /> Registering...
                  </>
                ) : (
                  <>
                    <UserPlus size={18} /> Create Account
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
