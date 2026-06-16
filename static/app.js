document.addEventListener('DOMContentLoaded', () => {
  // Animate progress bars
  requestAnimationFrame(() => {
    setTimeout(() => {
      document.querySelectorAll('.bar-fill[data-width]').forEach(el => {
        el.style.width = el.dataset.width + '%';
      });
    }, 80);
  });

  // Auto-dismiss flash messages after 5 seconds
  const flashes = document.querySelectorAll('.flash');
  if (flashes.length) {
    setTimeout(() => {
      flashes.forEach(el => {
        el.style.transition = 'opacity 0.4s, transform 0.4s';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-4px)';
        setTimeout(() => el.remove(), 400);
      });
    }, 5000);
  }

  // Fade-in page content
  const main = document.querySelector('.main-inner');
  if (main) {
    main.style.opacity = '0';
    main.style.transform = 'translateY(6px)';
    main.style.transition = 'opacity .3s ease, transform .3s ease';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        main.style.opacity = '1';
        main.style.transform = 'translateY(0)';
      });
    });
  }
});
