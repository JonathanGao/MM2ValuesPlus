document.querySelector('#weapon-search-form').addEventListener('input', (event) => {
    const searchValue = event.target.value.toLowerCase();
    const weaponNames = document.querySelectorAll('.weapon-name');
    weaponNames.forEach(weaponName => {
        if (!weaponName.textContent.toLowerCase().includes(searchValue)) {
            weaponName.parentElement.style.display = 'none';
        }
        else {
            weaponName.parentElement.style.display = 'block';
        }
    });
});