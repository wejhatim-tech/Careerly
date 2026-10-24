const aiForms = document.querySelectorAll('.ai-form');
const aiButtons = document.querySelectorAll('.ai-submit-btn');

const aiResult = document.getElementById('ai-result');

const resultTabs = document.querySelectorAll('.ai-result-tab');
const savedResults = document.querySelectorAll('.ai-saved-result');

const coverModeButtons = document.querySelectorAll('.cover-mode-btn');
const coverPdfBox = document.querySelector('.cover-pdf-box');
const coverTextBox = document.querySelector('.cover-text-box');

let aiBusy = false;


// Disable or enable all AI submit buttons
function setAiBusy(isBusy) {
    aiBusy = isBusy;

    aiButtons.forEach(function(button) {
        button.disabled = isBusy;
    });
}


// Switch between PDF and text for cover letter
coverModeButtons.forEach(function(button) {
    button.addEventListener('click', function() {
        if (aiBusy) {
            return;
        }

        const mode = button.dataset.mode;

        coverModeButtons.forEach(function(modeButton) {
            modeButton.classList.remove('active');
        });

        button.classList.add('active');

        if (mode === 'pdf') {
            coverPdfBox.classList.remove('d-none');
            coverTextBox.classList.add('d-none');
        } else {
            coverPdfBox.classList.add('d-none');
            coverTextBox.classList.remove('d-none');
        }
    });
});


// Switch between saved AI result tabs
resultTabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
        const selectedTool = tab.dataset.resultTab;

        showSavedResult(selectedTool);
    });
});


function showSavedResult(tool) {
    resultTabs.forEach(function(tab) {
        tab.classList.toggle(
            'active',
            tab.dataset.resultTab === tool
        );
    });

    savedResults.forEach(function(resultBox) {
        resultBox.classList.toggle(
            'active',
            resultBox.dataset.result === tool
        );
    });
}


// Submit AI tools
aiForms.forEach(function(form) {
    form.addEventListener('submit', function(event) {
        event.preventDefault();

        if (aiBusy) {
            return;
        }

        const tool = form.dataset.tool;
        const jobId = form.dataset.job;
        const jobUrl = form.dataset.jobUrl;

        const submitButton = form.querySelector(
            '.ai-submit-btn'
        );

        const fileInput = form.querySelector(
            '.ai-file'
        );

        const formData = new FormData();

        formData.append('tool', tool);
        formData.append('job_id', jobId);
        formData.append('job_url', jobUrl);

        formData.append(
            'csrfmiddlewaretoken',
            document.querySelector(
                '[name=csrfmiddlewaretoken]'
            ).value
        );


        // CV requires a PDF
        if (tool === 'cv') {
            if (!fileInput || !fileInput.files.length) {
                showMessage(
                    'Please upload your CV as a PDF first.',
                    true
                );
                return;
            }

            formData.append(
                'file',
                fileInput.files[0]
            );
        }


        // Cover letter accepts PDF or text
        if (tool === 'cover_letter') {
            const activeMode = form.querySelector(
                '.cover-mode-btn.active'
            );

            if (!activeMode) {
                showMessage(
                    'Please choose PDF or text.',
                    true
                );
                return;
            }

            const mode = activeMode.dataset.mode;

            if (mode === 'pdf') {
                if (!fileInput || !fileInput.files.length) {
                    showMessage(
                        'Please upload your cover letter as a PDF.',
                        true
                    );
                    return;
                }

                formData.append(
                    'file',
                    fileInput.files[0]
                );
            } else {
                const textArea = form.querySelector(
                    '.cover-letter-text'
                );

                const textContent = textArea.value.trim();

                if (!textContent) {
                    showMessage(
                        'Please write or paste your cover letter.',
                        true
                    );
                    return;
                }

                formData.append(
                    'text_content',
                    textContent
                );
            }
        }


        const originalButtonText = submitButton.textContent;

        setAiBusy(true);

        submitButton.textContent = 'Working...';

        showMessage(
            'AI is working, please wait...',
            false
        );


        fetch('/job/ai', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                hideMessage();

                updateSavedResult(
                    tool,
                    data.result,
                    data.file_name || ''
                );

                updateSavedState(
                    form,
                    tool,
                    data.file_name || ''
                );

                showSavedResult(tool);
            } else {
                showMessage(
                    data.message || 'Something went wrong.',
                    true
                );
            }
        })
        .catch(function() {
            showMessage(
                'Something went wrong, please try again.',
                true
            );
        })
        .finally(function() {
            setAiBusy(false);

            submitButton.textContent = originalButtonText;
        });
    });
});


