import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import { 
  Search, Send, Database, AlertTriangle, CheckCircle2, 
  ChevronDown, ChevronUp, Loader, BrainCircuit, Sparkles
} from 'lucide-react';

const SUGGESTION_CHIPS = [
  "Show all transactions from the last 24 hours with anomaly score above 80",
  "List all currently frozen wallets and their reasons",
  "Which senders have been flagged for fraud more than once?",
  "Show KYC re-verification queue ordered by priority",
  "Top 5 highest anomaly score transactions this week",
  "Show all remediation actions taken in the last 7 days"
];

export default function FraudInvestigator({ showToast }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (query) => {
    const q = query || inputValue.trim();
    if (!q || loading) return;

    setInputValue('');
    setMessages(prev => [...prev, { type: 'user', content: q }]);
    setLoading(true);

    try {
      const result = await api.investigateQuery(q);
      setMessages(prev => [...prev, { type: 'assistant', ...result }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        type: 'assistant', 
        success: false, 
        error: err.message || 'Failed to execute query',
        results: [],
        sql: null
      }]);
      showToast(err.message || 'Investigation query failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div style={{ 
      display: 'flex', flexDirection: 'column', height: '600px',
      border: '1px solid var(--border-color)', borderRadius: '12px',
      overflow: 'hidden', background: 'rgba(10, 10, 18, 0.6)'
    }}>
      {/* Header */}
      <div style={{ 
        padding: '1rem 1.5rem', borderBottom: '1px solid var(--border-color)',
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        background: 'rgba(15, 15, 25, 0.8)'
      }}>
        <BrainCircuit size={22} style={{ color: 'var(--primary)' }} />
        <div>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>AI Fraud Investigator</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Powered by Snowflake Cortex &middot; Natural language queries over FDS data
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div style={{ 
        flex: 1, overflowY: 'auto', padding: '1rem 1.5rem',
        display: 'flex', flexDirection: 'column', gap: '1rem'
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <Sparkles size={36} style={{ color: 'var(--primary)', opacity: 0.6, marginBottom: '1rem' }} />
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              Ask questions in plain English about transactions, fraud patterns, and remediation actions.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center' }}>
              {SUGGESTION_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  onClick={() => handleSubmit(chip)}
                  style={{
                    padding: '0.4rem 0.75rem', fontSize: '0.75rem',
                    background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)',
                    borderRadius: '20px', color: 'var(--primary)', cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.target.style.background = 'rgba(99, 102, 241, 0.2)'}
                  onMouseLeave={(e) => e.target.style.background = 'rgba(99, 102, 241, 0.1)'}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
            <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
            <span style={{ fontSize: '0.85rem' }}>Analyzing with Cortex AI...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ 
        padding: '1rem 1.5rem', borderTop: '1px solid var(--border-color)',
        background: 'rgba(15, 15, 25, 0.8)'
      }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about fraud patterns, transactions, risk levels..."
            disabled={loading}
            style={{
              flex: 1, padding: '0.75rem 1rem', fontSize: '0.9rem',
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)',
              borderRadius: '8px', color: 'var(--text-color)', outline: 'none'
            }}
          />
          <button
            onClick={() => handleSubmit()}
            disabled={!inputValue.trim() || loading}
            style={{
              padding: '0.75rem', background: 'var(--primary)', border: 'none',
              borderRadius: '8px', cursor: inputValue.trim() && !loading ? 'pointer' : 'not-allowed',
              opacity: inputValue.trim() && !loading ? 1 : 0.5, display: 'flex',
              alignItems: 'center', justifyContent: 'center'
            }}
          >
            <Send size={18} style={{ color: '#fff' }} />
          </button>
        </div>
      </div>
    </div>
  );
}


function MessageBubble({ message }) {
  const [showSql, setShowSql] = useState(false);

  if (message.type === 'user') {
    return (
      <div style={{ 
        alignSelf: 'flex-end', maxWidth: '80%', padding: '0.75rem 1rem',
        background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '12px 12px 4px 12px', fontSize: '0.9rem'
      }}>
        {message.content}
      </div>
    );
  }

  // Assistant response
  const { success, error, sql, results, columns, row_count } = message;

  return (
    <div style={{ 
      alignSelf: 'flex-start', maxWidth: '95%', width: '100%',
      padding: '1rem', background: 'rgba(255,255,255,0.03)',
      border: '1px solid var(--border-color)', borderRadius: '4px 12px 12px 12px'
    }}>
      {!success ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger)' }}>
          <AlertTriangle size={16} />
          <span style={{ fontSize: '0.85rem' }}>{error}</span>
        </div>
      ) : (
        <>
          {/* Result summary */}
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem',
            color: 'var(--success)'
          }}>
            <CheckCircle2 size={16} />
            <span style={{ fontSize: '0.85rem' }}>
              {row_count} result{row_count !== 1 ? 's' : ''} found
            </span>
          </div>

          {/* SQL toggle */}
          {sql && (
            <div style={{ marginBottom: '0.75rem' }}>
              <button
                onClick={() => setShowSql(!showSql)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  background: 'none', border: 'none', color: 'var(--text-muted)',
                  cursor: 'pointer', fontSize: '0.75rem', padding: 0
                }}
              >
                <Database size={12} />
                {showSql ? 'Hide' : 'Show'} Generated SQL
                {showSql ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {showSql && (
                <pre style={{
                  marginTop: '0.5rem', padding: '0.75rem', fontSize: '0.75rem',
                  background: 'rgba(0,0,0,0.3)', borderRadius: '6px',
                  overflow: 'auto', maxHeight: '150px', whiteSpace: 'pre-wrap',
                  color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.2)'
                }}>
                  {sql}
                </pre>
              )}
            </div>
          )}

          {/* Results table */}
          {results && results.length > 0 && (
            <div style={{ overflow: 'auto', maxHeight: '300px' }}>
              <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {columns.map((col, i) => (
                      <th key={i} style={{
                        padding: '0.5rem', textAlign: 'left',
                        borderBottom: '1px solid var(--border-color)',
                        color: 'var(--text-muted)', fontWeight: 600,
                        whiteSpace: 'nowrap', position: 'sticky', top: 0,
                        background: 'rgba(10, 10, 18, 0.95)'
                      }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map((row, ri) => (
                    <tr key={ri}>
                      {columns.map((col, ci) => {
                        const val = row[col];
                        const isHighRisk = col === 'ANOMALY_SCORE' && parseFloat(val) >= 80;
                        const isFraud = col === 'IS_FRAUD' && val === true;
                        const isCritical = col === 'RISK_TIER' && val === 'CRITICAL';
                        const highlight = isHighRisk || isFraud || isCritical;
                        return (
                          <td key={ci} style={{
                            padding: '0.4rem 0.5rem',
                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                            color: highlight ? 'var(--danger)' : 'var(--text-color)',
                            fontWeight: highlight ? 600 : 400,
                            maxWidth: '200px', overflow: 'hidden',
                            textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                          }}
                          title={typeof val === 'string' ? val : JSON.stringify(val)}
                          >
                            {val === null ? '—' : typeof val === 'object' ? JSON.stringify(val) : String(val)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {results && results.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0.5rem 0 0' }}>
              No matching records found.
            </p>
          )}
        </>
      )}
    </div>
  );
}
