// Full Screen Image Viewer SPA
class FullScreenImageViewer {
    constructor() {
        this.currentImageData = null;
        this.config = window.imageViewerConfig || {};
        this.init();

        this.page = 1;
        this.pageSize = 50;
        this.hasNext = false;
        this.loading = false;
        this.similarImagesContainer = null;
        this.boards = [];

    }

    init() {
        this.bindEvents();
        this.loadImageFromURL();
        console.log('FullScreenImageViewer initialized');
    }

    bindEvents() {
        // Back button
        const backButton = document.getElementById('backButton');
        if (backButton) {
            backButton.addEventListener('click', this.goBack.bind(this));
        }

        // Create board button
        const createButton = document.getElementById('createBoardButton');
        if (createButton) {
            createButton.addEventListener('click', this.createNewBoard.bind(this));
        }

        // Enter key on input
        const boardInput = document.getElementById('newBoardInput');
        if (boardInput) {
            boardInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.createNewBoard();
                }
            });
        }

        window.addEventListener('scroll', this.handleScroll.bind(this));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.goBack();
            }
        });
    }

    loadImageFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const imageUrl = urlParams.get('image_url') || urlParams.get('url');
        if(!imageUrl) return this.showError('No image specified');

        const imageData = { url: decodeURIComponent(imageUrl) };
        this.loadImageDetails(imageData);
    }

    async loadImageDetails(imageData) {
        this.currentImageData = imageData;
        this.page = 1;
        this.hasNext = false;
        console.log('Loading image details for:', imageData);
        
        // Show image
        this.displayImage(imageData.url);
        
        // Show loading state
        this.showBoardsLoading();
        
        try {
            // Fetch detailed information and boards
            const params = new URLSearchParams({
                image_url: imageData.url,
                type: imageData.type,
                ...(imageData.id && { id: imageData.id }),
                ...(imageData.filename && { filename: imageData.filename })
            });

            const url = `${this.config.imageDetailUrl}?${params.toString()}`;
            console.log('Fetching from URL:', url);
            console.log('Config:', this.config);

            const response = await fetch(url);
            const data = await response.json();
            
            console.log('API Response:', data);

            if (data.status === 'success') {
                this.displayBoards(data.boards || []);
            } else {
                console.error('API Error:', data);
                this.showError('Failed to load boards');
            }
        } catch (error) {
            console.error('Error fetching image details:', error);
            this.showError('Failed to load boards');
        }

        this.similarImagesContainer = document.getElementById('similarImagesGrid');
        if(this.similarImagesContainer) this.similarImagesContainer.innerHTML = '';
        await this.loadSimilarImages();
    }

    displayImage(imageUrl) {
        const mainImage = document.getElementById('mainImage');
        const imageLoader = document.getElementById('imageLoader');
        
        if (!mainImage || !imageLoader) return;

        // Show loader
        imageLoader.style.display = 'flex';
        mainImage.style.opacity = '0';
        mainImage.style.transform = 'scale(0.9)';

        // Load image
        const img = new Image();
        img.onload = () => {
            mainImage.src = imageUrl;
            imageLoader.style.display = 'none';
            mainImage.classList.add('loaded');
            
            // Smooth reveal animation
            setTimeout(() => {
                mainImage.style.opacity = '1';
                mainImage.style.transform = 'scale(1)';
            }, 100);
        };
        
        img.onerror = () => {
            imageLoader.style.display = 'none';
            this.showError('Failed to load image');
        };
        
        img.src = imageUrl;
    }

    showBoardsLoading() {
        const boardsLoader = document.getElementById('boardsLoader');
        const boardsContainer = document.getElementById('boardsContainer');
        
        if (boardsLoader) boardsLoader.style.display = 'flex';
        if (boardsContainer) boardsContainer.classList.remove('visible');
    }

    displayBoards(boards) {
        const boardsLoader = document.getElementById('boardsLoader');
        const boardsContainer = document.getElementById('boardsContainer');
        const boardsGrid = document.getElementById('boardsGrid');
        
        if (!boardsGrid) return;

        // Hide loader
        if (boardsLoader) boardsLoader.style.display = 'none';
        if (boardsContainer) boardsContainer.classList.add('visible');

        // Clear existing boards
        boardsGrid.innerHTML = '';

        if (boards.length === 0) {
            boardsGrid.innerHTML = `
                <div class="no-boards-message">
                    <p style="text-align: center; color: #6b7280; font-style: italic;">
                        No boards yet. Create your first one below!
                    </p>
                </div>
            `;
            return;
        }

        // Add boards with stagger animation
        boards.forEach((board, index) => {
            const boardCard = this.createBoardCard(board);
            boardCard.style.animationDelay = `${index * 0.1}s`;
            boardsGrid.appendChild(boardCard);
        });
    }

    createBoardCard(board) {
        const boardCard = document.createElement('div');
        boardCard.className = 'board-card';
        boardCard.style.animation = 'fadeInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards';
        boardCard.style.opacity = '0';
        
        boardCard.innerHTML = `
            <span class="board-name">${this.escapeHtml(board.name)}</span>
            <span class="board-count">${board.count || 0}</span>
        `;

        boardCard.addEventListener('click', () => {
            this.saveToBoard(board.id, board.name);
        });

        // Remove opacity after animation
        setTimeout(() => {
            boardCard.style.opacity = '1';
        }, 400);

        return boardCard;
    }

    async createNewBoard() {
        const boardInput = document.getElementById('newBoardInput');
        const createButton = document.getElementById('createBoardButton');
        
        if (!boardInput || !createButton) return;

        const boardName = boardInput.value.trim();
        
        if (!boardName) {
            this.showError('Please enter a board name');
            boardInput.focus();
            return;
        }

        // Disable button during creation
        createButton.disabled = true;
        createButton.innerHTML = `
            <div class="loading-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>
            Creating...
        `;

        try {
            const formData = new FormData();
            formData.append('name', boardName);
            formData.append('csrfmiddlewaretoken', this.config.csrfToken);

            const response = await fetch(this.config.createBoardUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.config.csrfToken
                }
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                // Clear input
                boardInput.value = '';
                
                // Save to the newly created board
                await this.saveToBoard(data.board_id, data.board_name || boardName, true);
                
                // Add the new board to the list
                this.addBoardToList(data.board_id, data.board_name || boardName, 1);
            } else {
                this.showError(data.message || 'Failed to create board');
            }
        } catch (error) {
            console.error('Error creating board:', error);
            this.showError('Failed to create board');
        } finally {
            // Re-enable button
            createButton.disabled = false;
            createButton.innerHTML = `
                <i class="bi bi-plus-lg"></i>
                Create
            `;
        }
    }

    addBoardToList(boardId, boardName, count = 0) {
        const boardsGrid = document.getElementById('boardsGrid');
        if (!boardsGrid) return;

        // Remove "no boards" message if it exists
        const noBoards = boardsGrid.querySelector('.no-boards-message');
        if (noBoards) {
            noBoards.remove();
        }

        // Create new board card
        const newBoard = { id: boardId, name: boardName, count: count };
        const boardCard = this.createBoardCard(newBoard);
        
        // Add to top of list
        boardsGrid.insertBefore(boardCard, boardsGrid.firstChild);
    }

    async saveToBoard(boardId, boardName, isNewBoard = false) {
        if (!this.currentImageData) {
            this.showError('No image selected');
            return;
        }

        try {
            const response = await fetch(this.config.saveToBoardUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify({
                    board_id: boardId,
                    image_url: this.currentImageData.url
                })
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                const message = isNewBoard 
                    ? `Board "${boardName}" created and image saved!`
                    : `Saved to "${boardName}"!`;
                
                this.showSuccess(message);
                
                // Update board count in UI if not a new board
                if (!isNewBoard) {
                    this.updateBoardCount(boardId);
                }
                
                // Auto-close after success
                setTimeout(() => {
                    this.goBack();
                }, 2000);
            } else {
                this.showError(data.message || 'Failed to save image');
            }
        } catch (error) {
            console.error('Error saving to board:', error);
            this.showError('Failed to save image');
        }
    }

    updateBoardCount(boardId) {
        const boardCards = document.querySelectorAll('.board-card');
        boardCards.forEach(card => {
            if (card.querySelector('.board-name')?.textContent && 
                card.dataset.boardId === boardId.toString()) {
                const countSpan = card.querySelector('.board-count');
                if (countSpan) {
                    const currentCount = parseInt(countSpan.textContent) || 0;
                    countSpan.textContent = currentCount + 1;
                }
            }
        });
    }

    async loadSimilarImages() {
        if(!this.currentImageData || this.loading) return;
        this.loading=true;

        try {
            const params = new URLSearchParams({
                image_url: this.currentImageData.url,
                page: this.page,
                page_size: this.pageSize
            });
            const url = `${window.imageViewerConfig.imageDetailUrl}?${params.toString()}`;
            const res = await fetch(url, {credentials:'include'});
            const data = await res.json();
            if(data.status==='success'){
                this.hasNext = data.has_next;
                this.page += 1;
                const noMsg = document.getElementById('noSimilarImagesMsg');
                if(data.similar_images.length===0 && noMsg) noMsg.style.display='block';
                else if(noMsg) noMsg.style.display='none';

                const container = this.similarImagesContainer;
                data.similar_images.forEach(url=>{
                    const img=document.createElement('img');
                    img.src=url;
                    img.className='similar-image-thumb img-thumbnail';
                    img.loading='lazy';
                    img.onclick = ()=>this.loadImageDetails({url});
                    container.appendChild(img);
                });
            }
        } catch(err){ console.error(err); }
        finally{ this.loading=false; }
    }

    handleScroll(){
        if(!this.hasNext || this.loading) return;
        const scrollPos = window.innerHeight + window.scrollY;
        if(scrollPos >= document.body.offsetHeight-200) this.loadSimilarImages();
    }

    showSuccess(message) {
        const successElement = document.getElementById('successMessage');
        const errorElement = document.getElementById('errorMessage');
        
        if (errorElement) errorElement.classList.remove('show');
        
        if (successElement) {
            const messageText = successElement.querySelector('.message-text');
            if (messageText) messageText.textContent = message;
            
            successElement.classList.add('show');
            
            // Auto-hide after 3 seconds
            setTimeout(() => {
                successElement.classList.remove('show');
            }, 3000);
        }
    }

    showError(message) {
        const successElement = document.getElementById('successMessage');
        const errorElement = document.getElementById('errorMessage');
        
        if (successElement) successElement.classList.remove('show');
        
        if (errorElement) {
            const messageText = errorElement.querySelector('.message-text');
            if (messageText) messageText.textContent = message;
            
            errorElement.classList.add('show');
            
            // Auto-hide after 4 seconds
            setTimeout(() => {
                errorElement.classList.remove('show');
            }, 4000);
        }
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    goBack() {
        // Add exit animation
        document.body.style.animation = 'fadeOut 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        setTimeout(() => {
            if (this.config.homeUrl) {
                window.location.href = this.config.homeUrl;
            } else {
                window.history.back();
            }
        }, 300);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing FullScreenImageViewer');
    window.imageViewer = new FullScreenImageViewer();
});

// Also initialize if DOM is already loaded
if (document.readyState !== 'loading') {
    console.log('DOM already loaded, initializing FullScreenImageViewer immediately');
    window.imageViewer = new FullScreenImageViewer();
}

// Add exit animation CSS
const exitAnimationStyle = document.createElement('style');
exitAnimationStyle.textContent = `
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: scale(1);
        }
        to {
            opacity: 0;
            transform: scale(0.95);
        }
    }
`;
document.head.appendChild(exitAnimationStyle);