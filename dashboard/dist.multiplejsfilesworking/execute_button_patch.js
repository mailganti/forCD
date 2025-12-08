/* execute_button_patch.js - Fix Execute Button Without Changing Styling */

/**
 * This patch fixes the Execute button to call the script endpoint
 * instead of the broken workflow notification system.
 * 
 * It preserves ALL your existing dashboard styling and functionality.
 */

(function() {
    console.log('[PATCH] Loading execute button fix...');
    
    // Wait for page to load
    function init() {
        // Find all Execute buttons
        const executeButtons = document.querySelectorAll('[onclick*="execute"]');
        console.log(`[PATCH] Found ${executeButtons.length} execute buttons`);
        
        executeButtons.forEach(button => {
            // Get the workflow ID from the onclick attribute
            const onclickAttr = button.getAttribute('onclick');
            const workflowIdMatch = onclickAttr.match(/execute.*?\(['"]([^'"]+)['"]\)/);
            
            if (workflowIdMatch) {
                const workflowId = workflowIdMatch[1];
                console.log(`[PATCH] Patching button for workflow: ${workflowId}`);
                
                // Replace onclick with new functionality
                button.onclick = async function(e) {
                    e.preventDefault();
                    
                    console.log(`[PATCH] Execute clicked for workflow: ${workflowId}`);
                    
                    // Disable button during execution
                    button.disabled = true;
                    const originalText = button.textContent;
                    button.textContent = 'Executing...';
                    
                    try {
                        // Get workflow to find script_id
                        const workflowsResp = await fetch('/api/workflows', {
                            credentials: 'include'
                        });
                        const workflowsData = await workflowsResp.json();
                        const workflows = workflowsData.workflows || workflowsData || [];
                        
                        const workflow = workflows.find(w => w.workflow_id === workflowId);
                        
                        if (!workflow) {
                            throw new Error('Workflow not found');
                        }
                        
                        if (!workflow.script_id) {
                            throw new Error('Workflow has no associated script');
                        }
                        
                        console.log(`[PATCH] Executing script: ${workflow.script_id}`);
                        
                        // Execute the SCRIPT (not the workflow)
                        const response = await fetch(`/api/scripts/${workflow.script_id}/execute`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            credentials: 'include',
                            body: JSON.stringify({})
                        });
                        
                        if (!response.ok) {
                            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                            throw new Error(error.detail || `HTTP ${response.status}`);
                        }
                        
                        const result = await response.json();
                        console.log('[PATCH] Execution successful:', result);
                        
                        // Show success message
                        alert(`✅ Script executed successfully!\nExecution ID: ${result.execution_id}`);
                        
                        // Trigger refresh if available
                        if (window.loadWorkflows) {
                            window.loadWorkflows();
                        }
                        if (window.app && window.app.loadData) {
                            window.app.loadData();
                        }
                        
                    } catch (error) {
                        console.error('[PATCH] Execution failed:', error);
                        alert(`❌ Execution failed: ${error.message}`);
                    } finally {
                        // Re-enable button
                        button.disabled = false;
                        button.textContent = originalText;
                    }
                };
            }
        });
    }
    
    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Also run after data loads (for dynamic content)
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args).then(response => {
            // Re-patch after any fetch that might reload workflows
            if (args[0] && args[0].includes('/workflows')) {
                setTimeout(init, 100);
            }
            return response;
        });
    };
    
    console.log('[PATCH] Execute button fix loaded successfully');
})();

