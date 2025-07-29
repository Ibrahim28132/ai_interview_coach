document.addEventListener('DOMContentLoaded', function() {
    const setupForm = document.getElementById('setup-form');
    const chatSection = document.getElementById('chat-section');
    const setupSection = document.getElementById('setup-section');
    const chatContainer = document.getElementById('chat-container');
    const responseInput = document.getElementById('response-input');
    const sendBtn = document.getElementById('send-btn');
    let socket = null;
    let interviewActive = false;

    // Add message to chat
    function addMessage(text, sender = 'system', type = 'text') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        if (type === 'question') {
            messageDiv.innerHTML = `
                <div class="message-header">Interview Question</div>
                <div class="message-content">${text}</div>
            `;
        } else if (type === 'response') {
            messageDiv.innerHTML = `
                <div class="message-header">Your Answer</div>
                <div class="message-content">${text}</div>
            `;
        } else if (type === 'feedback') {
            messageDiv.innerHTML = `
                <div class="message-header">Feedback</div>
                <div class="message-content">${text}</div>
            `;
        } else {
            messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Initialize WebSocket connection
    function initWebSocket() {
        const clientId = 'client-' + Math.random().toString(36).substr(2, 9);
        socket = new WebSocket(`ws://${window.location.host}/ws/${clientId}`);

        socket.onopen = function() {
            interviewActive = true;
            addMessage('Connected to interview session');

            // Get form data
            const interviewType = document.getElementById('interview-type').value;
            const experienceLevel = document.getElementById('experience-level').value;
            const resumeUpload = document.getElementById('resume-upload');

            // Read resume if uploaded
            const fileReader = new FileReader();
            fileReader.onload = function() {
                const message = {
                    type: 'start_interview',
                    interview_type: interviewType,
                    level: experienceLevel,
                    resume_text: fileReader.result || '',
                    use_voice: false // Explicitly disable voice input
                };
                socket.send(JSON.stringify(message));
            };

            if (resumeUpload.files.length > 0) {
                fileReader.readAsText(resumeUpload.files[0]);
            } else {
                fileReader.onload(); // Trigger with empty resume
            }
        };

        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log('Received:', data);

            if (data.type === 'question') {
                addMessage(data.question, 'bot', 'question');
                // Focus input field when new question arrives
                responseInput.focus();
            }
            else if (data.type === 'feedback') {
                let feedbackText = data.feedback.feedback;
                if (data.feedback.metrics) {
                    feedbackText += '<br><br><strong>Metrics:</strong><br>';
                    for (const [metric, value] of Object.entries(data.feedback.metrics)) {
                        feedbackText += `${metric.replace('_', ' ')}: ${value}/10<br>`;
                    }
                }
                addMessage(feedbackText, 'bot', 'feedback');
            }
            else if (data.type === 'summary') {
                showInterviewComplete(data.summary);
            }
            else if (data.type === 'ack') {
                // Acknowledge response was received
                console.log('Response acknowledged by server');
            }
        };

        socket.onerror = function(error) {
            addMessage(`Connection error: ${error.message || 'Unknown error'}`, 'error');
        };

        socket.onclose = function(event) {
            if (interviewActive && event.code !== 1000) {
                addMessage('Connection lost - please refresh to continue', 'error');
            }
        };
    }

    // Show interview completion message
    function showInterviewComplete(summary) {
        const completionDiv = document.createElement('div');
        completionDiv.className = 'interview-complete';

        completionDiv.innerHTML = `
            <div class="completion-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M22 11.08V12C21.9988 14.1564 21.3005 16.2547 20.0093 17.9818C18.7182 19.709 16.9033 20.9725 14.8354 21.5839C12.7674 22.1953 10.5573 22.1219 8.53447 21.3746C6.51168 20.6273 4.78465 19.2461 3.61096 17.4371C2.43727 15.628 1.87979 13.4881 2.02168 11.3363C2.16356 9.18455 2.99721 7.13631 4.39828 5.49706C5.79935 3.85781 7.69279 2.71537 9.79619 2.24013C11.8996 1.7649 14.1003 1.98232 16.07 2.86" stroke="#4CAF50" stroke-width="2" stroke-linecap="round"/>
                    <path d="M22 4L12 14.01L9 11.01" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>Interview Completed</span>
            </div>
            <div class="summary-content">
                <div class="summary-score">Your Score: <strong>${summary.score}/100</strong></div>
                <div class="summary-overview">${summary.overview}</div>
                <div class="completion-footer">
                    Refresh the page to start a new interview
                </div>
            </div>
        `;

        chatContainer.appendChild(completionDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Disable input after completion
        responseInput.disabled = true;
        sendBtn.disabled = true;
        responseInput.placeholder = 'Interview completed - refresh to start new';
        interviewActive = false;
    }

    // Form submission handler
    setupForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Show chat and hide setup
        setupSection.classList.add('hidden');
        chatSection.classList.remove('hidden');
        responseInput.focus();

        // Initialize WebSocket connection
        initWebSocket();
    });

    // Send response handler
    function sendResponse() {
        const response = responseInput.value.trim();
        if (response && socket && socket.readyState === WebSocket.OPEN && interviewActive) {
            addMessage(response, 'user', 'response');
            socket.send(JSON.stringify({
                type: 'response',
                response: response,
                is_text_response: true // Explicitly mark as text response
            }));
            responseInput.value = '';
            responseInput.focus();
        }
    }

    // Event listeners
    sendBtn.addEventListener('click', sendResponse);
    responseInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendResponse();
        }
    });
});