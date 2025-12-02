/**
 * Voice Agent - Radial Menu Module (Advanced)
 * Smooth elastic animations with magnetic pointer tracking
 */

// Menu configuration - single source of truth
const CONFIG = {
    radius: 140,              // Distance from center to items
    itemSize: 56,             // Size of menu items
    animDuration: 500,        // Base animation duration in ms
    staggerDelay: 60,         // Delay between each item animation
    pointerLerp: 0.18,        // Pointer interpolation speed (0-1, lower = smoother)
    magneticRadius: 80,       // Distance at which items "pull" the pointer
    magneticStrength: 0.4,    // How strong the magnetic pull is
};

// Menu actions configuration
const MENU_ACTIONS = [
    { 
        id: 'music', 
        icon: 'M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z',
        label: 'Play Music',
        action: () => sendCommand('Play some music')
    },
    { 
        id: 'weather', 
        icon: 'M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.79 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z',
        label: 'Weather',
        action: () => sendCommand("What's the weather like?")
    },
    { 
        id: 'search', 
        icon: 'M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
        label: 'Web Search',
        action: () => promptSearch()
    },
    { 
        id: 'memory', 
        icon: 'M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z',
        label: 'Memory',
        action: () => sendCommand('What do you remember about me?')
    },
    { 
        id: 'time', 
        icon: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
        label: 'Time & Date',
        action: () => sendCommand('What time is it?')
    },
    { 
        id: 'joke', 
        icon: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z',
        label: 'Tell a Joke',
        action: () => sendCommand('Tell me a joke')
    }
];

// State
let isOpen = false;
let menuEl = null;
let toggleEl = null;
let pointerEl = null;
let linesEl = null;
let descriptionEl = null;
let sendMessageFn = null;
let activeItem = null;

// Pointer animation state
let pointerTarget = { x: 0, y: 0 };
let pointerCurrent = { x: 0, y: 0 };
let pointerAnimationFrame = null;
let items = [];

/**
 * Initialize the radial menu
 * @param {Function} sendMessage - Function to send messages via WebSocket
 */
export function initRadialMenu(sendMessage) {
    sendMessageFn = sendMessage;
    
    // Cache elements
    menuEl = document.getElementById('radialMenu');
    toggleEl = document.getElementById('radialToggle');
    pointerEl = document.getElementById('radialPointer');
    descriptionEl = document.getElementById('radialDescription');
    linesEl = menuEl?.querySelector('.radial-lines');
    
    if (!menuEl || !toggleEl) {
        console.warn('Radial menu elements not found');
        return;
    }
    
    // Position items and cache their data
    items = positionItems();
    
    // Setup event listeners
    setupEventListeners();
    
    // Add ripple effect to items
    addRippleEffects();
    
    console.log('Radial menu initialized with', items.length, 'items');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Toggle button
    toggleEl.addEventListener('change', (e) => {
        isOpen = e.target.checked;
        if (isOpen) {
            animateOpen();
        } else {
            animateClose();
        }
    });
    
    // Menu items
    const items = document.querySelectorAll('.radial-item');
    items.forEach((item) => {
        item.addEventListener('click', (e) => handleItemClick(e));
        
        // Hover effect - move pointer toward item and show description
        item.addEventListener('mouseenter', () => {
            if (isOpen) {
                movePointerToItem(item);
                showDescription(item);
            }
        });
        
        // Hide description on mouse leave
        item.addEventListener('mouseleave', () => {
            if (isOpen) {
                hideDescription();
            }
        });
        
        // Add keyboard support
        item.setAttribute('tabindex', '0');
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleItemClick(e);
            }
        });
    });
    
    // Close on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen) {
            closeMenu();
        }
    });
    
    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (isOpen && !menuEl.contains(e.target)) {
            closeMenu();
        }
    });
}

/**
 * Position items in a circle and cache all data
 * Returns array of item data for efficient access
 */
function positionItems() {
    const itemElements = document.querySelectorAll('.radial-item');
    const count = itemElements.length;
    const startAngle = -90; // Start from top (-90 degrees = 12 o'clock)
    const angleStep = 360 / count;
    
    const itemsData = [];
    
    itemElements.forEach((item, index) => {
        const angle = startAngle + (index * angleStep);
        const radian = (angle * Math.PI) / 180;
        
        // Calculate position on circle
        const x = Math.cos(radian) * CONFIG.radius;
        const y = Math.sin(radian) * CONFIG.radius;
        
        // Store all data on element and in array
        const itemData = {
            element: item,
            x,
            y,
            angle,
            radian,
            index
        };
        
        item.dataset.x = x;
        item.dataset.y = y;
        item.dataset.angle = angle;
        item.dataset.index = index;
        
        // Apply position using CSS custom properties (for smooth animation)
        item.style.setProperty('--item-x', `${x}px`);
        item.style.setProperty('--item-y', `${y}px`);
        
        console.log(`Item ${index}: angle=${angle}°, x=${x.toFixed(1)}, y=${y.toFixed(1)}`);
        
        itemsData.push(itemData);
    });
    
    console.log(`Positioned ${itemsData.length} items in a circle with radius ${CONFIG.radius}px`);
    
    return itemsData;
}

