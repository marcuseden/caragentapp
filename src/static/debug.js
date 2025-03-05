/**
 * Debug utility functions
 */

function debugLog(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
    if (data) {
        console.log(data);
    }
}

function showDebugInfo(message, data = null) {
    // Check if debug mode is enabled
    const debugMode = localStorage.getItem('debugMode') === 'true';
    if (!debugMode) return;
    
    // Find or create debug container
    let debugContainer = document.getElementById('debugContainer');
    if (!debugContainer) {
        debugContainer = document.createElement('div');
        debugContainer.id = 'debugContainer';
        debugContainer.className = 'fixed bottom-0 right-0 bg-gray-800 text-white p-4 m-4 rounded-lg shadow-lg max-w-lg max-h-96 overflow-auto';
        document.body.appendChild(debugContainer);
    }
    
    // Add message
    const msgEl = document.createElement('div');
    msgEl.className = 'text-sm font-mono mb-2';
    msgEl.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    debugContainer.appendChild(msgEl);
    
    // Add data if provided
    if (data) {
        const dataEl = document.createElement('pre');
        dataEl.className = 'text-xs bg-gray-700 p-2 rounded mb-3 overflow-auto';
        dataEl.textContent = typeof data === 'object' ? JSON.stringify(data, null, 2) : data;
        debugContainer.appendChild(dataEl);
    }
    
    // Scroll to bottom
    debugContainer.scrollTop = debugContainer.scrollHeight;
}

// Add a global error handler
window.addEventListener('error', function(event) {
    showDebugInfo(`ERROR: ${event.message}`, `${event.filename}:${event.lineno}`);
}); 