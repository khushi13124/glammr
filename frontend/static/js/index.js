/* ---------- Performance Optimized Variables ---------- */
let selectedImageUrl = null;
let boardsCache = null;
let isLoadingBoards = false;
let modalInstance = null;
let preloadPromise = null;

/* ---------- Debounced Functions ---------- */
const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// Simulate progressive loading bar for images
function attachProgressHandlers(img, wrapper) {
  if (!wrapper) return;
  let progress = 0;
  let done = false;
  wrapper.style.setProperty('--progress', '0%');

  // progressive timer to simulate progress until load fires
  const tick = () => {
    if (done) return;
    // ease towards 85% max before real load
    progress = Math.min(progress + (progress < 50 ? 8 : progress < 70 ? 5 : 2), 85);
    wrapper.style.setProperty('--progress', progress + '%');
    wrapper._progressTimer = setTimeout(tick, 120);
  };
  tick();

  const finalize = () => {
    if (done) return;
    done = true;
    clearTimeout(wrapper._progressTimer);
    wrapper.style.setProperty('--progress', '100%');
    // let the bar reach 100%, then remove placeholder styles
    setTimeout(() => {
      wrapper.classList.remove('loading');
      wrapper.style.removeProperty('--progress');
      img.style.backgroundImage = '';
      img.style.backgroundColor = '';
    }, 180);
  };

  const fail = () => {
    if (done) return;
    done = true;
    clearTimeout(wrapper._progressTimer);
    wrapper.classList.remove('loading');
    wrapper.style.removeProperty('--progress');
  };

  img.addEventListener('load', finalize, { once: true });
  img.addEventListener('error', fail, { once: true });
}

/* ---------- Lazy Image Loading ---------- */
const imageObserver = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      if (img.dataset.src && !img.src) {
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        observer.unobserve(img);
      }
    }
  });
}, {
  rootMargin: '50px 0px',
  threshold: 0.01
});

/* ---------- Performance Optimized Event Handling ---------- */
document.addEventListener("DOMContentLoaded", () => {
  // Initialize modal instance for better performance
  const modalElement = document.getElementById('saveModal');
  if (modalElement) {
    modalInstance = new bootstrap.Modal(modalElement);
  }

  // Preload boards with delay to not block initial render
  setTimeout(() => {
    preloadPromise = loadBoardsBackground();
  }, 100);

  // Setup lazy loading for images with progress placeholder
  document.querySelectorAll('.img-wrapper img').forEach(img => {
    const wrapper = img.closest('.img-wrapper');
    if (wrapper) {
      wrapper.classList.add('loading');
      wrapper.style.setProperty('--progress', '0%');
    }
    if (img.src) {
      img.dataset.src = img.src;
      img.removeAttribute('src');
      img.style.backgroundColor = '#f0f0f0';
      attachProgressHandlers(img, wrapper);
      imageObserver.observe(img);
    }
  });

  // Optimized event delegation with throttling
  const masonryGrid = document.getElementById('masonry-grid');
  if (masonryGrid) {
    // Throttled image click handler
    const throttledImageClick = throttle((target) => {
      let imageLink = target.closest('.image-detail-link');
      if (!imageLink) {
        const wrapper = target.closest('.img-wrapper');
        if (wrapper) imageLink = wrapper.querySelector('.image-detail-link');
      }
      if (imageLink) {
        handleImageClick(imageLink);
      }
    }, 300);

    masonryGrid.addEventListener('click', function(e) {
      // Handle save button clicks
      const saveBtn = e.target.closest('.save-btn');
      if (saveBtn) {
        e.preventDefault();
        e.stopPropagation();
        handleSaveButtonClick(saveBtn);
        return;
      }
      
      // Handle image clicks (throttled)
      if (!e.target.closest('.save-btn')) {
        e.preventDefault();
        e.stopPropagation();
        throttledImageClick(e.target);
      }
    });

    // Darken overlay when hovering/clicking save button
    masonryGrid.addEventListener('mouseover', function(e) {
      const btn = e.target.closest('.save-btn');
      if (btn) {
        const wrapper = btn.closest('.img-wrapper');
        if (wrapper) wrapper.classList.add('overlay-strong');
      }
    });
    masonryGrid.addEventListener('mouseout', function(e) {
      const btn = e.target.closest('.save-btn');
      if (btn) {
        const wrapper = btn.closest('.img-wrapper');
        if (wrapper) wrapper.classList.remove('overlay-strong');
      }
    });
    masonryGrid.addEventListener('mousedown', function(e) {
      const btn = e.target.closest('.save-btn');
      if (btn) {
        const wrapper = btn.closest('.img-wrapper');
        if (wrapper) wrapper.classList.add('overlay-strong');
      }
    });
    masonryGrid.addEventListener('mouseup', function(e) {
      const btn = e.target.closest('.save-btn');
      if (btn) {
        const wrapper = btn.closest('.img-wrapper');
        if (wrapper) wrapper.classList.remove('overlay-strong');
      }
    });
  }

  // ------- Incremental rendering (prevents page freeze on huge grids) -------
  const GRID_INITIAL = 60;   // show first 60 items
  const GRID_BATCH = 40;     // reveal 40 more per step
  const gridItems = Array.from(document.querySelectorAll('#masonry-grid .grid-item'));
  let revealedCount = 0;

  if (gridItems.length > 0) {
    // Hide all first to avoid initial massive layout
    gridItems.forEach(el => { el.style.display = 'none'; });

    function revealNext(count) {
      const end = Math.min(revealedCount + count, gridItems.length);
      for (let i = revealedCount; i < end; i++) {
        const el = gridItems[i];
        el.style.display = 'inline-block';
        // trigger soft fade-in
        el.classList.add('revealed');
        // If the image has a data-src, ensure it is observed
        const img = el.querySelector('img');
        if (img && img.dataset && img.dataset.src) {
          imageObserver.observe(img);
        }
      }
      revealedCount = end;
    }

    // Initial reveal
    revealNext(GRID_INITIAL);

    const onScroll = throttle(() => {
      const nearBottom = (window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 800);
      if (nearBottom && revealedCount < gridItems.length) {
        revealNext(GRID_BATCH);
      }
    }, 200);

    window.addEventListener('scroll', onScroll, { passive: true });
  }
});

