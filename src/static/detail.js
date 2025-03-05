async function loadCarDetails() {
    try {
        const carId = window.location.pathname.split('/').pop();
        const response = await fetch(`/api/car/${carId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const car = await response.json();
        
        // Update title
        document.getElementById('carTitle').textContent = `${car.brand || 'Unknown'} ${car.model || ''}`;
        document.title = `${car.brand} ${car.model} - Car Details`;

        // Basic Information
        const basicInfo = document.getElementById('basicInfo');
        basicInfo.innerHTML = createInfoRows([
            ['Brand', car.brand],
            ['Model', car.model],
            ['Year', car.year],
            ['First Registration', car.first_registration],
            ['Mileage', car.mileage_formatted],
            ['Fuel Type', car.fuel_type]
        ]);

        // Price Information
        const priceInfo = document.getElementById('priceInfo');
        priceInfo.innerHTML = createInfoRows([
            ['Cash Price', car.cash_price_formatted],
            ['Annual Tax', car.annual_tax ? `${car.annual_tax} DKK/year` : 'N/A']
        ]);

        // Technical Specifications
        const techSpecs = document.getElementById('techSpecs');
        techSpecs.innerHTML = createInfoRows([
            ['Power', `${car.horsepower || 'N/A'} hp / ${car.torque_nm || 'N/A'} Nm`],
            ['Acceleration', car.acceleration ? `${car.acceleration}s` : 'N/A'],
            ['Top Speed', car.top_speed ? `${car.top_speed} km/h` : 'N/A'],
            ['Weight', car.weight ? `${car.weight} kg` : 'N/A'],
            ['Trunk Size', car.trunk_size ? `${car.trunk_size} liters` : 'N/A']
        ]);

        // EV Specifications
        const evSpecsContainer = document.getElementById('evSpecsContainer');
        if (car.fuel_type === 'El') {
            evSpecsContainer.classList.remove('hidden');
            const evSpecs = document.getElementById('evSpecs');
            evSpecs.innerHTML = createInfoRows([
                ['Range (WLTP)', car.range_km ? `${car.range_km} km` : 'N/A'],
                ['Battery Capacity', car.battery_capacity ? `${car.battery_capacity} kWh` : 'N/A'],
                ['Energy Consumption', car.energy_consumption ? `${car.energy_consumption} Wh/km` : 'N/A']
            ]);
        } else {
            evSpecsContainer.classList.add('hidden');
        }

        // Equipment
        const equipment = document.getElementById('equipment');
        equipment.innerHTML = car.equipment && car.equipment.length > 0
            ? car.equipment.map(item => `<div class="equipment-item">${item}</div>`).join('')
            : '<div class="text-gray-500">No equipment information available</div>';

    } catch (error) {
        console.error('Error loading car:', error);
        document.getElementById('carTitle').textContent = 'Error loading car data';
    }
}

function createInfoRows(data) {
    return data.map(([label, value]) => `
        <div class="info-row">
            <span class="info-label">${label}</span>
            <span class="info-value">${value || 'N/A'}</span>
        </div>
    `).join('');
}

// Load car details when page loads
document.addEventListener('DOMContentLoaded', loadCarDetails); 