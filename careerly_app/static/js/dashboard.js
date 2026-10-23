const findJobsBtn = document.getElementById('find-jobs-btn');
const jobsLoading = document.getElementById('jobs-loading');
const loadingText = document.getElementById('loading-text');
const jobsResults = document.getElementById('jobs-results');

const loadingMessages = [
    'Reading your career profile...',
    'Checking your skills and preferences...',
    'Searching current job opportunities...',
    'Comparing jobs with your profile...',
    'Finding your best matches...',
    'Almost done...'
];

let loadingInterval;
let loadingMessageIndex = 0;

function startLoading() {
    jobsLoading.classList.remove('d-none');
    jobsResults.innerHTML = '';
    findJobsBtn.disabled = true;

    loadingMessageIndex = 0;
    loadingText.textContent = loadingMessages[loadingMessageIndex];

    loadingInterval = setInterval(function() {
        loadingMessageIndex++;

        if (loadingMessageIndex >= loadingMessages.length) {
            loadingMessageIndex = loadingMessages.length - 1;
        }

        loadingText.textContent = loadingMessages[loadingMessageIndex];
    }, 2500);
}

function stopLoading() {
    clearInterval(loadingInterval);
    jobsLoading.classList.add('d-none');
    findJobsBtn.disabled = false;
}

if (findJobsBtn) {
    findJobsBtn.addEventListener('click', function() {
        startLoading();

        fetch('/dashboard/find-jobs', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            stopLoading();

            if (!data.success) {
                jobsResults.innerHTML = `
                    <div class="dashboard-empty">
                        <h3>Could not find jobs</h3>
                        <p>${data.message}</p>
                    </div>
                `;
                return;
            }

            displayJobs(data.jobs);
        })
        .catch(() => {
            stopLoading();

            jobsResults.innerHTML = `
                <div class="dashboard-empty">
                    <h3>Something went wrong</h3>
                    <p>Please try again.</p>
                </div>
            `;
        });
    });
}

function displayJobs(jobs) {
    jobsResults.innerHTML = '';

    jobs.forEach(function(job) {
        const jobCard = document.createElement('div');
        jobCard.classList.add('dashboard-job-card');

        jobCard.innerHTML = `
            <div class="job-card-top">
                <div>
                    <h3>${job.title}</h3>
                    <p>${job.company}</p>
                </div>

                <span class="job-match match-${job.match.toLowerCase()}">
                    ${job.match} Match
                </span>
            </div>

            <p class="job-location">
                ${job.location || 'Location not available'}
            </p>

            <p class="job-reason">
                ${job.reason || ''}
            </p>

            <a href="/job?id=${encodeURIComponent(job.job_id)}" class="btn details-btn">
                View Details
            </a>
        `;

        jobsResults.appendChild(jobCard);
    });
}

function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === name + '=') {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );

                break;
            }
        }
    }

    return cookieValue;
}

const viewAllApplicationsBtn = document.getElementById('view-all-applications');

if (viewAllApplicationsBtn) {
    viewAllApplicationsBtn.addEventListener('click', function() {
        const extraApplications = document.querySelectorAll('.extra-application');

        extraApplications.forEach(function(application) {
            application.classList.toggle('d-none');
        });

        if (viewAllApplicationsBtn.textContent.trim() === 'View All Applications') {
            viewAllApplicationsBtn.textContent = 'Show Less';
        } else {
            viewAllApplicationsBtn.textContent = 'View All Applications';
        }
    });
}