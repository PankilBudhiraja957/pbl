import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import { FaRobot, FaTimes, FaPaperPlane, FaMicrophone, FaMicrophoneSlash, FaVolumeUp, FaVolumeMute, FaBrain } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import './ChatWidget.css';

const socket = io('/', {
  path: '/socket.io',
  autoConnect: true,
  reconnection: true,
  transports: ['polling', 'websocket']
});

function ChatWidget() {
  const { currentUser, refreshAuthStatus } = useAuth();
  const { refreshCart } = useCart();
  const [isOpen, setIsOpen] = useState(false);
  const [showAgents, setShowAgents] = useState(false);

  // Agent states
  const [agents, setAgents] = useState({
    "Coordinator": { status: "idle", message: "Standing by." },
    "Nutritionist": { status: "idle", message: "Ready." },
    "MenuSpecialist": { status: "idle", message: "Ready." },
    "OrderManager": { status: "idle", message: "Ready." },
    "ChefAdvisor": { status: "idle", message: "Ready." },
    "FeedbackAgent": { status: "idle", message: "Ready." },
    "Sommelier": { status: "idle", message: "Ready." },
    "Reservationist": { status: "idle", message: "Ready." }
  });
  const [activeAgent, setActiveAgent] = useState(null);

  const getInitialMessage = () => ({
    sender: 'bot',
    text: 'Hello! I am DineSmartAI, your virtual assistant. How can I help you with our menu, ordering, or reservations today?'
  });

  const [messages, setMessages] = useState([getInitialMessage()]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [lastInputWasVoice, setLastInputWasVoice] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen && currentUser) {
      axios.get('/api/ai/chat/history', { withCredentials: true })
        .then(res => {
          if (res.data.history && res.data.history.length > 0) {
            const mappedHistory = res.data.history.map(msg => ({
              sender: msg.role === 'assistant' ? 'bot' : 'user',
              text: msg.content
            }));
            setMessages([getInitialMessage(), ...mappedHistory]);
          }
        })
        .catch(err => console.error("Failed to load chat history", err));
    }
  }, [isOpen, currentUser]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, agents]);

  useEffect(() => {
    socket.on('agent_status', (data) => {
      setAgents(prev => ({
        ...prev,
        [data.agent]: { status: data.status, message: data.message || prev[data.agent]?.message }
      }));
      if (['active', 'thinking', 'tool_use', 'responding'].includes(data.status)) {
        setActiveAgent(data.agent);
      } else if (data.status === 'idle') {
        setActiveAgent(prev => prev === data.agent ? null : prev);
      }
    });

    socket.on('cart_updated', () => {
      if (refreshCart) refreshCart();
    });

    return () => {
      socket.off('agent_status');
      socket.off('cart_updated');
    };
  }, [refreshCart]);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setLastInputWasVoice(true);
      };

      recognitionRef.current.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.start();
        setIsListening(true);
      } else {
        alert("Speech recognition is not supported in this browser.");
      }
    }
  };

  const speak = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*_#]/g, '').replace(/\[.*?\]\(.*?\)/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      window.speechSynthesis.speak(utterance);
    }
  };

  const toggleVoice = () => setVoiceEnabled(!voiceEnabled);

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await axios.post('/api/ai/chat', { message: userMessage.text }, { withCredentials: true });
      const botMessage = { sender: 'bot', text: res.data.reply || res.data };
      setMessages(prev => [...prev, botMessage]);
      
      if (lastInputWasVoice && voiceEnabled) {
        speak(botMessage.text);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: 'bot', text: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className={`chat-widget-toggle ${isOpen ? 'open' : ''}`} onClick={() => setIsOpen(!isOpen)}>
        {isOpen ? <FaTimes /> : <FaRobot />}
      </div>

      <div className={`chat-widget-container ${isOpen ? 'open' : ''}`}>
        <div className="chat-header">
          <div className="header-info">
            <h3>DineSmartAI</h3>
            <span className="agent-status-indicator">
              {activeAgent ? `Agent Active: ${activeAgent}` : 'Agents Standby'}
            </span>
          </div>
          <div className="header-actions">
            <button type="button" className="icon-button" onClick={() => setShowAgents(!showAgents)} title="View Agents">
              <FaBrain />
            </button>
            <button type="button" className="icon-button" onClick={toggleVoice} title={voiceEnabled ? "Mute Voice" : "Enable Voice"}>
              {voiceEnabled ? <FaVolumeUp /> : <FaVolumeMute />}
            </button>
          </div>
        </div>

        {showAgents && (
          <div className="agents-panel">
            <h4>AI Specialists</h4>
            <div className="agents-grid">
              {Object.entries(agents).map(([name, data]) => (
                <div key={name} className={`agent-card ${data.status}`}>
                  <div className="agent-name">{name}</div>
                  <div className="agent-state">{data.status}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              <div className="message-content">
                {msg.sender === 'bot' ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                ) : (
                  msg.text.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message bot">
              <div className="message-content typing-indicator">
                <span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input */}
        <div className="chat-input-area">
          <form onSubmit={handleSendMessage} className="chat-input-form">
            <div className="input-container">
              <input
                type="text"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  setLastInputWasVoice(false);
                }}
                placeholder="Ask me about our menu..."
                disabled={isLoading}
                className="chat-input"
              />
              <button
                type="button"
                className={`voice-button ${isListening ? 'listening' : ''}`}
                onClick={toggleListening}
                disabled={isLoading}
                title="Voice input"
              >
                {isListening ? <FaMicrophoneSlash /> : <FaMicrophone />}
              </button>
            </div>
            <button type="submit" className="send-button" disabled={isLoading || !input.trim()}>
              <FaPaperPlane />
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

export default ChatWidget;
