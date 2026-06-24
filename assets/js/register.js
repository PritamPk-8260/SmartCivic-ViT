document.addEventListener('DOMContentLoaded', function() {
    
    const registerForm = document.querySelector('form');

    registerForm.addEventListener('submit', async function(event) {
        event.preventDefault(); 

        const name = document.getElementById('nameInput').value;
        const email = document.getElementById('emailInput').value;
        const password = document.getElementById('passwordInput').value;
        const confirmPassword = document.getElementById('confirmPasswordInput').value;

        // --- Frontend Validation ---
        if (!name || !email || !password) {
            alert("Please fill out all fields.");
            return;
        }
        if (password !== confirmPassword) {
            alert("Error: Passwords do not match!");
            return;
        }

        // --- Send data to backend ---
        // We use FormData to easily send the form's data
        const formData = new FormData(registerForm);

        try {
            const response = await fetch('/register', {
                method: 'POST',
                body: formData
            });
            
            // The server will handle redirection, so we just follow it
            if (response.redirected) {
                window.location.href = response.url;
            }

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during registration.');
        }
    });
});