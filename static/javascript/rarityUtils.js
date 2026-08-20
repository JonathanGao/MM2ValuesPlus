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