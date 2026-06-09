(function () {
  var boot = window.__BANK_WIZARD__ || {};
  var state = {
    step: 1,
    joinMode: 'free'
  };
  var nameEl = document.getElementById('wizardName');
  var descEl = document.getElementById('wizardDescription');
  var isPublicEl = document.getElementById('wizardIsPublic');
  var publicDescEl = document.getElementById('wizardPublicDescription');
  var coverImageEl = document.getElementById('wizardCoverImage');
  var coverFileEl = document.getElementById('wizardCoverFile');
  var coverUploadBtn = document.getElementById('wizardCoverUploadBtn');
  var coverPreviewEl = document.getElementById('wizardCoverPreview');
  var coverPreviewImg = document.getElementById('wizardCoverPreviewImg');
  var joinNoteEl = document.getElementById('wizardJoinNote');
  var feedbackEl = document.getElementById('wizardFeedback');
  var submitBtn = document.getElementById('wizardSubmitBtn');
  var panels = Array.prototype.slice.call(document.querySelectorAll('.wizard-panel'));
  var steps = Array.prototype.slice.call(document.querySelectorAll('.wizard-step'));
  var joinModeButtons = Array.prototype.slice.call(document.querySelectorAll('[data-join-mode]'));
  var allowedCoverTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
  var maxCoverBytes = 5 * 1024 * 1024;

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setFeedback(message, isError) {
    if (!feedbackEl) return;
    feedbackEl.textContent = message || '';
    feedbackEl.style.color = isError ? '#ef4444' : '';
  }

  function setCoverUploading(isUploading) {
    if (!coverUploadBtn) return;
    coverUploadBtn.classList.toggle('uploading', !!isUploading);
    coverUploadBtn.textContent = isUploading ? '上传中...' : '选择图片';
  }

  function setCoverPreview(url) {
    var coverUrl = String(url || '').trim();
    if (!coverPreviewEl || !coverPreviewImg) return;
    if (!coverUrl) {
      coverPreviewImg.removeAttribute('src');
      coverPreviewEl.hidden = true;
      return;
    }
    coverPreviewImg.src = coverUrl;
    coverPreviewEl.hidden = false;
  }

  function renderStep() {
    panels.forEach(function (panel) {
      panel.classList.toggle('active', Number(panel.getAttribute('data-panel')) === state.step);
    });
    steps.forEach(function (stepEl) {
      stepEl.classList.toggle('active', Number(stepEl.getAttribute('data-step')) === state.step);
    });
    document.getElementById('wizardPrevBtn').style.display = state.step === 1 ? 'none' : 'inline-flex';
    document.getElementById('wizardNextBtn').style.display = state.step === 3 ? 'none' : 'inline-flex';
    submitBtn.style.display = state.step === 3 ? 'inline-flex' : 'none';
  }

  function validateStep(step) {
    if (step === 1) {
      var name = String(nameEl && nameEl.value || '').trim();
      if (!name || name.length < 2 || name.length > 50) {
        setFeedback('题库名称需要 2-50 个字符', true);
        return false;
      }
      if (String(descEl && descEl.value || '').trim().length > 200) {
        setFeedback('私人描述不能超过 200 个字符', true);
        return false;
      }
    }
    if (step === 2) {
      if (String(publicDescEl && publicDescEl.value || '').trim().length > 200) {
        setFeedback('公开简介不能超过 200 个字符', true);
        return false;
      }
      if (String(coverImageEl && coverImageEl.value || '').trim().length > 500) {
        setFeedback('封面图地址不能超过 500 个字符', true);
        return false;
      }
    }
    if (step === 3) {
      if (String(joinNoteEl && joinNoteEl.value || '').trim().length > 200) {
        setFeedback('加入说明不能超过 200 个字符', true);
        return false;
      }
    }
    setFeedback('');
    return true;
  }

  function fetchJson(url, options) {
    return fetch(url, options || { credentials: 'same-origin' }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (json) {
        if (!response.ok || !json || json.code !== 0) {
          throw new Error((json && json.message) || '请求失败');
        }
        return json;
      });
    });
  }

  function updateJoinMode(mode) {
    state.joinMode = mode || 'free';
    joinModeButtons.forEach(function (button) {
      button.classList.toggle('active', button.getAttribute('data-join-mode') === state.joinMode);
    });
  }

  function hydrate(bank) {
    if (!bank) return;
    if (nameEl) nameEl.value = bank.name || '';
    if (descEl) descEl.value = bank.description || '';
    if (publicDescEl) publicDescEl.value = bank.public_description || '';
    if (coverImageEl) coverImageEl.value = bank.cover_image || '';
    setCoverPreview(bank.cover_image || '');
    if (joinNoteEl) joinNoteEl.value = bank.join_note || '';
    if (isPublicEl) isPublicEl.checked = !!bank.is_public;
    updateJoinMode(bank.join_mode || 'free');
  }

  function uploadCoverFile(file) {
    if (!file) return Promise.resolve();
    if (file.type && allowedCoverTypes.indexOf(file.type) === -1) {
      setFeedback('请上传 png、jpg、jpeg、gif 或 webp 图片', true);
      return Promise.resolve();
    }
    if (file.size > maxCoverBytes) {
      setFeedback('封面图片不能超过 5MB', true);
      return Promise.resolve();
    }

    var formData = new FormData();
    formData.append('file', file);
    var uploadUrl = boot.mode === 'edit' && boot.bank_id
      ? '/user/banks/api/' + encodeURIComponent(String(boot.bank_id)) + '/cover/upload'
      : '/user/banks/api/cover/upload';

    setCoverUploading(true);
    setFeedback('正在上传封面图片...');

    return fetchJson(uploadUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData
    }).then(function (json) {
      var url = json.data && json.data.url;
      if (!url) throw new Error('上传成功但未返回图片地址');
      if (coverImageEl) coverImageEl.value = url;
      setCoverPreview(url);
      setFeedback('封面上传成功，保存后生效');
    }).catch(function (error) {
      setFeedback((error && error.message) || '封面上传失败', true);
    }).finally(function () {
      setCoverUploading(false);
      if (coverFileEl) coverFileEl.value = '';
    });
  }

  function loadBank() {
    if (boot.mode !== 'edit' || !boot.bank_id) return Promise.resolve();
    return fetchJson('/user/banks/api/' + encodeURIComponent(String(boot.bank_id)), { credentials: 'same-origin' }).then(function (json) {
      hydrate(json.data || {});
    });
  }

  function submit() {
    if (!validateStep(1) || !validateStep(2) || !validateStep(3)) return;
    var payload = {
      name: String(nameEl && nameEl.value || '').trim(),
      description: String(descEl && descEl.value || '').trim(),
      public_description: String(publicDescEl && publicDescEl.value || '').trim(),
      cover_image: String(coverImageEl && coverImageEl.value || '').trim(),
      join_mode: state.joinMode,
      join_note: String(joinNoteEl && joinNoteEl.value || '').trim(),
      is_public: !!(isPublicEl && isPublicEl.checked)
    };
    submitBtn.disabled = true;
    submitBtn.textContent = boot.mode === 'add' ? '创建中...' : '保存中...';
    setFeedback('正在保存题库信息...');

    var promise;
    if (boot.mode === 'add') {
      promise = fetchJson('/user/banks/api', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify(payload)
      }).then(function (json) {
        return json.data && json.data.id;
      });
    } else {
      promise = fetchJson('/user/banks/api/' + encodeURIComponent(String(boot.bank_id)), {
        method: 'PUT',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify(payload)
      }).then(function () {
        return boot.bank_id;
      });
    }

    promise.then(function (bankId) {
      return fetchJson('/user/banks/api/' + encodeURIComponent(String(bankId)) + '/public', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({
          is_public: payload.is_public,
          public_description: payload.public_description
        })
      }).then(function () {
        return bankId;
      });
    }).then(function () {
      window.location.href = '/user/banks?scope=created';
    }).catch(function (error) {
      setFeedback((error && error.message) || '保存失败', true);
    }).finally(function () {
      submitBtn.disabled = false;
      submitBtn.textContent = boot.mode === 'add' ? '创建题库' : '保存修改';
    });
  }

  document.getElementById('wizardPrevBtn').addEventListener('click', function () {
    if (state.step > 1) state.step -= 1;
    renderStep();
  });
  document.getElementById('wizardNextBtn').addEventListener('click', function () {
    if (!validateStep(state.step)) return;
    if (state.step < 3) state.step += 1;
    renderStep();
  });
  document.getElementById('bankWizardForm').addEventListener('submit', function (event) {
    event.preventDefault();
    submit();
  });
  joinModeButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      updateJoinMode(button.getAttribute('data-join-mode') || 'free');
    });
  });
  if (coverFileEl) {
    coverFileEl.addEventListener('change', function () {
      var file = coverFileEl.files && coverFileEl.files[0];
      uploadCoverFile(file);
    });
  }
  if (coverImageEl) {
    coverImageEl.addEventListener('input', function () {
      setCoverPreview(coverImageEl.value);
    });
  }
  steps.forEach(function (button) {
    button.addEventListener('click', function () {
      var next = Number(button.getAttribute('data-step') || 1);
      if (next > state.step && !validateStep(state.step)) return;
      state.step = next;
      renderStep();
    });
  });

  renderStep();
  updateJoinMode('free');
  loadBank();
})();
