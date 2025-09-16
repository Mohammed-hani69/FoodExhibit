// Food Exhibition Platform - Main JavaScript
// Socket.IO initialization and client-side functionality

let socket;
let currentChatExhibitorId = null;
let calendar = null;

// Initialize Socket.IO when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeSocketIO();
    initializeCalendar();
    setupEventHandlers();
});

// Socket.IO Functions
function initializeSocketIO() {
    socket = io();
    
    // Handle connection events
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
    
    // Handle chat messages
    socket.on('chat_message', function(data) {
        displayChatMessage(data);
    });
    
    socket.on('user_joined_chat', function(data) {
        console.log('User joined chat:', data.username);
    });
    
    socket.on('user_left_chat', function(data) {
        console.log('User left chat:', data.username);
    });
}

// Chat Functions
function showChat(exhibitorId) {
    currentChatExhibitorId = exhibitorId;
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.style.display = 'block';
        joinChatRoom(exhibitorId);
        loadChatHistory(exhibitorId);
    }
}

function hideChat() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.style.display = 'none';
        if (currentChatExhibitorId) {
            leaveChatRoom(currentChatExhibitorId);
            currentChatExhibitorId = null;
        }
    }
}

function joinChatRoom(exhibitorId) {
    socket.emit('join_chat', {
        exhibitor_id: exhibitorId
    });
}

function leaveChatRoom(exhibitorId) {
    socket.emit('leave_chat', {
        exhibitor_id: exhibitorId
    });
}

function sendChatMessage() {
    const messageInput = document.getElementById('chat-message-input');
    const message = messageInput.value.trim();
    
    if (message && currentChatExhibitorId) {
        socket.emit('send_message', {
            exhibitor_id: currentChatExhibitorId,
            message: message
        });
        
        messageInput.value = '';
    }
}

function displayChatMessage(data) {
    const chatBody = document.querySelector('.chat-body');
    if (!chatBody) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${data.sender_type}`;
    
    const timestamp = new Date(data.timestamp).toLocaleTimeString('ar-EG', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    messageElement.innerHTML = `
        <div class="message-content">${data.message}</div>
        <div class="message-time">${timestamp}</div>
    `;
    
    chatBody.appendChild(messageElement);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function loadChatHistory(exhibitorId) {
    // Clear current chat
    const chatBody = document.querySelector('.chat-body');
    if (chatBody) {
        chatBody.innerHTML = '';
    }
    
    // Load chat history via AJAX
    fetch(`/api/chat-history/${exhibitorId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                data.messages.forEach(message => {
                    displayChatMessage(message);
                });
            }
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
        });
}

// Favorite Functions
function toggleFavoriteExhibitor(exhibitorId) {
    const favoriteBtn = document.getElementById('favorite-btn');
    
    fetch(`/toggle-favorite-exhibitor/${exhibitorId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateFavoriteButton(favoriteBtn, data.action);
            showNotification(
                data.action === 'added' ? 'تم إضافة العارض للمفضلة' : 'تم إزالة العارض من المفضلة',
                'success'
            );
        } else {
            showNotification('حدث خطأ في العملية', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('حدث خطأ في الاتصال', 'error');
    });
}

function toggleFavoriteProduct(productId) {
    fetch(`/toggle-favorite-product/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Find the product favorite button
            const productCard = document.querySelector(`[data-product-id="${productId}"]`);
            if (productCard) {
                const favoriteBtn = productCard.querySelector('.favorite-btn');
                if (favoriteBtn) {
                    updateFavoriteButton(favoriteBtn, data.action);
                }
            }
            
            showNotification(
                data.action === 'added' ? 'تم إضافة المنتج للمفضلة' : 'تم إزالة المنتج من المفضلة',
                'success'
            );
        } else {
            showNotification('حدث خطأ في العملية', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('حدث خطأ في الاتصال', 'error');
    });
}

function removeFavoriteExhibitor(exhibitorId) {
    if (confirm('هل أنت متأكد من إزالة هذا العارض من المفضلة؟')) {
        toggleFavoriteExhibitor(exhibitorId);
        
        // Remove the card from the page after a delay
        setTimeout(() => {
            const exhibitorCard = document.querySelector(`[data-exhibitor-id="${exhibitorId}"]`);
            if (exhibitorCard) {
                exhibitorCard.remove();
            }
        }, 1000);
    }
}

function removeFavoriteProduct(productId) {
    if (confirm('هل أنت متأكد من إزالة هذا المنتج من المفضلة؟')) {
        toggleFavoriteProduct(productId);
        
        // Remove the card from the page after a delay
        setTimeout(() => {
            const productCard = document.querySelector(`[data-product-id="${productId}"]`);
            if (productCard) {
                productCard.remove();
            }
        }, 1000);
    }
}

function updateFavoriteButton(button, action) {
    if (!button) return;
    
    if (action === 'added') {
        button.classList.add('favorited');
        button.innerHTML = '<i class="fas fa-heart fa-2x"></i><div class="mt-2">مُضاف للمفضلة</div>';
    } else {
        button.classList.remove('favorited');
        button.innerHTML = '<i class="fas fa-heart fa-2x"></i><div class="mt-2">إضافة للمفضلة</div>';
    }
}

// Navigation Functions
function visitExhibitor(exhibitorId) {
    window.location.href = `/exhibitor/${exhibitorId}`;
}

function viewProduct(productId) {
    // Show product modal or navigate to product page
    showProductModal(productId);
}

