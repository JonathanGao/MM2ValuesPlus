function getSelectedPredictor() {
    return new URLSearchParams(window.location.search).get('predictor') || '';
}

export function getData(rarity, weapon) {
    return fetch(`/api/${rarity}/${weapon}`)
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
        })
}

export function getPredictions(rarity, weapon, predictorId) {
    // An explicit id loads that model. With no id, the page's selected model is used.
    const predictor = encodeURIComponent(
        predictorId == null ? getSelectedPredictor() : predictorId
    );
    const query = predictor ? `?predictor=${predictor}` : '';

    return fetch(`/api/predictions/${rarity}/${weapon}${query}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(text => {
            // The forecast route sends a JSON list as plain text. A weapon with no
            // forecast for this model comes back as an HTML error page instead.
            try {
                const data = JSON.parse(text);
                return Array.isArray(data) ? data : null;
            } catch (error) {
                return null;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            return null;
        })
}

// Newest forecast for one model, or null when that model has not forecast this weapon.
export function getLatestPrediction(rarity, weapon, predictorId) {
    return getPredictions(rarity, weapon, predictorId)
        .then(data => {
            if (!data || !Array.isArray(data) || data.length === 0) return null;
            data.sort((a, b) => new Date(a.predictedAt) - new Date(b.predictedAt));
            return data[data.length - 1];
        });
}
