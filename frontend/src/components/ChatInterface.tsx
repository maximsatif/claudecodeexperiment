import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, runFullAnalysis } from '../services/api';
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

const SUGGESTED_QUESTIONS = [
  'What is the current systemic risk level?',
  'Which entities are most at risk of contagion?',
  'What would happen if JPM experienced a shock?',
  'What are the current margin call probabilities?',
  'Explain the R0 number and its implications.',
  'Are there any correlation breakdowns happening?',
];

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: 'Welcome to ContagionGuard AI. I can analyze cross-market contagion risks, simulate shock scenarios, and provide margin impact assessments. Ask me anything about current market conditions and systemic risk.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(userMessage.content);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'I encountered an error connecting to the analysis engine. Please ensure the backend is running and try again.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFullAnalysis = async () => {
    setAnalyzing(true);
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: '[Running Full Multi-Agent Analysis...]',
        timestamp: new Date(),
      },
    ]);

    try {
      const result = await runFullAnalysis();
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Full analysis complete.\n\n${JSON.stringify(result, null, 2).slice(0, 3000)}`,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Full analysis requires AWS Bedrock credentials to be configured. The agent orchestration engine coordinates 6 specialized AI agents for comprehensive risk assessment.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-120px)]">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-900/50 rounded-xl border border-gray-800">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                msg.role === 'user' ? 'bg-blue-600' :
                msg.role === 'system' ? 'bg-purple-600' : 'bg-gray-700'
              }`}>
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200'
              }`}>
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                <div className="text-xs opacity-50 mt-1">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-gray-800 rounded-xl px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-800 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about market risk, contagion, or margin impact..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 px-4 py-2 rounded-lg transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 space-y-4">
        {/* Full Analysis Button */}
        <button
          onClick={handleFullAnalysis}
          disabled={analyzing}
          className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-gray-700 disabled:to-gray-700 rounded-xl p-4 text-left transition-all"
        >
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5" />
            <span className="font-semibold text-sm">
              {analyzing ? 'Running Analysis...' : 'Run Full AI Analysis'}
            </span>
          </div>
          <p className="text-xs text-gray-300">
            Orchestrates all 6 AI agents for comprehensive risk assessment
          </p>
        </button>

        {/* Suggested Questions */}
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Suggested Questions</h3>
          <div className="space-y-2">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => { setInput(q); }}
                className="w-full text-left text-xs text-gray-400 hover:text-white bg-gray-800/50 hover:bg-gray-800 rounded-lg p-2 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Agent Info */}
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">AI Agents</h3>
          <div className="space-y-2 text-xs">
            {[
              { name: 'Market Data Agent', desc: 'yFinance + FRED', color: 'bg-blue-500' },
              { name: 'News & Sentiment', desc: 'Finnhub + NLP', color: 'bg-purple-500' },
              { name: 'Contagion Graph', desc: 'NetworkX + SIR', color: 'bg-red-500' },
              { name: 'Risk Analysis', desc: 'Anomaly Detection', color: 'bg-orange-500' },
              { name: 'Margin Impact', desc: 'Stress Testing', color: 'bg-yellow-500' },
              { name: 'Narrative Report', desc: 'LLM Generation', color: 'bg-green-500' },
            ].map(agent => (
              <div key={agent.name} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${agent.color}`} />
                <div>
                  <span className="text-gray-300">{agent.name}</span>
                  <span className="text-gray-600 ml-1">({agent.desc})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