function showProductModal(productId) {
    // Create and show product modal
    fetch(`/api/product/${productId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayProductModal(data.product);
            }
        })
        .catch(error => {
            console.error('Error loading product:', error);
            showNotification('حدث خطأ في تحميل المنتج', 'error');
        });
}

function displayProductModal(product) {
    const modalHtml = `
        <div class="modal fade" id="productModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${product.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                ${product.image_url ? 
                                    `<img src="${product.image_url}" class="img-fluid rounded" alt="${product.name}">` :
                                    '<div class="bg-light d-flex align-items-center justify-content-center" style="height: 300px;"><i class="fas fa-utensils fa-4x text-muted"></i></div>'
                                }
                            </div>
                            <div class="col-md-6">
                                <h4>${product.name}</h4>
                                <p class="text-muted">${product.description}</p>
                                <h5 class="text-primary">${product.price} ${product.currency}</h5>
                                <div class="mt-3">
                                    <button onclick="toggleFavoriteProduct(${product.id})" class="btn btn-outline-danger">
                                        <i class="fas fa-heart"></i> إضافة للمفضلة
                                    </button>
                                    <button onclick="visitExhibitor(${product.exhibitor_id})" class="btn btn-primary ms-2">
                                        زيارة العارض
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal
    const existingModal = document.getElementById('productModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
}

// Calendar Functions
function initializeCalendar() {
    const calendarEl = document.getElementById('appointment-calendar');
    if (!calendarEl) return;
    
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'ar',
        direction: 'rtl',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: '/api/available-slots/' + getExhibitorIdFromUrl(),
        selectable: true,
        selectMirror: true,
        select: function(info) {
            showBookingModal(info);
        },
        eventClick: function(info) {
            showSlotDetails(info.event);
        }
    });
    
    calendar.render();
}

function getExhibitorIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    return pathParts[pathParts.length - 1];
}

function showBookingModal(info) {
    const modalHtml = `
        <div class="modal fade" id="bookingModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">حجز موعد</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="booking-form">
                            <div class="mb-3">
                                <label class="form-label">التاريخ</label>
                                <input type="text" class="form-control" value="${info.startStr}" readonly>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">الوقت</label>
                                <select class="form-select" id="time-slot" required>
                                    <option value="">اختر الوقت المناسب</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">ملاحظات (اختياري)</label>
                                <textarea class="form-control" id="booking-notes" rows="3"></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إلغاء</button>
                        <button type="button" class="btn btn-primary" onclick="confirmBooking()">تأكيد الحجز</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal
    const existingModal = document.getElementById('bookingModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Load available time slots for the selected date
    loadAvailableTimeSlots(info.startStr);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('bookingModal'));
    modal.show();
}

function loadAvailableTimeSlots(date) {
    const exhibitorId = getExhibitorIdFromUrl();
    
    fetch(`/api/available-slots/${exhibitorId}?date=${date}`)
        .then(response => response.json())
        .then(data => {
            const timeSlotSelect = document.getElementById('time-slot');
            timeSlotSelect.innerHTML = '<option value="">اختر الوقت المناسب</option>';
            
            if (data.status === 'success' && data.slots.length > 0) {
                data.slots.forEach(slot => {
                    const option = document.createElement('option');
                    option.value = slot.id;
                    option.textContent = `${slot.start_time} - ${slot.end_time} (${slot.duration_minutes} دقيقة)`;
                    timeSlotSelect.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'لا توجد مواعيد متاحة في هذا التاريخ';
                timeSlotSelect.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error loading time slots:', error);
            showNotification('حدث خطأ في تحميل المواعيد المتاحة', 'error');
        });
}

function confirmBooking() {
    const slotId = document.getElementById('time-slot').value;
    const notes = document.getElementById('booking-notes').value;
    
    if (!slotId) {
        showNotification('يرجى اختيار الوقت المناسب', 'warning');
        return;
    }
    
    fetch('/book-appointment', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            slot_id: slotId,
            notes: notes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification(data.message, 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('bookingModal'));
            modal.hide();
            
            // Refresh calendar
            if (calendar) {
                calendar.refetchEvents();
            }
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error booking appointment:', error);
        showNotification('حدث خطأ في حجز الموعد', 'error');
    });
}

// Utility Functions
function showNotification(message, type = 'info') {
    const alertClass = type === 'success' ? 'alert-success' : 
                     type === 'error' ? 'alert-danger' : 
                     type === 'warning' ? 'alert-warning' : 'alert-info';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            if (alert.textContent.includes(message)) {
                const alertInstance = bootstrap.Alert.getOrCreateInstance(alert);
                alertInstance.close();
            }
        });
    }, 5000);
}

function setupEventHandlers() {
    // Chat message input handler
    const chatInput = document.getElementById('chat-message-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }
    
    // Chat header toggle
    const chatHeader = document.querySelector('.chat-header');
    if (chatHeader) {
        chatHeader.addEventListener('click', function() {
            const chatContainer = document.querySelector('.chat-container');
            if (chatContainer.style.display === 'none' || !chatContainer.style.display) {
                showChat(currentChatExhibitorId || getExhibitorIdFromUrl());
            } else {
                hideChat();
            }
        });
    }
}

// Export functions for global access
window.toggleFavoriteExhibitor = toggleFavoriteExhibitor;
window.toggleFavoriteProduct = toggleFavoriteProduct;
window.visitExhibitor = visitExhibitor;
window.viewProduct = viewProduct;
window.removeFavoriteExhibitor = removeFavoriteExhibitor;
window.removeFavoriteProduct = removeFavoriteProduct;
window.showChat = showChat;
window.hideChat = hideChat;
window.sendChatMessage = sendChatMessage;