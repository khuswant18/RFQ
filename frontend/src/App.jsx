import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import RFQDetail from './pages/RFQDetail.jsx'
import Upload from './pages/Upload.jsx'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>⚙️  Smart RFQ Intelligence</h1>
          </div>
          <ul className="nav-links">
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/upload">Upload RFQ</Link></li>
          </ul>
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rfq/:rfqId" element={<RFQDetail />} />
            <Route path="/upload" element={<Upload />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
