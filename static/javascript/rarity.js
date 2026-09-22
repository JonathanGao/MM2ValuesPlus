import { getData, getPredictions } from './rarityUtils.js';

const main = document.getElementById('main');
const weaponPanel = document.getElementById('weapon-panel');

const weaponPanelButton = document.getElementById('weapon-panel-button');
const weaponPanelTitle = document.getElementById('weapon-panel-title');
const weaponPanelChart = document.getElementById('weapon-chart-container');
const weaponPanelInsights = document.getElementById('weapon-insights-container');

const WEAPON_COLORS = [
    '#2563eb', '#dc2626', '#16a34a', '#ca8a04', '#9333ea',
    '#0891b2', '#ea580c', '#db2777', '#4f46e5', '#059669',
];

let selectedWeaponTracker = [];

function colorForWeapon(weaponName) {
    const index = selectedWeaponTracker.indexOf(weaponName);
    return WEAPON_COLORS[index % WEAPON_COLORS.length];
}

function changeClass(changePct) {
    if (changePct > 0) return 'change-up';
    if (changePct < 0) return 'change-down';
    return 'change-flat';
}

function formatChangePct(changePct) {
    const value = Number(changePct) || 0;
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

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
        const allWeaponPredictions = [];

        if (!selectedWeaponTracker.includes(weaponName)) {
            selectedWeaponTracker.push(weaponName);
        };
        console.log(selectedWeaponTracker);

        // If the chart exists, clear it
        weaponPanelChart.innerHTML = '';

        // For all selected weapons, fetch data.
        for (const weapon of selectedWeaponTracker) {
            let weaponData = await getData(rarity, weapon);
            let weaponPredictions = await getPredictions(rarity, weapon)
                .then(data => {
                    if (!data || !Array.isArray(data) || data.length === 0) return null;
                    data.sort((a, b) => new Date(a.predictedAt) - new Date(b.predictedAt));
                    const latest = data[data.length - 1];
                    return {
                        name: latest.item,
                        predictedValue: latest.predictedValue,
                        changePct: latest.changePct,
                        color: colorForWeapon(weapon),
                    };
                })

            // Process the data and turn it into a chart.
            if (weaponData) {
                allWeaponData.push(weaponData);
            }
            if (weaponPredictions) {
                allWeaponPredictions.push(weaponPredictions);
            }
        };

        // map only creates a new array, so join eliminates the commas that separate the elements in the array.
        weaponPanelInsights.innerHTML = allWeaponPredictions.map(weapon => `
            <div class="weapon-insight-item">
                <h1 class="weapon-insight-item-title" style="color: ${weapon.color}">${weapon.name}</h1>
                <h2 class="weapon-insight-item-content">
                    Predicted Value: ${weapon.predictedValue}
                    <span class="weapon-insight-change ${changeClass(weapon.changePct)}">
                        (${formatChangePct(weapon.changePct)})
                    </span>
                </h2>
            </div>
        `).join('');

        const chartColors = allWeaponData.map(weapon => colorForWeapon(weapon.name));

        const chart = new ApexCharts(weaponPanelChart, {
            chart: { type: 'line', height: 200 },
            series: allWeaponData,
            colors: chartColors,
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

    weaponPanelChart.innerHTML = '';
    
    main.classList.remove('panel-open');
    weaponPanel.classList.add('hidden');
    weaponPanel.setAttribute('aria-hidden', 'true');
});