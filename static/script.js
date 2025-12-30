// Onboarding Logic
let currentStep = 1;
const totalSteps = 3;
let autoAdvanceInterval = null;

function nextStep() {
    if (currentStep < totalSteps) {
        document.querySelector(`.onboarding-step[data-step="${currentStep}"]`).classList.remove('active');
        currentStep++;
        document.querySelector(`.onboarding-step[data-step="${currentStep}"]`).classList.add('active');
    } else {
        skipOnboarding();
    }
}

function skipOnboarding() {
    const onboarding = document.getElementById('onboarding');
    onboarding.classList.add('hidden');
    if (autoAdvanceInterval) {
        clearInterval(autoAdvanceInterval);
        autoAdvanceInterval = null;
    }
    setTimeout(() => {
        onboarding.style.display = 'none';
    }, 500);
    
    // Check API key status
    checkApiKey();
}

function showOnboarding() {
    const onboarding = document.getElementById('onboarding');
    onboarding.style.display = 'flex';
    onboarding.classList.remove('hidden');
    currentStep = 1;
    
    // Reset all steps
    document.querySelectorAll('.onboarding-step').forEach(step => {
        step.classList.remove('active');
    });
    document.querySelector('.onboarding-step[data-step="1"]').classList.add('active');
    
    // Start auto-advance
    if (autoAdvanceInterval) {
        clearInterval(autoAdvanceInterval);
    }
    
    setTimeout(() => {
        autoAdvanceInterval = setInterval(() => {
            if (currentStep < totalSteps) {
                nextStep();
            } else {
                clearInterval(autoAdvanceInterval);
                autoAdvanceInterval = null;
            }
        }, 3000);
    }, 2000);
}

// Check if onboarding was already shown (only on first load)
if (localStorage.getItem('onboardingShown')) {
    document.getElementById('onboarding').style.display = 'none';
    checkApiKey();
} else {
    // Show onboarding on first load
    showOnboarding();
    localStorage.setItem('onboardingShown', 'true');
}

// API Key Check
async function checkApiKey() {
    const statusIndicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.status-text');
    
    try {
        const response = await fetch('/api/check-api-key');
        const data = await response.json();
        
        if (data.has_api_key) {
            statusIndicator.classList.add('active');
            statusText.textContent = 'Gemini AI ready! You can upload your photo.';
        } else {
            statusText.textContent = 'API key not found. Add GEMINI_API_KEY to .env file.';
        }
    } catch (error) {
        statusText.textContent = 'API check failed.';
        console.error('API check error:', error);
    }
}

// File Upload Logic
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');

// Click to upload
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file!');
        return;
    }
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB!');
        return;
    }
    
    // Show loading
    uploadSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('An error occurred: ' + error.message);
        resetApp();
    }
}

