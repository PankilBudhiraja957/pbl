import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ModalStyles.css';

function CookingTipsModal({ isOpen, onClose, itemName }) {
    const [tips, setTips] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!isOpen || !itemName) return;
        setLoading(true);
        setTips('');
        axios.post('/api/menu/cooking-tips', { itemName })
            .then(res => setTips(res.data.tips || 'No tips available for this dish.'))
            .catch(() => setTips('Could not load cooking tips right now. Please try again.'))
            .finally(() => setLoading(false));
    }, [isOpen, itemName]);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content agent-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>👨‍🍳 Chef Arjun's Cooking Tips</h2>
                    <button className="modal-close" onClick={onClose}>&times;</button>
                </div>
                <div className="modal-body">
                    <h3 className="modal-item-name">{itemName}</h3>
                    {loading ? (
                        <div className="modal-loading">
                            <div className="loading-spinner"></div>
                            <p>Chef Arjun is preparing the tips...</p>
                        </div>
                    ) : (
                        <div className="modal-content-text">
                            {tips.split('\n').map((line, i) => line.trim() && <p key={i}>{line}</p>)}
                        </div>
                    )}
                </div>
                <div className="modal-footer">
                    <button className="modal-button" onClick={onClose}>Close</button>
                </div>
            </div>
        </div>
    );
}

export default CookingTipsModal;
