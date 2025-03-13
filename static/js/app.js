/**
 * Format SQL query with indentation for better readability
 * @param {string} sql - SQL query to format
 * @returns {string} - Formatted SQL query
 */
function formatSql(sql) {
    // This is a simple formatting function
    // In a production system, you might want to use a dedicated SQL formatter library
    return sql
        .replace(/\s+/g, ' ')
        .replace(/\(\s+/g, '(')
        .replace(/\s+\)/g, ')')
        .replace(/\s*,\s*/g, ', ')
        .replace(/\s*=\s*/g, ' = ')
        .replace(/\s*>\s*/g, ' > ')
        .replace(/\s*<\s*/g, ' < ')
        .replace(/\s*AND\s*/gi, ' AND ')
        .replace(/\s*OR\s*/gi, ' OR ')
        .replace(/\s*SELECT\s+/gi, 'SELECT\n  ')
        .replace(/\s*FROM\s+/gi, '\nFROM\n  ')
        .replace(/\s*WHERE\s+/gi, '\nWHERE\n  ')
        .replace(/\s*GROUP BY\s+/gi, '\nGROUP BY\n  ')
        .replace(/\s*HAVING\s+/gi, '\nHAVING\n  ')
        .replace(/\s*ORDER BY\s+/gi, '\nORDER BY\n  ')
        .replace(/\s*LIMIT\s+/gi, '\nLIMIT\n  ')
        .replace(/\s*JOIN\s+/gi, '\nJOIN\n  ')
        .replace(/\s*ON\s+/gi, '\nON\n  ')
        .replace(/\s*UNION\s+/gi, '\nUNION\n  ');
}

/**
 * Show a notification message to the user
 * @param {string} message - Message to display
 * @param {string} type - Notification type (info, success, warning, error)
 */