function displayResults(data) {
    // Hide loading, show results
    loadingSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
    
    // Display image
    document.getElementById('previewImage').src = data.image;
    
    // Check if single item or combination
    const isSingleItem = data.is_single_item === true;
    const compatibleItemsSection = document.getElementById('compatibleItemsSection');
    const outfitAssessmentSection = document.getElementById('outfitAssessmentSection');
    const itemColorSuggestionsSection = document.getElementById('itemColorSuggestionsSection');
    
    // Show/hide sections based on item type
    if (isSingleItem) {
        compatibleItemsSection.classList.remove('hidden');
        outfitAssessmentSection.classList.add('hidden');
        itemColorSuggestionsSection.classList.add('hidden'); // Tek parça varsa renk önerileri gösterme
    } else {
        compatibleItemsSection.classList.add('hidden');
        outfitAssessmentSection.classList.remove('hidden');
        itemColorSuggestionsSection.classList.remove('hidden'); // Kombin varsa renk önerilerini göster
    }
    
    // Display current outfit analysis
    const outfitInfo = document.getElementById('outfitInfo');
    if (data.current_outfit) {
        const itemsHtml = (data.current_outfit.items || []).map(item => 
            `<div class="outfit-item">
                <strong>${item.name}:</strong> 
                <span class="color-badge" style="background-color: ${item.color}">${item.color_name || item.color}</span>
            </div>`
        ).join('');
        
        const colorsHtml = (data.current_outfit.colors || []).map(color => 
            `<span class="color-badge" style="background-color: ${color}">${color}</span>`
        ).join('');
        
        outfitInfo.innerHTML = `
            <div class="outfit-description">
                <p><strong>${data.current_outfit.description || 'Analyzing...'}</strong></p>
                ${data.current_outfit.style ? `<p><strong>Style:</strong> ${data.current_outfit.style}</p>` : ''}
                ${itemsHtml ? `<div class="outfit-items">${itemsHtml}</div>` : ''}
                ${colorsHtml ? `<div class="outfit-colors"><strong>Overall Colors:</strong> ${colorsHtml}</div>` : ''}
            </div>
        `;
    } else {
        outfitInfo.innerHTML = '<p>Analyzing outfit...</p>';
    }
    
    // Display compatible items (for single item)
    if (isSingleItem && data.compatible_items && data.compatible_items.length > 0) {
        const compatibleItemsList = document.getElementById('compatibleItemsList');
        compatibleItemsList.innerHTML = '';
        
        data.compatible_items.forEach((compatibleItem, index) => {
            const card = document.createElement('div');
            card.className = 'compatible-item-card';
            card.style.animationDelay = `${index * 0.1}s`;
            
            const colorsHtml = (compatibleItem.suggested_colors || []).map(suggestion => `
                <div class="compatible-color-item">
                    <div class="compatible-color-swatch" style="background-color: ${suggestion.color}"></div>
                    <div class="compatible-color-info">
                        <div class="compatible-color-name">${suggestion.color_name || suggestion.color}</div>
                        <div class="compatible-color-reason">${suggestion.reason || ''}</div>
                    </div>
                </div>
            `).join('');
            
            card.innerHTML = `
                <div class="compatible-item-header">
                    <h4>${compatibleItem.item_type}</h4>
                </div>
                <div class="compatible-colors-list">
                    ${colorsHtml || '<p>No color suggestions found.</p>'}
                </div>
            `;
            
            compatibleItemsList.appendChild(card);
        });
    }
    
    // Display outfit assessment (for combinations)
    if (!isSingleItem && data.current_outfit) {
        const assessmentContent = document.getElementById('assessmentContent');
        const goodAspects = data.current_outfit.good_aspects || [];
        const needsImprovement = data.current_outfit.needs_improvement || [];
        
        const goodAspectsHtml = goodAspects.length > 0 ? `
            <div class="assessment-good">
                <h4>✅ Good Points</h4>
                <ul>
                    ${goodAspects.map(aspect => `<li>${aspect}</li>`).join('')}
                </ul>
            </div>
        ` : '';
        
        const needsImprovementHtml = needsImprovement.length > 0 ? `
            <div class="assessment-improve">
                <h4>🔧 Can Be Improved</h4>
                <ul>
                    ${needsImprovement.map(improve => `<li>${improve}</li>`).join('')}
                </ul>
            </div>
        ` : '';
        
        assessmentContent.innerHTML = `
            ${goodAspectsHtml}
            ${needsImprovementHtml}
            ${!goodAspectsHtml && !needsImprovementHtml ? '<p>Evaluating...</p>' : ''}
        `;
    }
    
    // Display color analysis
    const colorAnalysisContent = document.getElementById('colorAnalysisContent');
    colorAnalysisContent.innerHTML = '';
    
    if (data.color_analysis) {
        const analysis = data.color_analysis;
        const dominantColorsHtml = (analysis.dominant_colors || []).map(color => `
            <div class="analysis-color-item">
                <div class="analysis-color-swatch" style="background-color: ${color.hex}"></div>
                <div class="analysis-color-info">
                    <div class="analysis-color-name">${color.name || color.hex}</div>
                    ${color.percentage ? `<div class="analysis-color-percentage">${color.percentage}</div>` : ''}
                </div>
            </div>
        `).join('');
        
        colorAnalysisContent.innerHTML = `
            <div class="analysis-section">
                <h4>Dominant Colors</h4>
                <div class="analysis-colors-grid">${dominantColorsHtml || '<p>Analyzing colors...</p>'}</div>
            </div>
            <div class="analysis-section">
                <div class="analysis-item">
                    <strong>Color Harmony:</strong> ${analysis.color_harmony || 'Not specified'}
                </div>
                <div class="analysis-item">
                    <strong>Color Temperature:</strong> ${analysis.color_temperature || 'Not specified'}
                </div>
                <div class="analysis-item">
                    <strong>Color Contrast:</strong> ${analysis.color_contrast || 'Not specified'}
                </div>
                ${analysis.overall_assessment ? `
                    <div class="analysis-assessment">
                        <strong>Overall Assessment:</strong>
                        <p>${analysis.overall_assessment}</p>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    // Display item color suggestions (only for combinations)
    if (!isSingleItem) {
        const itemSuggestionsList = document.getElementById('itemSuggestionsList');
        itemSuggestionsList.innerHTML = '';
        
        if (data.item_color_suggestions && data.item_color_suggestions.length > 0) {
            data.item_color_suggestions.forEach((item, index) => {
                const card = document.createElement('div');
                card.className = 'item-suggestion-card';
                card.style.animationDelay = `${index * 0.1}s`;
                
                const suggestedColorsHtml = (item.suggested_colors || []).map(suggestion => `
                    <div class="suggested-color-item">
                        <div class="suggested-color-swatch" style="background-color: ${suggestion.color}"></div>
                        <div class="suggested-color-info">
                            <div class="suggested-color-name">${suggestion.color_name || suggestion.color}</div>
                            <div class="suggested-color-reason">${suggestion.reason || ''}</div>
                        </div>
                    </div>
                `).join('');
                
                card.innerHTML = `
                    <div class="item-suggestion-header">
                        <h4>${item.item}</h4>
                        <div class="current-color-info">
                            <span>Current Color:</span>
                            <span class="color-badge" style="background-color: ${item.current_color}">
                                ${item.current_color_name || item.current_color}
                            </span>
                        </div>
                    </div>
                    <div class="suggested-colors-list">
                        ${suggestedColorsHtml || '<p>No color suggestions found.</p>'}
                    </div>
                `;
                
                itemSuggestionsList.appendChild(card);
            });
        } else {
            itemSuggestionsList.innerHTML = '<p>No color suggestions found.</p>';
        }
    }
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetApp() {
    uploadSection.classList.remove('hidden');
    loadingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    fileInput.value = '';
}

// Save when onboarding is skipped
const originalSkip = skipOnboarding;
skipOnboarding = function() {
    localStorage.setItem('onboardingShown', 'true');
    originalSkip();
};



