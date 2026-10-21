const skillForm = document.getElementById('skill-form');
const skillInput = document.getElementById('skill-input');
const skillsList = document.getElementById('skills-list');

if (skillForm) {
    skillForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData();
        formData.append('skill', skillInput.value);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        fetch('/profile/skill/add', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const noSkills = document.getElementById('no-skills');

                if (noSkills) {
                    noSkills.remove();
                }

                const skillItem = document.createElement('div');
                skillItem.classList.add('skill-item');
                skillItem.dataset.skillId = data.skill_id;

                skillItem.innerHTML = `
                    <span>${data.skill_name}</span>
                    <button type="button" class="skill-remove">×</button>
                `;

                skillsList.appendChild(skillItem);
                skillInput.value = '';
            }
        });
    });
}

if (skillsList) {
    skillsList.addEventListener('click', function(e) {
        if (e.target.classList.contains('skill-remove')) {
            const skillItem = e.target.closest('.skill-item');
            const skillId = skillItem.dataset.skillId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            fetch(`/profile/skill/${skillId}/remove`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    skillItem.remove();

                    if (!skillsList.querySelector('.skill-item')) {
                        skillsList.innerHTML = '<p class="no-skills" id="no-skills">No skills added yet.</p>';
                    }
                }
            });
        }
    });
}