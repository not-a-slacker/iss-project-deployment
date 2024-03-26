document.addEventListener('DOMContentLoaded', function() {
    const confirmPasswordInput = document.getElementById('confirm-password');
    const confirmPasswordCheck = document.getElementById('confirm-password-check');

    confirmPasswordInput.addEventListener('input', function() {
        const password = document.getElementById('password').value;
        const confirmPassword = confirmPasswordInput.value;

        if (confirmPassword.length === 0) {
            confirmPasswordCheck.innerHTML = '';
            return;
        }

        if (password === confirmPassword) {
            confirmPasswordCheck.innerHTML = '&#10004;';
            confirmPasswordCheck.style.color = 'green';
        } else {
            confirmPasswordCheck.innerHTML = '&#9888;';
            confirmPasswordCheck.style.color = 'red';
        }
    });
});

