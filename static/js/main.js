// Main JavaScript file for Credit Lense application

document.addEventListener('DOMContentLoaded', function() {
    console.log('Credit Lense application loaded');

    // Handle document upload form submission
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission

            const fileInput = document.getElementById('file-input');
            if (fileInput && fileInput.files.length === 0) {
                alert('Please select a file to upload');
                return;
            }

            // Create FormData object from the form
            const formData = new FormData(this);

            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.textContent;
            submitButton.textContent = 'Uploading...';
            submitButton.disabled = true;

            // Submit the form via fetch
            fetch('/documents/', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Show success message
                alert(data.message || 'Document uploaded successfully!');

                // Redirect to documents page
                window.location.href = '/documents';
            })
            .catch(error => {
                console.error('Error uploading document:', error);
                alert('An error occurred while uploading the document');
            })
            .finally(() => {
                // Reset button state
                submitButton.textContent = originalButtonText;
                submitButton.disabled = false;
            });
        });
    }

    // Handle document deletion
    const deleteButtons = document.querySelectorAll('.delete-document');
    if (deleteButtons.length > 0) {
        deleteButtons.forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();

                if (confirm('Are you sure you want to delete this document?')) {
                    const documentId = this.getAttribute('data-id');
                    try {
                        const response = await fetch(`/documents/${documentId}`, {
                            method: 'DELETE'
                        });

                        if (response.ok) {
                            // Remove the document from the UI
                            const documentRow = this.closest('tr');
                            if (documentRow) {
                                documentRow.remove();
                            }

                            // Show success message
                            alert('Document deleted successfully');
                        } else {
                            const data = await response.json();
                            alert(`Error: ${data.detail || 'Failed to delete document'}`);
                        }
                    } catch (error) {
                        console.error('Error deleting document:', error);
                        alert('An error occurred while deleting the document');
                    }
                }
            });
        });
    }

    // Handle memo generation with selected LLM provider
    const generateButtons = document.querySelectorAll('.generate-memo');
    if (generateButtons.length > 0) {
        generateButtons.forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();

                const documentId = this.getAttribute('data-id');
                const providerSelect = document.getElementById(`provider-${documentId}`);
                const provider = providerSelect ? providerSelect.value : 'google';

                try {
                    // Show loading state
                    this.textContent = 'Generating...';
                    this.disabled = true;

                    // Include the selected provider in the request
                    const response = await fetch(`/generate-memo/${documentId}?provider=${provider}`, {
                        method: 'POST'
                    });

                    if (response.ok) {
                        const data = await response.json();
                        alert(data.message);

                        // Redirect to memos page after a short delay
                        setTimeout(() => {
                            window.location.href = '/memos';
                        }, 1500);
                    } else {
                        const data = await response.json();
                        alert(`Error: ${data.detail || 'Failed to generate memo'}`);
                    }
                } catch (error) {
                    console.error('Error generating memo:', error);
                    alert('An error occurred while generating the memo');
                } finally {
                    // Reset button state
                    this.textContent = 'Generate Memo';
                    this.disabled = false;
                }
            });
        });
    }

    // Handle LLM comparison
    const compareButtons = document.querySelectorAll('.compare-llms');
    if (compareButtons.length > 0) {
        compareButtons.forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();

                const documentId = this.getAttribute('data-id');

                try {
                    // Show loading state
                    this.textContent = 'Comparing...';
                    this.disabled = true;

                    // Generate memo with Google Gemini
                    const googleResponse = await fetch(`/generate-memo/${documentId}?provider=google`, {
                        method: 'POST'
                    });

                    if (!googleResponse.ok) {
                        const data = await googleResponse.json();
                        throw new Error(data.detail || 'Failed to generate memo with Google Gemini');
                    }

                    // Generate memo with OpenAI
                    const openaiResponse = await fetch(`/generate-memo/${documentId}?provider=openai`, {
                        method: 'POST'
                    });

                    if (!openaiResponse.ok) {
                        const data = await openaiResponse.json();
                        throw new Error(data.detail || 'Failed to generate memo with OpenAI');
                    }

                    alert('Memos generated with both Google Gemini and OpenAI. Check the memos page to compare them.');

                    // Redirect to memos page after a short delay
                    setTimeout(() => {
                        window.location.href = '/memos';
                    }, 1500);
                } catch (error) {
                    console.error('Error comparing LLMs:', error);
                    alert(`An error occurred while comparing LLMs: ${error.message}`);
                } finally {
                    // Reset button state
                    this.textContent = 'Compare LLMs';
                    this.disabled = false;
                }
            });
        });
    }

    // Handle memo deletion
    const deleteMemoButtons = document.querySelectorAll('.delete-memo');
    if (deleteMemoButtons.length > 0) {
        deleteMemoButtons.forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();

                if (confirm('Are you sure you want to delete this memo?')) {
                    const memoId = this.getAttribute('data-id');
                    try {
                        const response = await fetch(`/memos/${memoId}`, {
                            method: 'DELETE'
                        });

                        if (response.ok) {
                            // Remove the memo from the UI
                            const memoRow = this.closest('tr');
                            if (memoRow) {
                                memoRow.remove();
                            }

                            // Show success message
                            alert('Memo deleted successfully');
                        } else {
                            const data = await response.json();
                            alert(`Error: ${data.detail || 'Failed to delete memo'}`);
                        }
                    } catch (error) {
                        console.error('Error deleting memo:', error);
                        alert('An error occurred while deleting the memo');
                    }
                }
            });
        });
    }
});
