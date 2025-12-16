// static/geodesic.js
class GeodesicLine {
    /**
     * Calculate points along a great circle (geodesic) between two points
     * This handles the wrap-around at ±180° longitude correctly
     */
    static calculateGreatCircle(lat1, lon1, lat2, lon2, numPoints = 50) {
        // Convert to radians
        const φ1 = lat1 * Math.PI / 180;
        const λ1 = lon1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const λ2 = lon2 * Math.PI / 180;
        
        const points = [];
        
        // Calculate the great circle distance
        const Δλ = λ2 - λ1;
        const Δσ = Math.acos(
            Math.sin(φ1) * Math.sin(φ2) + 
            Math.cos(φ1) * Math.cos(φ2) * Math.cos(Δλ)
        );
        
        // If points are antipodal or very close, return simple line
        if (Δσ < 0.001 || isNaN(Δσ)) {
            return [[lat1, lon1], [lat2, lon2]];
        }
        
        for (let i = 0; i <= numPoints; i++) {
            const fraction = i / numPoints;
            
            // Calculate intermediate point
            const A = Math.sin((1 - fraction) * Δσ) / Math.sin(Δσ);
            const B = Math.sin(fraction * Δσ) / Math.sin(Δσ);
            
            const x = A * Math.cos(φ1) * Math.cos(λ1) + B * Math.cos(φ2) * Math.cos(λ2);
            const y = A * Math.cos(φ1) * Math.sin(λ1) + B * Math.cos(φ2) * Math.sin(λ2);
            const z = A * Math.sin(φ1) + B * Math.sin(φ2);
            
            const φi = Math.atan2(z, Math.sqrt(x*x + y*y));
            let λi = Math.atan2(y, x);
            
            // Convert back to degrees
            const lat = φi * 180 / Math.PI;
            let lon = λi * 180 / Math.PI;
            
            // Normalize longitude to [-180, 180]
            while (lon > 180) lon -= 360;
            while (lon < -180) lon += 360;
            
            points.push([lat, lon]);
        }
        
        return points;
    }
    
    /**
     * Smart line creation that handles wrap-around automatically
     * Returns coordinates that Leaflet can draw correctly
     */
    static createFlightPath(origin, destination) {
        const [lat1, lon1] = origin;
        const [lat2, lon2] = destination;
        
        // Calculate if we cross the antimeridian (180°)
        const lonDiff = Math.abs(lon2 - lon1);
        
        if (lonDiff > 180) {
            // We need to cross the antimeridian
            // Calculate points with proper geodesic
            const points = this.calculateGreatCircle(lat1, lon1, lat2, lon2, 100);
            
            // Split the line at the antimeridian if needed
            return this.splitAtAntimeridian(points);
        } else {
            // Normal flight - use geodesic for curved appearance
            return this.calculateGreatCircle(lat1, lon1, lat2, lon2, 30);
        }
    }
    
    /**
     * Split line segments that cross the ±180° meridian
     */
    static splitAtAntimeridian(points) {
        const result = [];
        let currentSegment = [];
        
        for (let i = 0; i < points.length; i++) {
            const [lat, lon] = points[i];
            
            if (currentSegment.length === 0) {
                currentSegment.push([lat, lon]);
            } else {
                const [prevLat, prevLon] = currentSegment[currentSegment.length - 1];
                
                // Check if we crossed the antimeridian
                if (Math.abs(lon - prevLon) > 180) {
                    // We crossed! End current segment and start new one
                    result.push([...currentSegment]);
                    
                    // Calculate intermediate point at ±180
                    const fraction = (180 - Math.abs(prevLon)) / Math.abs(lon - prevLon);
                    const midLat = prevLat + (lat - prevLat) * fraction;
                    const midLon = prevLon > 0 ? 180 : -180;
                    
                    // Add the break point
                    result[currentSegment.length - 1]?.push([midLat, midLon]);
                    
                    // Start new segment
                    currentSegment = [[midLat, -midLon], [lat, lon]];
                } else {
                    currentSegment.push([lat, lon]);
                }
            }
        }
        
        if (currentSegment.length > 0) {
            result.push(currentSegment);
        }
        
        // Flatten if only one segment
        return result.length === 1 ? result[0] : result.flat();
    }
}