const main = document.getElementById('main');
const weaponPanel = document.getElementById('weapon-panel');

const weaponPanelButton = document.getElementById('weapon-panel-button');
const weaponPanelTitle = document.getElementById('weapon-panel-title');
const weaponPanelInsights = document.getElementById('weapon-panel-insights');
const weaponPanelChart = document.getElementById('weapon-chart-container');

let selectedWeaponTracker = [];

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
    item.addEventListener('click', async (event) => {
        const weaponName = event.target.closest('.item').querySelector('.weapon-name').textContent;
        const rarity = document.getElementById('rarity-title').textContent;

        const allWeaponData = [];

        if (!selectedWeaponTracker.includes(weaponName)) {
            selectedWeaponTracker.push(weaponName);
        };
        console.log(selectedWeaponTracker);

        // If the chart exists, clear it
        if (weaponPanelChart.innerHTML !== '') {
            weaponPanelChart.innerHTML = '';
        }

        // For all selected weapons, fetch data.
        for (const weapon of selectedWeaponTracker) {
            let weaponData = await fetch(`/api/${rarity}/${weapon}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {

                    data.sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));

                    const values = data.map(item => item.value);
                    const maxValue = Math.max(...values);
                    const minValue = Math.min(...values);
                    const datesAndValues = data.map(item => {
                        let value = Number(item.value);
                        let date = new Date(item.createdAt).getTime();
                        return {'x': date, 'y': value};
                    })
                    
                    return {
                        name: weapon,
                        data: datesAndValues,
                        maxValue: maxValue,
                        minValue: minValue,
                    };
                })
                .catch(error => {
                    console.error('Error:', error);
                });    

            // Process the data and turn it into a chart.
            if (weaponData) {
                allWeaponData.push(weaponData);
            }
        };
        
        const chart = new ApexCharts(weaponPanelChart, {
            chart: { type: 'line', height: 200 },
            series: allWeaponData,
            xaxis: {
                type: 'datetime',
            },
            yaxis: {
                type: 'numeric',
                min: 0,
                max: Math.max(...allWeaponData.map(weapon => weapon.maxValue + (0.1 * weapon.maxValue))),
                decimalsInFloat: 0,
                forceNiceScale: true,
                labels: {formatter: (value) => Math.round(value).toString()}
            },
        })

        chart.render();


        weaponPanelTitle.textContent = weaponName;
        
        main.classList.add('panel-open');
        weaponPanel.classList.remove('hidden');
        weaponPanel.setAttribute('aria-hidden', 'false');
    });
});

document.querySelector('#weapon-panel-close').addEventListener('click', (event) => {
    
    selectedWeaponTracker = [];

    document.getElementById('weapon-panel-close').blur();
    
    main.classList.remove('panel-open');
    weaponPanel.classList.add('hidden');
    weaponPanel.setAttribute('aria-hidden', 'true');
});