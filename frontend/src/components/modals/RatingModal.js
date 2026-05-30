import React, { useState } from 'react';
import axios from 'axios';
import './ModalStyles.css';

function RatingModal({ isOpen, onClose, itemName, itemId }) {
    const [rating, setRating] = useState(0);
    const [hoverRating, setHoverRating] = useState(0);
    const [comment, setComment] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = async () => {
        if (rating === 0) {
            alert('Please select a rating!');
            return;
        }

        setLoading(true);
        try {
            await axios.post('/api/menu/rate', {
                itemId: itemId,
                rating: rating,
                comment: comment
            });
            setSubmitted(true);
        } catch (error) {
            console.error('Error submitting rating:', error);
            alert('Sorry, I couldn\'t submit your rating right now. Please try again later.');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setRating(0);
        setComment('');
        setSubmitted(false);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content agent-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>⭐ Rate: {itemName}</h2>
                    <button className="modal-close" onClick={handleClose}>&times;</button>
                </div>
                <div className="modal-body">
                    {!submitted ? (
                        <>
                            <div className="rating-stars">
                                {[1, 2, 3, 4, 5].map((star) => (
                                    <span
                                        key={star}
                                        className={`star ${star <= (hoverRating || rating) ? 'active' : ''}`}
                                        onClick={() => setRating(star)}
                                        onMouseEnter={() => setHoverRating(star)}
                                        onMouseLeave={() => setHoverRating(0)}
                                    >
                                        ★
                                    </span>
                                ))}
                            </div>
                            <p className="rating-label">
                                {rating > 0 ? `${rating} star${rating > 1 ? 's' : ''}` : 'Select your rating'}
                            </p>
                            <textarea
                                className="rating-comment"
                                placeholder="Share your thoughts about this dish (optional)..."
                                value={comment}
                                onChange={(e) => setComment(e.target.value)}
                                rows={4}
                            />
                        </>
                    ) : (
                        <div className="modal-content-text" style={{ textAlign: 'center', padding: '2rem 0' }}>
                            <div className="success-icon" style={{ fontSize: '4rem', marginBottom: '1rem' }}>✅</div>
                            <h3>Thank You!</h3>
                            <p>Your {rating}-star rating for {itemName} has been recorded.</p>
                            {comment && <p className="mt-2 text-sm italic text-gray-400">"{comment}"</p>}
                        </div>
                    )}
                </div>
                <div className="modal-footer">
                    {!submitted ? (
                        <>
                            <button className="modal-button secondary" onClick={handleClose}>Cancel</button>
                            <button
                                className="modal-button primary"
                                onClick={handleSubmit}
                                disabled={loading || rating === 0}
                            >
                                {loading ? 'Submitting...' : 'Submit Rating'}
                            </button>
                        </>
                    ) : (
                        <button className="modal-button" onClick={handleClose}>Close</button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default RatingModal;
