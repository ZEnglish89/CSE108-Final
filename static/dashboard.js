// static/dashboard.js - INFINITE HORIZONTAL SCROLL WITH GEODESIC CURVES
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map with proper infinite scroll settings
    const map = L.map('map', {
        worldCopyJump: true,          // Show markers on all world copies
        continuousWorld: true,        // Enable infinite horizontal scroll
        maxBoundsViscosity: 0.0,      // Don't bounce back at edges
        inertia: false               // Disable inertia for smoother infinite scroll
    }).setView([40, -20], 2);
    
    // Add tile layer with infinite wrap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18,
        minZoom: 1,
        noWrap: false,               // Allow tiles to wrap infinitely
        continuousWorld: true        // Tile layer also wraps
    }).addTo(map);

    const tripLayers = {};
    
    // ========== GEODESIC CALCULATION FUNCTIONS ==========
    
    function calculateGeodesicPoints(lat1, lon1, lat2, lon2, numPoints = 100) {
        // Convert to radians
        const toRad = Math.PI / 180;
        const φ1 = lat1 * toRad;
        let λ1 = lon1 * toRad;
        const φ2 = lat2 * toRad;
        let λ2 = lon2 * toRad;
        
        // Choose the shortest path (wrap direction)
        const lonDiff = (λ2 - λ1) * 180 / Math.PI;
        if (Math.abs(lonDiff) > 180) {
            if (lonDiff > 0) {
                λ2 -= 2 * Math.PI;  // Go west across Pacific
            } else {
                λ2 += 2 * Math.PI;  // Go east across Pacific
            }
        }
        
        const points = [];
        const Δλ = λ2 - λ1;
        
        // Great circle distance
        const Δσ = Math.acos(
            Math.max(-1, Math.min(1,
                Math.sin(φ1) * Math.sin(φ2) + 
                Math.cos(φ1) * Math.cos(φ2) * Math.cos(Δλ)
            ))
        );
        
        if (Δσ < 0.001) {
            return [[lat1, lon1], [lat2, lon2]];
        }
        
        // Initial bearing
        const θ = Math.atan2(
            Math.sin(Δλ) * Math.cos(φ2),
            Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ)
        );
        
        // Generate points along the geodesic
        for (let i = 0; i <= numPoints; i++) {
            const f = i / numPoints;
            const σ = f * Δσ;
            
            const φ = Math.asin(
                Math.sin(φ1) * Math.cos(σ) + 
                Math.cos(φ1) * Math.sin(σ) * Math.cos(θ)
            );
            
            const λ = λ1 + Math.atan2(
                Math.sin(θ) * Math.sin(σ) * Math.cos(φ1),
                Math.cos(σ) - Math.sin(φ1) * Math.sin(φ)
            );
            
            const lat = φ * 180 / Math.PI;
            let lon = λ * 180 / Math.PI;
            
            points.push([lat, lon]);
        }
        
        return points;
    }
    
    function splitAtAntimeridian(points) {
        const segments = [];
        let currentSegment = [];
        
        for (let i = 0; i < points.length; i++) {
            const [lat, lon] = points[i];
            
            if (currentSegment.length === 0) {
                currentSegment.push([lat, lon]);
            } else {
                const [prevLat, prevLon] = currentSegment[currentSegment.length - 1];
                
                // Check if we crossed the antimeridian (jump > 180°)
                if (Math.abs(lon - prevLon) > 180) {
                    // Calculate intersection with ±180°
                    const fraction = (180 - Math.abs(prevLon)) / Math.abs(lon - prevLon);
                    const midLat = prevLat + (lat - prevLat) * fraction;
                    const midLon = prevLon > 0 ? 179.999 : -179.999;
                    
                    // End current segment
                    currentSegment.push([midLat, midLon]);
                    segments.push([...currentSegment]);
                    
                    // Start new segment on other side
                    const otherLon = prevLon > 0 ? -179.999 : 179.999;
                    currentSegment = [[midLat, otherLon], [lat, lon]];
                } else {
                    currentSegment.push([lat, lon]);
                }
            }
        }
        
        if (currentSegment.length > 0) {
            segments.push(currentSegment);
        }
        
        return segments;
    }
    
    // ========== INFINITE WORLD WRAP FUNCTIONS ==========
    
    // Create geodesic line with infinite horizontal copies
    function createInfiniteGeodesicLine(origin, dest, options = {}) {
        const [lat1, lon1] = origin;
        const [lat2, lon2] = dest;
        
        // Calculate geodesic points
        const geodesicPoints = calculateGeodesicPoints(lat1, lon1, lat2, lon2, 100);
        
        // Split at antimeridian if needed
        const segments = splitAtAntimeridian(geodesicPoints);
        
        // Create a layer group for all polylines
        const lineGroup = L.layerGroup();
        
        // For each segment, create multiple copies for infinite scroll
        segments.forEach((segment, segmentIndex) => {
            // Create polylines for multiple world copies
            // We create more copies to ensure coverage during scrolling
            for (let offset = -720; offset <= 720; offset += 360) {
                const offsetSegment = segment.map(point => [point[0], point[1] + offset]);
                const line = L.polyline(offsetSegment, {
                    color: options.color || '#ff4444',
                    weight: options.weight || 3,
                    opacity: options.opacity || 0.7,
                    smoothFactor: 1.0,
                    interactive: offset === 0 && segmentIndex === 0  // Only primary is interactive
                });
                
                // Add popup to the primary segment
                if (offset === 0 && segmentIndex === 0) {
                    line.bindPopup(options.popupContent || 'Flight Path');
                }
                
                lineGroup.addLayer(line);
            }
        });
        
        return lineGroup;
    }
    
    // Create markers with infinite horizontal copies
    function createInfiniteMarker(latlng, options = {}, popupContent = '') {
        const markerGroup = L.layerGroup();
        const [lat, lon] = latlng;
        
        // Create markers for multiple world copies
        for (let offset = -720; offset <= 720; offset += 360) {
            const marker = L.circleMarker([lat, lon + offset], {
                radius: options.radius || 8,
                color: options.color || '#0066cc',
                fillColor: options.fillColor || '#0066cc',
                fillOpacity: options.fillOpacity || 0.8,
                weight: options.weight || 2,
                interactive: offset === 0  // Only primary is interactive
            });
            
            // Add popup to primary marker
            if (offset === 0 && popupContent) {
                marker.bindPopup(popupContent);
            }
            
            markerGroup.addLayer(marker);
        }
        
        return markerGroup;
    }
    
    // ========== CREATE TRIP LAYERS ==========
    
    if (window.tripsData && window.tripsData.length > 0) {
        window.tripsData.forEach(t => {
            // Create infinite geodesic line
            const lineGroup = createInfiniteGeodesicLine(t.origin, t.dest, {
                color: '#ff4444',
                weight: 3,
                opacity: 0.7,
                popupContent: `
                    <b>${t.origin_code} → ${t.dest_code}</b><br>
                    Distance: ${t.distance.toFixed(0)} km<br>
                    CO₂ Emissions: ${t.emissions.toFixed(1)} kg<br>
                    <small>Click trip in list to toggle visibility</small>
                `
            });
            
            // Create infinite origin marker
            const originGroup = createInfiniteMarker(
                t.origin,
                {
                    radius: 8,
                    color: '#0066cc',
                    fillColor: '#0066cc',
                    fillOpacity: 0.8,
                    weight: 2
                },
                `<b>Origin:</b> ${t.origin_code}`
            );
            
            // Create infinite destination marker
            const destGroup = createInfiniteMarker(
                t.dest,
                {
                    radius: 8,
                    color: '#00cc66',
                    fillColor: '#00cc66',
                    fillOpacity: 0.8,
                    weight: 2
                },
                `<b>Destination:</b> ${t.dest_code}`
            );
            
            // Combine everything
            const tripGroup = L.layerGroup([lineGroup, originGroup, destGroup]);
            tripGroup.addTo(map);
            
            // Store layer reference
            tripLayers[t.id] = {
                group: tripGroup,
                emissions: t.emissions,
                distance: t.distance
            };
        });
        
        // Fit map to show all trips in primary world
        fitMapToVisibleTrips();
    } else {
        // No trips yet - create marker with infinite copies
        const noTripsGroup = L.layerGroup();
        
        for (let offset = -720; offset <= 720; offset += 360) {
            const marker = L.marker([40, -20 + offset], { 
                interactive: offset === 0 
            });
            
            if (offset === 0) {
                marker.bindPopup('No trips yet. Add your first flight trip!')
                      .openPopup();
            }
            
            noTripsGroup.addLayer(marker);
        }
        
        noTripsGroup.addTo(map);
    }
    
    // ========== CUSTOM MAP CONTROLS FOR INFINITE SCROLL ==========
    
    // Add custom control to explain infinite scroll
    const infoControl = L.control({ position: 'bottomleft' });
    // infoControl.onAdd = function(map) {
    //     const div = L.DomUtil.create('div', 'info-control');
    //     div.innerHTML = `
    //         <div style="background: white; padding: 6px 10px; border-radius: 4px; 
    //                     font-size: 12px; box-shadow: 0 1px 5px rgba(0,0,0,0.2);">
    //             <strong>✈️ Infinite Map</strong><br>
    //             <small>Scroll horizontally infinitely</small>
    //         </div>
    //     `;
    //     return div;
    // };
    infoControl.addTo(map);
    
    // ========== EVENT HANDLERS ==========
    
    document.querySelectorAll(".trip-checkbox").forEach(cb => {
        cb.addEventListener("change", handleTripToggle);
    });

    function handleTripToggle(e) {
        const id = e.target.dataset.tripId;
        const layers = tripLayers[id];

        if (e.target.checked) {
            layers.group.addTo(map);
        } else {
            map.removeLayer(layers.group);
        }

        updateAnalytics();
        fitMapToVisibleTrips();
    }

    function updateAnalytics() {
        let totalEmissions = 0;
        let totalDistance = 0;
        let visibleCount = 0;

        document.querySelectorAll(".trip-checkbox").forEach(cb => {
            const id = cb.dataset.tripId;
            if (cb.checked && tripLayers[id]) {
                totalEmissions += tripLayers[id].emissions;
                totalDistance += tripLayers[id].distance;
                visibleCount++;
            }
        });

        document.getElementById("total-emissions").textContent = 
            totalEmissions.toFixed(1) + " kg";

        document.getElementById("tree-equivalent").textContent = 
            (totalEmissions / 21).toFixed(1) + " trees";

        document.getElementById("trip-count").textContent = 
            visibleCount;
    }

    function fitMapToVisibleTrips() {
        const bounds = [];

        document.querySelectorAll(".trip-checkbox").forEach(cb => {
            if (cb.checked) {
                const id = cb.dataset.tripId;
                if (tripLayers[id]) {
                    // Get bounds only from primary world layers
                    tripLayers[id].group.getLayers().forEach(layerGroup => {
                        if (layerGroup.getLayers) {
                            layerGroup.getLayers().forEach(layer => {
                                if (layer.getBounds) {
                                    const layerBounds = layer.getBounds();
                                    // Check if this layer is in primary world
                                    const centerLon = (layerBounds.getWest() + layerBounds.getEast()) / 2;
                                    if (centerLon >= -180 && centerLon <= 180) {
                                        bounds.push(layerBounds);
                                    }
                                }
                            });
                        }
                    });
                }
            }
        });

        if (bounds.length > 0) {
            let latLngBounds = L.latLngBounds(bounds[0]);
            bounds.forEach(bound => {
                latLngBounds.extend(bound);
            });
            
            // Add some padding
            const paddedBounds = latLngBounds.pad(0.1);
            map.fitBounds(paddedBounds, { 
                padding: [50, 50], 
                maxZoom: 10,
                animate: true
            });
        } else {
            // Default view
            map.setView([40, -20], 2, { animate: true });
        }
    }

    updateAnalytics();
    
    // Add scale control
    L.control.scale({ imperial: false }).addTo(map);
    
    // Enable dragging for infinite scroll
    map.dragging.enable();
    
    // Listen for drag events to ensure smooth infinite scroll
    let isDragging = false;
    map.on('dragstart', function() {
        isDragging = true;
    });
    
    map.on('dragend', function() {
        isDragging = false;
        // After dragging, we could recenter if needed
        const center = map.getCenter();
        console.log(`Current center: ${center.lat.toFixed(2)}, ${center.lng.toFixed(2)}`);
    });
    
    // Optional: Add keyboard controls for infinite scroll
    document.addEventListener('keydown', function(e) {
        if (!map) return;
        
        const panAmount = 100; // pixels to pan
        
        switch(e.key) {
            case 'ArrowLeft':
                map.panBy([-panAmount, 0]);
                break;
            case 'ArrowRight':
                map.panBy([panAmount, 0]);
                break;
            case 'ArrowUp':
                map.panBy([0, -panAmount]);
                break;
            case 'ArrowDown':
                map.panBy([0, panAmount]);
                break;
        }
    });
});

