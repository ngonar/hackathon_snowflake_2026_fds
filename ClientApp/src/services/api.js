const API_BASE = '/api';

let token = localStorage.getItem('remit_token') || null;

export const setToken = (newToken) => {
  token = newToken;
  if (newToken) {
    localStorage.setItem('remit_token', newToken);
  } else {
    localStorage.removeItem('remit_token');
  }
};

export const getToken = () => token;

export const logout = () => {
  setToken(null);
};

async function request(path, options = {}) {
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !(options.body instanceof URLSearchParams) && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch (e) {
      // ignore
    }

    let message = `Request failed with status ${response.status}`;
    if (errorData) {
      if (typeof errorData.detail === 'string') {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join(', ');
      } else if (errorData.message) {
        message = errorData.message;
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  // Auth
  register: (email, fullName, password) => {
    return request('/auth/register', {
      method: 'POST',
      body: { email, full_name: fullName, password }
    });
  },

  login: async (email, password) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const data = await request('/auth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    });

    if (data && data.access_token) {
      setToken(data.access_token);
    }
    return data;
  },

  // Users
  getMe: () => request('/users/me'),

  submitKyc: (documentType, documentNumber) => {
    return request('/users/me/kyc', {
      method: 'POST',
      body: { kyc_document_type: documentType, kyc_document_number: documentNumber }
    });
  },

  deposit: (amount) => {
    return request('/users/me/deposit', {
      method: 'POST',
      body: { amount: parseFloat(amount) }
    });
  },

  // Exchange Rates
  getRates: () => request('/rates'),

  estimateTransfer: (sourceCurrency, targetCurrency, sourceAmount) => {
    const params = new URLSearchParams({
      source_currency: sourceCurrency,
      target_currency: targetCurrency,
      source_amount: sourceAmount.toString()
    });
    return request(`/rates/estimate?${params.toString()}`);
  },

  // Recipients
  listRecipients: () => request('/recipients'),

  createRecipient: (recipientData) => {
    return request('/recipients', {
      method: 'POST',
      body: {
        name: recipientData.name,
        bank_name: recipientData.bankName,
        account_number: recipientData.accountNumber,
        routing_number: recipientData.routingNumber || null,
        country: recipientData.country,
        currency: recipientData.currency
      }
    });
  },

  // Transactions
  listTransactions: () => request('/transactions'),

  createTransaction: (recipientId, sourceAmount) => {
    return request('/transactions', {
      method: 'POST',
      body: {
        recipient_id: parseInt(recipientId),
        source_amount: parseFloat(sourceAmount)
      }
    });
  },

  bulkTransfer: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/transactions/bulk', {
      method: 'POST',
      body: formData
    });
  },

  fundTransaction: (txnId) => {
    return request(`/transactions/${txnId}/fund`, {
      method: 'POST'
    });
  },

  getTransaction: (txnId) => request(`/transactions/${txnId}`),

  // Admin
  getPendingKyc: () => request('/admin/kyc'),

  approveKyc: (userId, approve) => {
    return request(`/admin/kyc/${userId}/approve?approve=${approve}`, {
      method: 'POST'
    });
  },

  listAllTransactions: () => request('/admin/transactions'),

  updateTransactionStatus: (txnId, statusValue) => {
    return request(`/admin/transactions/${txnId}/status?status_value=${statusValue}`, {
      method: 'POST'
    });
  },

  createOrUpdateRate: (sourceCurrency, targetCurrency, rate, feePercentage) => {
    return request('/admin/rates', {
      method: 'POST',
      body: {
        source_currency: sourceCurrency,
        target_currency: targetCurrency,
        rate: parseFloat(rate),
        fee_percentage: parseFloat(feePercentage)
      }
    });
  },

  investigateQuery: (query) => {
    return request('/admin/investigate', {
      method: 'POST',
      body: { query }
    });
  }
};
