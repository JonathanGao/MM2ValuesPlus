const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const COLORS = ["#2563eb", "#9333ea", "#16a34a", "#ca8a04"];

const note = document.getElementById("accuracy-note");
const emptyMessage = document.getElementById("accuracy-empty");
const content = document.getElementById("accuracy-content");

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function shortDate(isoDate) {
    if (!isoDate) return "";
    const [, month, day] = isoDate.split("-");
    return `${MONTHS[Number(month) - 1]} ${Number(day)}`;
}

// Local midnight, so a stored day like 2026-10-04 stays October 4 on the chart.
function dateMs(isoDate) {
    const [year, month, day] = isoDate.split("-").map(Number);
    return new Date(year, month - 1, day).getTime();
}

function eachIsoDate(firstDate, lastDate) {
    const dates = [];
    const cursor = new Date(dateMs(firstDate));
    const last = dateMs(lastDate);
    while (cursor.getTime() <= last) {
        const month = String(cursor.getMonth() + 1).padStart(2, "0");
        const day = String(cursor.getDate()).padStart(2, "0");
        dates.push(`${cursor.getFullYear()}-${month}-${day}`);
        cursor.setDate(cursor.getDate() + 1);
    }
    return dates;
}

function formatPct(value) {
    return `${Number(value).toFixed(2)}%`;
}

function formatDirection(value) {
    return `${Number(value).toFixed(1)}%`;
}

function metricCell(row, field, formatter) {
    if (!row) return "<td>—</td>";
    return `<td>${formatter(row[field])}</td>`;
}

function rowsByKey(rows, keyName) {
    const grouped = new Map();
    rows.forEach(row => {
        if (!grouped.has(row[keyName])) grouped.set(row[keyName], []);
        grouped.get(row[keyName]).push(row);
    });
    return grouped;
}

function renderCards(accuracy) {
    const cards = document.getElementById("accuracy-cards");
    const overall = accuracy.matched.overall;
    if (!overall.length) {
        cards.innerHTML = `<p class="accuracy-note">No shared forecasts yet. The charts use each model's own scored days.</p>`;
        return;
    }
    cards.innerHTML = overall.map(row => {
        const predictor = accuracy.predictors.find(item => item.id === row.predictor);
        const label = predictor ? predictor.label : row.predictor;
        return `
            <article class="accuracy-card">
                <h2>${escapeHtml(label)}</h2>
                <div class="accuracy-metrics">
                    <div class="accuracy-metric"><span>WAPE</span><strong>${formatPct(row.wape)}</strong></div>
                    <div class="accuracy-metric"><span>MAE</span><strong>${Number(row.mae).toFixed(2)}</strong></div>
                    <div class="accuracy-metric"><span>Direction</span><strong>${formatDirection(row.directionPct)}</strong></div>
                </div>
            </article>
        `;
    }).join("");
}

function renderTable(table, headerHtml, bodyHtml) {
    table.innerHTML = `<thead>${headerHtml}</thead><tbody>${bodyHtml}</tbody>`;
}

function renderRarityTable(accuracy) {
    const table = document.getElementById("accuracy-rarity-table");
    const grouped = rowsByKey(accuracy.matched.byRarity, "rarity");
    if (!grouped.size) {
        table.innerHTML = "<tbody><tr><td>No shared forecasts yet.</td></tr></tbody>";
        return;
    }
    const header = `
        <tr>
            <th rowspan="2">Rarity</th>
            <th rowspan="2">Forecasts</th>
            ${accuracy.predictors.map(predictor => `<th colspan="2">${escapeHtml(predictor.label)}</th>`).join("")}
        </tr>
        <tr>
            ${accuracy.predictors.map(() => "<th>WAPE</th><th>Direction</th>").join("")}
        </tr>
    `;
    const body = Array.from(grouped.entries()).map(([rarity, rows]) => {
        const cells = accuracy.predictors.map(predictor => {
            const row = rows.find(item => item.predictor === predictor.id);
            return metricCell(row, "wape", formatPct) + metricCell(row, "directionPct", formatDirection);
        }).join("");
        return `<tr><td>${escapeHtml(rarity)}</td><td>${rows[0].count}</td>${cells}</tr>`;
    }).join("");
    renderTable(table, header, body);
}

