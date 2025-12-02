import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, TrendingUp, Clock, Users, Package, Settings, LogOut, Award } from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws'; // WebSocket endpoint (for future implementation)

const BiddingSystemUI = () => {
  const [view, setView] = useState('login');
  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [bidAmount, setBidAmount] = useState('');
  const [message, setMessage] = useState('');
  const wsRef = useRef(null);

  useEffect(() => {
    if (user && selectedProduct) {
      // Load leaderboard when product is selected
      loadLeaderboard(selectedProduct.session_id);

      // Set up polling for leaderboard updates (every 3 seconds)
      const intervalId = setInterval(() => {
        loadLeaderboard(selectedProduct.session_id);
      }, 3000);

      return () => {
        clearInterval(intervalId);
      };
    }
  }, [user, selectedProduct]);

  const handleAuth = async (isLogin, username, password, email, isAdmin = false) => {
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { username, password }
        : { username, email: email || `${username}@example.com`, password };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (response.ok) {
        setUser({
          id: data.user_id,
          username: data.username,
          token: data.token,
          weight: data.weight || 1.0,
          is_admin: data.is_admin || false
        });
        setView(data.is_admin ? 'admin' : 'user');
        setMessage('Login successful!');
        loadProducts(data.token);
      } else {
        // Handle validation errors (422) which return array of errors
        if (Array.isArray(data.detail)) {
          const errorMessages = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
          setMessage(errorMessages);
        } else if (typeof data.detail === 'string') {
          setMessage(data.detail);
        } else {
          setMessage('Authentication failed');
        }
      }
    } catch (error) {
      setMessage('Connection error. Make sure backend is running at localhost:8000');
    }
  };

  const loadProducts = async (token) => {
    try {
      const response = await fetch(`${API_BASE}/sessions/active`);
      const data = await response.json();
      // Backend returns array directly, map to expected format
      const sessions = Array.isArray(data) ? data : [];
      setProducts(sessions.map(session => ({
        id: session.session_id,
        session_id: session.session_id,
        product_id: session.product_id,
        name: session.name,
        description: session.description,
        inventory: session.inventory,
        base_price: session.base_price,
        alpha: session.alpha,
        beta: session.beta,
        gamma: session.gamma,
        start_time: session.start_time,
        end_time: session.end_time,
        status: session.status
      })));
    } catch (error) {
      console.error('Failed to load products:', error);
      setMessage('Failed to load active sessions');
    }
  };

  const loadLeaderboard = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/leaderboard/${sessionId}`);
      const data = await response.json();
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  const handleBid = async () => {
    if (!bidAmount || !selectedProduct) return;

    try {
      const response = await fetch(`${API_BASE}/bid`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({
          session_id: selectedProduct.session_id,
          price: parseFloat(bidAmount)
        })
      });

      const data = await response.json();
      if (response.ok) {
        setMessage(`Bid submitted! Your score: ${data.score?.toFixed(2)}, Rank: ${data.rank}`);
        setBidAmount('');
        // Refresh leaderboard after bid
        loadLeaderboard(selectedProduct.session_id);
      } else {
        // Handle validation errors
        if (Array.isArray(data.detail)) {
          const errorMessages = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
          setMessage(errorMessages);
        } else if (typeof data.detail === 'string') {
          setMessage(data.detail);
        } else {
          setMessage('Bid failed');
        }
      }
    } catch (error) {
      setMessage('Failed to submit bid');
    }
  };

  const handleCreateProduct = async (formData) => {
    try {
      // Use combined endpoint to create product and session
      const response = await fetch(`${API_BASE}/admin/sessions/combined`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || '',
          upset_price: formData.base_price,
          inventory: formData.inventory,
          alpha: formData.alpha,
          beta: formData.beta,
          gamma: formData.gamma,
          duration_minutes: formData.duration_minutes || 60
        })
      });

      const data = await response.json();
      if (response.ok) {
        setMessage('Product and session created successfully!');
        loadProducts(user.token);
      } else {
        // Handle validation errors
        if (Array.isArray(data.detail)) {
          const errorMessages = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
          setMessage(errorMessages);
        } else if (typeof data.detail === 'string') {
          setMessage(data.detail);
        } else {
          setMessage('Failed to create product');
        }
      }
    } catch (error) {
      setMessage('Failed to create product');
    }
  };

  const logout = () => {
    setUser(null);
    setView('login');
    setSelectedProduct(null);
    setLeaderboard([]);
    if (wsRef.current) wsRef.current.close();
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-logo">
            <TrendingUp size={32} />
            <h1>Flash Bidding System</h1>
          </div>
          {user && (
            <div className="header-user">
              <span className="user-info">
                {user.username} {user.is_admin && '(Admin)'} | Weight: {user.weight}
              </span>
              <button onClick={logout} className="btn btn-logout">
                <LogOut size={16} />
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {message && (
        <div className="message-banner">
          <AlertCircle size={20} />
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="message-close">✕</button>
        </div>
      )}

      <div className="main-content">
        {view === 'login' && <LoginView onAuth={handleAuth} />}
        {view === 'user' && (
          <UserView
            products={products}
            selectedProduct={selectedProduct}
            setSelectedProduct={setSelectedProduct}
            leaderboard={leaderboard}
            bidAmount={bidAmount}
            setBidAmount={setBidAmount}
            onBid={handleBid}
            userWeight={user.weight}
          />
        )}
        {view === 'admin' && (
          <AdminView
            products={products}
            onCreate={handleCreateProduct}
            onRefresh={() => loadProducts(user.token)}
          />
        )}
      </div>
    </div>
  );
};

const LoginView = ({ onAuth }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();

    // Validation
    if (!username || !password) {
      alert('Please enter username and password');
      return;
    }

    if (!isLogin && !email) {
      alert('Please enter email for registration');
      return;
    }

    console.log('Submitting auth:', { isLogin, username, email, isAdmin });
    onAuth(isLogin, username, password, email, isAdmin);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>{isLogin ? 'Login' : 'Register'}</h2>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            className="input"
          />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            className="input"
          />
        </div>
        {!isLogin && (
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
              className="input"
              placeholder="your@email.com"
            />
          </div>
        )}
        <div className="checkbox-group">
          <input
            type="checkbox"
            id="admin"
            checked={isAdmin}
            onChange={(e) => setIsAdmin(e.target.checked)}
          />
          <label htmlFor="admin">Login as Admin</label>
        </div>
        <button onClick={handleSubmit} className="btn btn-primary btn-full">
          {isLogin ? 'Login' : 'Register'}
        </button>
        <button onClick={() => setIsLogin(!isLogin)} className="btn-link">
          {isLogin ? 'Need an account? Register' : 'Already have an account? Login'}
        </button>
      </div>
    </div>
  );
};

const UserView = ({ products, selectedProduct, setSelectedProduct, leaderboard, bidAmount, setBidAmount, onBid, userWeight }) => {
  return (
    <div className="user-view">
      <div className="sidebar">
        <div className="card">
          <h3 className="card-title">
            <Package size={24} />
            Available Products
          </h3>
          <div className="product-list">
            {products.map((product) => (
              <button
                key={product.id}
                onClick={() => setSelectedProduct(product)}
                className={`product-item ${selectedProduct?.id === product.id ? 'active' : ''}`}
              >
                <div className="product-name">{product.name}</div>
                <div className="product-detail">Stock: {product.inventory}</div>
                <div className="product-detail">Base Price: ${product.base_price}</div>
              </button>
            ))}
            {products.length === 0 && (
              <p className="empty-state">No products available</p>
            )}
          </div>
        </div>
      </div>

      <div className="main-area">
        {selectedProduct ? (
          <>
            <div className="card">
              <h3>{selectedProduct.name}</h3>
              <div className="stats-grid">
                <div className="stat-box">
                  <div className="stat-label">Base Price</div>
                  <div className="stat-value">${selectedProduct.base_price}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Available Stock</div>
                  <div className="stat-value">{selectedProduct.inventory}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Your Weight (W)</div>
                  <div className="stat-value">{userWeight.toFixed(2)}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Parameters</div>
                  <div className="stat-params">
                    α={selectedProduct.alpha} β={selectedProduct.beta} γ={selectedProduct.gamma}
                  </div>
                </div>
              </div>
              
              <div className="bid-form">
                <label>Your Bid Amount ($)</label>
                <input
                  type="number"
                  value={bidAmount}
                  onChange={(e) => setBidAmount(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && onBid()}
                  min={selectedProduct.base_price}
                  step="0.01"
                  placeholder={`Min: $${selectedProduct.base_price}`}
                  className="input input-large"
                />
                <button onClick={onBid} className="btn btn-primary btn-full btn-large">
                  Submit Bid
                </button>
              </div>
            </div>

            <div className="card">
              <h3 className="card-title">
                <Award size={24} color="#ffc107" />
                Live Leaderboard (Top {selectedProduct.inventory})
              </h3>
              {leaderboard.length > 0 ? (
                <div className="leaderboard">
                  {leaderboard.map((entry, index) => (
                    <div
                      key={entry.user_id}
                      className={`leaderboard-item ${entry.is_winner ? 'winner' : ''}`}
                    >
                      <div className="leaderboard-left">
                        <div className={`rank-badge rank-${entry.rank}`}>
                          {entry.rank}
                        </div>
                        <div className="user-details">
                          <div className="username">{entry.username}</div>
                          <div className="score">Score: {entry.score?.toFixed(2)} | Price: ${entry.price}</div>
                        </div>
                      </div>
                      {entry.is_winner && (
                        <span className="winner-badge">Winner 🎉</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">No bids yet. Be the first!</p>
              )}
            </div>
          </>
        ) : (
          <div className="card empty-selection">
            <Package size={64} color="#ccc" />
            <p>Select a product to start bidding</p>
          </div>
        )}
      </div>
    </div>
  );
};

const AdminView = ({ products, onCreate, onRefresh }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    inventory: 5,
    base_price: 100,
    alpha: 0.5,
    beta: 1000,
    gamma: 2.0,
    duration_minutes: 60
  });

  const handleSubmit = () => {
    onCreate(formData);
    setFormData({
      name: '',
      description: '',
      inventory: 5,
      base_price: 100,
      alpha: 0.5,
      beta: 1000,
      gamma: 2.0,
      duration_minutes: 60
    });
  };

  return (
    <div className="admin-view">
      <div className="admin-left">
        <div className="card">
          <h3 className="card-title">
            <Settings size={24} />
            Create New Product
          </h3>
          <div className="form-group">
            <label>Product Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="input"
              placeholder="e.g., iPhone 15 Pro"
            />
          </div>
          <div className="form-group">
            <label>Description (Optional)</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="input"
              placeholder="Product description"
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Inventory (K)</label>
              <input
                type="number"
                value={formData.inventory}
                onChange={(e) => setFormData({...formData, inventory: parseInt(e.target.value)})}
                className="input"
                min="1"
              />
            </div>
            <div className="form-group">
              <label>Base Price ($)</label>
              <input
                type="number"
                value={formData.base_price}
                onChange={(e) => setFormData({...formData, base_price: parseFloat(e.target.value)})}
                className="input"
                min="0"
                step="0.01"
              />
            </div>
            <div className="form-group">
              <label>Duration (minutes)</label>
              <input
                type="number"
                value={formData.duration_minutes}
                onChange={(e) => setFormData({...formData, duration_minutes: parseInt(e.target.value)})}
                className="input"
                min="1"
              />
            </div>
          </div>
          <div className="formula-section">
            <h4>Formula Parameters</h4>
            <div className="formula-display">
              Score = α × Price + β / (Time + 1) + γ × Weight
            </div>
            <div className="form-row form-row-3">
              <div className="form-group">
                <label>Alpha (α)</label>
                <input
                  type="number"
                  value={formData.alpha}
                  onChange={(e) => setFormData({...formData, alpha: parseFloat(e.target.value)})}
                  className="input"
                  step="0.1"
                />
              </div>
              <div className="form-group">
                <label>Beta (β)</label>
                <input
                  type="number"
                  value={formData.beta}
                  onChange={(e) => setFormData({...formData, beta: parseFloat(e.target.value)})}
                  className="input"
                  step="1"
                />
              </div>
              <div className="form-group">
                <label>Gamma (γ)</label>
                <input
                  type="number"
                  value={formData.gamma}
                  onChange={(e) => setFormData({...formData, gamma: parseFloat(e.target.value)})}
                  className="input"
                  step="0.1"
                />
              </div>
            </div>
          </div>
          <button onClick={handleSubmit} className="btn btn-primary btn-full btn-large">
            Create Product
          </button>
        </div>
      </div>

      <div className="admin-right">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Package size={24} />
              Existing Products
            </h3>
            <button onClick={onRefresh} className="btn btn-secondary">
              Refresh
            </button>
          </div>
          <div className="product-grid">
            {products.map((product) => (
              <div key={product.id} className="product-card">
                <div className="product-card-title">{product.name}</div>
                <div className="product-card-grid">
                  <div>Stock: <strong>{product.inventory}</strong></div>
                  <div>Base: <strong>${product.base_price}</strong></div>
                  <div>α: <strong>{product.alpha}</strong></div>
                  <div>β: <strong>{product.beta}</strong></div>
                  <div>γ: <strong>{product.gamma}</strong></div>
                  <div>ID: <strong>{product.id}</strong></div>
                </div>
              </div>
            ))}
            {products.length === 0 && (
              <p className="empty-state">No products created yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BiddingSystemUI;