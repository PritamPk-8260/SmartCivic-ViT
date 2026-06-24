document.addEventListener('DOMContentLoaded', function() {
    
    const loginForm = document.querySelector('form');

    loginForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        // Use FormData to easily send the form's data
        const formData = new FormData(loginForm);

        try {
            const response = await fetch('/login', {
                method: 'POST',
                body: formData
            });
            
            // The server will handle redirection, so we just follow it
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                // If not redirected, it means there was an error. 
                // We reload the page to show the flashed error message.
                window.location.reload();
            }

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during login.');
        }
    });
});