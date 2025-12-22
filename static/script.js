/*const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

registerBtn.addEventListener('click', () => {
    container.classList.add("active");
});

loginBtn.addEventListener('click', () => {
    container.classList.remove("active");
});*/

// Get elements
const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

// Show Sign Up panel
registerBtn.addEventListener('click', () => {
    container.classList.add("active"); // slide to sign-up
});

// Show Sign In panel
loginBtn.addEventListener('click', () => {
    container.classList.remove("active"); // slide to sign-in
});
