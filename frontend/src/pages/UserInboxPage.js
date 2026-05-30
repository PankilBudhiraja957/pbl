import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './UserInboxPage.css';

const UserInboxPage = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedMessage, setSelectedMessage] = useState(null);

  useEffect(() => {
    fetchInbox();
  }, []);

  const fetchInbox = async () => {
    try {
      const response = await axios.get('/api/inbox', { withCredentials: true });
      setMessages(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load inbox');
      setLoading(false);
    }
  };

  const markAsRead = async (messageId) => {
    try {
      await axios.post(`/api/inbox/${messageId}/read`, {}, { withCredentials: true });
      setMessages(messages.map(msg =>
        msg.id === messageId ? { ...msg, is_read: true } : msg
      ));
    } catch (err) {
      console.error('Failed to mark as read', err);
    }
  };

  const handleMessageClick = (message) => {
    setSelectedMessage(message);
    if (!message.is_read) {
      markAsRead(message.id);
    }
  };

  if (loading) return <div className="inbox-loading">Loading your inbox...</div>;
  if (error) return <div className="inbox-error">{error}</div>;

  return (
    <div className="user-inbox-page page-content">
      <h1>Your Inbox</h1>
      <div className="inbox-container">
        <div className="inbox-list">
          {messages.length === 0 ? (
            <p className="no-messages">No messages yet. Bills will appear here after placing orders.</p>
          ) : (
            messages.map(message => (
              <div
                key={message.id}
                className={`inbox-item ${!message.is_read ? 'unread' : ''} ${selectedMessage?.id === message.id ? 'selected' : ''}`}
                onClick={() => handleMessageClick(message)}
              >
                <div className="inbox-item-header">
                  <h3>{message.subject}</h3>
                  <span className="timestamp">{new Date(message.timestamp).toLocaleString()}</span>
                </div>
                <p className="preview">{message.message.substring(0, 100)}...</p>
              </div>
            ))
          )}
        </div>
        <div className="inbox-content">
          {selectedMessage ? (
            <div className="message-detail">
              <h2>{selectedMessage.subject}</h2>
              <p className="timestamp">{new Date(selectedMessage.timestamp).toLocaleString()}</p>
              <div className="message-body">
                {selectedMessage.message.split('\n').map((line, index) => (
                  <p key={index}>{line}</p>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <p>Select a message to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserInboxPage;
