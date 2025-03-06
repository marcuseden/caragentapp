// Add this to your admin.js file or create it if it doesn't exist

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get references to the form elements
    const scraperForm = document.getElementById('scraper-form');
    const scraperType = document.getElementById('scraper-type');
    const scraperCountry = document.getElementById('scraper-country');
    const runScraperBtn = document.getElementById('run-scraper-btn');
    const scraperStatus = document.getElementById('scraper-status');
    const scraperStatusMessage = document.getElementById('scraper-status-message');
    
    // Add event listener for form submission
    scraperForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Disable the button to prevent multiple submissions
        runScraperBtn.disabled = true;
        runScraperBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';
        
        // Get the selected values
        const type = scraperType.value;
        const country = scraperCountry.value;
        
        // Call the API to run the scraper
        fetch('/api/admin/run-scraper', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: type,
                country: country
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Show the status message
            scraperStatus.style.display = 'block';
            scraperStatusMessage.textContent = data.message;
            
            // Re-enable the button after a delay
            setTimeout(() => {
                runScraperBtn.disabled = false;
                runScraperBtn.innerHTML = 'Run Scraper';
                
                // Update stats after a delay to reflect new data
                setTimeout(loadStats, 5000);
            }, 3000);
        })
        .catch(error => {
            console.error('Error:', error);
            scraperStatus.style.display = 'block';
            scraperStatusMessage.textContent = 'Error starting scraper: ' + error;
            runScraperBtn.disabled = false;
            runScraperBtn.innerHTML = 'Run Scraper';
        });
    });
    
    // Function to load stats (assuming you already have this)
    function loadStats() {
        fetch('/api/admin/stats')
            .then(response => response.json())
            .then(data => {
                // Update your stats display
                document.getElementById('totalCars').textContent = data.total_cars.toLocaleString();
                document.getElementById('carsWithUrl').textContent = data.cars_with_url.toLocaleString();
                document.getElementById('carsWithoutUrl').textContent = data.cars_without_url.toLocaleString();
            })
            .catch(error => console.error('Error loading stats:', error));
    }

    // Add this to your admin.js file
    const testMongoBtn = document.getElementById('testMongoBtn');
    const testMongoStatus = document.getElementById('testMongoStatus');

    if (testMongoBtn) {
        testMongoBtn.addEventListener('click', async function() {
            try {
                testMongoBtn.disabled = true;
                testMongoBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
                testMongoStatus.className = 'ml-2 text-sm text-blue-600';
                testMongoStatus.textContent = 'Testing connection...';
                
                const response = await fetch('/api/test-mongodb');
                const data = await response.json();
                
                if (data.success) {
                    testMongoStatus.className = 'ml-2 text-sm text-green-600';
                    testMongoStatus.textContent = `Success! ${data.message}. Total documents: ${data.total_documents}`;
                } else {
                    testMongoStatus.className = 'ml-2 text-sm text-red-600';
                    testMongoStatus.textContent = `Error: ${data.message}`;
                }
            } catch (error) {
                console.error('Error testing MongoDB connection:', error);
                testMongoStatus.className = 'ml-2 text-sm text-red-600';
                testMongoStatus.textContent = `Error: ${error.message}`;
            } finally {
                testMongoBtn.disabled = false;
                testMongoBtn.innerHTML = 'Test MongoDB Connection';
            }
        });
    }
}); 