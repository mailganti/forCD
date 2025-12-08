(function() {
    'use strict';
    
    // ========== PART 1: MODAL COMPONENT ==========
    // (from log_viewer.js)
    
    // Add CSS
    const style = document.createElement('style');
    style.textContent = `/* all the CSS */`;
    document.head.appendChild(style);
    
    // Add HTML
    const modalHTML = `<div id="logModal">...</div>`;
    document.body.appendChild(...);
    
    // Create window.logViewer object
    window.logViewer = {
        open: function(id) { ... },
        close: function() { ... },
        loadLogs: function() { ... },
        refresh: function() { ... },
        download: function() { ... }
    };
    
    // ========== PART 2: BUTTON ADDER ==========
    // (from add_log_viewer_patch.js)
    
    // Storage for execution IDs
    window.workflowExecutions = {};
    
    // Function to add buttons
    function addViewLogsButton(workflowElement) { ... }
    
    // Function to scan for workflows
    function scanForWorkflows() { ... }
    
    // Intercept fetch to capture execution IDs
    const originalFetch = window.fetch;
    window.fetch = async function(...args) { ... };
    
    // ========== PART 3: INITIALIZATION ==========
    
    function init() {
        scanForWorkflows();
        setInterval(scanForWorkflows, 5000);
    }
    
    // Wait for page to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 1000);
    }
    
})();
