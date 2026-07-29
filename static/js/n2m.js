/**
 * N2M — interactive UI: theme toggle, back-to-top, copy link toast, nav shadow on scroll
 */
(function () {
  'use strict';

  // Expose early so base fallback script can detect main JS immediately.
  window.N2M_INLINE_ACTIONS_READY = true;

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

  // Row 2: hide when scrolling down, show when scrolling up
  var row2 = document.querySelector('.navbar-n2m-bbc .navbar-n2m-container > .n2m-nav-row2');
  if (row2) {
    var lastScrollY = window.scrollY;
    var threshold = 10;
    function onScrollRow2() {
      var current = window.scrollY;
      if (current <= 60) {
        row2.classList.remove('n2m-nav-row2-hidden');
      } else if (current > lastScrollY + threshold) {
        row2.classList.add('n2m-nav-row2-hidden');
      } else if (current < lastScrollY - threshold) {
        row2.classList.remove('n2m-nav-row2-hidden');
      }
      lastScrollY = current;
    }
    window.addEventListener('scroll', onScrollRow2, { passive: true });
  }

  function toAbsoluteUrl(url) {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    return window.location.origin.replace(/\/$/, '') + (url.charAt(0) === '/' ? url : '/' + url);
  }

  var INSTAGRAM_PROFILE_FALLBACK = 'https://www.instagram.com/next251media/';

  var SHARE_NETWORK_LABELS = {
    instagram: 'Instagram',
    linkedin: 'LinkedIn',
    facebook: 'Facebook',
    messenger: 'Messenger',
    whatsapp: 'WhatsApp',
    email: 'Email',
    threads: 'Threads',
    tiktok: 'TikTok',
    twitter: 'X (Twitter)',
  };

  function normalizeShareSummary(s) {
    if (!s) return '';
    return String(s).replace(/\r\n/g, '\n').replace(/\s+/g, ' ').trim();
  }

  /** Full multi-line caption for clipboard and most apps (title, summary, optional image line, URL, attribution). */
  function buildShareCaption(title, summary, url, imageUrl) {
    var parts = [];
    var t = (title || '').trim();
    if (t) parts.push(t);
    var sum = normalizeShareSummary(summary);
    if (sum.length > 520) sum = sum.slice(0, 517) + '…';
    if (sum) parts.push(sum);
    if (imageUrl) parts.push('Image: ' + toAbsoluteUrl(imageUrl));
    var abs = toAbsoluteUrl(url);
    if (abs) parts.push(abs);
    parts.push('— Next 251 Media');
    return parts.join('\n\n');
  }

  function twitterIntentTextAndUrl(caption, pageUrl, title) {
    var abs = toAbsoluteUrl(pageUrl);
    var lines = (caption || '').split(/\n+/).map(function (l) { return l.trim(); }).filter(Boolean);
    var out = [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (abs && line === abs) continue;
      if (line.indexOf('Image: ') === 0) continue;
      if (line === '— Next 251 Media') continue;
      out.push(line);
    }
    var text = out.join('\n\n').replace(/\s+/g, ' ').trim();
    var max = 235;
    if (!text) text = ((title || '') + '').trim();
    if (text.length > max) text = text.slice(0, max - 1) + '…';
    return { text: text, url: abs };
  }

  /** Sync copy in the same user-gesture tick (helps iOS Safari; async clipboard often drops text). */
  function copyPlainTextSync(text) {
    if (!text) return;
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;margin:0;padding:0;border:0;opacity:0;';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand('copy');
    } catch (e) { /* ignore */ }
    document.body.removeChild(ta);
  }

  function facebookQuoteText(title, summaryPlain) {
    var parts = [];
    var tit = (title || '').trim();
    if (tit) parts.push(tit);
    var sum = normalizeShareSummary(summaryPlain);
    if (sum) parts.push(sum.length > 480 ? sum.slice(0, 477) + '…' : sum);
    return parts.join('\n\n');
  }

  function shareUrlFor(network, url, title, opts) {
    opts = opts || {};
    var caption = opts.caption != null ? opts.caption : '';
    var summaryRaw = opts.summary != null ? opts.summary : '';
    var absUrl = toAbsoluteUrl(url);
    var u = encodeURIComponent(absUrl);
    var t = encodeURIComponent(title || document.title || '');
    var sumNorm = normalizeShareSummary(summaryRaw);

    if (network === 'linkedin') {
      var titEnc = encodeURIComponent((title || '').trim().slice(0, 200));
      var sumEnc = encodeURIComponent(sumNorm.slice(0, 400));
      return (
        'https://www.linkedin.com/shareArticle?mini=true&url=' +
        u +
        '&title=' +
        titEnc +
        '&summary=' +
        sumEnc +
        '&source=' +
        encodeURIComponent('Next 251 Media')
      );
    }
    if (network === 'facebook') {
      var quote = facebookQuoteText(title, summaryRaw);
      var q = quote ? encodeURIComponent(quote) : '';
      return 'https://www.facebook.com/sharer/sharer.php?u=' + u + (q ? '&quote=' + q : '');
    }
    if (network === 'messenger') return 'https://www.facebook.com/dialog/send?link=' + u + '&app_id=291494419107518&redirect_uri=' + u;
    if (network === 'whatsapp') {
      var wa = caption || ((title || '') + '\n\n' + absUrl);
      return 'https://api.whatsapp.com/send?text=' + encodeURIComponent(wa);
    }
    if (network === 'email') {
      var body = caption || ((title || '') + '\n\n' + absUrl);
      return 'mailto:?subject=' + t + '&body=' + encodeURIComponent(body);
    }
    if (network === 'threads') return 'https://www.threads.net/';
    if (network === 'instagram') {
      var ig = opts.instagramPostUrl != null ? String(opts.instagramPostUrl).trim() : '';
      if (ig && /^https?:\/\//i.test(ig)) return ig;
      return INSTAGRAM_PROFILE_FALLBACK;
    }
    if (network === 'tiktok') return 'https://www.tiktok.com/';
    if (network === 'twitter') {
      var tw = twitterIntentTextAndUrl(caption, absUrl, title);
      return 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(tw.text) + '&url=' + encodeURIComponent(tw.url);
    }
    return '';
  }

  function copyPlainText(text, toastMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () {
        if (toastMsg) showToast(toastMsg);
      }).catch(function () {
        fallbackCopyPlainText(text, toastMsg);
      });
    }
    fallbackCopyPlainText(text, toastMsg);
    return Promise.resolve();
  }

  function fallbackCopyPlainText(text, toastMsg) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      if (toastMsg) showToast(toastMsg);
    } catch (e) {
      showToast('Copy failed');
    }
    document.body.removeChild(ta);
  }

  // Single global share sheet (#n2m-share-global); each card only has a .web-share-btn trigger.
  (function initGlobalShare() {
    var globalWrap = document.getElementById('n2m-share-global');
    if (!globalWrap) return;
    var menu = globalWrap.querySelector('.n2m-share-menu');
    var backdrop = globalWrap.querySelector('.n2m-share-backdrop');
    var dataSource = globalWrap.querySelector('.n2m-share-data-source');
    var stepMain = globalWrap.querySelector('.n2m-share-step-main');
    var stepPrepare = globalWrap.querySelector('.n2m-share-step-prepare');
    var prepareText = globalWrap.querySelector('.n2m-share-prepare-text');
    var prepareName = globalWrap.querySelector('.n2m-share-prepare-network-name');
    var prepareOpen = globalWrap.querySelector('.n2m-share-prepare-open');
    var prepareCopy = globalWrap.querySelector('.n2m-share-prepare-copy');
    var prepareBack = globalWrap.querySelector('.n2m-share-prepare-back');
    var row = globalWrap.querySelector('.n2m-share-sheet-row');
    var prevBtn = globalWrap.querySelector('.n2m-share-scroll-prev');
    var nextBtn = globalWrap.querySelector('.n2m-share-scroll-next');
    if (!menu || !dataSource) return;

    function closeAllShare() {
      menu.setAttribute('hidden', 'hidden');
      if (backdrop) backdrop.setAttribute('hidden', 'hidden');
      if (stepPrepare) stepPrepare.setAttribute('hidden', 'hidden');
      if (stepMain) stepMain.removeAttribute('hidden');
      document.querySelectorAll('.web-share-btn').forEach(function (b) {
        b.setAttribute('aria-expanded', 'false');
      });
      document.querySelectorAll('.card-n2m.n2m-share-open').forEach(function (c) {
        c.classList.remove('n2m-share-open');
      });
      globalWrap.setAttribute('aria-hidden', 'true');
    }

    function updateShareScrollArrow() {
      if (!row) return;
      var hasMore = row.scrollWidth > row.clientWidth + 4;
      var atStart = row.scrollLeft <= 4;
      var atEnd = row.scrollLeft + row.clientWidth >= row.scrollWidth - 4;
      if (prevBtn) {
        if (hasMore) prevBtn.removeAttribute('hidden');
        else prevBtn.setAttribute('hidden', 'hidden');
        prevBtn.disabled = atStart;
      }
      if (nextBtn) {
        if (hasMore) nextBtn.removeAttribute('hidden');
        else nextBtn.setAttribute('hidden', 'hidden');
        nextBtn.disabled = !hasMore || atEnd;
      }
    }

    function updateShareScrollArrowAfterLayout() {
      updateShareScrollArrow();
      requestAnimationFrame(function () {
        updateShareScrollArrow();
        requestAnimationFrame(updateShareScrollArrow);
      });
    }

    function urlFromSource() {
      return toAbsoluteUrl(dataSource.getAttribute('data-url') || '');
    }

    document.querySelectorAll('.web-share-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var wasHidden = menu.hasAttribute('hidden');
        if (!wasHidden) {
          closeAllShare();
          return;
        }
        closeAllShare();
        dataSource.setAttribute('data-url', btn.getAttribute('data-url') || '');
        dataSource.setAttribute('data-title', btn.getAttribute('data-title') || '');
        dataSource.setAttribute('data-summary', btn.getAttribute('data-summary') || '');
        dataSource.setAttribute('data-image', btn.getAttribute('data-image') || '');
        dataSource.setAttribute('data-instagram-post-url', btn.getAttribute('data-instagram-post-url') || '');
        menu.removeAttribute('hidden');
        if (backdrop) backdrop.removeAttribute('hidden');
        btn.setAttribute('aria-expanded', 'true');
        var card = btn.closest('.card-n2m');
        if (card) card.classList.add('n2m-share-open');
        globalWrap.setAttribute('aria-hidden', 'false');
        updateShareScrollArrowAfterLayout();
      });
    });

    if (backdrop) {
      backdrop.addEventListener('click', function () {
        closeAllShare();
      });
    }
    if (prevBtn && row) {
      prevBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        row.scrollBy({ left: -220, behavior: 'smooth' });
      });
    }
    if (nextBtn && row) {
      nextBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        row.scrollBy({ left: 220, behavior: 'smooth' });
      });
    }
    if (row) {
      row.addEventListener('scroll', updateShareScrollArrow, { passive: true });
      if (!globalWrap.dataset.n2mShareResizeBound) {
        globalWrap.dataset.n2mShareResizeBound = '1';
        window.addEventListener('resize', updateShareScrollArrow);
      }
    }

    if (prepareBack && stepPrepare && stepMain) {
      prepareBack.addEventListener('click', function (ev) {
        ev.preventDefault();
        stepPrepare.setAttribute('hidden', 'hidden');
        stepMain.removeAttribute('hidden');
        updateShareScrollArrowAfterLayout();
      });
    }

    window.N2M_SHARE_V2 = true;

    menu.querySelectorAll('.n2m-share-item').forEach(function (item) {
      item.addEventListener('click', function (e) {
        e.preventDefault();
        var network = item.getAttribute('data-share-network') || '';
        var url = urlFromSource();
        var title = dataSource.getAttribute('data-title') || document.title || '';
        var summary = dataSource.getAttribute('data-summary') || '';
        var image = dataSource.getAttribute('data-image') || '';
        if (!url) return;

        if (network === 'copy') {
          fallbackCopy(url, item);
          closeAllShare();
          return;
        }

        var caption = buildShareCaption(title, summary, url, image);
        var label = SHARE_NETWORK_LABELS[network] || network;

        function openTargetFromPrepare() {
          var textNow = prepareText ? prepareText.value : caption;
          var summary = dataSource.getAttribute('data-summary') || '';
          var igPost = (dataSource.getAttribute('data-instagram-post-url') || '').trim();
          var payload = { caption: textNow, summary: summary, instagramPostUrl: igPost };

          function doOpenWindow() {
            var target = shareUrlFor(network, url, title, payload);
            if (network === 'email' && target) {
              window.location.href = target;
            } else if (target) {
              window.open(target, '_blank', 'noopener,noreferrer');
            }
            closeAllShare();
          }

          /* Mobile/tablet: OS share sheet can pass text + URL into Instagram and other apps. */
          var ua = typeof navigator !== 'undefined' ? navigator.userAgent || '' : '';
          var isCoarseTouch = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(pointer:coarse)').matches;
          var isMobileUa = /Android|iPhone|iPad|iPod|Mobile|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua);
          var useNativeShare = isMobileUa || isCoarseTouch;
          if (useNativeShare && typeof navigator !== 'undefined' && navigator.share) {
            var nativeFirst = ['instagram', 'threads', 'tiktok', 'facebook'].indexOf(network) !== -1;
            if (nativeFirst) {
              var pageAbs = toAbsoluteUrl(url);
              var igAbs = igPost && /^https?:\/\//i.test(igPost) ? igPost : '';
              var shareData = {
                title: (title || '').trim(),
                text: textNow,
                url: network === 'instagram' && igAbs ? igAbs : pageAbs,
              };
              if (!navigator.canShare || navigator.canShare(shareData)) {
                var p = navigator.share(shareData);
                if (p && typeof p.then === 'function') {
                  p.then(function () {
                    closeAllShare();
                  }).catch(function (err) {
                    if (err && err.name === 'AbortError') {
                      closeAllShare();
                      return;
                    }
                    doOpenWindow();
                  });
                  return;
                }
              }
            }
          }

          doOpenWindow();
        }

        if (stepMain && stepPrepare && prepareText && prepareName && prepareOpen && prepareCopy) {
          prepareText.value = caption;
          prepareName.textContent = label;
          prepareOpen.textContent = 'Open ' + label;
          prepareOpen.onclick = function () {
            openTargetFromPrepare();
          };
          prepareCopy.onclick = function () {
            copyPlainTextSync(prepareText.value);
            copyPlainText(prepareText.value, 'Caption copied');
          };
          stepMain.setAttribute('hidden', 'hidden');
          stepPrepare.removeAttribute('hidden');
          copyPlainTextSync(caption);
          copyPlainText(caption, 'Caption copied — paste in ' + label);
        } else {
          copyPlainTextSync(caption);
          copyPlainText(caption, 'Caption copied — paste in ' + label);
          var summary = dataSource.getAttribute('data-summary') || '';
          var igPost2 = (dataSource.getAttribute('data-instagram-post-url') || '').trim();
          var target = shareUrlFor(network, url, title, {
            caption: caption,
            summary: summary,
            instagramPostUrl: igPost2,
          });
          if (network === 'email' && target) {
            window.location.href = target;
          } else if (target) {
            window.open(target, '_blank', 'noopener,noreferrer');
          }
          closeAllShare();
        }
      });
    });
  })();

  document.addEventListener('click', function (e) {
    if (e.target && e.target.closest && e.target.closest('.n2m-share-menu')) return;
    if (e.target && e.target.closest && e.target.closest('.web-share-btn')) return;
    var g = document.getElementById('n2m-share-global');
    if (!g) return;
    var menu = g.querySelector('.n2m-share-menu');
    var backdrop = g.querySelector('.n2m-share-backdrop');
    var stepPrepare = g.querySelector('.n2m-share-step-prepare');
    var stepMain = g.querySelector('.n2m-share-step-main');
    if (menu) menu.setAttribute('hidden', 'hidden');
    if (backdrop) backdrop.setAttribute('hidden', 'hidden');
    if (stepPrepare) stepPrepare.setAttribute('hidden', 'hidden');
    if (stepMain) stepMain.removeAttribute('hidden');
    document.querySelectorAll('.web-share-btn[aria-expanded="true"]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
    document.querySelectorAll('.card-n2m.n2m-share-open').forEach(function (c) { c.classList.remove('n2m-share-open'); });
    g.setAttribute('aria-hidden', 'true');
  });

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

  var ajaxHeaders = {
    'X-Requested-With': 'XMLHttpRequest',
    Accept: 'application/json',
  };

  function withAjaxParam(url) {
    if (!url) return url;
    return url.indexOf('?') === -1 ? (url + '?ajax=1') : (url + '&ajax=1');
  }

  function applyLikeUi(link, liked, likeCount) {
    link.classList.toggle('n2m-action-active', !!liked);
    var countSpan = link.querySelector('.n2m-action-count');
    if (countSpan && typeof likeCount === 'number') {
      countSpan.textContent = String(likeCount);
    }
    var iconSvg = link.querySelector('.n2m-action-icon svg');
    if (iconSvg) {
      if (liked) {
        iconSvg.setAttribute('fill', 'currentColor');
        iconSvg.setAttribute('stroke', 'currentColor');
      } else {
        iconSvg.setAttribute('fill', 'none');
        iconSvg.setAttribute('stroke', 'currentColor');
      }
    }
  }

  function setSaveCountOnLink(link, saveCount) {
    if (!link) return;
    var n = Number(saveCount);
    if (!isFinite(n)) return;
    var text = String(Math.max(0, Math.round(n)));
    link.querySelectorAll('.n2m-action-count').forEach(function (span) {
      span.textContent = text;
    });
    link.setAttribute('data-save-count', text);
  }

  function applySaveUi(link, saved, saveCount) {
    link.classList.toggle('n2m-action-active', !!saved);
    link.setAttribute('aria-label', saved ? 'Unsave' : 'Save');
    var labelSpan = link.querySelector('.n2m-action-label');
    if (labelSpan) {
      labelSpan.textContent = saved ? 'Saved' : 'Save';
    }
    setSaveCountOnLink(link, saveCount);
    var iconSvg = link.querySelector('.n2m-action-icon svg');
    if (iconSvg) {
      if (saved) {
        iconSvg.setAttribute('fill', 'currentColor');
        iconSvg.setAttribute('stroke', 'currentColor');
      } else {
        iconSvg.setAttribute('fill', 'none');
        iconSvg.setAttribute('stroke', 'currentColor');
      }
    }
  }

  function parseSaveTargetFromHref(href) {
    if (!href) return '';
    try {
      var parsed = new URL(href, window.location.origin);
      var path = parsed.pathname.replace(/\/+$/, '');
      var m = path.match(/\/save-(article|review|newsletter)\/(\d+)$/i);
      if (!m) return '';
      return m[1].toLowerCase() + ':' + m[2];
    } catch (e) {
      return '';
    }
  }

  function saveLinksForTarget(targetKey, sourceLink) {
    var links = [];
    if (targetKey) {
      document.querySelectorAll('[data-n2m-save-key="' + targetKey + '"]').forEach(function (el) {
        links.push(el);
      });
      var parts = targetKey.split(':');
      if (parts.length === 2) {
        var segment = '/save-' + parts[0] + '/' + parts[1];
        document.querySelectorAll('a[href*="' + segment + '"]').forEach(function (el) {
          if (links.indexOf(el) === -1) links.push(el);
        });
      }
    }
    if (!links.length && sourceLink) {
      links.push(sourceLink);
    }
    return links;
  }

  function applySaveUiByTarget(sourceLink, saved, saveCount) {
    var sourceHref = sourceLink ? (sourceLink.getAttribute('href') || '') : '';
    var targetKey = parseSaveTargetFromHref(sourceHref);
    if (!targetKey && sourceLink) {
      targetKey = sourceLink.getAttribute('data-n2m-save-key') || '';
    }
    saveLinksForTarget(targetKey, sourceLink).forEach(function (link) {
      applySaveUi(link, saved, saveCount);
    });
  }

  function handleSaveClick(link) {
    var url = withAjaxParam(link.getAttribute('href'));
    if (!url) return;

    var countSpan = link.querySelector('.n2m-action-count');
    var currentCount = countSpan ? parseInt(countSpan.textContent, 10) || 0 : 0;
    var wasActive = link.classList.contains('n2m-action-active');
    var optimisticSaved = !wasActive;
    var optimisticCount = wasActive ? Math.max(0, currentCount - 1) : currentCount + 1;

    applySaveUiByTarget(link, optimisticSaved, optimisticCount);

    fetch(url, {
      method: 'GET',
      headers: ajaxHeaders,
      credentials: 'same-origin',
      cache: 'no-store',
    })
      .then(function (resp) {
        var ct = (resp.headers.get('content-type') || '').toLowerCase();
        if (resp.ok && ct.indexOf('application/json') !== -1) {
          return resp.json();
        }
        return null;
      })
      .then(function (data) {
        if (data && data.ok) {
          var serverCount = Number(data.save_count);
          var resolvedCount = isFinite(serverCount) ? serverCount : optimisticCount;
          applySaveUiByTarget(link, !!data.saved, resolvedCount);
          return;
        }
        applySaveUiByTarget(link, optimisticSaved, optimisticCount);
      })
      .catch(function () {
        applySaveUiByTarget(link, wasActive, currentCount);
      });
  }

  function shouldInterceptActionLink(link) {
    if (!link || link.tagName !== 'A') return false;
    var href = link.getAttribute('href') || '';
    if (!href || href.indexOf('/accounts/login/') !== -1) return false;
    return (
      href.indexOf('/like/') !== -1 ||
      href.indexOf('/save-') !== -1
    );
  }

  function renderUploadPreview(input) {
    if (!input || !input.id) return;
    var form = input.closest('form');
    if (!form) return;
    var preview = form.querySelector('[data-preview-for="' + input.id + '"]');
    if (!preview) return;

    preview.innerHTML = '';
    var files = Array.prototype.slice.call(input.files || []);
    if (!files.length) return;

    files.forEach(function (file) {
      var tile = document.createElement('div');
      tile.className = 'n2m-media-tile n2m-media-tile-preview';

      if (file.type && file.type.indexOf('image/') === 0) {
        var img = document.createElement('img');
        img.className = 'n2m-media-thumb';
        img.alt = file.name || 'Image preview';
        tile.appendChild(img);
        var reader = new FileReader();
        reader.onload = function (evt) {
          img.src = evt.target && evt.target.result ? evt.target.result : '';
        };
        reader.readAsDataURL(file);
      } else if (file.type && file.type.indexOf('video/') === 0) {
        tile.classList.add('n2m-media-tile-video');
        var label = document.createElement('span');
        label.className = 'n2m-media-tile-label';
        label.textContent = 'Video';
        tile.appendChild(label);
      } else {
        var txt = document.createElement('span');
        txt.className = 'n2m-media-tile-label';
        txt.textContent = 'File';
        tile.appendChild(txt);
      }

      preview.appendChild(tile);
    });
  }

  function initUploadPreviews() {
    var inputs = document.querySelectorAll('input[type="file"][multiple]');
    inputs.forEach(function (input) {
      if (input.closest('[data-n2m-instagram-upload]')) return;
      input.addEventListener('change', function () {
        renderUploadPreview(input);
      });
      renderUploadPreview(input);
    });
  }

  var INSTAGRAM_MAX_MB = 6;
  var INSTAGRAM_MAX_EXTRA = 6;

  function setInputFiles(input, files) {
    if (!input) return;
    var dt = new DataTransfer();
    var list = files || [];
    for (var i = 0; i < list.length; i++) {
      dt.items.add(list[i]);
    }
    input.files = dt.files;
  }

  function findClearCheckbox(form, baseName) {
    if (!form || !baseName) return null;
    return form.querySelector('input[type="checkbox"][name="' + baseName + '-clear"]');
  }

  function initInstagramMediaUpload() {
    document.querySelectorAll('[data-n2m-instagram-upload]').forEach(function (root) {
      var form = root.closest('form');
      if (!form) return;

      var coverImageName = root.getAttribute('data-cover-image-name') || '';
      var coverVideoName = root.getAttribute('data-cover-video-name') || '';
      var coverImageInput = document.getElementById(root.getAttribute('data-cover-image-input') || '');
      var coverVideoInput = document.getElementById(root.getAttribute('data-cover-video-input') || '');
      var extraImagesInput = document.getElementById(root.getAttribute('data-extra-images-input') || '');
      var extraVideosInput = document.getElementById(root.getAttribute('data-extra-videos-input') || '');
      var zone = root.querySelector('.n2m-instagram-upload-zone');
      var picker = root.querySelector('.n2m-instagram-picker');
      var grid = root.querySelector('.n2m-instagram-upload-grid');
      var statusEl = root.querySelector('.n2m-instagram-upload-status');
      var imageCountEl = root.querySelector('[data-instagram-count-images]');
      var videoCountEl = root.querySelector('[data-instagram-count-videos]');
      if (!zone || !picker || !grid || !coverImageInput || !coverVideoInput || !extraImagesInput || !extraVideosInput) {
        return;
      }

      var state = {
        coverImg: null,
        coverVid: null,
        extraImgs: [],
        extraVids: [],
        serverImgRemoved: false,
        serverVidRemoved: false,
      };

      var serverImgTile = root.querySelector('.n2m-instagram-server-tile[data-server-asset="cover-image"]');
      var serverVidTile = root.querySelector('.n2m-instagram-server-tile[data-server-asset="cover-video"]');

      function maxBytes() {
        return INSTAGRAM_MAX_MB * 1024 * 1024;
      }

      function validateFile(f) {
        if (!f || !f.size) return true;
        if (f.size > maxBytes()) {
          showToast('Each file must be ' + INSTAGRAM_MAX_MB + ' MB or smaller');
          return false;
        }
        return true;
      }

      function hasServerCoverImage() {
        return !!(serverImgTile && !state.serverImgRemoved);
      }

      function hasServerCoverVideo() {
        return !!(serverVidTile && !state.serverVidRemoved);
      }

      function effectiveHasCoverImage() {
        if (state.coverImg) return true;
        return hasServerCoverImage();
      }

      function effectiveHasCoverVideo() {
        if (state.coverVid) return true;
        return hasServerCoverVideo();
      }

      function syncClearCheckboxes() {
        var cImg = findClearCheckbox(form, coverImageName);
        var cVid = findClearCheckbox(form, coverVideoName);
        if (cImg) {
          if (state.serverImgRemoved && !state.coverImg) {
            cImg.checked = true;
          } else {
            cImg.checked = false;
          }
        }
        if (cVid) {
          if (state.serverVidRemoved && !state.coverVid) {
            cVid.checked = true;
          } else {
            cVid.checked = false;
          }
        }
      }

      function syncNativeFileInputs() {
        setInputFiles(coverImageInput, state.coverImg ? [state.coverImg] : []);
        setInputFiles(coverVideoInput, state.coverVid ? [state.coverVid] : []);
        setInputFiles(extraImagesInput, state.extraImgs);
        setInputFiles(extraVideosInput, state.extraVids);
        syncClearCheckboxes();
      }

      function removeStagedCover(kind) {
        if (kind === 'image') state.coverImg = null;
        if (kind === 'video') state.coverVid = null;
        renderGrid();
        syncNativeFileInputs();
      }

      function removeStagedExtra(kind, index) {
        if (kind === 'image' && index >= 0 && index < state.extraImgs.length) {
          state.extraImgs.splice(index, 1);
        }
        if (kind === 'video' && index >= 0 && index < state.extraVids.length) {
          state.extraVids.splice(index, 1);
        }
        renderGrid();
        syncNativeFileInputs();
      }

      function addIncomingFiles(fileList) {
        var arr = Array.prototype.slice.call(fileList || []);
        var changed = false;
        arr.forEach(function (f) {
          if (!validateFile(f)) return;
          var t = (f.type || '').toLowerCase();
          if (t.indexOf('image/') === 0) {
            if (!effectiveHasCoverImage()) {
              state.coverImg = f;
              changed = true;
              return;
            }
            if (state.extraImgs.length < INSTAGRAM_MAX_EXTRA) {
              state.extraImgs.push(f);
              changed = true;
            } else {
              showToast('You can add at most ' + INSTAGRAM_MAX_EXTRA + ' gallery images.');
            }
          } else if (t.indexOf('video/') === 0) {
            if (!effectiveHasCoverVideo()) {
              state.coverVid = f;
              changed = true;
              return;
            }
            if (state.extraVids.length < INSTAGRAM_MAX_EXTRA) {
              state.extraVids.push(f);
              changed = true;
            } else {
              showToast('You can add at most ' + INSTAGRAM_MAX_EXTRA + ' gallery videos.');
            }
          } else {
            showToast('Skipped a file (use images or videos only).');
          }
        });
        if (changed) {
          renderGrid();
          syncNativeFileInputs();
        }
      }

      function makeRemoveBtn(ariaLabel) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'n2m-instagram-remove';
        b.setAttribute('aria-label', ariaLabel || 'Remove');
        b.innerHTML = '&times;';
        return b;
      }

      function renderGrid() {
        grid.innerHTML = '';
        var hintParts = [];
        if (state.coverImg) hintParts.push('1 new cover image');
        if (state.coverVid) hintParts.push('1 new cover video');
        if (state.extraImgs.length) hintParts.push(state.extraImgs.length + ' gallery image(s)');
        if (state.extraVids.length) hintParts.push(state.extraVids.length + ' gallery video(s)');
        if (statusEl) {
          statusEl.textContent = hintParts.length ? 'Ready to upload: ' + hintParts.join(', ') + '.' : '';
        }
        if (imageCountEl) {
          imageCountEl.textContent = 'Images ' + state.extraImgs.length + '/' + INSTAGRAM_MAX_EXTRA;
        }
        if (videoCountEl) {
          videoCountEl.textContent = 'Videos ' + state.extraVids.length + '/' + INSTAGRAM_MAX_EXTRA;
        }

        function addTile(file, badge, onRemove) {
          var tile = document.createElement('div');
          tile.className = 'n2m-media-tile n2m-media-tile-preview n2m-instagram-staged-tile';
          var badgeEl = document.createElement('span');
          badgeEl.className = 'n2m-instagram-badge n2m-instagram-badge-staged';
          badgeEl.textContent = badge;
          tile.appendChild(badgeEl);
          var rm = makeRemoveBtn('Remove');
          rm.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            onRemove();
          });
          tile.appendChild(rm);
          if (file.type && file.type.indexOf('image/') === 0) {
            var img = document.createElement('img');
            img.className = 'n2m-media-thumb';
            img.alt = file.name || '';
            tile.appendChild(img);
            var reader = new FileReader();
            reader.onload = function (evt) {
              img.src = evt.target && evt.target.result ? evt.target.result : '';
            };
            reader.readAsDataURL(file);
          } else {
            tile.classList.add('n2m-media-tile-video');
            var label = document.createElement('span');
            label.className = 'n2m-media-tile-label';
            label.textContent = 'Video';
            tile.appendChild(label);
          }
          grid.appendChild(tile);
        }

        if (state.coverImg) {
          addTile(state.coverImg, 'Cover', function () {
            removeStagedCover('image');
          });
        }
        if (state.coverVid) {
          addTile(state.coverVid, 'Cover', function () {
            removeStagedCover('video');
          });
        }
        state.extraImgs.forEach(function (f, i) {
          addTile(f, 'Gallery', function () {
            removeStagedExtra('image', i);
          });
        });
        state.extraVids.forEach(function (f, i) {
          addTile(f, 'Gallery', function () {
            removeStagedExtra('video', i);
          });
        });

        var addTile = document.createElement('button');
        addTile.type = 'button';
        addTile.className = 'n2m-media-tile n2m-instagram-add-tile';
        addTile.setAttribute('aria-label', 'Add more media');
        addTile.innerHTML = '<span class="n2m-instagram-add-plus">+</span>';
        addTile.addEventListener('click', function () {
          picker.click();
        });
        grid.appendChild(addTile);
      }

      root.querySelectorAll('.n2m-instagram-server-tile .n2m-instagram-remove').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          var tile = btn.closest('.n2m-instagram-server-tile');
          if (!tile) return;
          var kind = tile.getAttribute('data-server-asset') || '';
          tile.style.display = 'none';
          if (kind === 'cover-image') state.serverImgRemoved = true;
          if (kind === 'cover-video') state.serverVidRemoved = true;
          syncNativeFileInputs();
        });
      });

      picker.addEventListener('change', function () {
        addIncomingFiles(picker.files);
        picker.value = '';
      });

      ['dragenter', 'dragover'].forEach(function (ev) {
        zone.addEventListener(ev, function (e) {
          e.preventDefault();
          e.stopPropagation();
          zone.classList.add('n2m-instagram-upload-zone-active');
        });
      });
      zone.addEventListener('dragleave', function (e) {
        e.preventDefault();
        if (!zone.contains(e.relatedTarget)) zone.classList.remove('n2m-instagram-upload-zone-active');
      });
      zone.addEventListener('drop', function (e) {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('n2m-instagram-upload-zone-active');
        if (e.dataTransfer && e.dataTransfer.files) addIncomingFiles(e.dataTransfer.files);
      });

      zone.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          picker.click();
        }
      });

      renderGrid();
      syncNativeFileInputs();
    });
  }

  // Inline like / save: fetch JSON from Django (no redirect, no full page reload)
  function initInlineActions() {
    // Signal that primary inline action handlers are active.
    window.N2M_INLINE_ACTIONS_READY = true;

    // Global delegated handler: catches action links even if classes differ on some templates.
    document.addEventListener(
      'click',
      function (e) {
        var link = e.target && e.target.closest ? e.target.closest('a[href]') : null;
        if (!shouldInterceptActionLink(link)) return;
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
      },
      true
    );

    document.querySelectorAll('.n2m-action-like').forEach(function (btn) {
      var href = btn.getAttribute('href') || '';
      if (!href || href.indexOf('/accounts/login/') !== -1) {
        return;
      }
      btn.addEventListener('click', function (e) {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
          return;
        }
        e.preventDefault();
        var link = this;
        var url = withAjaxParam(link.getAttribute('href'));
        if (!url) return;

        var countSpan = link.querySelector('.n2m-action-count');
        var currentCount = countSpan ? parseInt(countSpan.textContent, 10) || 0 : 0;
        var wasActive = link.classList.contains('n2m-action-active');

        fetch(url, {
          method: 'GET',
          headers: ajaxHeaders,
          credentials: 'same-origin',
        })
          .then(function (resp) {
            var ct = (resp.headers.get('content-type') || '').toLowerCase();
            if (resp.ok && ct.indexOf('application/json') !== -1) {
              return resp.json();
            }
            return null;
          })
          .then(function (data) {
            if (data && data.ok) {
              applyLikeUi(link, data.liked, data.like_count);
              return;
            }
            // Fallback if server returned HTML (old deploy): local toggle
            var nextCount = wasActive ? Math.max(0, currentCount - 1) : currentCount + 1;
            applyLikeUi(link, !wasActive, nextCount);
          })
          .catch(function () {});
      });
    });

    document.addEventListener('click', function (e) {
      var link = e.target && e.target.closest ? e.target.closest('a.n2m-action-save[href*="/save-"]') : null;
      if (!link) return;
      var href = link.getAttribute('href') || '';
      if (!href || href.indexOf('/accounts/login/') !== -1) return;
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      e.stopPropagation();
      handleSaveClick(link);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initInlineActions();
      initInstagramMediaUpload();
      initUploadPreviews();
    });
  } else {
    initInlineActions();
    initInstagramMediaUpload();
    initUploadPreviews();
  }
})();