function renderDailyTable(accuracy) {
    const table = document.getElementById("accuracy-daily-table");
    const grouped = rowsByKey(accuracy.daily, "targetDate");
    const header = `
        <tr>
            <th rowspan="2">Date</th>
            ${accuracy.predictors.map(predictor => `<th colspan="2">${escapeHtml(predictor.label)}</th>`).join("")}
        </tr>
        <tr>
            ${accuracy.predictors.map(() => "<th>WAPE</th><th>Direction</th>").join("")}
        </tr>
    `;
    const body = Array.from(grouped.entries()).map(([targetDate, rows]) => {
        const cells = accuracy.predictors.map(predictor => {
            const row = rows.find(item => item.predictor === predictor.id);
            return metricCell(row, "wape", formatPct) + metricCell(row, "directionPct", formatDirection);
        }).join("");
        return `<tr><td>${shortDate(targetDate)}</td>${cells}</tr>`;
    }).join("");
    renderTable(table, header, body);
}

function chartSeries(accuracy, valueKey) {
    const dates = accuracy.daily.map(row => row.targetDate).sort();
    if (!dates.length) return [];
    const span = eachIsoDate(dates[0], dates[dates.length - 1]);
    return accuracy.predictors.map((predictor, index) => {
        const values = new Map(
            accuracy.daily
                .filter(row => row.predictor === predictor.id)
                .map(row => [row.targetDate, row[valueKey]])
        );
        return {
            name: predictor.label,
            data: span.map(isoDate => ({
                x: dateMs(isoDate),
                y: values.has(isoDate) ? values.get(isoDate) : null,
            })),
            color: COLORS[index % COLORS.length],
        };
    }).filter(series => series.data.some(point => point.y != null));
}

function renderChart(elementId, series, yTitle) {
    const element = document.getElementById(elementId);
    if (!series.length) {
        element.textContent = "No scored days yet.";
        return;
    }
    const chart = new ApexCharts(element, {
        chart: { type: "line", height: 280, toolbar: { show: false } },
        series: series.map(item => ({ name: item.name, data: item.data })),
        colors: series.map(item => item.color),
        stroke: { width: 2, curve: "straight" },
        markers: { size: 4 },
        xaxis: { type: "datetime", labels: { datetimeUTC: false } },
        yaxis: {
            title: { text: yTitle },
            labels: { formatter: value => (value == null ? "" : Number(value).toFixed(2)) },
        },
        tooltip: { x: { format: "MMM d, yyyy" } },
        legend: { position: "top" },
    });
    chart.render();
}

function showEmpty(message) {
    emptyMessage.textContent = message;
    emptyMessage.classList.remove("hidden");
    content.classList.add("hidden");
}

fetch("/api/accuracy")
    .then(response => {
        if (!response.ok) throw new Error("Accuracy request failed");
        return response.json();
    })
    .then(accuracy => {
        const matched = accuracy.matched;
        if (!accuracy.daily.length && !matched.count) {
            note.textContent = "Scores appear after a scrape on or after each forecast's target date.";
            showEmpty("No scored forecasts yet.");
            return;
        }

        if (matched.count) {
            const span = matched.firstDate === matched.lastDate
                ? shortDate(matched.firstDate)
                : `${shortDate(matched.firstDate)}–${shortDate(matched.lastDate)}`;
            note.textContent = `${matched.count} shared forecasts from ${span}. These cards compare only weapon-days every model scored. The charts include each model's full scored history.`;
        } else {
            note.textContent = "No shared forecasts yet. The charts include each model's own scored days.";
        }

        content.classList.remove("hidden");
        renderCards(accuracy);
        renderChart("accuracy-wape-chart", chartSeries(accuracy, "wape"), "WAPE (%)");
        renderChart("accuracy-direction-chart", chartSeries(accuracy, "directionPct"), "Direction correct (%)");
        renderRarityTable(accuracy);
        renderDailyTable(accuracy);
    })
    .catch(error => {
        console.error(error);
        note.textContent = "";
        showEmpty("Accuracy scores could not be loaded.");
    });
