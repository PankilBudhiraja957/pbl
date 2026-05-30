import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { motion, AnimatePresence } from 'framer-motion';
import './AgentVisualizer.css';

// Connect to the backend
const socket = io('http://localhost:5000');

const AgentVisualizer = ({ compact = false }) => {
    const [agents, setAgents] = useState({
        "Coordinator": { status: "idle", message: "Standing by.", key: "coordinator" },
        "Nutritionist": { status: "idle", message: "Ready to analyze.", key: "nutritionist" },
        "MenuSpecialist": { status: "idle", message: "Reviewing menu.", key: "menuspecialist" },
        "OrderManager": { status: "idle", message: "Monitoring cart.", key: "ordermanager" },
        "ChefAdvisor": { status: "idle", message: "Ready to cook.", key: "chefadvisor" },
        "FeedbackAgent": { status: "idle", message: "Listening.", key: "feedbackagent" },
        "Sommelier": { status: "idle", message: "Pairing drinks.", key: "sommelier" },
        "Reservationist": { status: "idle", message: "Booking tables.", key: "reservationist" }
    });

    const [activeConnection, setActiveConnection] = useState(null);
    const [dataspaceLog, setDataspaceLog] = useState([]);
    const logEndRef = useRef(null);

    // Socket.IO for status
    useEffect(() => {
        socket.on('agent_status', (data) => {
            setAgents(prev => ({
                ...prev,
                [data.agent]: {
                    ...prev[data.agent],
                    status: data.status,
                    message: data.message || prev[data.agent]?.message || ''
                }
            }));

            if (data.status !== 'idle') {
                setActiveConnection(data.agent);
            } else {
                setActiveConnection(data.agent === activeConnection ? null : activeConnection);
            }
        });

        return () => {
            socket.off('agent_status');
        };
    }, [activeConnection]);

    // Poll for global dataspace stream
    // Listen for new thoughts (Real-time Push)
    useEffect(() => {
        // Initial fetch to populate history (optional, or just start empty)
        const fetchHistory = async () => {
            try {
                const res = await fetch('http://localhost:5000/api/dataspace');
                if (res.ok) {
                    const data = await res.json();
                    setDataspaceLog(data);
                }
            } catch (err) {
                console.error("Initial dataspace fetch error:", err);
            }
        };
        fetchHistory();

        // Listen for real-time events
        socket.on('new_thought', (newEntry) => {
            setDataspaceLog((prevLogs) => {
                // Prepend new entry, keep max 50
                const updated = [newEntry, ...prevLogs];
                return updated.slice(0, 50);
            });
        });

        return () => {
            socket.off('new_thought');
        };
    }, []);

    const getAgentIcon = (name) => {
        switch (name) {
            case 'Nutritionist': return '🥗';
            case 'MenuSpecialist': return '👨‍🍳';
            case 'OrderManager': return '🛒';
            case 'Coordinator': return '🧠';
            case 'ChefAdvisor': return '🔥';
            case 'FeedbackAgent': return '⭐';
            case 'Sommelier': return '🍷';
            case 'Reservationist': return '📅';
            default: return '🤖';
        }
    };

    const getTypeColor = (type) => {
        switch (type) {
            case 'plan': return 'var(--neon-purple)';
            case 'action': return 'var(--neon-cyan)';
            case 'observation': return 'var(--neon-green)';
            case 'critique': return 'var(--neon-orange)';
            case 'decision': return 'var(--neon-pink)';
            case 'memory': return '#ffe600'; // neon yellow
            default: return 'var(--text-secondary)';
        }
    };

    return (
        <div className={`agent-visualizer-container ${compact ? 'compact' : ''}`}>

            <div className="visualizer-header">
                <h3><span className="pulse-dot"></span> GLOBAL SWARM INTELLIGENCE</h3>
                <div className="status-badge">ONLINE</div>
            </div>

            <div className="visualizer-content">
                {/* Left: Agent Grid (Neural Network) */}
                <div className="agent-network-panel">
                    {/* Neural Network SVG Lines (Background) */}
                    {!compact && (
                        <svg className="neural-network" viewBox="0 0 400 300">
                            {/* Coordinator (Center) */}
                            <circle cx="200" cy="150" r="40" fill="rgba(0,0,0,0.5)" stroke="var(--neon-purple)" opacity="0.2" />

                            {/* Dynamic connecting lines */}
                            {["Nutritionist", "MenuSpecialist", "OrderManager", "ChefAdvisor"].map((agent, i) => {
                                // Calculate positions roughly
                                const angles = [0, 90, 180, 270];
                                const angle = angles[i] * (Math.PI / 180);
                                const x = 200 + 120 * Math.cos(angle);
                                const y = 150 + 120 * Math.sin(angle);

                                return (
                                    <line
                                        key={agent}
                                        x1="200" y1="150"
                                        x2={x} y2={y}
                                        stroke={activeConnection === agent ? "var(--neon-cyan)" : "var(--text-muted)"}
                                        strokeWidth="2"
                                        opacity={activeConnection === agent ? 1 : 0.2}
                                        strokeDasharray={activeConnection === agent ? "none" : "5,5"}
                                    >
                                        {activeConnection === agent && (
                                            <animate attributeName="stroke-dashoffset" from="100" to="0" dur="1s" repeatCount="indefinite" />
                                        )}
                                    </line>
                                );
                            })}
                        </svg>
                    )}

                    <div className="agents-grid">
                        {Object.entries(agents).map(([name, data]) => (
                            <motion.div
                                key={name}
                                className={`agent-card ${data.key}`}
                                animate={{
                                    scale: data.status !== 'idle' ? 1.05 : 1,
                                    borderColor: data.status !== 'idle' ? 'var(--neon-cyan)' : 'rgba(255,255,255,0.1)',
                                    boxShadow: data.status !== 'idle' ? '0 0 15px var(--neon-cyan)' : 'none'
                                }}
                            >
                                <div className="agent-icon">{getAgentIcon(name)}</div>
                                <div className="agent-info">
                                    <span className="agent-name">{name === "OrderManager" ? "Turbo" : name}</span>
                                    <span className="agent-status">{data.status.toUpperCase()}</span>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Right: Dataspace Log (Live Stream) */}
                {!compact && (
                    <div className="dataspace-log-panel">
                        <div className="log-header">AUTONOMOUS THOUGHT STREAM</div>
                        <div className="log-scroll-area">
                            <AnimatePresence>
                                {dataspaceLog.map((entry) => (
                                    <motion.div
                                        key={entry.id}
                                        initial={{ opacity: 0, x: 20, height: 0 }}
                                        animate={{ opacity: 1, x: 0, height: 'auto' }}
                                        exit={{ opacity: 0 }}
                                        className="log-entry"
                                        style={{ borderLeftColor: getTypeColor(entry.type) }}
                                    >
                                        <div className="log-meta">
                                            <span className="log-agent" style={{ color: getTypeColor(entry.type) }}>
                                                {entry.agent}
                                            </span>
                                            <span className="log-type">::{entry.type.toUpperCase()}</span>
                                            <span className="log-time">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                                        </div>
                                        <div className="log-content">
                                            {entry.content}
                                            {/* Render extra data if memory retrieval */}
                                            {entry.type === 'memory' && entry.data?.count && (
                                                <span className="memory-tag"> [{entry.data.count} items]</span>
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                            {dataspaceLog.length === 0 && (
                                <div className="log-empty">Waiting for neural activity...</div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentVisualizer;
