import { getData, getLatestPrediction } from './rarityUtils.js';

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

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
}

// Every model in the page dropdown, in the same order the server registered them.
function listPredictors() {
    const select = document.getElementById('predictor-select');
    if (!select) return [];
    return Array.from(select.options).map(option => ({
        id: option.value,
        label: option.textContent.trim(),
    }));
}

function predictionCell(prediction) {
    if (!prediction || prediction.predictedValue == null) {
        return '<td class="weapon-insight-missing">—</td>';
    }
    return `<td>${escapeHtml(prediction.predictedValue)}<span class="weapon-insight-change ${changeClass(prediction.changePct)}">(${formatChangePct(prediction.changePct)})</span></td>`;
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
        const predictors = listPredictors();

        if (!selectedWeaponTracker.includes(weaponName)) {
            selectedWeaponTracker.push(weaponName);
        };

        // If the chart exists, clear it
        weaponPanelChart.innerHTML = '';

        // For all selected weapons, fetch data.
        for (const weapon of selectedWeaponTracker) {
            let weaponData = await getData(rarity, weapon);
            // One latest forecast per registered model, so the table can show them side by side.
            const forecasts = [];
            for (const predictor of predictors) {
                forecasts.push(await getLatestPrediction(rarity, weapon, predictor.id));
            }

            if (weaponData) {
                allWeaponData.push(weaponData);
            }
            if (forecasts.some(forecast => forecast)) {
                allWeaponPredictions.push({
                    name: weapon,
                    color: colorForWeapon(weapon),
                    forecasts,
                });
            }
        };

        const headerCells = predictors
            .map(predictor => `<th scope="col">${escapeHtml(predictor.label)}</th>`)
            .join('');
        const bodyRows = allWeaponPredictions.map(weapon => `
            <tr>
                <th class="weapon-insight-item-title" scope="row" style="color: ${weapon.color}">${escapeHtml(weapon.name)}</th>
                ${weapon.forecasts.map(predictionCell).join('')}
            </tr>
        `).join('');
        // One table for every selected weapon. Model names are written once,
        // as the header of each value column, and each weapon is a row under them.
        weaponPanelInsights.innerHTML = allWeaponPredictions.length ? `
            <table class="weapon-insight-table">
                <thead>
                    <tr>
                        <th scope="col"></th>
                        ${headerCells}
                    </tr>
                </thead>
                <tbody>${bodyRows}</tbody>
            </table>
        ` : '';

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