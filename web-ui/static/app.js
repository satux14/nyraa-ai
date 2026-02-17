(function () {
  const AUTH_TOKEN_KEY = 'nyraa_token';
  const AUTH_ROLE_KEY = 'nyraa_role';

  function getToken() { return sessionStorage.getItem(AUTH_TOKEN_KEY); }
  function getRole() { return sessionStorage.getItem(AUTH_ROLE_KEY); }
  function setSession(token, role) {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token);
    sessionStorage.setItem(AUTH_ROLE_KEY, role);
  }
  function clearSession() {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    sessionStorage.removeItem(AUTH_ROLE_KEY);
  }

  function showLogin() {
    var loginSection = document.getElementById('login-section');
    var appSection = document.getElementById('app-section');
    var adminView = document.getElementById('admin-view');
    if (loginSection) loginSection.classList.remove('hidden');
    if (appSection) appSection.classList.add('hidden');
    if (adminView) adminView.classList.add('hidden');
  }

  function showApp(role) {
    var loginSection = document.getElementById('login-section');
    var appSection = document.getElementById('app-section');
    var adminView = document.getElementById('admin-view');
    if (loginSection) loginSection.classList.add('hidden');
    if (appSection) appSection.classList.remove('hidden');
    if (adminView) adminView.classList.add('hidden');
    var badge = document.getElementById('user-badge');
    if (badge) badge.textContent = role === 'admin' ? 'Admin' : 'Guest';
    var viewAllLink = document.getElementById('view-all-link');
    var adminCustomerRow = document.getElementById('admin-customer-row');
    if (viewAllLink) viewAllLink.classList.toggle('hidden', role !== 'admin');
    if (adminCustomerRow) adminCustomerRow.classList.toggle('hidden', role !== 'admin');
  }

  function showAdminView() {
    document.getElementById('app-section').classList.add('hidden');
    document.getElementById('admin-view').classList.remove('hidden');
    loadAdminAnalyses();
  }

  function hideAdminView() {
    document.getElementById('admin-view').classList.add('hidden');
    document.getElementById('app-section').classList.remove('hidden');
  }

  const SKIN_TYPE_INFO = {
    Oily: 'Skin tends to produce more sebum; can look shiny and pores may be more visible. Benefits from oil-control and gentle, non-comedogenic cleansing.',
    Dry: 'Skin produces less natural oil and may feel tight or flaky. Needs hydration and nourishing ingredients to support the barrier.',
    Combination: 'Some areas (e.g. T-zone) are oilier while others are drier. Care often targets balance and zone-specific needs.',
    Normal: 'Balanced oil and moisture; generally few sensitivity or breakout issues. Maintenance focuses on gentle cleansing and protection.',
  };
  const ACNE_LEVEL_INFO = {
    Low: 'Few or occasional blemishes; minor congestion. Light exfoliation and consistent cleansing are usually enough.',
    Moderate: 'Regular breakouts or visible congestion. Professional treatments and targeted products can help manage and prevent flare-ups.',
    High: 'Frequent or widespread breakouts. A structured treatment plan and professional guidance are recommended.',
  };
  const DARK_CIRCLE_INFO = {
    Low: 'Under-eye area is even with cheek tone. Maintenance with gentle care is usually enough.',
    Moderate: 'Some darkness under the eyes. A targeted eye serum or brightening treatment can help.',
    High: 'Noticeable under-eye darkness. Consider caffeine-based or brightening eye treatments and adequate rest.',
  };
  const FACE_SHAPE_INFO = {
    Oval: 'Balanced proportions; many styles and cuts suit this shape. You can experiment with different looks.',
    Round: 'Softer angles and similar width/height. Layered cuts and volume on top can add definition and length.',
    Square: 'Strong jaw and forehead. Softer layers or curls can balance the angles and add softness.',
    Oblong: 'Longer face with similar width. Soft layers or side-swept styles can add width and balance.',
    Heart: 'Wider forehead, narrower chin. Chin-length or layered styles can balance the silhouette.',
    Diamond: 'Wider cheekbones, narrower forehead and chin. Styles that add width at forehead or chin work well.',
  };
  const SERVICE_INFO = {
    'Acne Control Facial': 'Deep-cleans and treats congestion; helps reduce breakouts and calm inflammation.',
    'Hydrating Facial': 'Restores moisture and supports the skin barrier; ideal for dry or dehydrated skin.',
    'Under-Eye Brightening Treatment': 'Targets under-eye darkness and puffiness for a fresher look.',
    'Layer Cut': 'Adds movement and structure; works well for round face shapes by creating length and definition.',
    'Soft Curl Styling': 'Adds softness and flow; balances stronger facial angles for a more relaxed look.',
    'Soft Layers / Side-Swept Styling': 'Adds width and balance for oblong face shapes.',
    'Chin-Length or Layered Cut': 'Balances a wider forehead and narrower chin.',
    'Styles to Add Width at Forehead or Chin': 'Complements diamond face shape by softening cheek prominence.',
  };
  const PRODUCT_INFO = {
    'Salicylic Cleanser': 'Helps clear pores and reduce oil and breakouts; suitable for oily or acne-prone skin.',
    'Vitamin C Serum': 'Supports brightness and protection; helps with dryness and uneven tone.',
    'Caffeine Eye Serum': 'Helps reduce under-eye darkness and puffiness.',
  };

  var FACE_SHAPE_INDICES = { forehead: 10, chin: 152, jawLeft: 234, jawRight: 454 };
  var LEGEND_BY_MODE = {
    skin: 'Face mesh points used for skin analysis across the face.',
    shape: 'Highlighted: jaw width and face height points used for face shape.',
    recommendations: 'Face shape and skin analysis inform your recommendations.',
  };

  const fileInput = document.getElementById('file');
  const analyzeBtn = document.getElementById('analyze');
  const previewSection = document.getElementById('preview');
  const previewImg = document.getElementById('preview-img');
  const landmarksCanvas = document.getElementById('landmarks-canvas');
  const landmarksLegend = document.getElementById('landmarks-legend');
  const resultsPreviewImg = document.getElementById('results-preview-img');
  const resultsLandmarksCanvas = document.getElementById('results-landmarks-canvas');
  const resultsLandmarksLegend = document.getElementById('results-landmarks-legend');
  const loadingSection = document.getElementById('loading');
  const errorSection = document.getElementById('error');
  const errorMessage = document.getElementById('error-message');
  const resultsSection = document.getElementById('results');

  var lastLandmarks = [];
  var currentTabMode = 'skin';
  var adminLandmarks = [];
  var adminCurrentTabMode = 'skin';

  document.addEventListener('DOMContentLoaded', function () {
    var token = getToken();
    var role = getRole();
    if (token && role) {
      showApp(role);
      if (window.location.hash === '#admin' && role === 'admin') showAdminView();
    } else {
      showLogin();
    }
  });

  var guestBtn = document.getElementById('guest-btn');
  if (guestBtn) {
    guestBtn.addEventListener('click', async function () {
      try {
        var res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: 'guest' }) });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) { document.getElementById('login-error').textContent = data.detail || 'Login failed'; document.getElementById('login-error').classList.remove('hidden'); return; }
        setSession(data.access_token, data.role || 'guest');
        document.getElementById('login-error').classList.add('hidden');
        showApp('guest');
      } catch (e) { document.getElementById('login-error').textContent = e.message || 'Network error'; document.getElementById('login-error').classList.remove('hidden'); }
    });
  }

  var adminLoginBtn = document.getElementById('admin-login-btn');
  if (adminLoginBtn) {
    adminLoginBtn.addEventListener('click', async function () {
      var user = document.getElementById('admin-user');
      var pwd = document.getElementById('admin-password');
      var errEl = document.getElementById('login-error');
      if (!user || !pwd) return;
      try {
        var res = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: user.value.trim(), password: pwd.value }) });
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) { errEl.textContent = data.detail || 'Invalid credentials'; errEl.classList.remove('hidden'); return; }
        setSession(data.access_token, data.role || 'admin');
        errEl.classList.add('hidden');
        showApp('admin');
      } catch (e) { errEl.textContent = e.message || 'Network error'; errEl.classList.remove('hidden'); }
    });
  }

  var logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', function () { clearSession(); showLogin(); });

  var viewAllLink = document.getElementById('view-all-link');
  if (viewAllLink) viewAllLink.addEventListener('click', function (e) { e.preventDefault(); showAdminView(); });

  var adminBackLink = document.getElementById('admin-back-link');
  if (adminBackLink) adminBackLink.addEventListener('click', function (e) { e.preventDefault(); hideAdminView(); });
  var adminBackLinkTop = document.getElementById('admin-back-link-top');
  if (adminBackLinkTop) adminBackLinkTop.addEventListener('click', function (e) { e.preventDefault(); hideAdminView(); });

  function formatCreatedAtForDisplay(created_at) {
    if (created_at == null) return '';
    var s = String(created_at).trim();
    if (s.indexOf(' IST') !== -1) return s;
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    var utcMs = d.getTime();
    var istMs = utcMs + (5.5 * 60 * 60 * 1000);
    var ist = new Date(istMs);
    var y = ist.getUTCFullYear();
    var m = String(ist.getUTCMonth() + 1).padStart(2, '0');
    var day = String(ist.getUTCDate()).padStart(2, '0');
    var h = String(ist.getUTCHours()).padStart(2, '0');
    var min = String(ist.getUTCMinutes()).padStart(2, '0');
    var sec = String(ist.getUTCSeconds()).padStart(2, '0');
    return y + '-' + m + '-' + day + ' ' + h + ':' + min + ':' + sec + ' IST';
  }

  function loadAdminAnalyses() {
    var wrap = document.getElementById('admin-table-wrap');
    var loading = document.getElementById('admin-loading');
    var tbody = document.getElementById('admin-tbody');
    if (wrap) wrap.classList.add('hidden');
    if (loading) { loading.classList.remove('hidden'); loading.textContent = 'Loading…'; }
    var token = getToken();
    if (!token) { if (loading) loading.textContent = 'Not logged in.'; return; }
    fetch('/api/admin/analyses', { headers: { Authorization: 'Bearer ' + token } })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || r.statusText); });
        return r.json();
      })
      .then(function (rows) {
        if (loading) loading.classList.add('hidden');
        if (!Array.isArray(rows)) { if (loading) { loading.textContent = 'Could not load data.'; loading.classList.remove('hidden'); } return; }
        if (tbody) tbody.innerHTML = '';
        if (rows.length === 0 && tbody) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td colspan="11" class="admin-empty">No analyses yet. Run an analysis as admin or guest to see results here.</td>';
          tbody.appendChild(tr);
        } else {
          rows.forEach(function (r) {
            var tr = document.createElement('tr');
            tr.className = 'admin-row-clickable';
            var id = r.id != null ? r.id : '';
            var services = Array.isArray(r.recommended_services) ? r.recommended_services.join(', ') : (r.recommended_services || '');
            var products = Array.isArray(r.recommended_products) ? r.recommended_products.join(', ') : (r.recommended_products || '');
            var createdDisplay = formatCreatedAtForDisplay(r.created_at);
            var checkCell = '<td class="admin-col-checkbox"><input type="checkbox" class="admin-row-checkbox" data-id="' + id + '" aria-label="Select row" /></td>';
            var photoCell = r.image_path
              ? '<td class="admin-thumb-cell"><img src="/api/uploads/' + r.image_path + '" alt="" class="admin-thumb" /></td>'
              : '<td class="admin-thumb-cell">—</td>';
            tr.innerHTML = checkCell + photoCell +
              '<td><a href="#" class="admin-view-result-link">' + createdDisplay + '</a></td>' +
              '<td>' + (r.user_type || '') + '</td><td>' + (r.customer_name || '—') + '</td><td>' + (r.skin_type || '—') + '</td><td>' + (r.face_shape || '—') + '</td><td>' + (r.dark_circle_score || '—') + '</td><td>' + (services || '—') + '</td><td>' + (products || '—') + '</td>' +
              '<td><a href="#" class="admin-view-result-link">View result</a></td>';
            tr._rowData = r;
            tr.addEventListener('click', function (ev) {
              if (ev.target.closest('a') || ev.target.closest('.admin-row-checkbox')) return;
              showAdminDetail(r);
            });
            tr.querySelectorAll('.admin-view-result-link').forEach(function (link) {
              link.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); showAdminDetail(r); });
            });
            var cb = tr.querySelector('.admin-row-checkbox');
            if (cb) cb.addEventListener('change', updateAdminDeleteButton);
            if (tbody) tbody.appendChild(tr);
          });
        }
        updateAdminDeleteButton();
        if (wrap) wrap.classList.remove('hidden');
      })
      .catch(function (err) { if (loading) { loading.textContent = err.message || 'Failed to load.'; loading.classList.remove('hidden'); } if (wrap) wrap.classList.add('hidden'); });
  }

  function updateAdminDeleteButton() {
    var btn = document.getElementById('admin-delete-selected');
    var checkboxes = document.querySelectorAll('.admin-row-checkbox:checked');
    if (btn) btn.disabled = !checkboxes.length;
  }

  function getSelectedAdminIds() {
    var ids = [];
    document.querySelectorAll('.admin-row-checkbox:checked').forEach(function (cb) {
      var id = cb.getAttribute('data-id');
      if (id !== '' && id != null) ids.push(parseInt(id, 10));
    });
    return ids;
  }

  var adminSelectAll = document.getElementById('admin-select-all');
  if (adminSelectAll) {
    adminSelectAll.addEventListener('change', function () {
      var checked = this.checked;
      document.querySelectorAll('.admin-row-checkbox').forEach(function (cb) { cb.checked = checked; });
      updateAdminDeleteButton();
    });
  }

  var adminDeleteSelected = document.getElementById('admin-delete-selected');
  if (adminDeleteSelected) {
    adminDeleteSelected.addEventListener('click', function () {
      var ids = getSelectedAdminIds();
      if (ids.length === 0) return;
      if (!confirm('Delete ' + ids.length + ' selected analysis entries? This cannot be undone.')) return;
      var statusEl = document.getElementById('admin-delete-status');
      if (statusEl) statusEl.textContent = 'Deleting…';
      adminDeleteSelected.disabled = true;
      var token = getToken();
      if (!token) { if (statusEl) statusEl.textContent = ''; updateAdminDeleteButton(); return; }
      fetch('/api/admin/analyses/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
        body: JSON.stringify({ ids: ids }),
      })
        .then(function (r) {
          if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || r.statusText); });
          return r.json();
        })
        .then(function (data) {
          if (statusEl) statusEl.textContent = 'Deleted ' + (data.deleted || ids.length) + ' entries.';
          loadAdminAnalyses();
          setTimeout(function () { if (statusEl) statusEl.textContent = ''; }, 3000);
        })
        .catch(function (err) {
          if (statusEl) statusEl.textContent = err.message || 'Delete failed.';
          setTimeout(function () { if (statusEl) statusEl.textContent = ''; }, 3000);
          updateAdminDeleteButton();
        });
    });
  }

  function setEl(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function showAdminDetail(r) {
    var tableWrap = document.getElementById('admin-table-wrap');
    var detail = document.getElementById('admin-detail');
    var imgEl = document.getElementById('admin-detail-img');
    var previewWrap = imgEl && imgEl.closest('.preview-wrap');
    if (tableWrap) tableWrap.classList.add('hidden');
    if (detail) detail.classList.remove('hidden');

    var res = r.analysis_result;
    if (typeof res === 'string') { try { res = JSON.parse(res); } catch (e) { res = {}; } }
    res = res || {};
    adminLandmarks = Array.isArray(res.landmarks) ? res.landmarks : [];
    adminCurrentTabMode = 'skin';

    if (imgEl && previewWrap) {
      var noImageNote = previewWrap.querySelector('.admin-no-image-note');
      if (r.image_path) {
        if (noImageNote) noImageNote.classList.add('hidden');
        imgEl.src = '/api/uploads/' + r.image_path;
        imgEl.style.display = '';
        imgEl.onerror = function () {
          imgEl.style.display = 'none';
          if (!noImageNote) {
            noImageNote = document.createElement('p');
            noImageNote.className = 'admin-no-image-note';
            noImageNote.textContent = 'Image could not be loaded.';
            previewWrap.appendChild(noImageNote);
          }
          noImageNote.textContent = 'Image could not be loaded.';
          noImageNote.classList.remove('hidden');
        };
        imgEl.onload = function () {
          if (noImageNote) noImageNote.classList.add('hidden');
        };
        previewWrap.classList.remove('hidden');
        imgEl.onload = function () {
          drawAdminLandmarks(adminCurrentTabMode);
        };
        if (imgEl.complete) drawAdminLandmarks(adminCurrentTabMode);
      } else {
        imgEl.removeAttribute('src');
        imgEl.style.display = 'none';
        noImageNote = previewWrap.querySelector('.admin-no-image-note');
        if (!noImageNote) {
          noImageNote = document.createElement('p');
          noImageNote.className = 'admin-no-image-note';
          previewWrap.appendChild(noImageNote);
        }
        noImageNote.textContent = 'No image saved for this analysis (older entry).';
        noImageNote.classList.remove('hidden');
        previewWrap.classList.remove('hidden');
        var adminCanvas = document.getElementById('admin-landmarks-canvas');
        if (adminCanvas && adminCanvas.getContext) adminCanvas.getContext('2d').clearRect(0, 0, adminCanvas.width, adminCanvas.height);
        var adminLegend = document.getElementById('admin-landmarks-legend');
        if (adminLegend) adminLegend.classList.add('hidden');
      }
    }

    var skin = res.skin || {};
    var shape = res.shape || {};
    var rec = res.recommendation || {};
    var st = skin.skin_type || r.skin_type || '';
    var al = skin.acne_level || r.acne_level || '';
    var dc = skin.dark_circle_score || r.dark_circle_score || '';
    var fs = shape.face_shape || r.face_shape || '';

    setEl('admin-skin-type', st || '—');
    setEl('admin-skin-type-desc', st ? (SKIN_TYPE_INFO[st] || '') : '');
    setEl('admin-acne-level', al || '—');
    setEl('admin-acne-level-desc', al ? (ACNE_LEVEL_INFO[al] || '') : '');
    setEl('admin-dark-circle-score', dc || '—');
    setEl('admin-dark-circle-desc', dc ? (DARK_CIRCLE_INFO[dc] || '') : '');
    setEl('admin-face-shape', fs || '—');
    setEl('admin-face-shape-desc', fs ? (FACE_SHAPE_INFO[fs] || '') : '');

    function toArr(v) {
      if (Array.isArray(v)) return v;
      if (typeof v === 'string') { try { var a = JSON.parse(v); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
      return [];
    }
    var services = toArr(rec.recommended_services || r.recommended_services);
    var products = toArr(rec.recommended_products || r.recommended_products);
    var servicesList = document.getElementById('admin-services-list');
    var productsList = document.getElementById('admin-products-list');
    if (servicesList) {
      servicesList.innerHTML = '';
      if (services.length === 0) servicesList.innerHTML = '<li class="rec-none">No specific services suggested for this profile.</li>';
      else services.forEach(function (name) {
        var li = document.createElement('li');
        li.innerHTML = '<strong>' + String(name) + '</strong>' + (SERVICE_INFO[name] ? '<span class="rec-desc"> ' + SERVICE_INFO[name] + '</span>' : '');
        servicesList.appendChild(li);
      });
    }
    if (productsList) {
      productsList.innerHTML = '';
      if (products.length === 0) productsList.innerHTML = '<li class="rec-none">No specific products suggested for this profile.</li>';
      else products.forEach(function (name) {
        var li = document.createElement('li');
        li.innerHTML = '<strong>' + String(name) + '</strong>' + (PRODUCT_INFO[name] ? '<span class="rec-desc"> ' + PRODUCT_INFO[name] + '</span>' : '');
        productsList.appendChild(li);
      });
    }

    var skinConsult = res.skin_consult || {};
    var adminScContent = document.getElementById('admin-skinconsult-content');
    if (adminScContent) {
      if (!skinConsult.face_detected) {
        adminScContent.innerHTML = '<p>No skin consult data for this analysis.</p>';
      } else {
        var scores = skinConsult.skin_scores || {};
        var html = '<h3>Confidence</h3><p><strong>Score:</strong> ' + (skinConsult.confidence_score != null ? skinConsult.confidence_score : '—') + '</p>';
        html += '<h3>Skin scores (0–100)</h3><p><strong>Brightness:</strong> ' + (scores.brightness != null ? scores.brightness : '—') + ' <strong>Pigmentation:</strong> ' + (scores.pigmentation_density != null ? scores.pigmentation_density : '—') + ' <strong>Redness:</strong> ' + (scores.redness != null ? scores.redness : '—') + ' <strong>Texture:</strong> ' + (scores.texture_roughness != null ? scores.texture_roughness : '—') + ' <strong>Dark circle:</strong> ' + (scores.dark_circle_index != null ? scores.dark_circle_index : '—') + ' <strong>Facial hair:</strong> ' + (scores.facial_hair_density != null ? scores.facial_hair_density : '—') + '</p>';
        var top3 = skinConsult.top_3_services || [];
        html += '<h3>Top recommended services</h3><ul class="rec-list">';
        if (top3.length === 0) html += '<li class="rec-none">No services from deep analysis.</li>';
        else top3.forEach(function (s) { html += '<li><strong>' + (s.service || '') + '</strong>' + (s.reason ? ' — ' + s.reason : '') + (s.estimated_improvement_pct != null ? ' (' + s.estimated_improvement_pct + '% improvement)' : '') + '</li>'; });
        html += '</ul>';
        var road = skinConsult.suggested_roadmap || [];
        html += '<h3>Suggested roadmap</h3><p>' + (road.length ? road.join(' → ') : '—') + '</p>';
        adminScContent.innerHTML = html;
      }
    }

    document.querySelectorAll('.admin-tab').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-admin-tab') === 'skin');
    });
    document.querySelectorAll('.admin-panel').forEach(function (panel) {
      var show = panel.id === 'admin-panel-skin';
      panel.classList.toggle('active', show);
      panel.hidden = !show;
    });
  }

  function drawAdminLandmarks(mode) {
    var canvas = document.getElementById('admin-landmarks-canvas');
    var img = document.getElementById('admin-detail-img');
    var legendEl = document.getElementById('admin-landmarks-legend');
    if (!canvas || !img) return;
    if (mode === 'skinconsult' || mode === 'original' || !adminLandmarks.length) {
      var ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (legendEl) legendEl.classList.add('hidden');
      canvas.classList.add('hidden');
      return;
    }
    canvas.classList.remove('hidden');
    drawLandmarks(adminLandmarks, {
      canvas: canvas,
      img: img,
      mode: mode,
      legendEl: legendEl,
    });
  }

  function switchAdminTab(tabName) {
    adminCurrentTabMode = tabName;
    document.querySelectorAll('.admin-tab').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-admin-tab') === tabName);
    });
    document.querySelectorAll('.admin-panel').forEach(function (panel) {
      var show = (panel.id === 'admin-panel-' + tabName);
      panel.classList.toggle('active', show);
      panel.hidden = !show;
    });
    drawAdminLandmarks(tabName);
  }

  function hideAdminDetail() {
    document.getElementById('admin-table-wrap').classList.remove('hidden');
    document.getElementById('admin-detail').classList.add('hidden');
  }
  var adminDetailBack = document.getElementById('admin-detail-back');
  if (adminDetailBack) adminDetailBack.addEventListener('click', hideAdminDetail);
  var adminDetailBackTop = document.getElementById('admin-detail-back-top');
  if (adminDetailBackTop) adminDetailBackTop.addEventListener('click', hideAdminDetail);
  var adminBackLinkDetail = document.getElementById('admin-back-link-detail');
  if (adminBackLinkDetail) adminBackLinkDetail.addEventListener('click', function (e) { e.preventDefault(); hideAdminView(); });
  document.querySelectorAll('.admin-tab').forEach(function (btn) {
    btn.addEventListener('click', function () { switchAdminTab(btn.getAttribute('data-admin-tab')); });
  });

  window.addEventListener('hashchange', function () {
    if (window.location.hash === '#admin' && getRole() === 'admin') showAdminView();
  });

  function clearLandmarks() {
    if (landmarksCanvas && landmarksCanvas.getContext) {
      var ctx = landmarksCanvas.getContext('2d');
      ctx.clearRect(0, 0, landmarksCanvas.width, landmarksCanvas.height);
    }
    if (resultsLandmarksCanvas && resultsLandmarksCanvas.getContext) {
      var ctx2 = resultsLandmarksCanvas.getContext('2d');
      ctx2.clearRect(0, 0, resultsLandmarksCanvas.width, resultsLandmarksCanvas.height);
    }
    if (landmarksLegend) landmarksLegend.classList.add('hidden');
  }

  function drawLandmarks(landmarks, opts) {
    opts = opts || {};
    var canvas = opts.canvas || landmarksCanvas;
    var img = opts.img || previewImg;
    var mode = opts.mode || 'shape';
    var legendEl = opts.legendEl !== undefined ? opts.legendEl : landmarksLegend;
    if (mode === 'original' && canvas) {
      var ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (legendEl) { legendEl.textContent = ''; legendEl.classList.add('hidden'); }
      return;
    }
    if (!landmarks || !landmarks.length || !img || !canvas) return;
    var w = img.offsetWidth;
    var h = img.offsetHeight;
    if (w <= 0 || h <= 0) return;
    canvas.width = w;
    canvas.height = h;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    var ctx = canvas.getContext('2d');
    var keyIndices = [FACE_SHAPE_INDICES.forehead, FACE_SHAPE_INDICES.chin, FACE_SHAPE_INDICES.jawLeft, FACE_SHAPE_INDICES.jawRight];
    var showKeyAndLines = mode === 'shape' || mode === 'recommendations';
    for (var i = 0; i < landmarks.length; i++) {
      var lm = landmarks[i];
      var x = lm.x * w;
      var y = lm.y * h;
      var isKey = showKeyAndLines && keyIndices.indexOf(i) !== -1;
      if (isKey) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(232, 197, 71, 0.95)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(74, 14, 54, 0.9)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(x, y, mode === 'skin' ? 1.2 : 1, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(212, 175, 55, 0.55)';
        ctx.fill();
      }
    }
    if (showKeyAndLines) {
      var p = function (idx) {
        var lm = landmarks[idx];
        return { x: lm.x * w, y: lm.y * h };
      };
      ctx.beginPath();
      ctx.moveTo(p(234).x, p(234).y);
      ctx.lineTo(p(454).x, p(454).y);
      ctx.strokeStyle = 'rgba(232, 197, 71, 0.75)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(p(10).x, p(10).y);
      ctx.lineTo(p(152).x, p(152).y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if (legendEl) {
      legendEl.textContent = LEGEND_BY_MODE[mode] || LEGEND_BY_MODE.skin;
      legendEl.classList.remove('hidden');
    }
  }

  function switchTab(mode) {
    currentTabMode = mode;
    var resultsEl = document.getElementById('results');
    var btns = resultsEl ? resultsEl.querySelectorAll('.tab-btn') : document.querySelectorAll('.tab-btn');
    var panels = resultsEl ? resultsEl.querySelectorAll('.tab-panel') : document.querySelectorAll('.tab-panel');
    btns.forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === mode);
      btn.setAttribute('aria-selected', btn.getAttribute('data-tab') === mode ? 'true' : 'false');
    });
    panels.forEach(function (panel) {
      var show = panel.id === 'tab-panel-' + mode;
      panel.classList.toggle('active', show);
      panel.hidden = !show;
    });
    if (mode === 'original' || mode === 'all' || mode === 'skinconsult') {
      if (resultsLandmarksCanvas) {
        resultsLandmarksCanvas.classList.add('hidden');
        var ctx = resultsLandmarksCanvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, resultsLandmarksCanvas.width, resultsLandmarksCanvas.height);
      }
      if (resultsLandmarksLegend) {
        resultsLandmarksLegend.textContent = (mode === 'all' ? 'Full analysis summary below.' : (mode === 'skinconsult' ? 'Deep skin consultation results.' : ''));
        resultsLandmarksLegend.classList.toggle('hidden', mode === 'original');
      }
    } else {
      if (resultsLandmarksCanvas) resultsLandmarksCanvas.classList.remove('hidden');
      if (lastLandmarks.length > 0 && resultsLandmarksCanvas && resultsPreviewImg) {
        drawLandmarks(lastLandmarks, {
          canvas: resultsLandmarksCanvas,
          img: resultsPreviewImg,
          mode: mode,
          legendEl: resultsLandmarksLegend,
        });
      } else if (resultsLandmarksLegend) resultsLandmarksLegend.classList.remove('hidden');
    }
  }

  function hideAll() {
    previewSection.classList.add('hidden');
    loadingSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
  }

  function showError(msg) {
    hideAll();
    errorMessage.textContent = msg;
    errorSection.classList.remove('hidden');
  }

  fileInput.addEventListener('change', function () {
    const file = this.files && this.files[0];
    analyzeBtn.disabled = !file;
    clearLandmarks();
    if (!file) {
      hideAll();
      return;
    }
    const url = URL.createObjectURL(file);
    previewImg.src = url;
    previewSection.classList.remove('hidden');
    loadingSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
  });

  analyzeBtn.addEventListener('click', async function () {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;

    hideAll();
    loadingSection.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);
    var token = getToken();
    if (!token) { showError('Not authenticated. Please log in again.'); return; }
    if (getRole() === 'admin') {
      var custInput = document.getElementById('customer-name');
      formData.append('customer_name', (custInput && custInput.value) ? custInput.value.trim() : 'GENERAL');
    }
    var headers = { Authorization: 'Bearer ' + token };

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: headers,
        body: formData,
      });

      const data = await res.json().catch(function () {
        return { detail: res.statusText || 'Unknown error' };
      });

      if (!res.ok) {
        var msg = data.detail || JSON.stringify(data);
        if (res.status === 422 && (msg.indexOf('face') !== -1 || msg.indexOf('detect') !== -1)) {
          msg = 'We couldn\'t detect a face in this image. Please use a clear, front-facing photo with your face clearly visible and good lighting.';
        }
        showError(msg);
        return;
      }

      loadingSection.classList.add('hidden');
      errorSection.classList.add('hidden');
      resultsSection.classList.remove('hidden');
      previewSection.classList.add('hidden');

      const skin = data.skin || {};
      const shape = data.shape || {};
      const rec = data.recommendation || {};
      const landmarks = data.landmarks || [];
      lastLandmarks = landmarks || [];

      resultsPreviewImg.src = previewImg.src || '';
      if (landmarks.length > 0) {
        if (previewImg.complete) {
          drawLandmarks(landmarks);
        } else {
          previewImg.addEventListener('load', function onLoad() {
            previewImg.removeEventListener('load', onLoad);
            drawLandmarks(landmarks);
          });
        }
        function drawResultsLandmarks() {
          drawLandmarks(lastLandmarks, {
            canvas: resultsLandmarksCanvas,
            img: resultsPreviewImg,
            mode: currentTabMode,
            legendEl: resultsLandmarksLegend,
          });
        }
        if (resultsPreviewImg.complete) {
          drawResultsLandmarks();
        } else {
          resultsPreviewImg.addEventListener('load', function onLoad() {
            resultsPreviewImg.removeEventListener('load', onLoad);
            drawResultsLandmarks();
          });
        }
      } else {
        clearLandmarks();
      }

      currentTabMode = 'original';
      document.querySelectorAll('.tab-btn').forEach(function (btn) {
        btn.onclick = function () {
          switchTab(btn.getAttribute('data-tab'));
        };
      });
      switchTab('original');

      var st = skin.skin_type || '';
      var al = skin.acne_level || '';
      var dc = skin.dark_circle_score || '';
      var fs = shape.face_shape || '';

      document.getElementById('skin-type').textContent = st || '—';
      document.getElementById('skin-type-desc').textContent = st ? (SKIN_TYPE_INFO[st] || '') : '';
      document.getElementById('acne-level').textContent = al || '—';
      document.getElementById('acne-level-desc').textContent = al ? (ACNE_LEVEL_INFO[al] || '') : '';
      document.getElementById('dark-circle-score').textContent = dc || '—';
      document.getElementById('dark-circle-desc').textContent = dc ? (DARK_CIRCLE_INFO[dc] || '') : '';
      document.getElementById('face-shape').textContent = fs || '—';
      document.getElementById('face-shape-desc').textContent = fs ? (FACE_SHAPE_INFO[fs] || '') : '';

      function setEl(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
      }
      setEl('all-skin-type', st || '—');
      setEl('all-skin-type-desc', st ? (SKIN_TYPE_INFO[st] || '') : '');
      setEl('all-acne-level', al || '—');
      setEl('all-acne-level-desc', al ? (ACNE_LEVEL_INFO[al] || '') : '');
      setEl('all-dark-circle-score', dc || '—');
      setEl('all-dark-circle-desc', dc ? (DARK_CIRCLE_INFO[dc] || '') : '');
      setEl('all-face-shape', fs || '—');
      setEl('all-face-shape-desc', fs ? (FACE_SHAPE_INFO[fs] || '') : '');

      var servicesList = document.getElementById('services-list');
      var productsList = document.getElementById('products-list');
      var allServicesList = document.getElementById('all-services-list');
      var allProductsList = document.getElementById('all-products-list');
      servicesList.innerHTML = '';
      productsList.innerHTML = '';
      if (allServicesList) allServicesList.innerHTML = '';
      if (allProductsList) allProductsList.innerHTML = '';

      var services = rec.recommended_services || [];
      var products = rec.recommended_products || [];
      if (services.length === 0) {
        servicesList.innerHTML = '<li class="rec-none">No specific services suggested for this profile.</li>';
        if (allServicesList) allServicesList.innerHTML = '<li class="rec-none">No specific services suggested for this profile.</li>';
      } else {
        services.forEach(function (name) {
          var li = document.createElement('li');
          li.innerHTML = '<strong>' + name + '</strong>' +
            (SERVICE_INFO[name] ? '<span class="rec-desc"> ' + SERVICE_INFO[name] + '</span>' : '');
          servicesList.appendChild(li);
          if (allServicesList) allServicesList.appendChild(li.cloneNode(true));
        });
      }
      if (products.length === 0) {
        productsList.innerHTML = '<li class="rec-none">No specific products suggested for this profile.</li>';
        if (allProductsList) allProductsList.innerHTML = '<li class="rec-none">No specific products suggested for this profile.</li>';
      } else {
        products.forEach(function (name) {
          var li = document.createElement('li');
          li.innerHTML = '<strong>' + name + '</strong>' +
            (PRODUCT_INFO[name] ? '<span class="rec-desc"> ' + PRODUCT_INFO[name] + '</span>' : '');
        productsList.appendChild(li);
        if (allProductsList) allProductsList.appendChild(li.cloneNode(true));
        });
      }

      // Skin consultation: fetch and show in Skin consult tab
      var scLoading = document.getElementById('skinconsult-loading');
      var scUnavailable = document.getElementById('skinconsult-unavailable');
      var scContent = document.getElementById('skinconsult-content');
      if (scLoading) scLoading.classList.remove('hidden');
      if (scUnavailable) scUnavailable.classList.add('hidden');
      if (scContent) scContent.classList.add('hidden');

      var consultFormData = new FormData();
      consultFormData.append('file', file);
      fetch('/api/consult', { method: 'POST', headers: { Authorization: 'Bearer ' + getToken() }, body: consultFormData })
        .then(function (cRes) { return cRes.json().then(function (cData) { return { ok: cRes.ok, data: cData }; }); })
        .catch(function () { return { ok: false, data: {} }; })
        .then(function (result) {
          if (scLoading) scLoading.classList.add('hidden');
          if (!result.ok || !result.data.staff || !result.data.staff.face_detected) {
            if (scUnavailable) scUnavailable.classList.remove('hidden');
            return;
          }
          var staff = result.data.staff;
          var customer = result.data.customer || {};
          if (scUnavailable) scUnavailable.classList.add('hidden');
          if (scContent) scContent.classList.remove('hidden');

          var scores = staff.skin_scores || {};
          function scSet(id, text) { var el = document.getElementById(id); if (el) el.textContent = text; }
          scSet('sc-confidence', (staff.confidence_score != null) ? staff.confidence_score : '—');
          var mrEl = document.getElementById('sc-manual-review');
          if (mrEl) mrEl.classList.toggle('hidden', !staff.manual_review_required);

          scSet('sc-brightness', scores.brightness != null ? scores.brightness : '—');
          scSet('sc-pigmentation', scores.pigmentation_density != null ? scores.pigmentation_density : '—');
          scSet('sc-redness', scores.redness != null ? scores.redness : '—');
          scSet('sc-texture', scores.texture_roughness != null ? scores.texture_roughness : '—');
          scSet('sc-darkcircle', scores.dark_circle_index != null ? scores.dark_circle_index : '—');
          scSet('sc-facialhair', scores.facial_hair_density != null ? scores.facial_hair_density : '—');

          var topList = document.getElementById('sc-top-services');
          if (topList) {
            topList.innerHTML = '';
            var top3 = staff.top_3_services || [];
            if (top3.length === 0) {
              topList.innerHTML = '<li class="rec-none">No services from deep analysis.</li>';
            } else {
              top3.forEach(function (s) {
                var li = document.createElement('li');
                li.innerHTML = '<strong>' + (s.service || '') + '</strong>' +
                  (s.reason ? '<span class="rec-desc"> ' + s.reason + '</span>' : '') +
                  (s.expected_effect ? '<br/><em>Effect: ' + s.expected_effect + '</em>' : '') +
                  (s.estimated_improvement_pct != null ? ' <small>(' + s.estimated_improvement_pct + '% improvement)</small>' : '');
                topList.appendChild(li);
              });
            }
          }

          var roadmapEl = document.getElementById('sc-roadmap');
          if (roadmapEl) {
            var road = staff.suggested_roadmap || [];
            roadmapEl.textContent = road.length ? road.join(' → ') : '—';
          }

          var projEl = document.getElementById('sc-projection');
          if (projEl && staff.improvement_projection && typeof staff.improvement_projection === 'object') {
            var proj = staff.improvement_projection;
            var parts = [];
            Object.keys(proj).forEach(function (k) {
              parts.push(k.replace(/_/g, ' ') + ': ' + proj[k]);
            });
            projEl.textContent = parts.length ? parts.join(' · ') : '—';
          } else if (projEl) projEl.textContent = '—';

          var beforeImg = document.getElementById('sc-before-img');
          var afterImg = document.getElementById('sc-after-img');
          if (beforeImg && customer.before_image_base64) beforeImg.src = 'data:image/jpeg;base64,' + customer.before_image_base64;
          else if (beforeImg) beforeImg.removeAttribute('src');
          if (afterImg && customer.after_image_base64) afterImg.src = 'data:image/jpeg;base64,' + customer.after_image_base64;
          else if (afterImg) afterImg.removeAttribute('src');

          var discEl = document.getElementById('sc-disclaimer');
          if (discEl) discEl.textContent = customer.disclaimer || 'This visualization is a digital simulation. Results may vary.';
        });
    } catch (err) {
      showError(err.message || 'Network error');
    }
  });
})();
