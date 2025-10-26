const form = document.getElementById('chat-form');
const chatWindow = document.getElementById('chat-window');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userInput = document.getElementById('user-input').value;
    appendMessage('User', userInput);
    document.getElementById('user-input').value = '';
    // Send query to backend
    const response = await fetch('/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: userInput})
    });
    const data = await response.json();
    appendMessage('Bot', data.summary);
});

function appendMessage(sender, message) {
    const div = document.createElement('div');
    div.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
