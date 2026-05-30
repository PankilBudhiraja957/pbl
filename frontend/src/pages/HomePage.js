import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FaArrowRight, FaUtensils, FaStar, FaLeaf, FaWineGlass, FaMicrophone } from 'react-icons/fa';
import AgentVisualizer from '../components/AgentVisualizer';

import { useAuth } from '../context/AuthContext';

function HomePage() {
  const { currentUser } = useAuth();
  const isLoggedIn = !!currentUser;
  const [isLoaded, setIsLoaded] = useState(false);
  const [particles, setParticles] = useState([]);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const heroRef = useRef(null);

  useEffect(() => {
    setIsLoaded(true);

    // Generate subtle dust particles
    const newParticles = Array.from({ length: 40 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 20,
      duration: Math.random() * 20 + 20,
      size: Math.random() * 2 + 1
    }));
    setParticles(newParticles);
  }, []);

  // Parallax mouse effect (Subtler)
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        const x = (e.clientX - rect.left - rect.width / 2) / 100; // Increased divider for subtler effect
        const y = (e.clientY - rect.top - rect.height / 2) / 100;
        setMousePosition({ x, y });
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="homepage">
      {/* Premium Dust Particles */}
      <div className="particles-container">
        {particles.map(p => (
          <div
            key={p.id}
            className="particle"
            style={{
              left: `${p.left}%`,
              animationDelay: `-${p.delay}s`,
              animationDuration: `${p.duration}s`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: Math.random() * 0.3
            }}
          />
        ))}
      </div>

      {/* Hero Section */}
      <section className="hero-section" ref={heroRef}>
        <div className="hero-content">
          <div className={`hero-text ${isLoaded ? 'animate-in' : ''}`}>
            <div className="hero-badge">
              <FaStar size={10} style={{ marginRight: '8px' }} /> AI-Powered Gastronomy
            </div>

            <h1
              className="hero-title"
              style={{
                transform: `translate(${mousePosition.x}px, ${mousePosition.y}px)`
              }}
            >
              DINESMART<span className="brand-ai">AI</span>
            </h1>

            <p className="hero-subtitle">
              Experience the convergence of culinary tradition and autonomous intelligence.
              <br />
              <span className="hero-highlight">Self-evolving Multi-Agent Ecosystem</span> governing every flavor.
            </p>

            <div className="hero-cta-group">
              <Link to="/menu" className="btn btn-primary">
                View Menu
              </Link>
              {/* Conditional Redirect based on Auth */}
              <Link to={isLoggedIn ? "/menu" : "/signup"} className="btn btn-secondary">
                {isLoggedIn ? "Order Now" : "Join the Table"}
              </Link>
            </div>
          </div>
        </div>

        {/* Floating Food Cards - Elegant & Minimal */}
        <div className="floating-elements">
          <div
            className="floating-card card-1"
            style={{
              transform: `translate(${-mousePosition.x * 2}px, ${-mousePosition.y * 2}px)`
            }}
          >
            <div className="card-icon">🍛</div>
            <div className="card-info">
              <div className="card-text">Signature Butter Chicken</div>
              <div className="card-rating">★★★★★</div>
            </div>
          </div>
          <div
            className="floating-card card-2"
            style={{
              transform: `translate(${mousePosition.x * 1.5}px, ${mousePosition.y * 1.5}px)`
            }}
          >
            <div className="card-icon">🥗</div>
            <div className="card-info">
              <div className="card-text">Organic Quinoa Salad</div>
              <div className="card-rating">★★★★☆</div>
            </div>
          </div>
        </div>
      </section>

      {/* Agent Showcase with Live Dataspace */}
      <section className="agents-showcase">
        <div className="showcase-container">
          <h2 className="section-title">8 AI Agents Working For You</h2>
          <p className="section-subtitle">Real-time collaboration between specialized AI agents — from nutrition to reservations.</p>
          <div className="visualizer-wrapper" style={{ marginTop: '2rem' }}>
            <AgentVisualizer />
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="stats-section">
        <div className="stats-container">
          <div className="stat-item">
            <div className="stat-number">50+</div>
            <div className="stat-label">Dishes</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">8</div>
            <div className="stat-label">AI Agents</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">24/7</div>
            <div className="stat-label">Online</div>
          </div>
          <div className="stat-item">
            <div className="stat-number">5★</div>
            <div className="stat-label">Rated</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features-section">
        <div className="features-container">
          <div className="feature-card">
            <FaLeaf className="feature-card-icon" />
            <h3>Dietary Precision</h3>
            <p>Our Nutritionist Agent analyzes every ingredient to match your exact health requirements and allergy profile.</p>
          </div>
          <div className="feature-card">
            <FaMicrophone className="feature-card-icon" />
            <h3>Natural Dialogue</h3>
            <p>Converse naturally with our AI to place orders, book tables, ask for pairings, or get cooking tips.</p>
          </div>
          <div className="feature-card">
            <FaWineGlass className="feature-card-icon" />
            <h3>Smart Reservations</h3>
            <p>Book tables, plan events with budgets, and get occasion packages — all handled by the Reservation Agent.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default HomePage;
