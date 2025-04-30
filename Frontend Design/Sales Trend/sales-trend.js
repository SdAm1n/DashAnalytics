document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('isLoggedIn') !== 'true') {
        window.location.href = '../auth/login.html';
        return;
    }

    const setupImageUpload = () => {
        document.querySelectorAll('.upload-placeholder').forEach(placeholder => {
            const input = placeholder.querySelector('.image-upload-input');
            const targetId = input.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);

            placeholder.addEventListener('click', function(e) {
                if (e.target !== input) {
                    input.click();
                }
            });

            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(event) {
                        targetElement.src = event.target.result;
                        targetElement.style.display = 'block';
                        placeholder.style.display = 'none';
                        
                        localStorage.setItem(targetId, event.target.result);
                    };
                    reader.readAsDataURL(file);
                }
            });
        });

        document.querySelectorAll('.product-image').forEach(img => {
            const savedImage = localStorage.getItem(img.id);
            if (savedImage) {
                img.src = savedImage;
                img.style.display = 'block';
                img.nextElementSibling.style.display = 'none';
            }
        });
    };

    const setupLogout = () => {
        document.querySelector('.logout').addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('isLoggedIn');
            window.location.href = '../auth/login.html';
        });
    };

    const setupMenuItems = () => {
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', function() {
                if (!this.classList.contains('logout') && !this.classList.contains('active')) {
                    document.querySelectorAll('.menu-item').forEach(i => {
                        i.classList.remove('active');
                    });
                    this.classList.add('active');
                }
            });
        });
    };

    const updateNotificationBadge = () => {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
          //  const notificationCount = ;
            badge.textContent = notificationCount;
            badge.style.display = notificationCount > 0 ? 'flex' : 'none';
        }
    };

    const setupClearButtons = () => {
        document.querySelectorAll('.product-image-container').forEach(container => {
            const clearBtn = document.createElement('button');
            clearBtn.className = 'clear-image-btn';
            clearBtn.innerHTML = '<i class="fas fa-times"></i>';
            clearBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const img = container.querySelector('.product-image');
                const placeholder = container.querySelector('.upload-placeholder');
                const input = container.querySelector('.image-upload-input');
                
                img.src = '';
                img.style.display = 'none';
                placeholder.style.display = 'flex';
                input.value = '';
                localStorage.removeItem(img.id);
                clearBtn.style.display = 'none';
            });
            
            container.appendChild(clearBtn);
            
            container.addEventListener('mouseenter', function() {
                const img = this.querySelector('.product-image');
                if (img.style.display === 'block') {
                    clearBtn.style.display = 'flex';
                }
            });
            
            container.addEventListener('mouseleave', function() {
                clearBtn.style.display = 'none';
            });
        });
    };

    setupImageUpload();
    setupLogout();
    setupMenuItems();
    updateNotificationBadge();
    setupClearButtons();
});