// Update saved AI result immediately
function updateSavedResult(tool, result, fileName) {
    const resultBox = document.getElementById(
        'result-' + tool
    );

    if (!resultBox) {
        return;
    }

    resultBox.innerHTML = '';


    const meta = document.createElement('div');

    meta.className = 'ai-result-meta';


    const savedLabel = document.createElement('span');

    savedLabel.textContent = 'Latest saved result';

    meta.appendChild(savedLabel);


    if (tool === 'cv' && fileName) {
        const fileLabel = document.createElement('span');

        fileLabel.textContent = fileName;

        meta.appendChild(fileLabel);
    }


    if (tool === 'cover_letter') {
        const coverLabel = document.createElement('span');

        coverLabel.textContent = fileName
            ? fileName
            : 'Written text';

        meta.appendChild(coverLabel);
    }


    const content = document.createElement('div');

    content.className = 'ai-result-content';

    content.textContent = result;

    content.style.whiteSpace = 'pre-line';


    resultBox.appendChild(meta);
    resultBox.appendChild(content);
}


// Update Saved badge and saved file name
function updateSavedState(form, tool, fileName) {
    let badge = form.querySelector(
        '.ai-saved-badge'
    );

    const header = form.querySelector(
        '.ai-tool-header'
    );


    if (!badge && header) {
        badge = document.createElement('span');

        badge.className = 'ai-saved-badge';

        header.appendChild(badge);
    }


    if (badge) {
        badge.textContent = 'Saved ✓';
    }


    if (
        (tool === 'cv' || tool === 'cover_letter') &&
        fileName
    ) {
        updateSavedFile(
            form,
            tool,
            fileName
        );
    }


    if (tool === 'interview') {
        let savedNote = form.querySelector(
            '.ai-saved-note'
        );

        if (!savedNote) {
            savedNote = document.createElement('div');

            savedNote.className = 'ai-saved-note';

            savedNote.textContent =
                'Your latest questions are saved below.';

            const button = form.querySelector(
                '.ai-submit-btn'
            );

            form.insertBefore(
                savedNote,
                button
            );
        }
    }
}


// Show the latest saved file name
function updateSavedFile(form, tool, fileName) {
    let savedFile = form.querySelector(
        '.ai-saved-file'
    );


    if (!savedFile) {
        savedFile = document.createElement('div');

        savedFile.className = 'ai-saved-file';


        const label = document.createElement('span');

        label.textContent = tool === 'cv'
            ? 'Last CV'
            : 'Last file';


        const name = document.createElement('strong');

        savedFile.appendChild(label);
        savedFile.appendChild(name);


        const fileInput = form.querySelector(
            '.ai-file'
        );

        const filePicker = fileInput
            ? fileInput.nextElementSibling
            : null;


        if (filePicker) {
            form.insertBefore(
                savedFile,
                fileInput
            );
        }
    }


    const name = savedFile.querySelector(
        'strong'
    );

    if (name) {
        name.textContent = fileName;
    }
}


// Show selected file name
document.querySelectorAll('.ai-file').forEach(function(input) {
    input.addEventListener('change', function() {
        const form = input.closest('.ai-form');

        const nameBox = form.querySelector(
            '.file-name'
        );

        if (!nameBox) {
            return;
        }

        nameBox.textContent = input.files.length
            ? input.files[0].name
            : 'No file chosen';
    });
});


// Show loading or error message
function showMessage(text, isError) {
    if (!aiResult) {
        return;
    }

    aiResult.textContent = text;

    aiResult.className = isError
        ? 'ai-result alert alert-danger'
        : 'ai-result result-box';

    aiResult.style.display = 'block';
}


// Hide temporary AI message
function hideMessage() {
    if (!aiResult) {
        return;
    }

    aiResult.textContent = '';
    aiResult.className = 'ai-result';
    aiResult.style.display = 'none';
}