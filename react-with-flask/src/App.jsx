import { Routes, Route } from 'react-router-dom'
import Landing from './landing.jsx'
import Dashboard from './dashboard.jsx'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  )
}

export default App
