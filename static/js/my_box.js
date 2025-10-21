function toggleFavoriteExhibitor(exhibitorId) {
    fetch(`/toggle-favorite-exhibitor/${exhibitorId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Reload page to show updated favorites
            window.location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function toggleFavoriteProduct(productId) {
    fetch(`/toggle-favorite-product/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Reload page to show updated favorites
            window.location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}