// Throttle function for performance
function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

function handleSaveButtonClick(saveBtn) {
  selectedImageUrl = saveBtn.getAttribute('data-image');
  document.getElementById('selectedImage').value = selectedImageUrl;
  
  // Visual feedback
  saveBtn.classList.add('clicked');
  setTimeout(() => saveBtn.classList.remove('clicked'), 200);
  
  // Show modal immediately if boards are cached
  if (boardsCache) {
    displayBoardsInstantly(boardsCache);
  }
}

function handleImageClick(linkElement) {
  // Create URL immediately to reduce perceived latency
  const imageUrl = linkElement.getAttribute("data-path");
  const type = linkElement.getAttribute("data-type");
  const id = linkElement.getAttribute("data-id") || "";
  const filename = linkElement.getAttribute("data-filename") || "";

  const baseUrl = window.urls.imageView;
  const url = `${baseUrl}?url=${encodeURIComponent(imageUrl)}&type=${encodeURIComponent(type)}&id=${encodeURIComponent(id)}&filename=${encodeURIComponent(filename)}`;
  
  // Use requestIdleCallback for better performance if available
  if (window.requestIdleCallback) {
    requestIdleCallback(() => {
      window.location.href = url;
    });
  } else {
    setTimeout(() => {
      window.location.href = url;
    }, 0);
  }
}

/* ---------- Optimized Board Loading ---------- */
async function loadBoardsBackground() {
  if (isLoadingBoards || boardsCache) return boardsCache;
  
  isLoadingBoards = true;
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    const boardsurl= window.urls.getBoards;
    const response = await fetch(boardsurl+"?t=" + Date.now(), {
      signal: controller.signal,
      cache: 'no-store'
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.status === "success") {
      boardsCache = data.boards;
      return boardsCache;
    } else {
      throw new Error(data.message || 'Failed to load boards');
    }
  } catch (err) {
    console.error("Background board loading failed:", err);
    return null;
  } finally {
    isLoadingBoards = false;
  }
}

