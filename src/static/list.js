async function loadCars() {
    try {
        const response = await fetch('/api/cars');
        const cars = await response.json();
        
        const carList = document.getElementById('carList');
        carList.innerHTML = cars.map(car => `
            <a href="/car/${car.id}" class="block bg-white rounded-lg shadow hover:shadow-md transition-shadow">
                <div class="p-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h2 class="text-xl font-semibold">${car.brand} ${car.model}</h2>
                            <p class="text-gray-600">${car.year}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-lg font-bold text-blue-600">${car.price}</p>
                            <p class="text-sm text-gray-500">${car.mileage}</p>
                        </div>
                    </div>
                    <div class="mt-2 text-sm text-gray-500">
                        Country: ${car.country}
                    </div>
                </div>
            </a>
        `).join('');
    } catch (error) {
        console.error('Error loading cars:', error);
        document.getElementById('carList').innerHTML = '<div class="bg-red-100 text-red-700 p-4 rounded">Error loading cars</div>';
    }
}

document.addEventListener('DOMContentLoaded', loadCars);
