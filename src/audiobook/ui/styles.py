"""UI styles for the application."""

css = """
/* General styles */
.header {
    text-align: center;
    margin-bottom: 2rem;
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

/* Button styles */
button.primary {
    background-color: #2196F3;
    color: white;
}

button.stop {
    background-color: #f44336;
    color: white;
    font-weight: bold;
}

button.stop:hover {
    background-color: #d32f2f;
}

/* Status styles */
.error {
    color: #f44336;
}

.success {
    color: #4CAF50;
}

/* Voice list styles */
.voice-list {
    margin-top: 2rem;
}

/* Audio player styles */
.audio-player {
    margin: 1rem 0;
}

/* Tab styles */
.tab-nav {
    margin-bottom: 1rem;
}

/* Slider styles */
.slider {
    margin: 1rem 0;
}

/* Loading indicator */
.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid rgba(0,0,0,.1);
    border-radius: 50%;
    border-top-color: #2196F3;
    animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Stop button specific styles */
button[variant="stop"] {
    background-color: #f44336;
    color: white;
    font-weight: bold;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

button[variant="stop"]:hover {
    background-color: #d32f2f;
}

button[variant="stop"]:active {
    background-color: #b71c1c;
}

/* Hide stop button when not needed */
button[variant="stop"][style*="display: none"] {
    display: none !important;
}
"""
