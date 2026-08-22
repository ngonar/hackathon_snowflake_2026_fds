import React, { useState } from 'react';
import { api } from '../services/api';
import { Settings, DollarSign, Check } from 'lucide-react';

const CURRENCIES = [
  { code: 'USD', label: 'USD (US Dollar)' },
  { code: 'EUR', label: 'EUR (Euro)' },
  { code: 'GBP', label: 'GBP (British Pound)' },
  { code: 'KES', label: 'KES (Kenyan Shilling)' },
  { code: 'INR', label: 'INR (Indian Rupee)' },
  { code: 'PHP', label: 'PHP (Philippine Peso)' },
  { code: 'MXN', label: 'MXN (Mexican Peso)' },
];

export default function SettingsPage({ user, onRefreshUser, showToast }) {
  const [baseCurrency, setBaseCurrency] = useState(user.base_currency || 'USD');
  const [saving, setSaving] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.updateBaseCurrency(baseCurrency);
      showToast(`Base currency updated to ${baseCurrency}`, 'success');
      onRefreshUser();
    } catch (err) {
      showToast(err.message || 'Failed to update settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const hasChanged = baseCurrency !== (user.base_currency || 'USD');

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem 1rem' }}>
      <div className="glass card">
        <div className="card-header">
          <div className="card-title-icon">
            <Settings className="text-primary" style={{ color: 'var(--primary)' }} />
            <h3>Configuration</h3>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', fontWeight: 600 }}>
              <DollarSign size={16} />
              Base Currency
            </label>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              This is the currency your wallet holds and the source currency used for all outgoing transfers.
            </p>
            <select
              className="input-control calc-select"
              value={baseCurrency}
              onChange={(e) => setBaseCurrency(e.target.value)}
              style={{ width: '100%' }}
            >
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>{c.label}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={saving || !hasChanged}
          >
            {saving ? 'Saving...' : (
              <>
                <Check size={16} />
                Save Settings
              </>
            )}
          </button>

          {!hasChanged && (
            <p style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
              No changes to save.
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
