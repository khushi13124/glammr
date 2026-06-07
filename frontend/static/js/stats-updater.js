class StatsUpdater {
    constructor() {
      this.endpoints = {
        saves: '/api/get-stats/saves/',
        uploads: '/api/get-stats/uploads/',
        boards: '/api/get-stats/boards/',
        likes: '/api/get-stats/likes/'
      };
      
      this.init();
    }
  
    init() {
      // Listen for storage events from other tabs
      window.addEventListener('storage', this.handleStorageUpdate.bind(this));
      
      // Listen for custom events within the same tab
      window.addEventListener('statsUpdate', this.handleStatsUpdate.bind(this));
      
      // Auto-refresh stats every 30 seconds
      setInterval(() => {
        this.refreshAllStats();
      }, 30000);
    }
  
    async updateStat(statType, change = null) {
      const statCard = document.querySelector(`.stat-card[data-stat="${statType}"]`);
      const statValue = statCard?.querySelector('.stat-value');
      const statLabel = statCard?.querySelector('.stat-label');
      
      if (!statCard || !statValue) return;
  
      try {
        // Add loading state
        statCard.classList.add('loading');
        
        // If we have a change amount, optimistically update
        if (change !== null) {
          const currentValue = parseInt(statValue.textContent) || 0;
          const newValue = Math.max(0, currentValue + change);
          this.animateValueChange(statValue, newValue);
          this.updateLabel(statLabel, newValue);
        }
  
        // Fetch actual value from server
        const response = await fetch(this.endpoints[statType], {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken()
          }
        });
  
        if (response.ok) {
          const data = await response.json();
          const actualValue = data.count;
          
          // Update with actual value
          this.animateValueChange(statValue, actualValue);
          this.updateLabel(statLabel, actualValue);
          
          // Success animation
          statCard.classList.remove('loading');
          statCard.classList.add('success', 'updated');
          
          setTimeout(() => {
            statCard.classList.remove('success', 'updated');
          }, 2000);
          
          // Notify other tabs
          localStorage.setItem(`stats_${statType}`, actualValue.toString());
          localStorage.setItem(`stats_${statType}_timestamp`, Date.now().toString());
          
        } else {
          throw new Error(`Failed to fetch ${statType} stats`);
        }
        
      } catch (error) {
        console.error(`Error updating ${statType} stats:`, error);
        
        // Error animation
        statCard.classList.remove('loading');
        statCard.classList.add('error');
        
        setTimeout(() => {
          statCard.classList.remove('error');
        }, 1000);
      }
    }
  
    animateValueChange(element, newValue) {
      const currentValue = parseInt(element.textContent) || 0;
      
      if (currentValue === newValue) return;
      
      element.classList.add('updating');
      
      // Animate the number change
      const duration = 600;
      const startTime = performance.now();
      const difference = newValue - currentValue;
      
      const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeOutCubic = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(currentValue + (difference * easeOutCubic));
        
        element.textContent = current.toLocaleString();
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          element.classList.remove('updating');
        }
      };
      
      requestAnimationFrame(animate);
    }
  
    updateLabel(labelElement, count) {
      if (!labelElement) return;
      
      const labelText = labelElement.textContent.toLowerCase();
      
      if (labelText.includes('save')) {
        labelElement.textContent = count === 1 ? 'Save' : 'Saves';
      } else if (labelText.includes('upload')) {
        labelElement.textContent = count === 1 ? 'Upload' : 'Uploads';
      } else if (labelText.includes('board')) {
        labelElement.textContent = count === 1 ? 'Board' : 'Boards';
      } else if (labelText.includes('like')) {
        labelElement.textContent = count === 1 ? 'Like' : 'Likes';
      }
    }
  
    handleStorageUpdate(event) {
      if (event.key?.startsWith('stats_') && !event.key.includes('timestamp')) {
        const statType = event.key.replace('stats_', '');
        const newValue = parseInt(event.newValue) || 0;
        
        const statCard = document.querySelector(`.stat-card[data-stat="${statType}"]`);
        const statValue = statCard?.querySelector('.stat-value');
        const statLabel = statCard?.querySelector('.stat-label');
        
        if (statValue && statLabel) {
          this.animateValueChange(statValue, newValue);
          this.updateLabel(statLabel, newValue);
          
          // Show update animation
          statCard.classList.add('updated');
          setTimeout(() => {
            statCard.classList.remove('updated');
          }, 2000);
        }
      }
    }
  
    handleStatsUpdate(event) {
      const { statType, change } = event.detail;
      this.updateStat(statType, change);
    }
  
    async refreshAllStats() {
      const statTypes = ['saves', 'uploads', 'boards', 'likes'];
      
      for (const statType of statTypes) {
        await this.updateStat(statType);
      }
    }
  
    getCsrfToken() {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
             document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
  
    // Public methods to trigger updates
    static incrementSaves() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'saves', change: 1 }
      }));
    }
  
    static decrementSaves() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'saves', change: -1 }
      }));
    }
  
    static incrementUploads() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'uploads', change: 1 }
      }));
    }
  
    static incrementBoards() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'boards', change: 1 }
      }));
    }
  
    static decrementBoards() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'boards', change: -1 }
      }));
    }
  
    static incrementLikes() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'likes', change: 1 }
      }));
    }
  
    static decrementLikes() {
      window.dispatchEvent(new CustomEvent('statsUpdate', {
        detail: { statType: 'likes', change: -1 }
      }));
    }
  }
  
  // Initialize the stats updater
  document.addEventListener('DOMContentLoaded', () => {
    window.statsUpdater = new StatsUpdater();
  });
  
  // Export for use in other files
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatsUpdater;
  }
