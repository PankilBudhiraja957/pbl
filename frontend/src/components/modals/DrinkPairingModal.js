import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ModalStyles.css';

function DrinkPairingModal({ isOpen, onClose, itemName }) {
    const [pairings, setPairings] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchPairings = async () => {
            setLoading(true);
            try {
                const response = await axios.post('/api/menu/pairings', {
                    itemName: itemName
                });
                setPairings(response.data.pairings);
            } catch (error) {
                console.error('Error fetching pairings:', error);
                setPairings('Sorry, I couldn\'t fetch drink pairings right now. Please try again later.');
            } finally {
                setLoading(false);
            }
        };

        if (isOpen && itemName) {
            fetchPairings();
        }
    }, [isOpen, itemName]);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content agent-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>🍷 Perfect Pairing for {itemName}</h2>
                    <button className="modal-close" onClick={onClose}>&times;</button>
                </div>
                <div className="modal-body">
                    {loading ? (
                        <div className="modal-loading">
                            <div className="loading-spinner"></div>
                            <p>Our Sommelier is selecting the perfect pairing...</p>
                        </div>
                    ) : (
                        <div className="modal-content-text">
                            {pairings.split('\n').map((line, index) => (
                                <p key={index}>{line}</p>
                            ))}
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

export default DrinkPairingModal;
