import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, TrendingUp, Clock, Users, Package, Settings, LogOut, Award, List, Plus, X } from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws'; // WebSocket endpoint (for future implementation)

const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">{title}</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

const BiddingSystemUI = () => {
  const [view, setView] = useState('login');
  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [adminProducts, setAdminProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [highestBid, setHighestBid] = useState(null);
  const [thresholdScore, setThresholdScore] = useState(null);
  const [leaderboardPage, setLeaderboardPage] = useState(1);
  const [leaderboardTotalPages, setLeaderboardTotalPages] = useState(0);
  const [leaderboardTotalCount, setLeaderboardTotalCount] = useState(0);
  const [bidAmount, setBidAmount] = useState('');
  const [message, setMessage] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const sessionWsRef = useRef(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        setView(userData.is_admin ? 'admin' : 'user');
        loadProducts(userData.token);
        if (userData.is_admin) {
          loadAdminProducts(userData.token);
        }
      } catch (error) {
        console.error('Failed to parse stored user:', error);
        localStorage.removeItem('user');
      }
    }
  }, []);

  // WebSocket connection for session list updates
  useEffect(() => {
    let reconnectTimeout;
    let isMounted = true;

    const connectSessionWs = () => {
      if (!user || !isMounted) return;

      console.log('Connecting to session list WebSocket...');
      const sessionWs = new WebSocket('ws://localhost:8000/ws/sessions');
      sessionWsRef.current = sessionWs;

      sessionWs.onopen = () => {
        console.log('✓ Session list WebSocket connected');
        // Force a refresh of products on connection to ensure we're in sync
        loadProducts(user.token);
      };

      sessionWs.onclose = () => {
        console.log('Session list WebSocket disconnected');
        // Try to reconnect after 3 seconds
        if (isMounted) {
          reconnectTimeout = setTimeout(() => {
            console.log('Attempting to reconnect session list WebSocket...');
            connectSessionWs();
          }, 3000);
        }
      };

      sessionWs.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('📩 WebSocket message received:', message.type);
          if (message.type === 'session_list_update' && message.data) {
            console.log('✓ Session list updated, received', message.data.length, 'sessions');

            // Backend sends sessions directly in message.data (array)
            const now = new Date();
            const formattedSessions = message.data.map(session => {
              const endTime = new Date(session.end_time);
              const isEnded = now > endTime || session.status === 'ended';

              return {
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
                status: isEnded ? 'ended' : 'active',
                isEnded: isEnded
              };
            });

            setProducts(formattedSessions);
          }
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error);
        }
      };

      sessionWs.onerror = (error) => {
        console.error('❌ Session list WebSocket error:', error);
        sessionWs.close(); // Force close to trigger reconnect
      };
    };

    if (user) {
      connectSessionWs();
    }

    // Cleanup on component unmount or user logout
    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (sessionWsRef.current) {
        sessionWsRef.current.onclose = null; // Prevent reconnect on cleanup
        sessionWsRef.current.close();
        sessionWsRef.current = null;
      }
    };
  }, [user]);

  // Local timer to update session status (Active -> Ended) in real-time
  useEffect(() => {
    if (!products.length) return;

    const intervalId = setInterval(() => {
      const now = new Date();
      let hasChanges = false;

      const updatedProducts = products.map(product => {
        if (product.status === 'ended') return product; // Already ended

        const endTime = new Date(product.end_time);
        if (now > endTime) {
          hasChanges = true;
          return { ...product, status: 'ended', isEnded: true };
        }
        return product;
      });

      if (hasChanges) {
        console.log('↻ Local timer: Updating session status');
        setProducts(updatedProducts);

        // If the currently selected product just ended, update it too
        if (selectedProduct && !selectedProduct.isEnded) {
          const currentSelected = updatedProducts.find(p => p.id === selectedProduct.id);
          if (currentSelected && currentSelected.isEnded) {
            setSelectedProduct(currentSelected);
          }
        }
      }
    }, 1000);

    return () => clearInterval(intervalId);
  }, [products, selectedProduct]);

  useEffect(() => {
    if (user && selectedProduct) {
      // Load initial leaderboard
      loadLeaderboard(selectedProduct.session_id);

      // Only set up WebSocket connection for active sessions
      if (!selectedProduct.isEnded) {
        const ws = new WebSocket(`ws://localhost:8000/ws/${selectedProduct.session_id}`);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(`WebSocket connected to session ${selectedProduct.session_id}`);
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'leaderboard_update' && message.data) {
              setLeaderboard(message.data.leaderboard || []);
              setHighestBid(message.data.highest_bid);
              setThresholdScore(message.data.threshold_score);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setWsConnected(false);
          // Fallback to polling if WebSocket fails
          const intervalId = setInterval(() => {
            loadLeaderboard(selectedProduct.session_id);
          }, 3000);
          return () => clearInterval(intervalId);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setWsConnected(false);
        };

        // Cleanup on component unmount or product change
        return () => {
          if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
          }
        };
      } else {
        // For ended sessions, just show the final leaderboard without WebSocket
        setWsConnected(false);
        console.log('Session ended, showing final leaderboard without WebSocket');
      }
    }
  }, [user, selectedProduct]);

  const handleAuth = async (isLogin, username, password, email, isAdmin = false) => {
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { username, password }
        : { username, email: email || `${username}@example.com`, password, is_admin: isAdmin };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (response.ok) {
        const userData = {
          id: data.user_id,
          username: data.username,
          token: data.token,
          weight: data.weight || 1.0,
          is_admin: data.is_admin || false
        };
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));

        setView(data.is_admin ? 'admin' : 'user');
        setMessage('Login successful!');
        loadProducts(data.token);
        if (data.is_admin) {
          loadAdminProducts(data.token);
        }
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
      const response = await fetch(`${API_BASE}/sessions`);
      const data = await response.json();
      // Backend returns array directly, map to expected format
      const sessions = Array.isArray(data) ? data : [];
      const now = new Date();

      setProducts(sessions.map(session => {
        const endTime = new Date(session.end_time);
        const isEnded = now > endTime || session.status === 'ended' || !session.is_active;

        return {
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
          status: isEnded ? 'ended' : 'active',
          isEnded: isEnded
        };
      }));
    } catch (error) {
      console.error('Failed to load products:', error);
      setMessage('Failed to load active sessions');
    }
  };

  const loadAdminProducts = async (token) => {
    try {
      const response = await fetch(`${API_BASE}/admin/products`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setAdminProducts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load admin products:', error);
    }
  };

  const loadLeaderboard = async (sessionId, page = 1) => {
    try {
      const response = await fetch(`${API_BASE}/leaderboard/${sessionId}?page=${page}&page_size=50`);
      const data = await response.json();
      setLeaderboard(data.leaderboard || []);
      setHighestBid(data.highest_bid);
      setThresholdScore(data.threshold_score);
      setLeaderboardPage(data.page);
      setLeaderboardTotalPages(data.total_pages);
      setLeaderboardTotalCount(data.total_count);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  const handleLeaderboardPageChange = (newPage) => {
    if (selectedProduct) {
      loadLeaderboard(selectedProduct.session_id, newPage);
    }
  };

  const handleBid = async () => {
    if (!bidAmount || !selectedProduct) return;

    console.log('📤 Submitting bid:', { session_id: selectedProduct.session_id, price: parseFloat(bidAmount) });

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
      console.log('📥 Bid response:', { status: response.status, data });

      if (response.ok) {
        setMessage(`Bid submitted! Your score: ${data.score?.toFixed(2)}, Rank: ${data.rank}`);
        setBidAmount('');
        // WebSocket will automatically update the leaderboard
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
      console.error('❌ Bid error:', error);
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
        return true; // Return success status
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
        return false;
      }
    } catch (error) {
      setMessage('Failed to create product');
      return false;
    }
  };

  const handleCreateProductOnly = async (productData) => {
    try {
      const response = await fetch(`${API_BASE}/admin/products`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify(productData)
      });

      const data = await response.json();
      if (response.ok) {
        setMessage('Product created successfully!');
        loadAdminProducts(user.token);
        return true; // Return success status
      } else {
        if (Array.isArray(data.detail)) {
          const errorMessages = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
          setMessage(errorMessages);
        } else if (typeof data.detail === 'string') {
          setMessage(data.detail);
        } else {
          setMessage('Failed to create product');
        }
        return false;
      }
    } catch (error) {
      setMessage('Failed to create product');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('user');
    setUser(null);
    setView('login');
    setSelectedProduct(null);
    setLeaderboard([]);
    if (wsRef.current) wsRef.current.close();
    if (sessionWsRef.current) sessionWsRef.current.close();
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
            highestBid={highestBid}
            thresholdScore={thresholdScore}
            leaderboardPage={leaderboardPage}
            leaderboardTotalPages={leaderboardTotalPages}
            leaderboardTotalCount={leaderboardTotalCount}
            bidAmount={bidAmount}
            setBidAmount={setBidAmount}
            onBid={handleBid}
            onLeaderboardPageChange={handleLeaderboardPageChange}
            userWeight={user.weight}
            wsConnected={wsConnected}
            sessionWsRef={sessionWsRef}
          />
        )}
        {view === 'admin' && (
          <AdminView
            products={products}
            adminProducts={adminProducts}
            onCreate={handleCreateProduct}
            onCreateProductOnly={handleCreateProductOnly}
            onRefresh={() => loadProducts(user.token)}
            onRefreshProducts={() => loadAdminProducts(user.token)}
            user={user}
            loadProducts={loadProducts}
            setMessage={setMessage}
            leaderboard={leaderboard}
            loadLeaderboard={loadLeaderboard}
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
          <>
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
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="admin"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
              />
              <label htmlFor="admin">Register as Admin</label>
            </div>
          </>
        )}
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

const SessionCard = ({ session, isSelected, onClick, variant = 'compact', isAdmin = false }) => {
  const isEnded = session.status === 'ended' || session.isEnded;
  const statusColor = isEnded ? '#f44336' : '#4caf50';
  const statusText = isEnded ? '🔴 Closed' : '🟢 Open';

  if (variant === 'compact') {
    return (
      <button
        onClick={onClick}
        className={`product-item ${isSelected ? 'active' : ''}`}
        style={isEnded ? { opacity: 0.7 } : {}}
      >
        <div className="product-name">{session.name}</div>
        <div className="product-detail">Stock: {session.inventory}</div>
        <div className="product-detail">Base Price: ${session.base_price}</div>
        <div className="product-status" style={{ color: statusColor, fontSize: '12px', marginTop: '4px' }}>
          {statusText}
        </div>
      </button>
    );
  }

  // Full variant (Grid)
  return (
    <div className="product-card" style={isEnded ? { borderLeft: '4px solid #f44336', opacity: 0.8 } : { borderLeft: '4px solid #4caf50' }}>
      <div className="product-card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>{session.name}</span>
        <span style={{ fontSize: '12px', color: statusColor, padding: '2px 6px', border: `1px solid ${statusColor}`, borderRadius: '4px' }}>
          {statusText.toUpperCase()}
        </span>
      </div>
      <p style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>{session.description}</p>
      <div className="product-card-grid">
        <div>Stock: <strong>{session.inventory}</strong></div>
        <div>Base: <strong>${session.base_price}</strong></div>
        {isAdmin && (
          <>
            <div>α: <strong>{session.alpha}</strong></div>
            <div>β: <strong>{session.beta}</strong></div>
            <div>γ: <strong>{session.gamma}</strong></div>
            <div>ID: <strong title={session.id}>{session.id.substring(0, 8)}...</strong></div>
            <div style={{ gridColumn: '1 / -1', marginTop: '4px', fontSize: '11px', color: '#888' }}>
              Start: {new Date(session.start_time).toLocaleString()}<br />
              End: {new Date(session.end_time).toLocaleString()}
            </div>
          </>
        )}
      </div>
      {onClick && (
        <button onClick={onClick} className="btn btn-secondary btn-sm" style={{ marginTop: '8px', width: '100%' }}>
          View Details
        </button>
      )}
    </div>
  );
};

const SessionList = ({ sessions, selectedId, onSelect, variant = 'compact', isAdmin = false, sessionWsRef }) => {
  const activeSessions = sessions.filter(s => s.status !== 'ended' && !s.isEnded);
  const endedSessions = sessions.filter(s => s.status === 'ended' || s.isEnded);

  const containerClass = variant === 'compact' ? 'product-list' : 'product-grid';

  return (
    <div className="session-list-container">
      {/* Active Sessions Section */}
      <div className={variant === 'compact' ? 'card' : 'card mb-4'}>
        {variant === 'compact' ? (
          <h3 className="card-title">
            <Package size={24} />
            Active Sales
            {sessionWsRef && sessionWsRef.current && sessionWsRef.current.readyState === WebSocket.OPEN && (
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4caf50', marginLeft: 'auto', display: 'inline-block' }} title="Live Updates Active"></span>
            )}
          </h3>
        ) : (
          <div className="card-header">
            <h3 className="card-title">
              <Package size={24} />
              Active Sessions
            </h3>
          </div>
        )}

        <div className={containerClass}>
          {activeSessions.map(session => (
            <SessionCard
              key={session.id}
              session={session}
              isSelected={selectedId === session.id}
              onClick={() => onSelect && onSelect(session)}
              variant={variant}
              isAdmin={isAdmin}
            />
          ))}
          {activeSessions.length === 0 && (
            <p className="empty-state">No active sessions</p>
          )}
        </div>
      </div>

      {/* Ended Sessions Section */}
      {(endedSessions.length > 0 || variant === 'grid') && (
        <div className={variant === 'compact' ? 'card' : 'card'} style={variant === 'compact' ? { marginTop: '16px' } : { marginTop: '24px' }}>
          {variant === 'compact' ? (
            <h3 className="card-title">
              <Package size={24} />
              Ended Sales
            </h3>
          ) : (
            <div className="card-header">
              <h3 className="card-title">
                <Package size={24} />
                Ended Sessions
              </h3>
            </div>
          )}

          <div className={containerClass}>
            {endedSessions.map(session => (
              <SessionCard
                key={session.id}
                session={session}
                isSelected={selectedId === session.id}
                onClick={() => onSelect && onSelect(session)}
                variant={variant}
                isAdmin={isAdmin}
              />
            ))}
            {endedSessions.length === 0 && (
              <p className="empty-state">No ended sessions</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};


const LeaderboardList = ({ leaderboard, highestBid, thresholdScore, currentPage, totalPages, totalCount, onPageChange }) => {
  if (!leaderboard || leaderboard.length === 0) {
    return <p className="empty-state">No bids yet. Be the first!</p>;
  }

  const handlePrevPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div>
      {/* Summary stats */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '16px',
        padding: '12px',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Highest Bid</div>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2196f3' }}>
            {highestBid !== null && highestBid !== undefined ? `$${highestBid.toFixed(2)}` : 'N/A'}
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Threshold Score</div>
          <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#ff9800' }}>
            {thresholdScore !== null && thresholdScore !== undefined ? thresholdScore.toFixed(2) : 'N/A'}
          </div>
        </div>
      </div>
      
      {/* Leaderboard list */}
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

      {/* Pagination controls */}
      {totalPages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '16px',
          padding: '12px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px'
        }}>
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            style={{
              padding: '8px 16px',
              backgroundColor: currentPage <= 1 ? '#ccc' : '#2196f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            ← Previous
          </button>
          <div style={{ fontSize: '14px', color: '#666', fontWeight: 'bold' }}>
            Page {currentPage} of {totalPages} ({totalCount} total bidders)
          </div>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= totalPages}
            style={{
              padding: '8px 16px',
              backgroundColor: currentPage >= totalPages ? '#ccc' : '#2196f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

const UserView = ({ products, selectedProduct, setSelectedProduct, leaderboard, highestBid, thresholdScore, leaderboardPage, leaderboardTotalPages, leaderboardTotalCount, bidAmount, setBidAmount, onBid, onLeaderboardPageChange, userWeight, wsConnected, sessionWsRef }) => {
  const activeProducts = products.filter(p => !p.isEnded);
  const endedProducts = products.filter(p => p.isEnded);

  return (
    <div className="user-view">
      <div className="sidebar">
        <SessionList
          sessions={products}
          selectedId={selectedProduct?.id}
          onSelect={setSelectedProduct}
          variant="compact"
          sessionWsRef={sessionWsRef}
        />
      </div>
      <div className="main-area">
        {selectedProduct ? (
          <>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0 }}>{selectedProduct.name}</h3>
                {selectedProduct.isEnded ? (
                  <span style={{
                    padding: '6px 12px',
                    backgroundColor: '#f44336',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}>
                    BIDDING ENDED
                  </span>
                ) : (
                  <span style={{
                    padding: '6px 12px',
                    backgroundColor: '#4caf50',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}>
                    LIVE
                  </span>
                )}
              </div>
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

              {selectedProduct.isEnded ? (
                <div style={{
                  padding: '20px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px',
                  textAlign: 'center',
                  marginTop: '20px'
                }}>
                  <p style={{ fontSize: '16px', color: '#666', margin: 0 }}>
                    This bidding session has ended. You can view the final leaderboard below.
                  </p>
                </div>
              ) : (
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
              )}
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 className="card-title" style={{ margin: 0 }}>
                  <Award size={24} color="#ffc107" />
                  {selectedProduct.isEnded ? 'Final Results' : 'Live Leaderboard'} (Top {selectedProduct.inventory})
                </h3>
                {!selectedProduct.isEnded && (
                  <span style={{
                    padding: '4px 8px',
                    backgroundColor: wsConnected ? '#4caf50' : '#ff9800',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 'bold'
                  }}>
                    {wsConnected ? '🟢 LIVE' : '⚠️ POLLING'}
                  </span>
                )}
              </div>
              <LeaderboardList 
                leaderboard={leaderboard}
                highestBid={highestBid}
                thresholdScore={thresholdScore}
                currentPage={leaderboardPage}
                totalPages={leaderboardTotalPages}
                totalCount={leaderboardTotalCount}
                onPageChange={onLeaderboardPageChange}
              />
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

const AdminView = ({ products, adminProducts, onCreate, onCreateProductOnly, onRefresh, onRefreshProducts, user, loadProducts, setMessage, leaderboard, loadLeaderboard }) => {
  const [activeTab, setActiveTab] = useState('sessions'); // 'sessions' or 'products'
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const handleSessionSelect = (session) => {
    setSelectedSession(session);
    setIsDetailModalOpen(true);
    if (loadLeaderboard) {
        loadLeaderboard(session.id);
    }
  };

  // Session Form Data
  const [sessionFormData, setSessionFormData] = useState({
    product_id: '',
    inventory: 5,
    base_price: 100,
    alpha: 0.5,
    beta: 1000,
    gamma: 2.0,
    duration_minutes: 60
  });

  // Product Form Data
  const [productFormData, setProductFormData] = useState({
    name: '',
    description: ''
  });

  const handleSessionSubmit = async () => {
    if (!sessionFormData.product_id) {
      alert('Please select a product');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/admin/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({
          product_id: sessionFormData.product_id,
          upset_price: sessionFormData.base_price,
          inventory: sessionFormData.inventory,
          alpha: sessionFormData.alpha,
          beta: sessionFormData.beta,
          gamma: sessionFormData.gamma,
          duration_minutes: sessionFormData.duration_minutes,
          is_active: true
        })
      });

      const data = await response.json();
      if (response.ok) {
        setMessage('Session created successfully!');
        loadProducts(user.token);
        setSessionFormData({
          product_id: '',
          inventory: 5,
          base_price: 100,
          alpha: 0.5,
          beta: 1000,
          gamma: 2.0,
          duration_minutes: 60
        });
        setIsModalOpen(false);
      } else {
        if (Array.isArray(data.detail)) {
          const errorMessages = data.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
          setMessage(errorMessages);
        } else if (typeof data.detail === 'string') {
          setMessage(data.detail);
        } else {
          setMessage('Failed to create session');
        }
      }
    } catch (error) {
      setMessage('Failed to create session');
    }
  };

  const handleProductSubmit = async () => {
    const success = await onCreateProductOnly(productFormData);
    if (success) {
      setProductFormData({
        name: '',
        description: ''
      });
      setIsModalOpen(false);
    }
  };

  return (
    <div className="admin-view">
      <div className="admin-header">
        <div className="admin-tabs">
          <button
            className={`btn ${activeTab === 'sessions' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('sessions')}
          >
            Session Management
          </button>
          <button
            className={`btn ${activeTab === 'products' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('products')}
          >
            Product Management
          </button>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} />
          Create New {activeTab === 'sessions' ? 'Session' : 'Product'}
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'sessions' ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
              <button onClick={onRefresh} className="btn btn-secondary">
                Refresh Sessions
              </button>
            </div>
            <SessionList
              sessions={products}
              variant="grid"
              isAdmin={true}
              onSelect={handleSessionSelect}
            />
          </div>

        ) : (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Package size={24} />
                Products
              </h3>
              <button onClick={onRefreshProducts} className="btn btn-secondary">
                Refresh
              </button>
            </div>
            <div className="product-grid">
              {adminProducts.map((product) => (
                <div key={product.id} className="product-card">
                  <div className="product-card-title">{product.name}</div>
                  <p>{product.description}</p>
                  <div className="product-card-grid" style={{ marginTop: '8px' }}>
                    <div>Created: <strong>{new Date(product.created_at).toLocaleDateString()}</strong></div>
                  </div>
                </div>
              ))}
              {adminProducts.length === 0 && (
                <p className="empty-state">No products found</p>
              )}
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={`Create New ${activeTab === 'sessions' ? 'Session' : 'Product'}`}
      >
        {activeTab === 'sessions' ? (
          <div className="form-grid">
            <div className="form-group full-width">
              <label>Select Product</label>
              <select
                value={sessionFormData.product_id}
                onChange={(e) => setSessionFormData({ ...sessionFormData, product_id: e.target.value })}
                className="input"
              >
                <option value="">-- Select a Product --</option>
                {adminProducts.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Base Price ($)</label>
              <input
                type="number"
                value={sessionFormData.base_price}
                onChange={(e) => setSessionFormData({ ...sessionFormData, base_price: parseFloat(e.target.value) })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Inventory</label>
              <input
                type="number"
                value={sessionFormData.inventory}
                onChange={(e) => setSessionFormData({ ...sessionFormData, inventory: parseInt(e.target.value) })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Alpha (α)</label>
              <input
                type="number"
                step="0.1"
                value={sessionFormData.alpha}
                onChange={(e) => setSessionFormData({ ...sessionFormData, alpha: parseFloat(e.target.value) })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Beta (β)</label>
              <input
                type="number"
                value={sessionFormData.beta}
                onChange={(e) => setSessionFormData({ ...sessionFormData, beta: parseFloat(e.target.value) })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Gamma (γ)</label>
              <input
                type="number"
                step="0.1"
                value={sessionFormData.gamma}
                onChange={(e) => setSessionFormData({ ...sessionFormData, gamma: parseFloat(e.target.value) })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Duration (Minutes)</label>
              <input
                type="number"
                value={sessionFormData.duration_minutes}
                onChange={(e) => setSessionFormData({ ...sessionFormData, duration_minutes: parseInt(e.target.value) })}
                className="input"
              />
            </div>
            <button onClick={handleSessionSubmit} className="btn btn-primary full-width" style={{ marginTop: '16px' }}>
              Create Session
            </button>
          </div>
        ) : (
          <div className="form-grid">
            <div className="form-group full-width">
              <label>Product Name</label>
              <input
                type="text"
                value={productFormData.name}
                onChange={(e) => setProductFormData({ ...productFormData, name: e.target.value })}
                className="input"
                placeholder="e.g. Limited Edition Sneakers"
              />
            </div>
            <div className="form-group full-width">
              <label>Description</label>
              <textarea
                value={productFormData.description}
                onChange={(e) => setProductFormData({ ...productFormData, description: e.target.value })}
                className="input"
                rows="3"
                placeholder="Product details..."
              />
            </div>
            <button onClick={handleProductSubmit} className="btn btn-primary full-width" style={{ marginTop: '16px' }}>
              Create Product
            </button>
          </div>
        )}
      </Modal>
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title="Session Details"
      >
        {selectedSession && (
            <div>
                <SessionCard session={selectedSession} variant="grid" isAdmin={true} />
                <div style={{ marginTop: '24px' }}>
                    <h3>Leaderboard</h3>
                    <LeaderboardList leaderboard={leaderboard} />
                </div>
            </div>
        )}
      </Modal>
    </div>
  );
};

export default BiddingSystemUI;