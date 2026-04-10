document.addEventListener("DOMContentLoaded", () => {
    
    // We add an artificial delay to allow the beautiful loader 
    // text animation (Bodoni Moda font with fade/blur) to play out.
    // The animation takes 2.8s total in CSS.
    
    setTimeout(() => {
        // Start fading out the loader background
        const loader = document.querySelector('.loader');
        loader.style.opacity = '0';
        
        // Wait for the opacity transition to finish (it's 1.2s in CSS)
        setTimeout(() => {
            // Remove from DOM flow and unlock scroll
            loader.style.display = 'none';
            document.body.style.overflow = 'auto'; // allow scrolling natively if content expands
            
            // Reveal main content shell
            const content = document.querySelector('.content');
            content.style.opacity = '1';

            // Trigger staggered entry animations on the UI elements
            
            // Nav links drop down elegantly
            document.querySelectorAll('.nav-link').forEach((el, index) => {
                el.classList.add('fade-in-down');
                // Calculate dynamic delay based on order
                el.style.animationDelay = `${0.3 + (index * 0.15)}s`;
            });

            // Hamburger menu button drop
            const menuBtn = document.querySelector('.menu-btn');
            menuBtn.classList.add('fade-in-down');
            menuBtn.style.animationDelay = `0.6s`;

            // Hero section lifts up gently
            document.querySelector('.hero-title').classList.add('fade-in-up', 'delay-1');
            document.querySelector('.hero-subtitle').classList.add('fade-in-up', 'delay-2');
            
            // Footer fades in last
            document.querySelector('.footer').classList.add('fade-in', 'delay-4');

        }, 1200); 
    }, 2800); 
});
