document.getElementById('signupForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (email && username && password) {
        
        localStorage.setItem('tempEmail', email);
        localStorage.setItem('tempUsername', username);
        
        
        window.location.href = 'login.html'; 
        
        localStorage.setItem('signupSuccess', 'true');
    }
});


document.getElementById('loginForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (email && password) {
       
        const tempEmail = localStorage.getItem('tempEmail');
        const isNewUser = tempEmail && tempEmail === email;
        
        if (isNewUser) {
            
            localStorage.setItem('userEmail', email);
            localStorage.removeItem('tempEmail');
        }
      
     
        localStorage.setItem('isLoggedIn', 'true');
        
        window.location.href = '../dashboard/index.html';
    }
});