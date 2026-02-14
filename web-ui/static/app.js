(function () {
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
  const FACE_SHAPE_INFO = {
    Oval: 'Balanced proportions; many styles and cuts suit this shape. You can experiment with different looks.',
    Round: 'Softer angles and similar width/height. Layered cuts and volume on top can add definition and length.',
    Square: 'Strong jaw and forehead. Softer layers or curls can balance the angles and add softness.',
  };
  const SERVICE_INFO = {
    'Acne Control Facial': 'Deep-cleans and treats congestion; helps reduce breakouts and calm inflammation.',
    'Hydrating Facial': 'Restores moisture and supports the skin barrier; ideal for dry or dehydrated skin.',
    'Layer Cut': 'Adds movement and structure; works well for round face shapes by creating length and definition.',
    'Soft Curl Styling': 'Adds softness and flow; balances stronger facial angles for a more relaxed look.',
  };
  const PRODUCT_INFO = {
    'Salicylic Cleanser': 'Helps clear pores and reduce oil and breakouts; suitable for oily or acne-prone skin.',
    'Vitamin C Serum': 'Supports brightness and protection; helps with dryness and uneven tone.',
  };

  var FACE_SHAPE_INDICES = { forehead: 10, chin: 152, jawLeft: 234, jawRight: 454 };

  const fileInput = document.getElementById('file');
  const analyzeBtn = document.getElementById('analyze');
  const previewSection = document.getElementById('preview');
  const previewImg = document.getElementById('preview-img');
  const landmarksCanvas = document.getElementById('landmarks-canvas');
  const landmarksLegend = document.getElementById('landmarks-legend');
  const loadingSection = document.getElementById('loading');
  const errorSection = document.getElementById('error');
  const errorMessage = document.getElementById('error-message');
  const resultsSection = document.getElementById('results');

  function clearLandmarks() {
    if (!landmarksCanvas || !landmarksCanvas.getContext) return;
    var ctx = landmarksCanvas.getContext('2d');
    ctx.clearRect(0, 0, landmarksCanvas.width, landmarksCanvas.height);
    if (landmarksLegend) landmarksLegend.classList.add('hidden');
  }

  function drawLandmarks(landmarks) {
    if (!landmarks || !landmarks.length || !previewImg || !landmarksCanvas) return;
    var img = previewImg;
    var w = img.offsetWidth;
    var h = img.offsetHeight;
    if (w <= 0 || h <= 0) return;
    landmarksCanvas.width = w;
    landmarksCanvas.height = h;
    landmarksCanvas.style.width = w + 'px';
    landmarksCanvas.style.height = h + 'px';
    var ctx = landmarksCanvas.getContext('2d');
    var keyIndices = [FACE_SHAPE_INDICES.forehead, FACE_SHAPE_INDICES.chin, FACE_SHAPE_INDICES.jawLeft, FACE_SHAPE_INDICES.jawRight];
    for (var i = 0; i < landmarks.length; i++) {
      var lm = landmarks[i];
      var x = lm.x * w;
      var y = lm.y * h;
      var isKey = keyIndices.indexOf(i) !== -1;
      if (isKey) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(184, 74, 92, 0.9)';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(x, y, 1, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(184, 74, 92, 0.5)';
        ctx.fill();
      }
    }
    var p = function (idx) {
      var lm = landmarks[idx];
      return { x: lm.x * w, y: lm.y * h };
    };
    ctx.beginPath();
    ctx.moveTo(p(234).x, p(234).y);
    ctx.lineTo(p(454).x, p(454).y);
    ctx.strokeStyle = 'rgba(184, 74, 92, 0.7)';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(p(10).x, p(10).y);
    ctx.lineTo(p(152).x, p(152).y);
    ctx.stroke();
    ctx.setLineDash([]);
    if (landmarksLegend) landmarksLegend.classList.remove('hidden');
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

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
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
      previewSection.classList.remove('hidden');

      const skin = data.skin || {};
      const shape = data.shape || {};
      const rec = data.recommendation || {};
      const landmarks = data.landmarks || [];

      if (landmarks.length > 0) {
        if (previewImg.complete) {
          drawLandmarks(landmarks);
        } else {
          previewImg.addEventListener('load', function onLoad() {
            previewImg.removeEventListener('load', onLoad);
            drawLandmarks(landmarks);
          });
        }
      } else {
        clearLandmarks();
      }

      var st = skin.skin_type || '';
      var al = skin.acne_level || '';
      var fs = shape.face_shape || '';

      document.getElementById('skin-type').textContent = st || '—';
      document.getElementById('skin-type-desc').textContent = st ? (SKIN_TYPE_INFO[st] || '') : '';
      document.getElementById('acne-level').textContent = al || '—';
      document.getElementById('acne-level-desc').textContent = al ? (ACNE_LEVEL_INFO[al] || '') : '';
      document.getElementById('face-shape').textContent = fs || '—';
      document.getElementById('face-shape-desc').textContent = fs ? (FACE_SHAPE_INFO[fs] || '') : '';

      var servicesList = document.getElementById('services-list');
      var productsList = document.getElementById('products-list');
      servicesList.innerHTML = '';
      productsList.innerHTML = '';

      var services = rec.recommended_services || [];
      var products = rec.recommended_products || [];
      if (services.length === 0) {
        servicesList.innerHTML = '<li class="rec-none">No specific services suggested for this profile.</li>';
      } else {
        services.forEach(function (name) {
          var li = document.createElement('li');
          li.innerHTML = '<strong>' + name + '</strong>' +
            (SERVICE_INFO[name] ? '<span class="rec-desc"> ' + SERVICE_INFO[name] + '</span>' : '');
          servicesList.appendChild(li);
        });
      }
      if (products.length === 0) {
        productsList.innerHTML = '<li class="rec-none">No specific products suggested for this profile.</li>';
      } else {
        products.forEach(function (name) {
          var li = document.createElement('li');
          li.innerHTML = '<strong>' + name + '</strong>' +
            (PRODUCT_INFO[name] ? '<span class="rec-desc"> ' + PRODUCT_INFO[name] + '</span>' : '');
          productsList.appendChild(li);
        });
      }
    } catch (err) {
      showError(err.message || 'Network error');
    }
  });
})();