// Force-reload boards immediately and refresh the modal list if open
async function reloadBoardsNow() {
  try {
    const boardsurl= window.urls.getBoards;
    const response = await fetch(boardsurl+"?t=" + Date.now(), {
      cache: 'no-store'
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (data.status === "success") {
      boardsCache = data.boards;
      const modalEl = document.getElementById('saveModal');
      // If modal is currently visible, re-render the list immediately
      if (modalEl && modalEl.classList.contains('show')) {
        displayBoardsInstantly(boardsCache || []);
      }
    }
  } catch (e) {
    console.error('reloadBoardsNow failed:', e);
  }
}

// Instant modal show with cached data
document.getElementById("saveModal").addEventListener("show.bs.modal", function () {
  const loadingEl = document.getElementById('boardsLoading');
  const listEl = document.getElementById('modalBoardsList');
  
  if (boardsCache) {
    // Show immediately if cached
    displayBoardsInstantly(boardsCache);
    // Also refresh in background so deletions/restores are reflected ASAP
    reloadBoardsNow();
  } else {
    // Show loading and load in background
    if (loadingEl) loadingEl.style.display = 'flex';
    if (listEl) listEl.style.display = 'none';
    
    if (preloadPromise) {
      preloadPromise.then(boards => {
        if (boards) {
          boardsCache = boards;
          displayBoardsInstantly(boards);
        } else {
          showBoardsError();
        }
      }).finally(() => {
        if (loadingEl) loadingEl.style.display = 'none';
      });
    } else {
      loadBoardsBackground().then(boards => {
        if (boards) {
          boardsCache = boards;
          displayBoardsInstantly(boards);
        } else {
          showBoardsError();
        }
      }).finally(() => {
        if (loadingEl) loadingEl.style.display = 'none';
      });
    }
  }
});

function displayBoardsInstantly(boards) {
  const listEl = document.getElementById('modalBoardsList');
  if (!listEl) return;

  listEl.style.display = 'block';
  
  if (boards.length === 0) {
    listEl.innerHTML = `
      <div class="no-boards-message">
        <i class="bi bi-collection"></i>
        <p>No boards yet. Create your first one below!</p>
      </div>`;
    return;
  }

  // Use virtual scrolling for large lists
  if (boards.length > 20) {
    displayBoardsVirtual(boards, listEl);
  } else {
    displayBoardsNormal(boards, listEl);
  }
}

function displayBoardsNormal(boards, container) {
  const fragment = document.createDocumentFragment();
  
  boards.forEach(board => {
    const button = createBoardButton(board);
    fragment.appendChild(button);
  });
  
  container.innerHTML = '';
  container.appendChild(fragment);
}

function displayBoardsVirtual(boards, container) {
  // Simple virtual scrolling for performance with large lists
  const itemHeight = 60;
  const visibleItems = Math.ceil(280 / itemHeight);
  const buffer = 5;
  
  let startIndex = 0;
  let endIndex = Math.min(visibleItems + buffer, boards.length);
  
  function renderVisibleItems() {
    const fragment = document.createDocumentFragment();
    
    for (let i = startIndex; i < endIndex; i++) {
      const button = createBoardButton(boards[i]);
      fragment.appendChild(button);
    }
    
    container.innerHTML = '';
    container.appendChild(fragment);
  }
  
  // Debounced scroll handler
  const debouncedScroll = debounce(() => {
    const scrollTop = container.scrollTop;
    const newStartIndex = Math.floor(scrollTop / itemHeight) - buffer;
    const newEndIndex = Math.min(newStartIndex + visibleItems + (buffer * 2), boards.length);
    
    if (newStartIndex !== startIndex || newEndIndex !== endIndex) {
      startIndex = Math.max(0, newStartIndex);
      endIndex = newEndIndex;
      renderVisibleItems();
    }
  }, 16);
  
  container.addEventListener('scroll', debouncedScroll);
  renderVisibleItems();
}

function createBoardButton(board) {
  const button = document.createElement('button');
  button.className = 'save-to-board-btn';
  button.setAttribute('data-board', board.id);
  button.setAttribute('data-count', board.non_deleted_count || 0);
  
  button.innerHTML = `
    <div class="board-info">
      <span class="board-name">${escapeHtml(board.name)}</span>
      <span class="board-count">${board.non_deleted_count || 0}</span>
    </div>
    <div class="save-status">
      <i class="bi bi-plus-lg"></i>
    </div>
  `;
  
  return button;
}

function showBoardsError(message = 'Failed to load boards. Please try again.') {
  const listEl = document.getElementById('modalBoardsList');
  if (listEl) {
    listEl.innerHTML = `
      <div class="error-message">
        <i class="bi bi-exclamation-triangle"></i>
        <p>${escapeHtml(message)}</p>
        <button class="retry-btn" onclick="loadBoards()">Retry</button>
      </div>`;
    listEl.style.display = 'block';
  }
}

// Utility function to escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Event delegation for "Save to Board" buttons
document.querySelector('#modalBoardsList').addEventListener('click', function(e) {
  const boardBtn = e.target.closest('.save-to-board-btn');
  if (boardBtn && !boardBtn.disabled) {
    const boardId = boardBtn.getAttribute('data-board');
    saveToBoard(boardId, selectedImageUrl, boardBtn);
  }
});

// Create new board and save
document.getElementById('createBoardBtn').addEventListener('click', function () {
  const boardName = document.getElementById('newBoardName').value.trim();
  const btn = this;
  
  if (!boardName || btn.disabled) return;

  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-arrow-clockwise spinning"></i><span>Creating...</span>';
  const createboardurl= window.urls.createBoard;
  fetch(createboardurl, {
    method: "POST",
    headers: {
      "X-CSRFToken": "{{ csrf_token }}",
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: "name=" + encodeURIComponent(boardName)
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === "success") {
      boardsCache = null; // Clear cache to force refresh
      saveToBoard(data.board_id, selectedImageUrl);
      document.getElementById('newBoardName').value = '';
      localStorage.setItem('sync_event', JSON.stringify({
        action: 'create_board',
        board: { id: data.board_id, name: data.board_name, image_count: 1 },
        ts: Date.now()
      }));
      // Immediately refresh boards shown in modal so the new board appears
      reloadBoardsNow();
    } else {
      showError(data.message || 'Failed to create board');
    }
  })
  .catch(err => {
    console.error("Create board failed:", err);
    showError('Network error. Please try again.');
  })
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-plus-lg"></i><span>Create & Save</span>';
  });
});

