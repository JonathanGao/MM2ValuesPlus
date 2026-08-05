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

document.querySelectorAll('.item').forEach(item => {
    item.addEventListener('click', (event) => {
        const weaponName = event.target.closest('.item').querySelector('.weapon-name').textContent;
        const rarity = document.getElementById('rarity-title').textContent;
        fetch(`/api/${rarity}/${weaponName}`)
            .then(response => response.json())
            .then(data => {
            console.log(data);
        })
    });
});