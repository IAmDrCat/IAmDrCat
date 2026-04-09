// Data derived from product catalog and user specifications
const productsData = {
    wave: {
        id: 'wave',
        name: 'Wave Executor',
        variants: [
            { name: 'Wave 1 Day Key', price: 2.49 },
            { name: 'Wave 7 Day Key', price: 5.99 },
            { name: 'Wave 30 Day Key', price: 18.99 },
            { name: 'Wave 90 Day Key', price: 39.99 }
        ]
    },
    volt: {
        id: 'volt',
        name: 'Volt Executor',
        variants: [
            { name: 'Volt 7 Day Key', price: 5.99 },
            { name: 'Volt 7 Day Farmer Key', price: 9.99 },
            { name: 'Volt 30 Day Key', price: 19.99 },
            { name: 'Volt 90 Day Key', price: 49.99 }
        ]
    },
    potassium: {
        id: 'potassium',
        name: 'Potassium Executor',
        variants: [
            // Updated to $24 based on user's spec
            { name: 'Potassium Executor Lifetime', price: 24.00 }
        ]
    },
    matcha: {
        id: 'matcha',
        name: 'Matcha Executor',
        variants: [
            { name: 'Matcha Lifetime', price: 9.99 },
            { name: 'Matcha Beta Lifetime', price: 26.99 }
        ]
    }
};

// State
let currentProduct = 'wave';
let currentVariantIndex = 0;

// DOM Elements
const productSelector = document.getElementById('product-selector');
const variantSelect = document.getElementById('variant-select');
const checkRef = document.getElementById('check-ref');
const checkCode = document.getElementById('check-code');

const dispName = document.getElementById('display-product-name');
const dispOrigPrice = document.getElementById('display-original-price');
const dispDiscAmount = document.getElementById('display-discount-amount');
const dispDiscPercent = document.getElementById('display-discount-percent');
const dispFinalPrice = document.getElementById('display-final-price');
const btnBuy = document.getElementById('btn-buy');

// Initialize UI
function init() {
    renderProductButtons();
    renderVariants();
    calculate();

    // Event Listeners
    variantSelect.addEventListener('change', (e) => {
        currentVariantIndex = e.target.value;
        calculate();
    });

    checkRef.addEventListener('change', calculate);
    checkCode.addEventListener('change', calculate);
}

// Render Product Selection Buttons
function renderProductButtons() {
    productSelector.innerHTML = '';
    Object.values(productsData).forEach(prod => {
        const isSelected = prod.id === currentProduct;
        const btn = document.createElement('button');
        
        btn.className = 'btn-product';
        if (isSelected) {
            btn.classList.add('active');
        }
        
        btn.innerText = prod.name.split(' ')[0]; // Just Wave, Volt, Potassium
        
        btn.onclick = () => {
            currentProduct = prod.id;
            currentVariantIndex = 0; // reset variant when switching product
            renderProductButtons();
            renderVariants();
            calculate();
        };
        productSelector.appendChild(btn);
    });
}

// Render Variant Dropdown based on selected product
function renderVariants() {
    variantSelect.innerHTML = '';
    const variants = productsData[currentProduct].variants;
    
    variants.forEach((v, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.text = `${v.name} - $${v.price.toFixed(2)}`;
        variantSelect.appendChild(option);
    });
    variantSelect.value = currentVariantIndex;
}

// Main Calculation Logic
function calculate() {
    const product = productsData[currentProduct];
    const variant = product.variants[currentVariantIndex];
    
    const origPrice = variant.price;
    let discountPercent = 0;

    if (checkRef.checked) discountPercent += 5;
    if (checkCode.checked) discountPercent += 5;

    // Stackable additive discounts
    const discountAmount = origPrice * (discountPercent / 100);
    const finalPrice = origPrice - discountAmount;

    // Update DOM Display
    dispName.innerText = variant.name;
    dispOrigPrice.innerText = `$${origPrice.toFixed(2)}`;
    dispDiscPercent.innerText = discountPercent;
    
    dispDiscAmount.innerText = `-$${discountAmount.toFixed(2)}`;
    
    if (discountAmount > 0) {
        dispDiscAmount.style.color = 'var(--success)';
    } else {
        dispDiscAmount.style.color = 'var(--text)';
    }
    
    dispFinalPrice.innerText = `$${finalPrice.toFixed(2)}`;
    
    // Update Buy Now link dynamically
    btnBuy.href = `https://robloxcheatz.com/product?id=${currentProduct}&ref=lowa`;
}

// Utility: Copy to clipboard function for the UI buttons
function copyText(text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHtml = btnElement.innerHTML;
        
        // Show success state
        btnElement.innerHTML = `
            <span>Copied!</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
        btnElement.classList.add('copied-state');
        
        // Reset after 2 seconds
        setTimeout(() => {
            btnElement.innerHTML = originalHtml;
            btnElement.classList.remove('copied-state');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}

// Run on load
document.addEventListener('DOMContentLoaded', init);
