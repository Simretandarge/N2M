/**
 * N2M — interactive UI: theme toggle, back-to-top, copy link toast, nav shadow on scroll
 */
(function () {
  'use strict';

  var THEME_KEY = 'n2m-theme';
  var THEME_DARK = 'dark';
  var THEME_LIGHT = 'light';

  function getStoredTheme() {
    try {
      return localStorage.getItem(THEME_KEY) || THEME_DARK;
    } catch (e) {
      return THEME_DARK;
    }
  }
  function setTheme(theme) {
    var html = document.documentElement;
    if (!html) return;
    html.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (e) {}
    var btn = document.getElementById('themeToggle');
    if (btn) {
      var iconDark = btn.querySelector('.n2m-theme-icon-dark');
      var iconLight = btn.querySelector('.n2m-theme-icon-light');
      if (theme === THEME_LIGHT) {
        if (iconDark) iconDark.classList.add('d-none');
        if (iconLight) iconLight.classList.remove('d-none');
      } else {
        if (iconDark) iconDark.classList.remove('d-none');
        if (iconLight) iconLight.classList.add('d-none');
      }
    }
  }
  function initTheme() {
    setTheme(getStoredTheme());
  }
  function toggleTheme() {
    var current = getStoredTheme();
    setTheme(current === THEME_DARK ? THEME_LIGHT : THEME_DARK);
  }

  initTheme();
  var themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
  }

  // Back to top: show after scroll, smooth scroll on click
  var backToTop = document.getElementById('backToTop');
  if (backToTop) {
    function toggleBackToTop() {
      if (window.scrollY > 400) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    }
    window.addEventListener('scroll', toggleBackToTop, { passive: true });
    toggleBackToTop();
    backToTop.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Left account menu (BBC-style): closed by default; open only when user clicks the menu button
  var accountMenu = document.getElementById('n2mAccountMenu');
  if (accountMenu) {
    accountMenu.addEventListener('click', function (e) {
      var link = e.target.closest('a[href]');
      if (link && link.getAttribute('href') && link.getAttribute('href') !== '#') {
        var offcanvas = bootstrap.Offcanvas.getInstance(accountMenu);
        if (offcanvas) offcanvas.hide();
      }
    });
  }

  // Navbar: add shadow when scrolled
  var mainNav = document.getElementById('mainNav');
  if (mainNav) {
    function navScroll() {
      if (window.scrollY > 20) {
        mainNav.classList.add('navbar-scrolled');
      } else {
        mainNav.classList.remove('navbar-scrolled');
      }
    }
    window.addEventListener('scroll', navScroll, { passive: true });
    navScroll();
  }

  // Copy link buttons: copy URL and show toast
  document.querySelectorAll('.copy-link-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var url = this.getAttribute('data-url');
      if (!url) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          showToast('Link copied to clipboard');
        }).catch(function () {
          fallbackCopy(url, btn);
        });
      } else {
        fallbackCopy(url, btn);
      }
    });
  });

  function fallbackCopy(url, btn) {
    var input = document.createElement('input');
    input.value = url;
    input.setAttribute('readonly', '');
    input.style.position = 'absolute';
    input.style.left = '-9999px';
    document.body.appendChild(input);
    input.select();
    try {
      document.execCommand('copy');
      showToast('Link copied to clipboard');
    } catch (e) {
      showToast('Copy failed');
    }
    document.body.removeChild(input);
  }

  function showToast(message) {
    var existing = document.getElementById('n2m-toast');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.id = 'n2m-toast';
    toast.className = 'n2m-toast';
    toast.setAttribute('role', 'alert');
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(function () {
      toast.classList.add('visible');
    });
    setTimeout(function () {
      toast.classList.remove('visible');
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, 2500);
  }
})();
