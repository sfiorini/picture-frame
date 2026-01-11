/**
 * Picture Frame Slideshow
 * ES5 JavaScript for iOS 5.1.1 Safari compatibility
 */

(function() {
    'use strict';

    // Configuration
    var config = {
        apiKey: '',
        delay: 10000,
        fadeDuration: 1000,
        displayOrder: 'random'
    };

    // State
    var state = {
        photos: [],
        currentIndex: 0,
        isLoading: false,
        isFirstLoad: true,
        isTransitioning: false  // Prevent concurrent transitions
    };

    // DOM elements
    var currentImgEl = null;
    var loadingEl = null;
    var errorEl = null;

    /**
     * XMLHttpRequest wrapper for ES5 compatibility
     */
    function makeRequest(url, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        callback(null, data);
                    } catch (e) {
                        callback(e, null);
                    }
                } else {
                    callback(new Error('Request failed: ' + xhr.status), null);
                }
            }
        };
        xhr.timeout = 30000;
        xhr.ontimeout = function() {
            callback(new Error('Request timeout'), null);
        };
        xhr.send();
    }

    /**
     * Load configuration from server
     */
    function loadConfig(callback) {
        makeRequest('/api/config', function(err, data) {
            if (err) {
                showError('Failed to load configuration');
                return;
            }
            config.delay = data.delay || 10000;
            config.fadeDuration = data.fadeDuration || 1000;
            config.displayOrder = data.displayOrder || 'random';

            // Update CSS transition duration
            var transitionStyle = 'opacity ' + (config.fadeDuration / 1000) + 's ease-in-out';
            currentImgEl.style.webkitTransition = transitionStyle;
            currentImgEl.style.mozTransition = transitionStyle;
            currentImgEl.style.oTransition = transitionStyle;
            currentImgEl.style.transition = transitionStyle;

            callback();
        });
    }

    /**
     * Load photo list from server
     */
    function loadPhotos(callback) {
        var url = '/api/photos?api_key=' + encodeURIComponent(config.apiKey) + '&order=' + config.displayOrder;
        makeRequest(url, function(err, data) {
            if (err) {
                showError('Failed to load photos: ' + (err.message || err));
                return;
            }
            state.photos = data.photos || [];
            callback();
        });
    }

    /**
     * Get API key from URL parameter or localStorage
     */
    function getApiKey() {
        // Check URL parameter first
        var urlParams = {};
        var parts = window.location.search.substring(1).split('&');
        for (var i = 0; i < parts.length; i++) {
            var pair = parts[i].split('=');
            if (pair.length === 2) {
                urlParams[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
            }
        }

        if (urlParams.api_key) {
            // Save to localStorage for future requests
            if (typeof localStorage !== 'undefined') {
                try {
                    localStorage.setItem('pictureframe_api_key', urlParams.api_key);
                } catch (e) {
                    // localStorage might be disabled
                }
            }
            return urlParams.api_key;
        }

        // Check localStorage
        if (typeof localStorage !== 'undefined') {
            try {
                var stored = localStorage.getItem('pictureframe_api_key');
                if (stored) {
                    return stored;
                }
            } catch (e) {
                // localStorage might be disabled
            }
        }

        return null;
    }

    /**
     * Show error message
     */
    function showError(message) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        loadingEl.style.display = 'none';

        // Auto-hide after 5 seconds
        setTimeout(function() {
            errorEl.style.display = 'none';
        }, 5000);
    }

    /**
     * Hide error message
     */
    function hideError() {
        errorEl.style.display = 'none';
    }

    /**
     * Preload image
     */
    function preloadImage(url, callback) {
        var img = new Image();
        img.onload = function() {
            callback(null, img);
        };
        img.onerror = function() {
            callback(new Error('Failed to load image'));
        };
        img.src = url;
    }

    /**
     * Build photo URL with API key
     */
    function buildPhotoUrl(photo) {
        return photo.url + '?api_key=' + encodeURIComponent(config.apiKey);
    }

    /**
     * Smart image positioning based on orientation
     * - Landscape (width >= height): fill height, center horizontally, crop sides
     * - Portrait (height > width): fill width, center vertically, crop top/bottom
     */
    function positionImage(imgEl, imgWidth, imgHeight) {
        var viewportWidth = window.innerWidth;
        var viewportHeight = window.innerHeight;
        var imgAspect = imgWidth / imgHeight;
        var viewportAspect = viewportWidth / viewportHeight;

        var displayWidth, displayHeight, top, left;

        if (imgAspect >= viewportAspect) {
            // Image is landscape or square - fill height, crop sides
            displayHeight = viewportHeight;
            displayWidth = imgWidth * (viewportHeight / imgHeight);
            top = 0;
            left = (viewportWidth - displayWidth) / 2;
        } else {
            // Image is portrait - fill width, crop top/bottom
            displayWidth = viewportWidth;
            displayHeight = imgHeight * (viewportWidth / imgWidth);
            top = (viewportHeight - displayHeight) / 2;
            left = 0;
        }

        imgEl.style.width = displayWidth + 'px';
        imgEl.style.height = displayHeight + 'px';
        imgEl.style.left = left + 'px';
        imgEl.style.top = top + 'px';
        imgEl.style.display = 'block';
    }

    /**
     * Display next photo with fade transition
     */
    function showNextPhoto() {
        // Prevent concurrent transitions
        if (state.isTransitioning) {
            return;
        }

        if (state.photos.length === 0) {
            loadingEl.textContent = 'No photos found';
            return;
        }

        state.isTransitioning = true;

        // Get next photo (with wraparound)
        state.currentIndex = (state.currentIndex + 1) % state.photos.length;
        var photo = state.photos[state.currentIndex];
        var photoUrl = buildPhotoUrl(photo);

        // Only show loading on first load, not on transitions
        if (state.isFirstLoad) {
            loadingEl.style.display = 'block';
        }
        hideError();

        // Preload the next image
        preloadImage(photoUrl, function(err, img) {
            // Hide loading after preload completes
            loadingEl.style.display = 'none';
            state.isFirstLoad = false;

            if (err) {
                showError('Failed to load photo: ' + photo.name);
                // Skip to next photo after delay
                setTimeout(function() {
                    state.isTransitioning = false;
                    showNextPhoto();
                }, 3000);
                return;
            }

            // Check if current image is displayed
            var currentOpacity = currentImgEl.style.opacity || '0';
            var hasCurrentImage = currentOpacity !== '' && currentOpacity !== '0';

            // Position and set the new image
            positionImage(currentImgEl, img.width, img.height);
            currentImgEl.src = photoUrl;

            if (hasCurrentImage) {
                // Fade out current image first
                currentImgEl.style.opacity = '0';

                // After fade out, fade in new image
                setTimeout(function() {
                    currentImgEl.style.opacity = '1';
                }, config.fadeDuration + 50);
            } else {
                // No image currently displayed, show directly
                setTimeout(function() {
                    currentImgEl.style.opacity = '1';
                }, 50);
            }

            // Schedule next photo (wait for current transition + display delay)
            setTimeout(function() {
                state.isTransitioning = false;
                showNextPhoto();
            }, config.delay + config.fadeDuration);
        });
    }

    /**
     * Initialize the slideshow
     */
    function init() {
        // Get DOM elements
        currentImgEl = document.getElementById('current-image');
        loadingEl = document.getElementById('loading');
        errorEl = document.getElementById('error');

        // Verify elements exist
        if (!currentImgEl || !loadingEl || !errorEl) {
            alert('Error: Required DOM elements not found');
            return;
        }

        // Get API key
        config.apiKey = getApiKey();

        if (!config.apiKey) {
            showError('Please provide API key via ?api_key= parameter');
            loadingEl.style.display = 'none';
            return;
        }

        // Load config and photos, then start slideshow
        loadConfig(function() {
            loadPhotos(function() {
                // Start with first photo
                if (state.photos.length > 0) {
                    // Start at -1 so first increment gives us index 0
                    state.currentIndex = -1;
                    showNextPhoto();
                } else {
                    loadingEl.textContent = 'No photos found';
                }
            });
        });
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
