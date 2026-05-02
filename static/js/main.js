function switchTab(tabId) {
    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabId + '-form').classList.add('active');
    event.currentTarget.classList.add('active');
}

// App Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('query-form');
    if (!queryForm) return; // Not on app page

    // Fetch schema on load
    fetch('/api/schema')
        .then(res => res.json())
        .then(schema => {
            const container = document.getElementById('schema-container');
            let html = '';
            for (const [table, info] of Object.entries(schema)) {
                html += `<div class="schema-table">➔ ${table}</div>`;
                info.cols.forEach(col => {
                    html += `<div class="schema-col">${col}</div>`;
                });
            }
            container.innerHTML = html;
        });

    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('question');
        const question = input.value.trim();
        if (!question) return;

        const chat = document.getElementById('chat-history');
        
        // Add user message
        chat.innerHTML += `
            <div class="chat-message user">
                <div class="message-bubble">${question}</div>
            </div>
        `;
        
        input.value = '';
        
        // Add loading bot message
        const loaderId = 'loader-' + Date.now();
        chat.innerHTML += `
            <div class="chat-message bot" id="${loaderId}">
                <div class="message-bubble"><div class="loader"></div> Thinking & Generating SQL...</div>
            </div>
        `;
        chat.scrollTop = chat.scrollHeight;

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            const data = await res.json();
            
            const loaderEl = document.getElementById(loaderId);
            
            if (data.success) {
                let tableHtml = '';
                if (data.data && data.data.length > 0) {
                    const headers = Object.keys(data.data[0]);
                    tableHtml = '<table class="data-table"><thead><tr>';
                    headers.forEach(h => tableHtml += `<th>${h}</th>`);
                    tableHtml += '</tr></thead><tbody>';
                    data.data.forEach(row => {
                        tableHtml += '<tr>';
                        headers.forEach(h => tableHtml += `<td>${row[h]}</td>`);
                        tableHtml += '</tr>';
                    });
                    tableHtml += '</tbody></table>';
                } else {
                    tableHtml = '<p>No results found.</p>';
                }

                loaderEl.innerHTML = `
                    <div class="message-bubble">
                        <p>Generated SQL in ${data.attempts} attempt(s):</p>
                        <div class="sql-block">${data.sql}</div>
                        ${tableHtml}
                    </div>
                `;
            } else {
                loaderEl.innerHTML = `
                    <div class="message-bubble" style="border-color: #EF4444;">
                        <p style="color: #EF4444; font-weight: bold;">Error:</p>
                        <p>${data.error}</p>
                        ${data.sql ? `<div class="sql-block">${data.sql}</div>` : ''}
                    </div>
                `;
            }
        } catch (err) {
            document.getElementById(loaderId).innerHTML = `
                <div class="message-bubble" style="border-color: #EF4444;">
                    An unexpected error occurred.
                </div>
            `;
        }
        chat.scrollTop = chat.scrollHeight;
    });
});
