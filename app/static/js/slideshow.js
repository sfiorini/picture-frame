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
        isTransitioning: false,  // Prevent concurrent transitions
        currentPhoto: null  // Track current photo for orientation changes
    };

    // DOM elements
    var backgroundImgEl = null;
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

            // Update CSS transition duration for both images
            var transitionStyle = 'opacity ' + (config.fadeDuration / 1000) + 's ease-in-out';
            backgroundImgEl.style.webkitTransition = transitionStyle;
            backgroundImgEl.style.mozTransition = transitionStyle;
            backgroundImgEl.style.oTransition = transitionStyle;
            backgroundImgEl.style.transition = transitionStyle;
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
     * Build photo URL with API key and blur option
     */
    function buildPhotoUrl(photo, blur) {
        var url = photo.url + '?api_key=' + encodeURIComponent(config.apiKey);
        if (blur) {
            url += '&blur=true';
        }
        return url;
    }

    /**
     * Detect orientation of viewport or image
     * @param {number} width - Width of the element
     * @param {number} height - Height of the element
     * @returns {string} 'landscape' for width >= height, 'portrait' otherwise
     */
    function getOrientation(width, height) {
        return width >= height ? 'landscape' : 'portrait';
    }

    /**
     * Smart image positioning based on device and image orientation
     *
     * Logic:
     * - Landscape device + Portrait photo: Fill height, crop sides
     * - Portrait device + Landscape photo: Fill width, crop top/bottom
     * - Matching orientations: Fill based on aspect ratio comparison
     */
    function positionImage(imgEl, imgWidth, imgHeight) {
        var viewportWidth = window.innerWidth;
        var viewportHeight = window.innerHeight;

        var viewportOrientation = getOrientation(viewportWidth, viewportHeight);
        var imgOrientation = getOrientation(imgWidth, imgHeight);

        var displayWidth, displayHeight, top, left;

        // Handle mismatched orientations (cross-orientation)
        if (viewportOrientation !== imgOrientation) {
            if (viewportOrientation === 'landscape' && imgOrientation === 'portrait') {
                // Landscape device + Portrait photo: Fill height, crop sides
                displayHeight = viewportHeight;
                displayWidth = imgWidth * (viewportHeight / imgHeight);
                top = 0;
                left = (viewportWidth - displayWidth) / 2;
            } else {
                // Portrait device + Landscape photo: Fill width, crop top/bottom
                displayWidth = viewportWidth;
                displayHeight = imgHeight * (viewportWidth / imgWidth);
                top = (viewportHeight - displayHeight) / 2;
                left = 0;
            }
        } else {
            // Matching orientations - use aspect ratio comparison
            var imgAspect = imgWidth / imgHeight;
            var viewportAspect = viewportWidth / viewportHeight;

            if (imgAspect >= viewportAspect) {
                // Image wider - fill height, crop sides
                displayHeight = viewportHeight;
                displayWidth = imgWidth * (viewportHeight / imgHeight);
                top = 0;
                left = (viewportWidth - displayWidth) / 2;
            } else {
                // Image narrower - fill width, crop top/bottom
                displayWidth = viewportWidth;
                displayHeight = imgHeight * (viewportWidth / imgWidth);
                top = (viewportHeight - displayHeight) / 2;
                left = 0;
            }
        }

        imgEl.style.width = displayWidth + 'px';
        imgEl.style.height = displayHeight + 'px';
        imgEl.style.left = left + 'px';
        imgEl.style.top = top + 'px';
        imgEl.style.display = 'block';
    }

    /**
     * Display next photo with fade transition and blur background
     */
    function showNextPhoto() {
        if (state.isTransitioning) {
            return;
        }

        if (state.photos.length === 0) {
            loadingEl.textContent = 'No photos found';
            return;
        }

        state.isTransitioning = true;

        state.currentIndex = (state.currentIndex + 1) % state.photos.length;
        var photo = state.photos[state.currentIndex];
        state.currentPhoto = photo;

        var photoUrl = buildPhotoUrl(photo, false);
        var blurUrl = buildPhotoUrl(photo, true);

        if (state.isFirstLoad) {
            loadingEl.style.display = 'block';
        }
        hideError();

        // Load both images in parallel
        var imagesLoaded = 0;
        var sharpImg = null;
        var blurImg = null;

        function checkLoadComplete() {
            imagesLoaded++;
            if (imagesLoaded === 2) {
                loadingEl.style.display = 'none';
                state.isFirstLoad = false;

                if (sharpImg && blurImg) {
                    displayPhotoWithBlur(sharpImg, blurImg);
                }
            }
        }

        // Load sharp image
        preloadImage(photoUrl, function(err, img) {
            if (err) {
                showError('Failed to load photo: ' + photo.name);
                setTimeout(function() {
                    state.isTransitioning = false;
                    showNextPhoto();
                }, 3000);
                return;
            }
            sharpImg = img;
            checkLoadComplete();
        });

        // Load blur image (non-critical - continue without it if it fails)
        preloadImage(blurUrl, function(err, img) {
            blurImg = err ? null : img;
            checkLoadComplete();
        });
    }

    /**
     * Display photo with blur background
     */
    function displayPhotoWithBlur(sharpImg, blurImg) {
        var currentOpacity = currentImgEl.style.opacity || '0';
        var hasCurrentImage = currentOpacity !== '' && currentOpacity !== '0';

        if (hasCurrentImage) {
            // Fade out both layers
            currentImgEl.style.opacity = '0';
            backgroundImgEl.style.opacity = '0';

            setTimeout(function() {
                // Update background - always show blur
                if (blurImg) {
                    backgroundImgEl.src = blurImg.src;
                    backgroundImgEl.style.display = 'block';
                    backgroundImgEl.style.opacity = '1';
                }

                // Update foreground
                positionImage(currentImgEl, sharpImg.width, sharpImg.height);
                currentImgEl.src = sharpImg.src;

                setTimeout(function() {
                    currentImgEl.style.opacity = '1';
                }, 50);
            }, config.fadeDuration + 50);
        } else {
            // First load - always show blur background
            if (blurImg) {
                backgroundImgEl.src = blurImg.src;
                backgroundImgEl.style.display = 'block';
                backgroundImgEl.style.opacity = '1';
            }

            positionImage(currentImgEl, sharpImg.width, sharpImg.height);
            currentImgEl.src = sharpImg.src;

            setTimeout(function() {
                currentImgEl.style.opacity = '1';
            }, 50);
        }

        // Schedule next photo
        setTimeout(function() {
            state.isTransitioning = false;
            showNextPhoto();
        }, config.delay + config.fadeDuration);
    }

    /**
     * Handle device orientation changes
     * Re-positions the current image when device rotates
     */
    function handleOrientationChange() {
        setTimeout(function() {
            // Reposition foreground image
            if (currentImgEl && currentImgEl.src && currentImgEl.complete) {
                positionImage(currentImgEl, currentImgEl.naturalWidth, currentImgEl.naturalHeight);
            }
        }, 100);
    }

    /**
     * Initialize the slideshow
     */
    function init() {
        // Get DOM elements
        backgroundImgEl = document.getElementById('background-image');
        currentImgEl = document.getElementById('current-image');
        loadingEl = document.getElementById('loading');
        errorEl = document.getElementById('error');

        // Verify elements exist
        if (!backgroundImgEl || !currentImgEl || !loadingEl || !errorEl) {
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

        // Add orientation change listeners (iOS 5.1.1 compatible)
        if (window.addEventListener) {
            window.addEventListener('orientationchange', handleOrientationChange);
            window.addEventListener('resize', handleOrientationChange);
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