// Optimized save to board function
function saveToBoard(boardId, imageUrl, btn) {
  if (btn) {
    btn.disabled = true;
    const statusIcon = btn.querySelector('.save-status i');
    statusIcon.className = 'bi bi-arrow-clockwise spinning';
  }
  const savetoboardurl= window.urls.saveToBoard;
  fetch(savetoboardurl, {
    method: "POST",
    headers: {
      "X-CSRFToken": "{{ csrf_token }}",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ board_id: boardId, image_url: imageUrl })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === "success") {
      if (btn) {
        const statusIcon = btn.querySelector('.save-status i');
        const countEl = btn.querySelector('.board-count');
        
        statusIcon.className = 'bi bi-check-lg success';
        countEl.textContent = data.board_image_count;
        
        // Update cache
        if (boardsCache) {
          const board = boardsCache.find(b => b.id == boardId);
          if (board) board.non_deleted_count = data.board_image_count;
        }
      }
      
      // Close modal after short delay
      setTimeout(() => {
        const modalInstance = bootstrap.Modal.getInstance(document.getElementById("saveModal"));
        if (modalInstance) {
          modalInstance.hide();
        }
      }, 800);
      
      updateSavesCount();
      
      // Broadcast save event
      localStorage.setItem('sync_event', JSON.stringify({
        action: 'save_image',
        board_id: boardId,
        board_image_count: data.board_image_count,
        default_board_id: data.default_board_id,
        default_board_count: data.default_board_count,
        ts: Date.now()
      }));
      
    } else {
      showError(data.message || 'Failed to save image');
      if (btn) {
        const statusIcon = btn.querySelector('.save-status i');
        statusIcon.className = 'bi bi-exclamation-lg error';
      }
    }
  })
  .catch(err => {
    console.error("Save failed:", err);
    showError('Network error. Please try again.');
    if (btn) {
      const statusIcon = btn.querySelector('.save-status i');
      statusIcon.className = 'bi bi-exclamation-lg error';
    }
  })
  .finally(() => {
    if (btn) {
      btn.disabled = false;
      // Reset icon after delay if not success
      setTimeout(() => {
        const statusIcon = btn.querySelector('.save-status i');
        if (!statusIcon.classList.contains('success')) {
          statusIcon.className = 'bi bi-plus-lg';
        }
      }, 2000);
    }
  });
}

// Error display function
function showError(message) {
  // Remove existing toasts first
  const existingToasts = document.querySelectorAll('.error-toast');
  existingToasts.forEach(toast => toast.remove());
  
  // Create toast notification
  const toast = document.createElement('div');
  toast.className = 'error-toast';
  toast.innerHTML = `
    <i class="bi bi-exclamation-circle"></i>
    <span>${escapeHtml(message)}</span>
  `;
  document.body.appendChild(toast);
  
  // Auto remove after 3 seconds
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, 3000);
}

