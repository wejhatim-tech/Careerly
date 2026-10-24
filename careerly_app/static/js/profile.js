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
                if (skillsList.querySelector(`[data-skill-id="${data.skill_id}"]`)) {
                    skillInput.value = '';
                    return;
                }

                const skillItem = document.createElement('div');
                skillItem.classList.add('skill-item');
                skillItem.dataset.skillId = data.skill_id;

                const skillName = document.createElement('span');
                skillName.textContent = data.skill_name;

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.classList.add('skill-remove');
                removeBtn.textContent = '×';

                skillItem.append(skillName, removeBtn);
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
// Close the dropdowns when clicking outside them
document.addEventListener('click', function (event) {
    document.querySelectorAll('.check-dropdown[open]').forEach(function (dropdown) {
        if (!dropdown.contains(event.target)) {
            dropdown.removeAttribute('open');
        }
    });
});