/**
 * Linear interpolation helper
 */
function lerp(start, end, factor) {
    return start + (end - start) * factor;
}

/**
 * Calculate distance between two points
 */
function distance(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Update pointer position with smooth interpolation
 * Uses requestAnimationFrame for 60fps smooth motion
 */
function updatePointer() {
    if (!pointerEl || !isOpen) {
        if (pointerAnimationFrame) {
            cancelAnimationFrame(pointerAnimationFrame);
            pointerAnimationFrame = null;
        }
        return;
    }
    
    // Smoothly interpolate current position toward target
    pointerCurrent.x = lerp(pointerCurrent.x, pointerTarget.x, CONFIG.pointerLerp);
    pointerCurrent.y = lerp(pointerCurrent.y, pointerTarget.y, CONFIG.pointerLerp);
    
    // Apply transform
    pointerEl.style.transform = `translate(calc(-50% + ${pointerCurrent.x}px), calc(-50% + ${pointerCurrent.y}px))`;
    
    // Continue animation loop
    pointerAnimationFrame = requestAnimationFrame(updatePointer);
}

/**
 * Start pointer animation loop
 */
function startPointerAnimation() {
    if (!pointerAnimationFrame) {
        pointerAnimationFrame = requestAnimationFrame(updatePointer);
    }
}

/**
 * Stop pointer animation loop
 */
function stopPointerAnimation() {
    if (pointerAnimationFrame) {
        cancelAnimationFrame(pointerAnimationFrame);
        pointerAnimationFrame = null;
    }
}

/**
 * Set pointer target position with optional magnetic attraction
 * @param {number} targetX - Target X coordinate
 * @param {number} targetY - Target Y coordinate
 * @param {boolean} magnetic - Whether to apply magnetic snap
 */
function setPointerTarget(targetX, targetY, magnetic = true) {
    if (!magnetic) {
        pointerTarget.x = targetX;
        pointerTarget.y = targetY;
        return;
    }
    
    // Find nearest item within magnetic radius
    let nearestItem = null;
    let nearestDist = Infinity;
    
    for (const itemData of items) {
        const dist = distance(targetX, targetY, itemData.x, itemData.y);
        if (dist < CONFIG.magneticRadius && dist < nearestDist) {
            nearestDist = dist;
            nearestItem = itemData;
        }
    }
    
    // If close to an item, pull pointer toward it
    if (nearestItem) {
        const pullFactor = 1 - (nearestDist / CONFIG.magneticRadius);
        const magnetPull = CONFIG.magneticStrength * pullFactor;
        
        pointerTarget.x = lerp(targetX, nearestItem.x, magnetPull);
        pointerTarget.y = lerp(targetY, nearestItem.y, magnetPull);
    } else {
        pointerTarget.x = targetX;
        pointerTarget.y = targetY;
    }
}

/**
 * Move pointer indicator toward an item on hover
 */
function movePointerToItem(item) {
    if (!pointerEl || !isOpen) return;
    
    const itemData = items.find(i => i.element === item);
    if (!itemData) return;
    
    // Move pointer 70% of the way toward the item
    const pointerRatio = 0.7;
    setPointerTarget(itemData.x * pointerRatio, itemData.y * pointerRatio, false);
    
    // Highlight the connecting line
    highlightLine(itemData.index);
}

/**
 * Show description tooltip for an item
 */
function showDescription(item) {
    if (!descriptionEl || !isOpen) return;
    
    const action = item.dataset.action;
    const menuAction = MENU_ACTIONS.find(a => a.id === action);
    
    if (menuAction && menuAction.label) {
        descriptionEl.textContent = menuAction.label;
        descriptionEl.classList.add('visible');
    }
}

/**
 * Hide description tooltip
 */
function hideDescription() {
    if (!descriptionEl) return;
    descriptionEl.classList.remove('visible');
}

/**
 * Highlight a specific connecting line
 */
function highlightLine(index) {
    if (!linesEl) return;
    
    const lines = linesEl.querySelectorAll('.radial-line');
    lines.forEach((line, i) => {
        if (i === index) {
            line.classList.add('active');
        } else {
            line.classList.remove('active');
        }
    });
}

/**
 * Reset pointer to center
 */
function resetPointer() {
    setPointerTarget(0, 0, false);
    
    // Clear line highlights
    if (linesEl) {
        const lines = linesEl.querySelectorAll('.radial-line');
        lines.forEach(line => line.classList.remove('active'));
    }
}

/**
 * Handle menu item click
 */
function handleItemClick(e) {
    e.stopPropagation();
    
    const item = e.currentTarget;
    const action = item.dataset.action;
    
    // Visual feedback
    setActiveItem(item);
    
    // Find and execute action
    const menuAction = MENU_ACTIONS.find(a => a.id === action);
    if (menuAction && menuAction.action) {
        // Add pulse animation
        item.classList.add('activated');
        setTimeout(() => item.classList.remove('activated'), 300);
        
        // Execute action after brief delay for visual feedback
        setTimeout(() => {
            menuAction.action();
            closeMenu();
        }, 150);
    }
}

/**
 * Set active item visual state
 */
function setActiveItem(item) {
    // Remove previous active state
    if (activeItem) {
        activeItem.classList.remove('active');
    }
    
    activeItem = item;
    item.classList.add('active');
}

/**
 * Animate menu open with staggered elastic effect
 */
function animateOpen() {
    menuEl.classList.add('open');
    
    const itemElements = document.querySelectorAll('.radial-item');
    itemElements.forEach((item, index) => {
        // Elastic stagger timing
        item.style.transitionDelay = `${index * CONFIG.staggerDelay}ms`;
    });
    
    // Start smooth pointer animation
    startPointerAnimation();
    
    // Emit custom event
    menuEl.dispatchEvent(new CustomEvent('radialmenu:opened'));
}

/**
 * Animate menu close with reverse stagger
 */
function animateClose() {
    const itemElements = document.querySelectorAll('.radial-item');
    const count = itemElements.length;
    
    itemElements.forEach((item, index) => {
        // Reverse stagger for close
        item.style.transitionDelay = `${(count - 1 - index) * (CONFIG.staggerDelay * 0.7)}ms`;
    });
    
    menuEl.classList.remove('open');
    
    // Reset pointer to center smoothly
    resetPointer();
    
    // Hide description
    hideDescription();
    
    // Stop pointer animation after transition
    setTimeout(() => {
        stopPointerAnimation();
        pointerCurrent = { x: 0, y: 0 };
        pointerTarget = { x: 0, y: 0 };
    }, CONFIG.animDuration);
    
    // Clear active item
    if (activeItem) {
        activeItem.classList.remove('active');
        activeItem = null;
    }
    
    // Emit custom event
    menuEl.dispatchEvent(new CustomEvent('radialmenu:closed'));
}

/**
 * Close the menu
 */
export function closeMenu() {
    if (toggleEl) {
        toggleEl.checked = false;
        isOpen = false;
        animateClose();
    }
}

/**
 * Open the menu
 */
export function openMenu() {
    if (toggleEl) {
        toggleEl.checked = true;
        isOpen = true;
        animateOpen();
    }
}

/**
 * Toggle the menu
 */
export function toggleMenu() {
    if (isOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

/**
 * Add ripple effect to menu items
 */
function addRippleEffects() {
    const items = document.querySelectorAll('.radial-item');
    
    items.forEach(item => {
        item.addEventListener('mousedown', (e) => {
            const rect = item.getBoundingClientRect();
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            ripple.style.left = `${e.clientX - rect.left}px`;
            ripple.style.top = `${e.clientY - rect.top}px`;
            item.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
}

/**
 * Send a command/message
 */
function sendCommand(text) {
    if (sendMessageFn) {
        sendMessageFn({
            type: 'text_message',
            text: text
        });
        
        // Also add to conversation UI
        addUserMessage(text);
    }
}

/**
 * Add user message to conversation (if available)
 */
function addUserMessage(text) {
    const conversation = document.getElementById('conversation');
    if (!conversation) return;
    
    const msgEl = document.createElement('div');
    msgEl.className = 'message user';
    msgEl.innerHTML = `<p>${escapeHtml(text)}</p>`;
    conversation.appendChild(msgEl);
    conversation.scrollTop = conversation.scrollHeight;
}

/**
 * Prompt for search query
 */
function promptSearch() {
    const query = prompt('What would you like to search for?');
    if (query && query.trim()) {
        sendCommand(`Search the web for: ${query.trim()}`);
    }
}

/**
 * Escape HTML for safe display
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Check if menu is currently open
 */
export function isMenuOpen() {
    return isOpen;
}