// Update saves count function
function updateSavesCount() {
  fetch("/api/saves-count/")
    .then(res => res.json())
    .then(data => {
      const savesCountEl = document.getElementById("saves-count");
      if (savesCountEl && data.count !== undefined) {
        savesCountEl.textContent = data.count;
      }
    })
    .catch(err => console.error("Error fetching saves count:", err));
}

// Update navbar stats function
function updateNavbarStats() {
  fetch('/api/get-stats/all/')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        const stats = data.stats;
        const elements = {
          'saves-count': stats.saves,
          'uploads-count': stats.uploads,
          'boards-count': stats.boards,
          'likes-count': stats.likes
        };
        
        Object.entries(elements).forEach(([id, count]) => {
          const el = document.getElementById(id);
          if (el && count !== undefined) el.textContent = count;
        });
      }
    })
    .catch(err => console.error('Error updating navbar stats:', err));
}

/* ---------- Real-time sync: listen for events from other tabs ---------- */
window.addEventListener('storage', (ev) => {
  if (!ev.key || ev.key !== 'sync_event') return;
  try {
    const data = JSON.parse(ev.newValue || '{}');
    if (!data || !data.action) return;

    if (data.action === 'save_image') {
      // Update cached board counts
      if (boardsCache) {
        const board = boardsCache.find(b => b.id == data.board_id);
        if (board) board.non_deleted_count = data.board_image_count;
        
        if (data.default_board_id && data.default_board_id !== data.board_id) {
          const defaultBoard = boardsCache.find(b => b.id == data.default_board_id);
          if (defaultBoard && data.default_board_count !== undefined) {
            defaultBoard.non_deleted_count = data.default_board_count;
          }
        }
      }
      
      updateNavbarStats();
    }

    if (data.action === 'unsave_image') {
      if (data.affected_boards && boardsCache) {
        data.affected_boards.forEach(b => {
          const board = boardsCache.find(board => board.id == b.board_id);
          if (board) board.non_deleted_count = b.count;
        });
      }
      updateNavbarStats();
    }

    if (data.action === 'delete_board') {
      // Remove from cache
      if (boardsCache) {
        boardsCache = boardsCache.filter(b => b.id != data.board_id);
      }
      // If modal is open, update the visible list immediately
      const modalEl = document.getElementById('saveModal');
      if (modalEl && modalEl.classList.contains('show')) {
        displayBoardsInstantly(boardsCache || []);
      }
      updateNavbarStats();
    }

    if (data.action === 'restore_board') {
      // Force cache refresh
      boardsCache = null;
      // If modal is open, reload from server now
      const modalEl = document.getElementById('saveModal');
      if (modalEl && modalEl.classList.contains('show')) {
        reloadBoardsNow();
      }
      updateNavbarStats();
    }

    if (data.action === 'create_board') {
      // Force cache refresh
      boardsCache = null;
      // If modal is open, reload from server now so new board shows
      const modalEl = document.getElementById('saveModal');
      if (modalEl && modalEl.classList.contains('show')) {
        reloadBoardsNow();
      }
      updateNavbarStats();
    }

  } catch (e) {
    console.error('sync parse error', e);
  }
});

// Reset modal state when hidden
document.getElementById("saveModal").addEventListener("hidden.bs.modal", function () {
  const buttons = document.querySelectorAll('.save-to-board-btn');
  buttons.forEach(btn => {
    btn.disabled = false;
    const statusIcon = btn.querySelector('.save-status i');
    if (statusIcon) statusIcon.className = 'bi bi-plus-lg';
  });
  
  const createBtn = document.getElementById('createBoardBtn');
  if (createBtn) {
    createBtn.disabled = false;
    createBtn.innerHTML = '<i class="bi bi-plus-lg"></i><span>Create & Save</span>';
  }
});
document.querySelectorAll('.purchase-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        const imageId = this.dataset.imageId;
         if (!imageId) {
            console.error('purchase-btn missing imageId');
            return;
        }
        // Replace the 0 with the real image ID
        const url = window.urls.purchase.replace('/0/', `/${imageId}/`);

        window.open(url, '_blank');
    });
});
