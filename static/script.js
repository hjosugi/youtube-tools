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
        
        // Handle file download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'youtube_downloads.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(false);
    }
    
    function setLoading(isLoading) {
        btn.disabled = isLoading;
        if (isLoading) {
            loader.style.display = 'block';
            btnText.textContent = 'Processing...';
        } else {
            loader.style.display = 'none';
            btnText.textContent = 'Download Zip';
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
