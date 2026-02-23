import { useState } from 'react';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import { Shield, Activity, MessageSquare, BarChart3 } from 'lucide-react';

type Tab = 'dashboard' | 'chat';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="flex items-center justify-between max-w-[1800px] mx-auto">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">ContagionGuard</h1>
              <p className="text-xs text-gray-400">Cross-Market Contagion & Margin Risk Early Warning</p>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="flex gap-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              AI Chat
            </button>
          </nav>

          {/* Status */}
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Activity className="w-3 h-3 text-green-400 animate-pulse" />
            <span>Live</span>
            <span className="text-gray-600">|</span>
            <span>DTCC 2026 Hackathon</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1800px] mx-auto p-4">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'chat' && <ChatInterface />}
      </main>
    </div>
  );
}

export default App;
