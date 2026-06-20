document.getElementById('download-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const form = e.target;
    // Check if at least one checkbox is selected
    const subtitles = document.getElementById('subtitles').checked;
    const mp3 = document.getElementById('mp3').checked;
    const mp4 = document.getElementById('mp4').checked;
    
    const btn = document.getElementById('submit-btn');
    const loader = document.getElementById('loader');
    const btnText = document.querySelector('.btn-text');
    const errorDiv = document.getElementById('error-message');
    
    if (!subtitles && !mp3 && !mp4) {
        showError('Please select at least one format to download.');
        return;
    }

    try {
        setLoading(true);
        hideError();
        
        const formData = new FormData(form);
        const response = await fetch('/api/download', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to process request.');
        }
        
        // Extract filename from Content-Disposition header if possible
        const disposition = response.headers.get('Content-Disposition');
        let filename = 'youtube_downloads.zip';
        if (disposition) {
            const utf8Regex = /filename\*=utf-8''([^;\n]*)/i;
            const matchesUtf8 = utf8Regex.exec(disposition);
            if (matchesUtf8 != null && matchesUtf8[1]) {
                filename = decodeURIComponent(matchesUtf8[1]);
            } else {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
        }
        
        // Handle file download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(false);
    }
    
    function setLoading(isLoading) {
        // Only re-enable btn if it isn't loading and at least one checkbox is checked
        if (isLoading) {
            btn.disabled = true;
            loader.style.display = 'block';
            btnText.textContent = 'Processing...';
        } else {
            const anyChecked = document.getElementById('subtitles').checked || 
                               document.getElementById('mp3').checked || 
                               document.getElementById('mp4').checked;
            btn.disabled = !anyChecked;
            loader.style.display = 'none';
            btnText.textContent = 'Download';
        }
    }
    
    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.className = 'error-visible';
    }
    
    function hideError() {
        errorDiv.className = 'error-hidden';
    }
});

// Real-time button disabling when no checkboxes are checked
const checkboxes = [
    document.getElementById('subtitles'),
    document.getElementById('mp3'),
    document.getElementById('mp4')
];
const submitBtn = document.getElementById('submit-btn');
const mp4Checkbox = document.getElementById('mp4');
const resolutionGroup = document.getElementById('resolution-group');

function updateButtonState() {
    const anyChecked = checkboxes.some(cb => cb.checked);
    submitBtn.disabled = !anyChecked;
    
    // Toggle resolution dropdown visibility
    if (mp4Checkbox.checked) {
        resolutionGroup.style.display = 'block';
    } else {
        resolutionGroup.style.display = 'none';
    }
}

checkboxes.forEach(cb => cb.addEventListener('change', updateButtonState));
updateButtonState();
