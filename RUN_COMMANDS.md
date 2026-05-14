# 🚀 How to Run the RFQ System

## Two Simple Commands

### 1️⃣ Run Everything (Backend + Frontend)

```bash
./start-all.sh
```

**What it does:**
- ✅ Starts backend on http://localhost:8000
- ✅ Starts frontend on http://localhost:5173
- ✅ Runs both in background with logs
- ✅ Press `Ctrl+C` to stop everything

**Output:**
```
==========================================
✅ RFQ System is Running!
==========================================

Services:
  • Backend:  http://localhost:8000
  • Frontend: http://localhost:5173
  • API Docs: http://localhost:8000/docs

Logs:
  • Backend:  tail -f backend.log
  • Frontend: tail -f frontend.log

Press Ctrl+C to stop all services
```

---

### 2️⃣ Run Backend Only

```bash
./start-backend.sh
```

**What it does:**
- ✅ Activates Python virtual environment
- ✅ Starts FastAPI server on http://localhost:8000
- ✅ Press `Ctrl+C` to stop

**Output:**
```
==========================================
Starting RFQ Backend Server
==========================================

✓ Activating virtual environment...
✓ Starting FastAPI server on http://localhost:8000

Backend is running...
  • API: http://localhost:8000
  • Docs: http://localhost:8000/docs
  • Health: http://localhost:8000/health

Press Ctrl+C to stop
```

---

### 3️⃣ Run Frontend Only

```bash
./start-frontend.sh
```

**What it does:**
- ✅ Installs npm dependencies (if needed)
- ✅ Starts Vite dev server on http://localhost:5173
- ✅ Press `Ctrl+C` to stop

**Output:**
```
==========================================
Starting RFQ Frontend (React + Vite)
==========================================

✓ Starting Vite dev server on http://localhost:5173

Frontend is running...
  • App: http://localhost:5173
  • Make sure backend is running on http://localhost:8000

Press Ctrl+C to stop
```

---

## Quick Reference

| Command | What it runs | URLs |
|---------|--------------|------|
| `./start-all.sh` | Backend + Frontend | Frontend: http://localhost:5173<br>Backend: http://localhost:8000 |
| `./start-backend.sh` | Backend only | http://localhost:8000 |
| `./start-frontend.sh` | Frontend only | http://localhost:5173 |

---

## First Time Setup

If this is your first time running the system:

```bash
# 1. Install backend dependencies
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
cd ..

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Now run the system
./start-all.sh
```

---

## Troubleshooting

### "Permission denied" error

Make scripts executable:
```bash
chmod +x start-all.sh start-backend.sh start-frontend.sh
```

### Port already in use

**Backend (port 8000):**
```bash
lsof -ti:8000 | xargs kill
```

**Frontend (port 5173):**
```bash
lsof -ti:5173 | xargs kill
```

### Backend won't start - Missing API keys

Set environment variables:
```bash
export GROQ_API_KEY_1=your_key_here
export GROQ_API_KEY_2=your_key_here
export GROQ_API_KEY_3=your_key_here
export GROQ_API_KEY_4=your_key_here
export GROQ_API_KEY_5=your_key_here
```

Or create `backend/.env` file with these variables.

### Check logs

**When using `./start-all.sh`:**
```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

---

## Testing

### 1. Check if backend is running

```bash
curl http://localhost:8000/health
```

Should return: `{"status":"healthy"}`

### 2. Check if frontend is running

Open browser: http://localhost:5173

### 3. Check RAG system

```bash
cd backend
../.venv/bin/python check_rag_status.py
```

Should show all collections populated.

---

## That's it! 🎉

Just run `./start-all.sh` and you're good to go!

For more details, see [QUICK_START.md](QUICK_START.md)