function showNotification(message, type = 'info') {
    // Create notification element if it doesn't exist
    let notification = document.querySelector('.notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.className = 'notification';
        document.body.appendChild(notification);
    }
    
    // Set notification type and message
    notification.className = `notification ${type}`;
    notification.innerHTML = message;
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('visible');
    }, 100);
    
    // Hide notification after 3 seconds
    setTimeout(() => {
        notification.classList.remove('visible');
        
        // Remove notification element after animation
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

/**
 * Toggle loading state of a button
 * @param {HTMLElement} button - Button element
 * @param {boolean} isLoading - Whether button is in loading state
 */
function toggleButtonLoading(button, isLoading) {
    if (isLoading) {
        button.setAttribute('disabled', true);
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading...';
    } else {
        button.removeAttribute('disabled');
        button.innerHTML = button.dataset.originalText;
    }
}

/**
 * Generate HTML for complexity badge
 * @param {string} complexity - Complexity level (beginner, intermediate, advanced)
 * @returns {string} - HTML for complexity badge
 */
function getComplexityBadge(complexity) {
    let badgeClass = '';
    let badgeIcon = '';
    
    switch(complexity) {
        case 'beginner':
            badgeClass = 'bg-success';
            badgeIcon = 'bi-stars';
            break;
        case 'intermediate':
            badgeClass = 'bg-warning';
            badgeIcon = 'bi-bar-chart-fill';
            break;
        case 'advanced':
            badgeClass = 'bg-danger';
            badgeIcon = 'bi-graph-up';
            break;
        default:
            badgeClass = 'bg-secondary';
            badgeIcon = 'bi-question-circle';
    }
    
    return `<span class="badge ${badgeClass}"><i class="bi ${badgeIcon} me-1"></i>${complexity.charAt(0).toUpperCase() + complexity.slice(1)}</span>`;
}

/**
 * Initialize SQL Buddy chat functionality
 */
function initSqlBuddy() {
    // This function can be called on pages that have SQL Buddy
    const buddyChat = document.getElementById('buddyChat');
    if (!buddyChat) return;
    
    const buddyInput = document.getElementById('buddyInput');
    const sendToBuddyBtn = document.getElementById('sendToBuddyBtn');
    const buddyInputGroup = document.getElementById('buddyInputGroup');
    
    // Function to add message to chat
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isUser ? 'buddy-message buddy-user-message' : 'buddy-message';
        
        let messageHTML = '';
        if (isUser) {
            messageHTML = `
                <i class="bi bi-person-circle me-2"></i>
                <div class="buddy-message-content">
                    <p>${text}</p>
                </div>
            `;
        } else {
            messageHTML = `
                <i class="bi bi-robot me-2"></i>
                <div class="buddy-message-content">
                    <p>${text}</p>
                </div>
            `;
        }
        
        messageDiv.innerHTML = messageHTML;
        buddyChat.appendChild(messageDiv);
        
        // Scroll to bottom
        buddyChat.scrollTop = buddyChat.scrollHeight;
    }
    
    // Function to handle user input
    function handleUserInput() {
        const userMessage = buddyInput.value.trim();
        if (!userMessage) return;
        
        // Clear input
        buddyInput.value = '';
        
        // Add user message to chat
        addMessage(userMessage, true);
        
        // Get current query as context
        const queryContext = document.querySelector('.CodeMirror') ? 
            document.querySelector('.CodeMirror').CodeMirror.getValue().trim() : '';
        
        // Send to API
        fetch('/api/sql-buddy-tip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                query: queryContext,
                user_message: userMessage 
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.tip) {
                addMessage(data.tip);
            } else {
                addMessage("I'm not sure how to help with that specific question. Try asking something about SQL syntax, query optimization, or database concepts.");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage("Sorry, I encountered an error processing your question. Please try again.");
        });
    }
    
    // Show input group if it exists and is hidden
    if (buddyInputGroup && buddyInputGroup.classList.contains('d-none')) {
        buddyInputGroup.classList.remove('d-none');
    }
    
    // Add event listeners if they don't exist yet
    if (sendToBuddyBtn && !sendToBuddyBtn._hasEventListener) {
        sendToBuddyBtn.addEventListener('click', handleUserInput);
        sendToBuddyBtn._hasEventListener = true;
    }
    
    if (buddyInput && !buddyInput._hasEventListener) {
        buddyInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleUserInput();
            }
        });
        buddyInput._hasEventListener = true;
    }
    
    // Make these functions accessible
    window.sqlBuddy = {
        addMessage,
        handleUserInput
    };
}

/**
 * Save SQL query to favorites
 * @param {string} sqlQuery - SQL query to save
 * @param {string} nlQuery - Natural language description of query
 * @param {Function} callback - Callback function after saving
 */
function saveQueryToFavorites(sqlQuery, nlQuery = '', callback = null) {
    // Show modal to get query details
    let queryTitle = prompt('Enter a title for this query:', nlQuery ? nlQuery.substring(0, 50) : 'My SQL Query');
    
    if (!queryTitle) return; // User cancelled
    
    // Default complexity based on query
    let complexity = 'beginner';
    
    // Simple complexity heuristic
    if (sqlQuery.toLowerCase().includes('join') || 
        sqlQuery.toLowerCase().includes('group by') || 
        sqlQuery.toLowerCase().includes('having')) {
        complexity = 'intermediate';
    }
    
    if (sqlQuery.toLowerCase().includes('with ') || 
        sqlQuery.toLowerCase().includes('partition by') || 
        sqlQuery.toLowerCase().includes('case when')) {
        complexity = 'advanced';
    }
    
    const queryData = {
        title: queryTitle,
        query_text: sqlQuery,
        nl_query: nlQuery || '',
        complexity: complexity
    };
    
    fetch('/api/save-query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(queryData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Query saved to favorites!', 'success');
            if (callback) callback(data);
        } else {
            showNotification('Error saving query: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving query', 'error');
    });
}