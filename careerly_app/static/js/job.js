const aiForms = document.querySelectorAll('.ai-form');
const aiResult = document.getElementById('ai-result');

aiForms.forEach(function(form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const button = form.querySelector('button');
        const fileInput = form.querySelector('.ai-file');
        const formData = new FormData();

        formData.append('tool', form.dataset.tool);
        formData.append('job_id', form.dataset.job);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        if (fileInput) {
            if (!fileInput.files.length) {
                showResult('Please upload a PDF file first.', true);
                return;
            }
            formData.append('file', fileInput.files[0]);
        }

        // Show loading while the AI is working
        const buttonText = button.textContent;
        button.disabled = true;
        button.textContent = 'Working...';
        showResult('AI is reading, please wait...', false);

        fetch('/job/ai', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResult(data.result, false);
            } else {
                showResult(data.message, true);
            }
        })
        .catch(() => {
            showResult('Something went wrong, please try again.', true);
        })
        .finally(() => {
            button.disabled = false;
            button.textContent = buttonText;
        });
    });
});

// Show the AI answer (textContent keeps it safe from XSS)
function showResult(text, isError) {
    aiResult.textContent = text;
    aiResult.className = isError ? 'ai-result alert alert-danger' : 'ai-result result-box';
}

// Show the chosen file name in English
document.querySelectorAll('.ai-file').forEach(function(input) {
    input.addEventListener('change', function() {
        const nameBox = input.parentElement.querySelector('.file-name');
        nameBox.textContent = input.files.length ? input.files[0].name : 'No file chosen';
    });
});