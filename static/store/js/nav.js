(function () {
    var triggers = document.querySelectorAll('.mega-nav-trigger, .filter-cat-trigger');
    var mobileToggle = document.getElementById('mobileNavToggle');
    var mobileClose = document.getElementById('mobileNavClose');
    var backdrop = document.getElementById('mobileNavBackdrop');
    var megaNav = document.getElementById('megaNav');

    function closeAllPanels() {
        document.querySelectorAll('.mega-nav-item.open, .filter-cat-item.open').forEach(function (item) {
            item.classList.remove('open');
            var t = item.querySelector('.mega-nav-trigger, .filter-cat-trigger');
            if (t) t.setAttribute('aria-expanded', 'false');

            // Reset any league/team drill-down back to the league list
            var leagueScreen = item.querySelector('.nav-screen-leagues');
            var teamScreen = item.querySelector('.nav-screen-teams');
            if (leagueScreen) leagueScreen.hidden = false;
            if (teamScreen) teamScreen.hidden = true;
        });
    }

    triggers.forEach(function (trigger) {
        if (trigger.tagName === 'A') return;
        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            var item = trigger.closest('.mega-nav-item, .filter-cat-item');
            if (!item) return;
            var isOpen = item.classList.contains('open');
            closeAllPanels();
            if (!isOpen) {
                item.classList.add('open');
                trigger.setAttribute('aria-expanded', 'true');
            }
        });
    });

            document.addEventListener('click', function (e) {
            if (megaNav && megaNav.classList.contains('mobile-open')) return; // drawer handles its own closing
            if (!e.target.closest('.mega-nav-item, .filter-cat-item')) {
                closeAllPanels();
            }
        });
    function openMobileNav() {
        if (!megaNav) return;
        megaNav.classList.add('mobile-open');
        if (backdrop) backdrop.classList.add('active');
        if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'true');
        document.body.classList.add('nav-locked');
    }

    function closeMobileNav() {
        if (!megaNav) return;
        megaNav.classList.remove('mobile-open');
        if (backdrop) backdrop.classList.remove('active');
        if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('nav-locked');
        closeAllPanels();
    }

    if (mobileToggle) mobileToggle.addEventListener('click', openMobileNav);
    if (mobileClose) mobileClose.addEventListener('click', closeMobileNav);
    if (backdrop) backdrop.addEventListener('click', closeMobileNav);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeAllPanels();
            closeMobileNav();
        }
    });

    // League -> teams drill-down inside each mega-nav dropdown
    document.querySelectorAll('.mega-nav-item').forEach(function (item) {
        var leagueScreen = item.querySelector('.nav-screen-leagues');
        var teamScreen = item.querySelector('.nav-screen-teams');
        var backBtn = item.querySelector('.team-back');

        item.querySelectorAll('.league-item').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                var idx = btn.dataset.leagueIndex;
                item.querySelectorAll('.team-group').forEach(function (g) {
                    g.hidden = g.dataset.leagueIndex !== idx;
                });
                leagueScreen.hidden = true;
                teamScreen.hidden = false;
            });
        });

        if (backBtn) {
            backBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                teamScreen.hidden = true;
                leagueScreen.hidden = false;
            });
        }
    });
})();

// ---------- Hero slideshow ----------
(function () {
    var hero = document.getElementById('heroImage');
    if (!hero) return;

    var slides = hero.querySelectorAll('.hero-slide');
    var dots = hero.querySelectorAll('.hero-dot');
    if (slides.length < 2) return;

    var current = 0;
    setInterval(function () {
        slides[current].classList.remove('active');
        if (dots[current]) dots[current].classList.remove('active');

        current = (current + 1) % slides.length;

        slides[current].classList.add('active');
        if (dots[current]) dots[current].classList.add('active');
    }, 3500);
})();