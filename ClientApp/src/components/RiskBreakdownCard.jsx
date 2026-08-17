import React, { useState } from 'react';
import { 
  AlertTriangle, ShieldAlert, ChevronDown, ChevronUp, 
  Zap, Activity, FileText, CheckCircle2, ShieldQuestion
} from 'lucide-react';

export default function RiskBreakdownCard({ transaction }) {
  const [expanded, setExpanded] = useState(false);
  const {
    status,
    anomaly_score,
    velocity_flags,
    fraud_explanation,
    fraud_evidence
  } = transaction;

  // Safe parsing of JSON array strings or comma-separated lists
  const parseJsonOrArray = (input) => {
    if (!input) return [];
    if (Array.isArray(input)) return input;
    try {
      const parsed = JSON.parse(input);
      if (Array.isArray(parsed)) return parsed;
      return [parsed];
    } catch (e) {
      if (typeof input === 'string') {
        return input.split(',').map(item => item.trim()).filter(Boolean);
      }
      return [input];
    }
  };

  const parsedFlags = parseJsonOrArray(velocity_flags).filter(f => f !== 'NONE' && f !== 'none');
  const parsedEvidence = parseJsonOrArray(fraud_evidence);

  const score = anomaly_score !== undefined && anomaly_score !== null ? Number(anomaly_score) : 0;
  
  // Decide badge/card theme color based on score or status
  const isFailed = status === 'FAILED' || score >= 75;
  const isSuspicious = status === 'SUSPICIOUS' || (score >= 50 && score < 75);
  
  const themeColor = isFailed ? 'var(--danger)' : isSuspicious ? 'var(--warning)' : 'var(--success)';
  const themeBg = isFailed ? 'var(--danger-bg)' : isSuspicious ? 'var(--warning-bg)' : 'var(--success-bg)';
  const themeBorder = isFailed ? 'var(--danger-border)' : isSuspicious ? 'var(--warning-border)' : 'var(--success-border)';

  return (
    <div className="risk-card glass" style={{
      border: `1px solid ${themeBorder}`,
      boxShadow: `0 8px 30px ${isFailed ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.05)'}`,
      margin: '1rem 0',
      padding: '1.25rem',
      borderRadius: '14px',
      background: `linear-gradient(135deg, rgba(13, 13, 23, 0.8) 0%, ${themeBg} 100%)`
    }}>
      {/* Header Info */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {isFailed ? (
            <ShieldAlert size={20} style={{ color: 'var(--danger)' }} />
          ) : (
            <AlertTriangle size={20} style={{ color: 'var(--warning)' }} />
          )}
          <span style={{ fontWeight: 600, letterSpacing: '0.02em', fontSize: '0.95rem' }}>
            AI Risk Assessment: <span style={{ color: themeColor }}>{status}</span>
          </span>
        </div>
        <span style={{
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem'
        }}>
          <Zap size={12} /> Powered by Snowflake Cortex AI
        </span>
      </div>

      {/* Main Grid: Score Gauge and Velocity Flags */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(200px, 1fr) 2fr',
        gap: '1.5rem',
        marginBottom: '1.25rem',
        alignItems: 'start'
      }} className="risk-card-grid">
        
        {/* Score gauge container */}
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '1rem',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%'
        }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 500 }}>
            Risk Anomaly Score
          </span>
          <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* Numeric display in middle */}
            <span style={{
              fontSize: '2rem',
              fontWeight: 700,
              color: themeColor,
              textShadow: `0 0 10px ${themeColor}40`
            }}>{score.toFixed(0)}<span style={{ fontSize: '1rem', opacity: 0.7 }}>/100</span></span>
          </div>

          {/* Progress bar gauge */}
          <div style={{
            width: '100%',
            height: '8px',
            backgroundColor: 'rgba(255,255,255,0.05)',
            borderRadius: '9999px',
            marginTop: '0.75rem',
            overflow: 'hidden',
            position: 'relative'
          }}>
            <div style={{
              width: `${score}%`,
              height: '100%',
              background: `linear-gradient(90deg, var(--success) 0%, var(--warning) 60%, var(--danger) 100%)`,
              borderRadius: '9999px',
              transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)'
            }} />
          </div>
          
          <span style={{
            fontSize: '0.75rem',
            marginTop: '0.5rem',
            fontWeight: 600,
            color: themeColor,
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            {score >= 75 ? 'HIGH RISK' : score >= 50 ? 'MEDIUM RISK' : 'LOW RISK'}
          </span>
        </div>

        {/* Velocity Flags & Detection Evidence */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          
          {/* Velocity risk tags */}
          <div>
            <div style={{
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
              marginBottom: '0.4rem',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <Activity size={14} /> Triggered Risk Flags
            </div>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {parsedFlags.length === 0 ? (
                <span style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                  padding: '0.2rem 0.5rem',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: '6px'
                }}>
                  No abnormal velocity flags triggered.
                </span>
              ) : (
                parsedFlags.map((flag, idx) => (
                  <span key={idx} style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '0.2rem 0.6rem',
                    borderRadius: '6px',
                    backgroundColor: themeBg,
                    border: `1px solid ${themeBorder}`,
                    color: themeColor,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem'
                  }}>
                    <Zap size={10} /> {flag.replace(/_/g, ' ')}
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Evidence bullet points */}
          <div>
            <div style={{
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
              marginBottom: '0.4rem',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <FileText size={14} /> Detection Evidence & Insights
            </div>
            
            <ul style={{
              margin: 0,
              paddingLeft: '1.25rem',
              fontSize: '0.825rem',
              color: 'var(--text-bright)',
              lineHeight: '1.4'
            }}>
              {parsedEvidence.length === 0 ? (
                <li style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No specific anomaly evidence flagged.
                </li>
              ) : (
                parsedEvidence.map((ev, idx) => (
                  <li key={idx} style={{ marginBottom: '0.25rem' }}>
                    {ev}
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

      </div>

      {/* Accordion / Collapsible AI Reasoning Section */}
      {fraud_explanation && (
        <div style={{
          borderTop: '1px solid var(--border-color)',
          paddingTop: '0.75rem',
          marginTop: '0.75rem'
        }}>
          <button 
            type="button" 
            onClick={() => setExpanded(!expanded)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '0.8rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              cursor: 'pointer',
              padding: 0,
              outline: 'none',
              width: '100%',
              justifyContent: 'space-between'
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <ShieldQuestion size={14} style={{ color: themeColor }} /> Detailed AI Reasoning Breakdown
            </span>
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {expanded && (
            <div style={{
              marginTop: '0.5rem',
              fontSize: '0.8rem',
              lineHeight: '1.5',
              color: 'var(--text-bright)',
              backgroundColor: 'rgba(0,0,0,0.2)',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              borderLeft: `3px solid ${themeColor}`,
              whiteSpace: 'pre-wrap'
            }}>
              {fraud_explanation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
