import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  User, Wallet, Shield, Users, CreditCard, Send, History, 
  Plus, Check, X, RefreshCw, AlertTriangle, ArrowRight, HelpCircle 
} from 'lucide-react';
import RiskBreakdownCard from './RiskBreakdownCard';

export default function UserDashboard({ user, onRefreshUser, showToast }) {
  // Loading states
  const [loadingKyc, setLoadingKyc] = useState(false);
  const [loadingDeposit, setLoadingDeposit] = useState(false);
  const [loadingRecipients, setLoadingRecipients] = useState(false);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [sendingMoney, setSendingMoney] = useState(false);
  const [fundingTxnId, setFundingTxnId] = useState(null);

  // FDS risk breakdown expansion state
  const [expandedTxnIds, setExpandedTxnIds] = useState({});

  const toggleTxnExpand = (txnId) => {
    setExpandedTxnIds(prev => ({
      ...prev,
      [txnId]: !prev[txnId]
    }));
  };

  // Data states
  const [recipients, setRecipients] = useState([]);
  const [transactions, setTransactions] = useState([]);

  // Form states
  const [kycDocType, setKycDocType] = useState('passport');
  const [kycDocNumber, setKycDocNumber] = useState('');
  
  const [depositAmount, setDepositAmount] = useState('');
  
  // Recipient form states
  const [showRecipientForm, setShowRecipientForm] = useState(false);
  const [recName, setRecName] = useState('');
  const [recBank, setRecBank] = useState('');
  const [recAccount, setRecAccount] = useState('');
  const [recRouting, setRecRouting] = useState('');
  const [recCountry, setRecCountry] = useState('');
  const [recCurrency, setRecCurrency] = useState('EUR');

  // Remittance form states
  const [selectedRecipientId, setSelectedRecipientId] = useState('');
  const [sendAmount, setSendAmount] = useState('');
  const [sendEstimate, setSendEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);

  // Fetch initial dashboard data
  useEffect(() => {
    fetchRecipients();
    fetchTransactions();
  }, []);

  const fetchRecipients = async () => {
    setLoadingRecipients(true);
    try {
      const data = await api.listRecipients();
      setRecipients(data);
      if (data.length > 0 && !selectedRecipientId) {
        setSelectedRecipientId(data[0].id.toString());
      }
    } catch (err) {
      showToast(err.message || 'Failed to load recipients', 'error');
    } finally {
      setLoadingRecipients(false);
    }
  };

  const fetchTransactions = async () => {
    setLoadingTransactions(true);
    try {
      const data = await api.listTransactions();
      // Sort transactions by date descending (newest first)
      const sorted = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setTransactions(sorted);
    } catch (err) {
      showToast(err.message || 'Failed to load transactions', 'error');
    } finally {
      setLoadingTransactions(false);
    }
  };

  // Run estimation when send inputs change
  useEffect(() => {
    if (!sendAmount || parseFloat(sendAmount) <= 0 || !selectedRecipientId) {
      setSendEstimate(null);
      return;
    }

    const recipient = recipients.find(r => r.id.toString() === selectedRecipientId);
    if (!recipient) return;

    const delayDebounce = setTimeout(async () => {
      setEstimating(true);
      try {
        const data = await api.estimateTransfer('USD', recipient.currency, parseFloat(sendAmount));
        setSendEstimate(data);
      } catch (err) {
        console.error(err);
        setSendEstimate(null);
      } finally {
        setEstimating(false);
      }
    }, 400);

    return () => clearTimeout(delayDebounce);
  }, [sendAmount, selectedRecipientId, recipients]);

  const handleKycSubmit = async (e) => {
    e.preventDefault();
    if (!kycDocNumber) {
      showToast('Please enter document number', 'warning');
      return;
    }
    setLoadingKyc(true);
    try {
      await api.submitKyc(kycDocType, kycDocNumber);
      showToast('KYC application submitted successfully', 'success');
      onRefreshUser(); // Refresh parent user profile
    } catch (err) {
      showToast(err.message || 'Failed to submit KYC', 'error');
    } finally {
      setLoadingKyc(false);
    }
  };

  const handleDepositSubmit = async (e) => {
    e.preventDefault();
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) {
      showToast('Please enter a valid amount to deposit', 'warning');
      return;
    }
    setLoadingDeposit(true);
    try {
      await api.deposit(amount);
      showToast(`Successfully deposited $${amount.toFixed(2)} USD`, 'success');
      setDepositAmount('');
      onRefreshUser();
    } catch (err) {
      showToast(err.message || 'Deposit failed', 'error');
    } finally {
      setLoadingDeposit(false);
    }
  };

  const handleCreateRecipient = async (e) => {
    e.preventDefault();
    if (!recName || !recBank || !recAccount || !recCountry || !recCurrency) {
      showToast('Please fill in all required fields', 'warning');
      return;
    }
    setLoadingRecipients(true);
    try {
      const newRec = await api.createRecipient({
        name: recName,
        bankName: recBank,
        accountNumber: recAccount,
        routingNumber: recRouting,
        country: recCountry,
        currency: recCurrency
      });
      showToast('Recipient added successfully', 'success');
      // Reset form
      setRecName('');
      setRecBank('');
      setRecAccount('');
      setRecRouting('');
      setRecCountry('');
      setShowRecipientForm(false);
      
      // Refresh list
      await fetchRecipients();
      // Set the newly created recipient as selected
      if (newRec && newRec.id) {
        setSelectedRecipientId(newRec.id.toString());
      }
    } catch (err) {
      showToast(err.message || 'Failed to add recipient', 'error');
    } finally {
      setLoadingRecipients(false);
    }
  };

  const handleSendMoney = async (e) => {
    e.preventDefault();
    if (!selectedRecipientId || !sendAmount) {
      showToast('Please select a recipient and enter amount', 'warning');
      return;
    }
    if (user.kyc_status !== 'APPROVED') {
      showToast('KYC approval is required before you can transfer funds', 'error');
      return;
    }
    const amount = parseFloat(sendAmount);
    if (isNaN(amount) || amount <= 0) {
      showToast('Please enter a valid transfer amount', 'warning');
      return;
    }

    setSendingMoney(true);
    try {
      const txn = await api.createTransaction(selectedRecipientId, amount);
      showToast(`Transfer created (Ref: ${txn.reference_number}). Status: PENDING`, 'success');
      setSendAmount('');
      setSendEstimate(null);
      
      // Reload transactions list
      await fetchTransactions();
    } catch (err) {
      showToast(err.message || 'Failed to initiate transfer', 'error');
    } finally {
      setSendingMoney(false);
    }
  };

  const handleFundTransaction = async (txnId, totalCost) => {
    if (user.wallet_balance < totalCost) {
      showToast(`Insufficient funds. You need $${totalCost.toFixed(2)} USD but only have $${user.wallet_balance.toFixed(2)} USD.`, 'error');
      return;
    }

    setFundingTxnId(txnId);
    try {
      await api.fundTransaction(txnId);
      showToast('Transaction funded successfully! Payout processing started.', 'success');
      onRefreshUser();
      await fetchTransactions();
    } catch (err) {
      showToast(err.message || 'Funding failed', 'error');
    } finally {
      setFundingTxnId(null);
    }
  };

  const getRecipientLabel = (recipientId) => {
    const r = recipients.find(x => x.id === recipientId);
    return r ? `${r.name} (${r.bank_name})` : `Recipient ID: ${recipientId}`;
  };

  return (
    <div className="dashboard-grid">
      
      {/* 1. Profile Card */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <User className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Your Profile</h3>
          </div>
          <span className={`badge badge-${user.kyc_status.toLowerCase()}`}>
            {user.kyc_status.replace('_', ' ')}
          </span>
        </div>
        
        <div className="profile-info">
          <div className="info-row">
            <span className="info-label">Full Name</span>
            <span className="info-value">{user.full_name}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Email Address</span>
            <span className="info-value">{user.email}</span>
          </div>
          <div className="info-row">
            <span className="info-label">KYC Document</span>
            <span className="info-value">
              {user.kyc_document_type ? (
                <span>
                  {user.kyc_document_type.toUpperCase()} ({user.kyc_document_number})
                </span>
              ) : (
                <span className="text-muted">Not submitted</span>
              )}
            </span>
          </div>
          <div className="info-row">
            <span className="info-label">Registration Date</span>
            <span className="info-value">
              {new Date(user.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* KYC Verification Action */}
        {user.kyc_status === 'UNSUBMITTED' && (
          <form onSubmit={handleKycSubmit} style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={18} className="text-warning" style={{ color: 'var(--warning)' }} />
              Submit KYC Documents
            </h4>
            <div className="calc-row">
              <div className="form-group">
                <label>Document Type</label>
                <select 
                  className="input-control calc-select"
                  value={kycDocType}
                  onChange={(e) => setKycDocType(e.target.value)}
                >
                  <option value="passport">Passport</option>
                  <option value="national_id">National ID</option>
                  <option value="drivers_license">Driver's License</option>
                </select>
              </div>
              <div className="form-group">
                <label>Document Number</label>
                <input 
                  type="text" 
                  className="input-control"
                  placeholder="E.g., G4582941"
                  value={kycDocNumber}
                  onChange={(e) => setKycDocNumber(e.target.value)}
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-sm" style={{ width: '100%' }} disabled={loadingKyc}>
              {loadingKyc ? 'Submitting...' : 'Submit Verification Docs'}
            </button>
          </form>
        )}

        {user.kyc_status === 'PENDING_APPROVAL' && (
          <div style={{ 
            marginTop: '1.5rem', 
            padding: '1rem', 
            borderRadius: '10px', 
            background: 'var(--warning-bg)', 
            border: '1px solid var(--warning-border)',
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'flex-start'
          }}>
            <AlertTriangle className="text-warning" style={{ color: 'var(--warning)', flexShrink: 0 }} size={20} />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--warning)', fontSize: '0.9rem' }}>Verification Pending</div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                Your identity verification request is currently under review by our compliance team. You will be able to make transfers once approved.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 2. Wallet & Balance Card */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <Wallet className="text-success" style={{ color: 'var(--success)' }} />
            <h3>Your Wallet</h3>
          </div>
        </div>

        <div className="wallet-balance-container">
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Wallet Balance (USD)</span>
          <span className="balance-amount">${user.wallet_balance.toFixed(2)}</span>
        </div>

        <form onSubmit={handleDepositSubmit}>
          <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CreditCard size={18} /> Add Mock Funds
          </h4>
          <div className="calc-row">
            <div className="form-group" style={{ gridColumn: '1 / span 2' }}>
              <label>Amount (USD)</label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                <input 
                  type="number" 
                  className="input-control" 
                  style={{ paddingLeft: '2rem' }}
                  placeholder="500.00"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  min="1"
                  required
                />
              </div>
            </div>
          </div>
          <button type="submit" className="btn btn-success" style={{ width: '100%' }} disabled={loadingDeposit}>
            {loadingDeposit ? 'Adding...' : 'Deposit Funds'}
          </button>
        </form>
      </div>

      {/* 3. Recipient Management Card */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <Users className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Recipients</h3>
          </div>
          <button 
            className="btn btn-secondary btn-sm"
            onClick={() => setShowRecipientForm(!showRecipientForm)}
          >
            {showRecipientForm ? <X size={14} /> : <Plus size={14} />}
            {showRecipientForm ? 'Cancel' : 'Add Recipient'}
          </button>
        </div>

        {showRecipientForm ? (
          <form onSubmit={handleCreateRecipient} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="form-group" style={{ marginBottom: '0.5rem' }}>
              <label>Full Name</label>
              <input 
                type="text" 
                className="input-control" 
                placeholder="Raj Kumar"
                value={recName} 
                onChange={(e) => setRecName(e.target.value)} 
                required 
              />
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                <label>Bank Name</label>
                <input 
                  type="text" 
                  className="input-control" 
                  placeholder="State Bank of India"
                  value={recBank} 
                  onChange={(e) => setRecBank(e.target.value)} 
                  required 
                />
              </div>
              <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                <label>Account Number</label>
                <input 
                  type="text" 
                  className="input-control" 
                  placeholder="9876543210"
                  value={recAccount} 
                  onChange={(e) => setRecAccount(e.target.value)} 
                  required 
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                <label>Routing/IFSC Number (Optional)</label>
                <input 
                  type="text" 
                  className="input-control" 
                  placeholder="SBIN0001234"
                  value={recRouting} 
                  onChange={(e) => setRecRouting(e.target.value)} 
                />
              </div>
              <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                <label>Country</label>
                <input 
                  type="text" 
                  className="input-control" 
                  placeholder="India"
                  value={recCountry} 
                  onChange={(e) => setRecCountry(e.target.value)} 
                  required 
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Payout Currency</label>
              <select 
                className="input-control calc-select"
                value={recCurrency}
                onChange={(e) => setRecCurrency(e.target.value)}
              >
                <option value="EUR">EUR (Euro)</option>
                <option value="KES">KES (Kenyan Shilling)</option>
                <option value="INR">INR (Indian Rupee)</option>
                <option value="PHP">PHP (Philippine Peso)</option>
                <option value="GBP">GBP (British Pound)</option>
                <option value="MXN">MXN (Mexican Peso)</option>
              </select>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loadingRecipients}>
              {loadingRecipients ? 'Adding...' : 'Save Recipient'}
            </button>
          </form>
        ) : (
          <div className="items-list">
            {recipients.length === 0 ? (
              <div className="empty-state">
                <Users size={32} />
                <span>No recipients added yet. Click "Add Recipient" to register one.</span>
              </div>
            ) : (
              recipients.map((r) => (
                <div key={r.id} className="list-item">
                  <div className="item-main">
                    <span className="item-title">{r.name}</span>
                    <span className="item-subtitle">{r.bank_name} • {r.account_number}</span>
                  </div>
                  <span className="badge badge-approved" style={{ fontSize: '0.7rem' }}>
                    {r.currency} ({r.country})
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* 4. Send Money Card */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <Send className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Send Money</h3>
          </div>
        </div>

        {user.kyc_status !== 'APPROVED' ? (
          <div className="empty-state" style={{ padding: '2rem 1rem' }}>
            <Shield size={36} className="text-warning" style={{ color: 'var(--warning)', opacity: 0.6 }} />
            <span style={{ fontWeight: 600 }}>KYC Approval Required</span>
            <span style={{ fontSize: '0.85rem' }}>
              To ensure compliance and security, you must submit identity verification documents and receive admin approval before sending money.
            </span>
          </div>
        ) : recipients.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem 1rem' }}>
            <Users size={36} style={{ opacity: 0.6 }} />
            <span style={{ fontWeight: 600 }}>No Recipients Available</span>
            <span style={{ fontSize: '0.85rem' }}>
              Please add at least one recipient bank account in the Recipients card before starting a transfer.
            </span>
          </div>
        ) : (
          <form onSubmit={handleSendMoney}>
            <div className="form-group">
              <label>Select Recipient</label>
              <select
                className="input-control calc-select"
                value={selectedRecipientId}
                onChange={(e) => setSelectedRecipientId(e.target.value)}
              >
                {recipients.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.bank_name} - {r.currency})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Send Amount (USD)</label>
              <div style={{ position: 'relative' }}>
                <span style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                <input
                  type="number"
                  className="input-control"
                  style={{ paddingLeft: '2rem' }}
                  placeholder="100.00"
                  value={sendAmount}
                  onChange={(e) => setSendAmount(e.target.value)}
                  min="1"
                  required
                />
              </div>
            </div>

            {estimating && (
              <div style={{ display: 'flex', justifyContent: 'center', margin: '1rem 0' }}>
                <RefreshCw size={20} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
              </div>
            )}

            {sendEstimate && !estimating && (
              <div className="calc-details" style={{ margin: '1rem 0', paddingLeft: '1rem' }}>
                <div className="calc-detail-item">
                  <span>Exchange Rate</span>
                  <span>1 USD = {sendEstimate.exchange_rate} {sendEstimate.target_currency}</span>
                </div>
                <div className="calc-detail-item">
                  <span>Dynamic Transfer Fee</span>
                  <span>${sendEstimate.fee.toFixed(2)} USD</span>
                </div>
                <div className="calc-detail-item">
                  <span>Recipient Will Get</span>
                  <span style={{ fontWeight: 600, color: 'var(--success)' }}>
                    {sendEstimate.target_amount.toFixed(2)} {sendEstimate.target_currency}
                  </span>
                </div>
                <div className="calc-detail-item total" style={{ fontSize: '1rem' }}>
                  <span>Total Wallet Cost</span>
                  <span style={{ color: user.wallet_balance >= sendEstimate.total_required ? 'var(--success)' : 'var(--danger)' }}>
                    ${sendEstimate.total_required.toFixed(2)} USD
                  </span>
                </div>
              </div>
            )}

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%', marginTop: '1rem' }}
              disabled={sendingMoney}
            >
              {sendingMoney ? 'Creating Transfer...' : 'Initiate Transfer'}
            </button>
          </form>
        )}
      </div>

      {/* 5. Transaction History Card (Span Full Width) */}
      <div className="glass card grid-span-full">
        <div className="card-header">
          <div className="card-title-icon">
            <History className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Transaction History</h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchTransactions} disabled={loadingTransactions}>
            <RefreshCw size={14} className={loadingTransactions ? 'animate-spin' : ''} style={loadingTransactions ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
        </div>

        {transactions.length === 0 ? (
          <div className="empty-state">
            <History size={36} />
            <span>No transactions recorded yet. When you send money, they will show up here.</span>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Ref Number</th>
                  <th>Recipient</th>
                  <th>Send (USD)</th>
                  <th>Fee</th>
                  <th>Payout Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => {
                  const feeAmount = t.fee;
                  const totalCost = t.source_amount + feeAmount;
                  const isRiskRow = t.status === 'FAILED' || t.status === 'SUSPICIOUS';
                  return (
                    <React.Fragment key={t.id}>
                      <tr 
                        style={{ cursor: isRiskRow ? 'pointer' : 'default' }}
                        onClick={() => isRiskRow && toggleTxnExpand(t.id)}
                        className={isRiskRow ? 'row-clickable' : ''}
                      >
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{t.reference_number}</td>
                        <td>{getRecipientLabel(t.recipient_id)}</td>
                        <td style={{ fontWeight: 500 }}>${t.source_amount.toFixed(2)}</td>
                        <td style={{ color: 'var(--text-muted)' }}>${feeAmount.toFixed(2)}</td>
                        <td style={{ fontWeight: 600, color: 'var(--success)' }}>
                          {t.target_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {t.target_currency}
                        </td>
                        <td>
                          <span className={`badge badge-${t.status.toLowerCase()}`}>
                            {t.status}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                          {new Date(t.created_at).toLocaleString()}
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {t.status === 'PENDING' ? (
                            <button
                              className="btn btn-success btn-sm"
                              style={{ display: 'inline-flex', padding: '0.3rem 0.6rem' }}
                              onClick={() => handleFundTransaction(t.id, totalCost)}
                              disabled={fundingTxnId === t.id}
                            >
                              {fundingTxnId === t.id ? (
                                <RefreshCw size={12} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
                              ) : (
                                'Pay / Fund'
                              )}
                            </button>
                          ) : isRiskRow ? (
                            <button
                              type="button"
                              className="btn btn-sm"
                              style={{ 
                                display: 'inline-flex', 
                                padding: '0.3rem 0.6rem', 
                                fontSize: '0.75rem',
                                backgroundColor: t.status === 'FAILED' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                                border: `1px solid ${t.status === 'FAILED' ? 'var(--danger-border)' : 'var(--warning-border)'}`,
                                color: t.status === 'FAILED' ? 'var(--danger)' : 'var(--warning)',
                                fontWeight: 600
                              }}
                              onClick={() => toggleTxnExpand(t.id)}
                            >
                              {expandedTxnIds[t.id] ? 'Hide Report' : 'Risk Report'}
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None</span>
                          )}
                        </td>
                      </tr>
                      {expandedTxnIds[t.id] && isRiskRow && (
                        <tr>
                          <td colSpan="8" style={{ padding: '0 1rem 1rem 1rem', borderTop: 'none', background: 'rgba(255,255,255,0.01)' }}>
                            <RiskBreakdownCard transaction={t} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
