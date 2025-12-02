# Frontend Integration Guide

## Changes Made to App.js

Your React frontend has been updated to correctly integrate with the FastAPI backend running on `localhost:8000`.

### ✅ API Endpoints Updated

**Before → After:**

1. **Base URL:**
   - Before: `http://localhost:3000/api`
   - After: `http://localhost:8000/api`

2. **Authentication:**
   - **Login:** `POST /api/auth/login`
     - Payload: `{ username, password }`
     - Returns: `{ user_id, username, token, weight, is_admin }`
   - **Register:** `POST /api/auth/register`
     - Payload: `{ username, email, password }`
     - Returns: `{ user_id, username, token, weight, is_admin }`

3. **Products/Sessions:**
   - **Get Active Sessions:** `GET /api/sessions/active`
     - Before: `/api/products`
     - Returns: Array of active sessions with product details

4. **Bidding:**
   - **Submit Bid:** `POST /api/bid`
     - Payload: `{ session_id, price }` (changed from `product_id`)
     - Returns: `{ status, score, rank, current_price, message }`
   - **Get Leaderboard:** `GET /api/leaderboard/{session_id}`
     - Returns: `{ session_id, leaderboard: [...] }`

5. **Admin:**
   - **Create Product + Session:** `POST /api/admin/sessions/combined`
     - Payload:
       ```json
       {
         "name": "Product Name",
         "description": "Description",
         "upset_price": 200.0,
         "inventory": 5,
         "alpha": 0.5,
         "beta": 1000.0,
         "gamma": 2.0,
         "duration_minutes": 60
       }
       ```

### 🔄 Data Flow Changes

**Product/Session Data:**
```javascript
// Backend response from /api/sessions/active
{
  "session_id": "uuid",
  "product_id": "uuid",
  "name": "iPhone 15 Pro",
  "description": "Limited Edition",
  "base_price": 200.0,
  "inventory": 5,
  "alpha": 0.5,
  "beta": 1000.0,
  "gamma": 2.0,
  "start_time": "2024-12-02T10:00:00",
  "end_time": "2024-12-02T11:00:00",
  "status": "active"
}
```

**Leaderboard Data:**
```javascript
// Backend response from /api/leaderboard/{session_id}
{
  "session_id": "uuid",
  "leaderboard": [
    {
      "user_id": "uuid",
      "username": "user1",
      "price": 250.0,
      "score": 1177.40,
      "rank": 1,
      "is_winner": true
    }
  ]
}
```

### 📝 Key Updates

1. **Email field added to registration form** - Required by backend API
2. **Leaderboard polling** - Updates every 3 seconds (replaces WebSocket for now)
3. **Session ID usage** - Changed from `product_id` to `session_id` for bids
4. **Error messages** - Now uses `data.detail` from FastAPI error responses
5. **Duration field** - Added to admin form for session duration

### 🚀 Running the Frontend

```bash
cd frontend
npm install
npm start
```

The app will run on http://localhost:3000

### 🔌 Testing the Integration

1. **Start the Backend:**
   ```bash
   cd ..
   python -m app.main
   # Backend runs on http://localhost:8000
   ```

2. **Start the Frontend:**
   ```bash
   cd frontend
   npm start
   # Frontend runs on http://localhost:3000
   ```

3. **Test Flow:**
   - Register a new user (email required)
   - Login
   - View active sessions
   - Select a session and submit a bid
   - Watch the leaderboard update

### 🎯 Admin Flow

1. **Register/Login as Admin:**
   - Check "Login as Admin" checkbox during registration
   - The backend will set `is_admin: true`

2. **Create Product:**
   - Fill in product details
   - Set scoring parameters (α, β, γ)
   - Set duration in minutes
   - Click "Create Product"

3. **View in User Panel:**
   - Logout and login as regular user
   - The new product appears in active sessions

### ⚠️ Important Notes

- **CORS**: Backend allows `localhost:3000` by default
- **JWT Tokens**: Stored in state, valid for 24 hours
- **Real-time Updates**: Currently uses polling (3s intervals)
  - WebSocket support can be added later for true real-time
- **Error Handling**: Shows user-friendly messages from backend

### 🐛 Troubleshooting

**"Connection error":**
- Make sure backend is running on port 8000
- Check CORS settings in backend

**"Authentication failed":**
- Check username/password/email format
- Ensure backend database is initialized

**"No products available":**
- Create products using admin panel first
- Check that sessions are active (within start/end time)

**Leaderboard not updating:**
- Check browser console for errors
- Verify session_id is correct
- Ensure bids are being submitted successfully

### 📊 Data Persistence

- **User data**: PostgreSQL
- **Session data**: PostgreSQL
- **Leaderboard**: Redis (real-time) + PostgreSQL (persistent)
- **Bids**: PostgreSQL

### 🔜 Future Enhancements

- [ ] WebSocket for real-time leaderboard updates
- [ ] User profile page
- [ ] Bid history
- [ ] Session countdown timer
- [ ] Notifications for winning bids
- [ ] Payment integration
