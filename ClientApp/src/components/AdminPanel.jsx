import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  Users, ShieldCheck, DollarSign, ListOrdered, CheckCircle2, 
  XCircle, Edit, RefreshCw, Eye, ArrowRight, HelpCircle, BrainCircuit,
  Lock, Unlock
} from 'lucide-react';
import RiskBreakdownCard from './RiskBreakdownCard';
import FraudInvestigator from './FraudInvestigator';

export default function AdminPanel({ showToast }) {
  // Tab state
  const [activeTab, setActiveTab] = useState('controls'); // 'controls' | 'investigator'

  // Loading states
  const [loadingKyc, setLoadingKyc] = useState(false);
  const [loadingRates, setLoadingRates] = useState(false);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [updatingTxnId, setUpdatingTxnId] = useState(null);

  // Data states
  const [pendingKycUsers, setPendingKycUsers] = useState([]);
  const [rates, setRates] = useState([]);
  const [allTransactions, setAllTransactions] = useState([]);

  // FDS risk breakdown expansion state
  const [expandedTxnIds, setExpandedTxnIds] = useState({});

  const toggleTxnExpand = (txnId) => {
    setExpandedTxnIds(prev => ({
      ...prev,
      [txnId]: !prev[txnId]
    }));
  };

  // Exchange rate form state
  const [rateSource, setRateSource] = useState('USD');
  const [rateTarget, setRateTarget] = useState('');
  const [rateValue, setRateValue] = useState('');
  const [rateFeePercent, setRateFeePercent] = useState('');
  const [editingRateId, setEditingRateId] = useState(null);
  const [savingRate, setSavingRate] = useState(false);

  // Wallet management state
  const [allUsers, setAllUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [walletActionUserId, setWalletActionUserId] = useState(null);
  const [kycActionUserId, setKycActionUserId] = useState(null);

  // Fetch all admin data on mount
  useEffect(() => {
    fetchPendingKyc();
    fetchRates();
    fetchAllTransactions();
    fetchAllUsers();
  }, []);

  const fetchAllUsers = async () => {
    setLoadingUsers(true);
    try {
      const data = await api.listAllUsers();
      setAllUsers(data);
    } catch (err) {
      showToast(err.message || 'Failed to fetch users', 'error');
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchPendingKyc = async () => {
    setLoadingKyc(true);
    try {
      const data = await api.getPendingKyc();
      setPendingKycUsers(data);
    } catch (err) {
      showToast(err.message || 'Failed to fetch pending KYC list', 'error');
    } finally {
      setLoadingKyc(false);
    }
  };

  const fetchRates = async () => {
    setLoadingRates(true);
    try {
      const data = await api.getRates();
      setRates(data);
    } catch (err) {
      showToast(err.message || 'Failed to fetch rates', 'error');
    } finally {
      setLoadingRates(false);
    }
  };

  const fetchAllTransactions = async () => {
    setLoadingTransactions(true);
    try {
      const data = await api.listAllTransactions();
      const sorted = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAllTransactions(sorted);
    } catch (err) {
      showToast(err.message || 'Failed to fetch global transactions', 'error');
    } finally {
      setLoadingTransactions(false);
    }
  };

  const handleApproveKyc = async (userId, approve) => {
    setLoadingKyc(true);
    try {
      await api.approveKyc(userId, approve);
      showToast(
        approve ? 'KYC application approved successfully' : 'KYC application rejected',
        approve ? 'success' : 'error'
      );
      await fetchPendingKyc();
    } catch (err) {
      showToast(err.message || 'Failed to process KYC decision', 'error');
    } finally {
      setLoadingKyc(false);
    }
  };

  const handleRateSubmit = async (e) => {
    e.preventDefault();
    if (!rateSource || !rateTarget || !rateValue || !rateFeePercent) {
      showToast('Please fill in all rates fields', 'warning');
      return;
    }
    const val = parseFloat(rateValue);
    const fee = parseFloat(rateFeePercent);
    if (isNaN(val) || val <= 0 || isNaN(fee) || fee < 0) {
      showToast('Please enter valid rate and fee percentage values', 'warning');
      return;
    }

    setSavingRate(true);
    try {
      await api.createOrUpdateRate(rateSource.toUpperCase(), rateTarget.toUpperCase(), val, fee);
      showToast(`Exchange rate for ${rateSource}/${rateTarget} saved successfully!`, 'success');
      
      // Reset form fields
      setRateTarget('');
      setRateValue('');
      setRateFeePercent('');
      setEditingRateId(null);
      
      // Refresh list
      await fetchRates();
    } catch (err) {
      showToast(err.message || 'Failed to update exchange rate', 'error');
    } finally {
      setSavingRate(false);
    }
  };

  const handleEditRate = (rate) => {
    setEditingRateId(rate.id);
    setRateSource(rate.source_currency);
    setRateTarget(rate.target_currency);
    setRateValue(rate.rate.toString());
    setRateFeePercent(rate.fee_percentage.toString());
  };

  const handleUpdateStatus = async (txnId, newStatus) => {
    setUpdatingTxnId(txnId);
    try {
      await api.updateTransactionStatus(txnId, newStatus);
      showToast(`Transaction #${txnId} status updated to ${newStatus}`, 'success');
      await fetchAllTransactions();
    } catch (err) {
      showToast(err.message || 'Failed to update transaction status', 'error');
    } finally {
      setUpdatingTxnId(null);
    }
  };

  const handleFreezeWallet = async (userId) => {
    setWalletActionUserId(userId);
    try {
      await api.freezeWallet(userId);
      showToast(`Wallet for user #${userId} has been frozen`, 'success');
      await fetchAllUsers();
    } catch (err) {
      showToast(err.message || 'Failed to freeze wallet', 'error');
    } finally {
      setWalletActionUserId(null);
    }
  };

  const handleUnfreezeWallet = async (userId) => {
    setWalletActionUserId(userId);
    try {
      await api.unfreezeWallet(userId);
      showToast(`Wallet for user #${userId} has been unfrozen`, 'success');
      await fetchAllUsers();
    } catch (err) {
      showToast(err.message || 'Failed to unfreeze wallet', 'error');
    } finally {
      setWalletActionUserId(null);
    }
  };

  const handleUpdateKycStatus = async (userId, newStatus) => {
    setKycActionUserId(userId);
    try {
      await api.updateKycStatus(userId, newStatus);
      showToast(`KYC status for user #${userId} updated to ${newStatus}`, 'success');
      await fetchAllUsers();
    } catch (err) {
      showToast(err.message || 'Failed to update KYC status', 'error');
    } finally {
      setKycActionUserId(null);
    }
  };

  return (
    <div>
      {/* Tab Navigation */}
      <div style={{ 
        display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', 
        borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem'
      }}>
        <button
          className={`btn btn-sm ${activeTab === 'controls' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('controls')}
        >
          <ShieldCheck size={14} /> Admin Controls
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'investigator' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('investigator')}
        >
          <BrainCircuit size={14} /> AI Investigator
        </button>
      </div>

      {/* AI Investigator Tab */}
      {activeTab === 'investigator' && (
        <FraudInvestigator showToast={showToast} />
      )}

      {/* Admin Controls Tab */}
      {activeTab === 'controls' && (
    <div className="dashboard-grid">
      
      {/* 1. KYC Approvals Queue */}
      <div className="glass card grid-span-full">
        <div className="card-header">
          <div className="card-title-icon">
            <Users className="text-warning" style={{ color: 'var(--warning)' }} />
            <h3>KYC Approval Queue</h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchPendingKyc} disabled={loadingKyc}>
            <RefreshCw size={14} className={loadingKyc ? 'animate-spin' : ''} style={loadingKyc ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
        </div>

        {pendingKycUsers.length === 0 ? (
          <div className="empty-state">
            <ShieldCheck size={36} className="text-success" style={{ color: 'var(--success)', opacity: 0.6 }} />
            <span>No pending KYC applications. All users are current.</span>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>User ID</th>
                  <th>Full Name</th>
                  <th>Email Address</th>
                  <th>Document Type</th>
                  <th>Document Number</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingKycUsers.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td style={{ fontWeight: 600 }}>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td style={{ textTransform: 'uppercase' }}>{u.kyc_document_type}</td>
                    <td style={{ fontFamily: 'monospace' }}>{u.kyc_document_number}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-success btn-sm"
                          style={{ display: 'inline-flex', padding: '0.3rem 0.6rem' }}
                          onClick={() => handleApproveKyc(u.id, true)}
                        >
                          <CheckCircle2 size={14} /> Approve
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          style={{ display: 'inline-flex', padding: '0.3rem 0.6rem' }}
                          onClick={() => handleApproveKyc(u.id, false)}
                        >
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Wallet Freeze / Unfreeze */}
      <div className="glass card grid-span-full">
        <div className="card-header">
          <div className="card-title-icon">
            <Lock className="text-danger" style={{ color: 'var(--danger)' }} />
            <h3>Wallet Management</h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchAllUsers} disabled={loadingUsers}>
            <RefreshCw size={14} className={loadingUsers ? 'animate-spin' : ''} style={loadingUsers ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
        </div>

        {allUsers.length === 0 ? (
          <div className="empty-state">
            <Users size={36} style={{ opacity: 0.6 }} />
            <span>{loadingUsers ? 'Loading users...' : 'No users found.'}</span>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Full Name</th>
                  <th>Email</th>
                  <th>KYC Status</th>
                  <th>Wallet Status</th>
                  <th>Balance</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allUsers.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td style={{ fontWeight: 600 }}>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        background: u.kyc_status === 'APPROVED' ? 'rgba(16,185,129,0.15)' :
                                    u.kyc_status === 'FROZEN' ? 'rgba(239,68,68,0.15)' :
                                    'rgba(245,158,11,0.15)',
                        color: u.kyc_status === 'APPROVED' ? 'var(--success)' :
                               u.kyc_status === 'FROZEN' ? 'var(--danger)' :
                               'var(--warning)'
                      }}>
                        {u.kyc_status}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        background: u.wallet_frozen === 'FROZEN' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                        color: u.wallet_frozen === 'FROZEN' ? 'var(--danger)' : 'var(--success)'
                      }}>
                        {u.wallet_frozen === 'FROZEN' ? 'FROZEN' : 'ACTIVE'}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>${u.wallet_balance?.toFixed(2)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        {u.wallet_frozen === 'FROZEN' ? (
                          <button
                            className="btn btn-success btn-sm"
                            style={{ display: 'inline-flex', padding: '0.3rem 0.6rem' }}
                            onClick={() => handleUnfreezeWallet(u.id)}
                            disabled={walletActionUserId === u.id}
                          >
                            <Unlock size={14} /> Unfreeze
                          </button>
                        ) : (
                          <button
                            className="btn btn-danger btn-sm"
                            style={{ display: 'inline-flex', padding: '0.3rem 0.6rem' }}
                            onClick={() => handleFreezeWallet(u.id)}
                            disabled={walletActionUserId === u.id}
                          >
                            <Lock size={14} /> Freeze
                          </button>
                        )}
                        <select
                          style={{
                            padding: '0.3rem 0.4rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-secondary)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer'
                          }}
                          value={u.kyc_status}
                          disabled={kycActionUserId === u.id}
                          onChange={(e) => handleUpdateKycStatus(u.id, e.target.value)}
                        >
                          <option value="PENDING_SUBMISSION">PENDING_SUBMISSION</option>
                          <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
                          <option value="APPROVED">APPROVED</option>
                          <option value="REJECTED">REJECTED</option>
                          <option value="FROZEN">FROZEN</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 2. Exchange Rates Editor */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <DollarSign className="text-success" style={{ color: 'var(--success)' }} />
            <h3>{editingRateId ? 'Edit Exchange Rate' : 'Add / Update Exchange Rate'}</h3>
          </div>
          {editingRateId && (
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setEditingRateId(null);
                setRateTarget('');
                setRateValue('');
                setRateFeePercent('');
              }}
            >
              Cancel Edit
            </button>
          )}
        </div>

        <form onSubmit={handleRateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group" style={{ marginBottom: '0.5rem' }}>
              <label>Source Currency</label>
              <input 
                type="text" 
                className="input-control" 
                value={rateSource} 
                disabled 
              />
            </div>
            <div className="form-group" style={{ marginBottom: '0.5rem' }}>
              <label>Target Currency</label>
              <input 
                type="text" 
                className="input-control" 
                placeholder="E.g., EUR, INR"
                value={rateTarget} 
                onChange={(e) => setRateTarget(e.target.value)} 
                disabled={editingRateId !== null}
                required 
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group" style={{ marginBottom: '0.5rem' }}>
              <label>Exchange Rate</label>
              <input 
                type="number" 
                step="0.0001"
                className="input-control" 
                placeholder="E.g., 0.92"
                value={rateValue} 
                onChange={(e) => setRateValue(e.target.value)} 
                required 
              />
            </div>
            <div className="form-group" style={{ marginBottom: '0.5rem' }}>
              <label>Fee Percentage (%)</label>
              <input 
                type="number" 
                step="0.1"
                className="input-control" 
                placeholder="E.g., 1.5"
                value={rateFeePercent} 
                onChange={(e) => setRateFeePercent(e.target.value)} 
                required 
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ marginTop: '0.5rem' }} disabled={savingRate}>
            {savingRate ? 'Saving Rate...' : 'Save Exchange Rate'}
          </button>
        </form>
      </div>

      {/* 3. Rates List */}
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <ListOrdered className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Rates Directory</h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchRates} disabled={loadingRates}>
            <RefreshCw size={14} className={loadingRates ? 'animate-spin' : ''} style={loadingRates ? { animation: 'spin 1s linear infinite' } : {}} />
          </button>
        </div>

        <div className="items-list" style={{ maxHeight: '260px' }}>
          {rates.length === 0 ? (
            <div className="empty-state">
              <span>No exchange rates configured.</span>
            </div>
          ) : (
            rates.map((r) => (
              <div key={r.id} className="list-item">
                <div className="item-main">
                  <span className="item-title">{r.source_currency} / {r.target_currency}</span>
                  <span className="item-subtitle">Rate: {r.rate} • Fee: {r.fee_percentage}%</span>
                </div>
                <button 
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '0.25rem 0.5rem', display: 'flex', gap: '0.25rem' }}
                  onClick={() => handleEditRate(r)}
                >
                  <Edit size={12} /> Edit
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 4. Global Transactions Monitor (Span Full Width) */}
      <div className="glass card grid-span-full">
        <div className="card-header">
          <div className="card-title-icon">
            <ListOrdered className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>System Transactions</h3>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchAllTransactions} disabled={loadingTransactions}>
            <RefreshCw size={14} className={loadingTransactions ? 'animate-spin' : ''} style={loadingTransactions ? { animation: 'spin 1s linear infinite' } : {}} />
            Refresh
          </button>
        </div>

        {allTransactions.length === 0 ? (
          <div className="empty-state">
            <span>No transactions have been made in the system.</span>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Ref Number</th>
                  <th>Sender ID</th>
                  <th>Recipient ID</th>
                  <th>Send (USD)</th>
                  <th>Payout</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Modify Status</th>
                </tr>
              </thead>
              <tbody>
                {allTransactions.map((t) => {
                  const isRiskRow = t.status === 'FAILED' || t.status === 'SUSPICIOUS';
                  return (
                    <React.Fragment key={t.id}>
                      <tr 
                        style={{ cursor: isRiskRow ? 'pointer' : 'default' }}
                        onClick={() => isRiskRow && toggleTxnExpand(t.id)}
                        className={isRiskRow ? 'row-clickable' : ''}
                      >
                        <td>{t.id}</td>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{t.reference_number}</td>
                        <td>User #{t.sender_id}</td>
                        <td>Recip #{t.recipient_id}</td>
                        <td>${t.source_amount.toFixed(2)} (+${t.fee.toFixed(2)})</td>
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
                          {t.status === 'FUNDED' && (
                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'PROCESSING')}
                                disabled={updatingTxnId === t.id}
                              >
                                Set Processing
                              </button>
                              <button
                                className="btn btn-success btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'COMPLETED')}
                                disabled={updatingTxnId === t.id}
                              >
                                Set Completed
                              </button>
                            </div>
                          )}
                          
                          {t.status === 'PROCESSING' && (
                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                              <button
                                className="btn btn-success btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'COMPLETED')}
                                disabled={updatingTxnId === t.id}
                              >
                                Set Completed
                              </button>
                              <button
                                className="btn btn-danger btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'FAILED')}
                                disabled={updatingTxnId === t.id}
                              >
                                Set Failed
                              </button>
                            </div>
                          )}

                          {t.status === 'SUSPICIOUS' && (
                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                              <button
                                className="btn btn-success btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'PROCESSING')}
                                disabled={updatingTxnId === t.id}
                              >
                                Approve/Process
                              </button>
                              <button
                                className="btn btn-danger btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => handleUpdateStatus(t.id, 'FAILED')}
                                disabled={updatingTxnId === t.id}
                              >
                                Reject/Fail
                              </button>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => toggleTxnExpand(t.id)}
                              >
                                {expandedTxnIds[t.id] ? 'Hide' : 'Audit'}
                              </button>
                            </div>
                          )}

                          {t.status === 'FAILED' && (
                            <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.8rem', color: 'var(--danger)', fontWeight: 500 }}>
                                Blocked
                              </span>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                                onClick={() => toggleTxnExpand(t.id)}
                              >
                                {expandedTxnIds[t.id] ? 'Hide' : 'Audit'}
                              </button>
                            </div>
                          )}

                          {t.status === 'PENDING' && (
                            <span style={{ fontSize: '0.8rem', color: 'var(--warning)', fontWeight: 500 }}>
                              Awaiting User Payment
                            </span>
                          )}

                          {t.status === 'COMPLETED' && (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              Finalized
                            </span>
                          )}
                        </td>
                      </tr>
                      {expandedTxnIds[t.id] && isRiskRow && (
                        <tr>
                          <td colSpan="9" style={{ padding: '0 1rem 1rem 1rem', borderTop: 'none', background: 'rgba(255,255,255,0.01)' }}>
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
      )}
    </div>
  );
}
