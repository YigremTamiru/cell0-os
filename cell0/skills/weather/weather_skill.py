#!/usr/bin/env python3
"""
Weather Skill for Cell 0 OS
Integration with wttr.in free weather service

No API key required - uses wttr.in which aggregates data from multiple sources.

Features:
- Current weather conditions
- Weather forecasts (1-3 days)
- Weather alerts
- Air quality index
- Sunrise/sunset times
- Historical weather data
- Multiple location format support
"""

import json
import re
import html
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta

# Optional requests import with fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None


class WeatherSkill:
    """Skill for retrieving weather information via wttr.in"""
    
    BASE_URL = "https://wttr.in"
    
    # Unit systems
    METRIC = "m"
    IMPERIAL = "u"
    
    def __init__(self):
        if not HAS_REQUESTS:
            raise RuntimeError(
                "The 'requests' library is required. "
                "Install it with: pip install requests"
            )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'curl/7.68.0'  # wttr.in works best with curl-like UA
        })
    
    def _make_request(
        self, 
        location: str, 
        format_code: Optional[str] = None,
        units: str = "metric",
        extra_params: Optional[Dict[str, str]] = None
    ) -> Union[Dict, str]:
        """
        Make a request to wttr.in
        
        Args:
            location: Location string
            format_code: wttr.in format code for custom output
            units: 'metric' or 'imperial'
            extra_params: Additional query parameters
            
        Returns:
            Response data (dict for JSON, str for text)
        """
        # Clean location string
        location = location.strip()
        
        # Build URL
        url = f"{self.BASE_URL}/{location}"
        
        # Build query parameters
        params = {}
        
        # Add format if specified
        if format_code:
            params['format'] = format_code
        else:
            params['format'] = 'j1'  # Default to JSON
        
        # Add units
        if units.lower() == 'imperial':
            params[self.IMPERIAL] = ''
        else:
            params[self.METRIC] = ''
        
        # Add extra params
        if extra_params:
            params.update(extra_params)
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
                
        except requests.exceptions.Timeout:
            raise RuntimeError("Request timed out. wttr.in may be slow, please try again.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Connection error. Please check your internet connection.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Location '{location}' not found. Try a different format.")
            raise RuntimeError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}")
    
    def _parse_location(self, location: str) -> str:
        """
        Parse and validate location string.
        
        Args:
            location: Raw location string
            
        Returns:
            Cleaned location string ready for wttr.in
        """
        location = location.strip()
        
        # Handle special formats
        if location.lower() in ['moon', ':ip', 'ip']:
            return location.lower()
        
        # Handle coordinates
        if re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', location):
            return location
        
        # Handle airport codes (3 letters)
        if re.match(r'^[A-Z]{3}$', location.upper()):
            return location.upper()
        
        # Handle domain names (@domain.com)
        if location.startswith('@'):
            return location
        
        # Handle regular city names - URL encode spaces
        location = location.replace(' ', '+')
        
        return location
    
    def get_current_weather(
        self, 
        location: str, 
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Get current weather conditions for a location.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            units: 'metric' (Celsius) or 'imperial' (Fahrenheit)
            
        Returns:
            Dictionary with current weather data
        """
        location = self._parse_location(location)
        data = self._make_request(location, units=units)
        
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format")
        
        # Extract current conditions from the first weather entry
        current = data.get('current_condition', [{}])[0]
        nearest_area = data.get('nearest_area', [{}])[0]
        
        # Build result
        result = {
            'location': {
                'city': nearest_area.get('areaName', [{}])[0].get('value', 'Unknown'),
                'region': nearest_area.get('region', [{}])[0].get('value', ''),
                'country': nearest_area.get('country', [{}])[0].get('value', ''),
                'latitude': nearest_area.get('latitude', ''),
                'longitude': nearest_area.get('longitude', ''),
            },
            'current': {
                'temperature': current.get(f'temp_{"C" if units == "metric" else "F"}', 'N/A'),
                'feels_like': current.get(f'FeelsLike{"C" if units == "metric" else "F"}', 'N/A'),
                'condition': current.get('weatherDesc', [{}])[0].get('value', 'Unknown'),
                'weather_code': current.get('weatherCode', ''),
                'humidity': current.get('humidity', 'N/A'),
                'wind_speed': current.get(f'windspeed{"Kmph" if units == "metric" else "Miles"}', 'N/A'),
                'wind_direction': current.get('winddir16Point', 'N/A'),
                'pressure': current.get('pressure', 'N/A'),
                'precipitation': current.get('precipMM', 'N/A'),
                'visibility': current.get('visibility', 'N/A'),
                'cloud_cover': current.get('cloudcover', 'N/A'),
                'uv_index': current.get('uvIndex', 'N/A'),
                'observation_time': current.get('observation_time', ''),
            },
            'units': units
        }
        
        return result
    
    def get_forecast(
        self, 
        location: str, 
        days: int = 3, 
        units: str = "metric"
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a location.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            days: Number of days to forecast (1-3)
            units: 'metric' (Celsius) or 'imperial' (Fahrenheit)
            
        Returns:
            Dictionary with forecast data
        """
        if not 1 <= days <= 3:
            raise ValueError("Days must be between 1 and 3")
        
        location = self._parse_location(location)
        data = self._make_request(location, units=units)
        
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format")
        
        # Get location info
        nearest_area = data.get('nearest_area', [{}])[0]
        location_info = {
            'city': nearest_area.get('areaName', [{}])[0].get('value', 'Unknown'),
            'region': nearest_area.get('region', [{}])[0].get('value', ''),
            'country': nearest_area.get('country', [{}])[0].get('value', ''),
        }
        
        # Extract forecast for requested days
        weather = data.get('weather', [])
        forecast = []
        
        for i in range(min(days, len(weather))):
            day = weather[i]
            temp_unit = 'C' if units == 'metric' else 'F'
            speed_unit = 'kmph' if units == 'metric' else 'mph'
            
            forecast.append({
                'date': day.get('date', ''),
                'max_temp': day.get(f'maxtemp{temp_unit}', 'N/A'),
                'min_temp': day.get(f'mintemp{temp_unit}', 'N/A'),
                'avg_temp': day.get(f'avgtemp{temp_unit}', 'N/A'),
                'sunrise': day.get('astronomy', [{}])[0].get('sunrise', 'N/A'),
                'sunset': day.get('astronomy', [{}])[0].get('sunset', 'N/A'),
                'moonrise': day.get('astronomy', [{}])[0].get('moonrise', 'N/A'),
                'moonset': day.get('astronomy', [{}])[0].get('moonset', 'N/A'),
                'moon_phase': day.get('astronomy', [{}])[0].get('moon_phase', 'N/A'),
                'moon_illumination': day.get('astronomy', [{}])[0].get('moon_illumination', 'N/A'),
                'uv_index': day.get('uvIndex', 'N/A'),
                'hourly': self._parse_hourly_forecast(day.get('hourly', []), units)
            })
        
        return {
            'location': location_info,
            'forecast': forecast,
            'units': units
        }
    
    def _parse_hourly_forecast(
        self, 
        hourly_data: List[Dict], 
        units: str
    ) -> List[Dict]:
        """Parse hourly forecast data."""
        parsed = []
        temp_unit = 'C' if units == 'metric' else 'F'
        
        for hour in hourly_data:
            parsed.append({
                'time': hour.get('time', '0000'),
                'temperature': hour.get(f'temp{temp_unit}', 'N/A'),
                'feels_like': hour.get(f'FeelsLike{temp_unit}', 'N/A'),
                'condition': hour.get('weatherDesc', [{}])[0].get('value', 'Unknown'),
                'weather_code': hour.get('weatherCode', ''),
                'wind_speed': hour.get(f'windspeed{temp_unit}', 'N/A'),
                'wind_direction': hour.get('winddir16Point', ''),
                'humidity': hour.get('humidity', ''),
                'precipitation': hour.get('precipMM', ''),
                'chance_of_rain': hour.get('chanceofrain', ''),
                'chance_of_snow': hour.get('chanceofsnow', ''),
                'visibility': hour.get('visibility', ''),
                'pressure': hour.get('pressure', ''),
                'cloud_cover': hour.get('cloudcover', ''),
                'uv_index': hour.get('uvIndex', ''),
            })
        
        return parsed
    
    def get_weather_alerts(self, location: str) -> Dict[str, Any]:
        """
        Get weather alerts and warnings for a location.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            
        Returns:
            Dictionary with alert information
        """
        location = self._parse_location(location)
        data = self._make_request(location)
        
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format")
        
        # Get location info
        nearest_area = data.get('nearest_area', [{}])[0]
        location_info = {
            'city': nearest_area.get('areaName', [{}])[0].get('value', 'Unknown'),
            'region': nearest_area.get('region', [{}])[0].get('value', ''),
            'country': nearest_area.get('country', [{}])[0].get('value', ''),
        }
        
        # Check for alerts in the data
        alerts = []
        current = data.get('current_condition', [{}])[0]
        
        # Extract any warning-level conditions
        weather_code = current.get('weatherCode', '')
        weather_desc = current.get('weatherDesc', [{}])[0].get('value', '')
        
        # Weather codes that indicate severe conditions (simplified)
        severe_codes = {
            '389': 'Thunderstorm',
            '386': 'Thunderstorm with hail',
            '200': 'Thundery outbreaks',
            '377': 'Heavy freezing drizzle',
            '374': 'Heavy freezing rain',
            '359': 'Torrential rain shower',
            '356': 'Heavy rain shower',
            '338': 'Heavy snow',
            '335': 'Heavy snow shower',
            '314': 'Heavy freezing rain',
            '311': 'Freezing drizzle',
            '284': 'Heavy freezing drizzle',
            '230': 'Blizzard',
            '227': 'Blowing snow',
        }
        
        if weather_code in severe_codes:
            alerts.append({
                'type': 'weather',
                'severity': 'warning',
                'description': f"{severe_codes[weather_code]} conditions present",
                'current_condition': weather_desc
            })
        
        # Check for extreme temperatures
        temp_c = current.get('temp_C', 0)
        if int(temp_c) > 35:
            alerts.append({
                'type': 'temperature',
                'severity': 'warning',
                'description': f"Extreme heat: {temp_c}°C"
            })
        elif int(temp_c) < -20:
            alerts.append({
                'type': 'temperature',
                'severity': 'warning',
                'description': f"Extreme cold: {temp_c}°C"
            })
        
        # Check for high winds
        wind_kmph = current.get('windspeedKmph', 0)
        if int(wind_kmph) > 60:
            alerts.append({
                'type': 'wind',
                'severity': 'warning',
                'description': f"High winds: {wind_kmph} km/h"
            })
        
        # Check for poor visibility
        visibility = current.get('visibility', 10)
        if int(visibility) < 2:
            alerts.append({
                'type': 'visibility',
                'severity': 'warning',
                'description': f"Very poor visibility: {visibility} km"
            })
        
        return {
            'location': location_info,
            'alerts': alerts,
            'alert_count': len(alerts),
            'has_alerts': len(alerts) > 0
        }
    
    def get_air_quality(self, location: str) -> Dict[str, Any]:
        """
        Get air quality information for a location.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            
        Returns:
            Dictionary with air quality data
        """
        location = self._parse_location(location)
        data = self._make_request(location)
        
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format")
        
        # Get location info
        nearest_area = data.get('nearest_area', [{}])[0]
        location_info = {
            'city': nearest_area.get('areaName', [{}])[0].get('value', 'Unknown'),
            'region': nearest_area.get('region', [{}])[0].get('value', ''),
            'country': nearest_area.get('country', [{}])[0].get('value', ''),
        }
        
        # Get current conditions which may include AQI
        current = data.get('current_condition', [{}])[0]
        
        # Air quality index (if available in the response)
        # Note: wttr.in may not always have AQI data for all locations
        aqi = current.get('air_quality', {})
        
        if not aqi:
            return {
                'location': location_info,
                'air_quality': None,
                'available': False,
                'message': 'Air quality data not available for this location'
            }
        
        # Parse AQI data
        aqi_value = aqi.get('us-epa-index', aqi.get('value', 'N/A'))
        
        # EPA AQI scale interpretation
        aqi_scale = {
            '1': ('Good', 'Air quality is satisfactory', 'green'),
            '2': ('Moderate', 'Acceptable; some pollutants may be a concern', 'yellow'),
            '3': ('Unhealthy for Sensitive Groups', 'Sensitive individuals should limit outdoor exertion', 'orange'),
            '4': ('Unhealthy', 'Everyone may experience health effects', 'red'),
            '5': ('Very Unhealthy', 'Health warnings of emergency conditions', 'purple'),
            '6': ('Hazardous', 'Health alert: everyone may experience serious effects', 'maroon'),
        }
        
        if str(aqi_value) in aqi_scale:
            category, description, color = aqi_scale[str(aqi_value)]
        else:
            category, description, color = 'Unknown', 'AQI data unavailable', 'gray'
        
        return {
            'location': location_info,
            'air_quality': {
                'aqi': aqi_value,
                'category': category,
                'description': description,
                'color': color,
                'pm25': aqi.get('pm2.5', 'N/A'),
                'pm10': aqi.get('pm10', 'N/A'),
                'o3': aqi.get('o3', 'N/A'),
                'no2': aqi.get('no2', 'N/A'),
                'so2': aqi.get('so2', 'N/A'),
                'co': aqi.get('co', 'N/A'),
            },
            'available': True
        }
    
    def get_sunrise_sunset(self, location: str) -> Dict[str, Any]:
        """
        Get sunrise and sunset times for a location.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            
        Returns:
            Dictionary with astronomical data
        """
        location = self._parse_location(location)
        data = self._make_request(location)
        
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected response format")
        
        # Get location info
        nearest_area = data.get('nearest_area', [{}])[0]
        location_info = {
            'city': nearest_area.get('areaName', [{}])[0].get('value', 'Unknown'),
            'region': nearest_area.get('region', [{}])[0].get('value', ''),
            'country': nearest_area.get('country', [{}])[0].get('value', ''),
            'latitude': nearest_area.get('latitude', ''),
            'longitude': nearest_area.get('longitude', ''),
        }
        
        # Get astronomy data from the first day's weather
        weather = data.get('weather', [])
        if not weather:
            raise RuntimeError("No weather data available")
        
        today = weather[0]
        astronomy = today.get('astronomy', [{}])[0]
        
        # Calculate day length
        sunrise = astronomy.get('sunrise', 'N/A')
        sunset = astronomy.get('sunset', 'N/A')
        
        day_length = "N/A"
        if sunrise != 'N/A' and sunset != 'N/A':
            try:
                # Parse times
                sunrise_dt = datetime.strptime(sunrise.strip(), '%I:%M %p')
                sunset_dt = datetime.strptime(sunset.strip(), '%I:%M %p')
                
                # Calculate duration
                duration = sunset_dt - sunrise_dt
                hours, remainder = divmod(duration.seconds, 3600)
                minutes = remainder // 60
                day_length = f"{hours}h {minutes}m"
            except:
                pass
        
        return {
            'location': location_info,
            'date': today.get('date', ''),
            'sunrise': sunrise,
            'sunset': sunset,
            'moonrise': astronomy.get('moonrise', 'N/A'),
            'moonset': astronomy.get('moonset', 'N/A'),
            'moon_phase': astronomy.get('moon_phase', 'N/A'),
            'moon_illumination': astronomy.get('moon_illumination', 'N/A'),
            'day_length': day_length,
        }
    
    def get_historical_weather(
        self, 
        location: str, 
        date: str
    ) -> Dict[str, Any]:
        """
        Get historical weather data for a location and date.
        
        Note: wttr.in has limited historical data (typically up to ~1 year).
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with historical weather data
        """
        # Validate date format
        try:
            query_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        
        # Check if date is not too far in the past (wttr.in limitation)
        one_year_ago = datetime.now() - timedelta(days=365)
        if query_date < one_year_ago:
            raise ValueError("Historical data only available for approximately the last year")
        
        # Check if date is in the future
        if query_date > datetime.now():
            raise ValueError("Use get_forecast() for future dates")
        
        location = self._parse_location(location)
        
        # wttr.in doesn't have a direct historical API, but we can try
        # to use the date parameter if supported
        # For now, return a message about the limitation
        return {
            'location': location,
            'date': date,
            'available': False,
            'message': (
                'Historical weather data requires a different data source. '
                'Consider using OpenWeatherMap Historical API or similar service '
                'for historical weather data.'
            ),
            'note': 'wttr.in focuses on current and forecast data'
        }
    
    def format_location(self, location: str) -> Dict[str, Any]:
        """
        Format and validate a location string, returning location info.
        
        Args:
            location: Location string to format
            
        Returns:
            Dictionary with formatted location and metadata
        """
        location = self._parse_location(location)
        
        try:
            data = self._make_request(location)
            
            if not isinstance(data, dict):
                raise RuntimeError("Unexpected response format")
            
            nearest_area = data.get('nearest_area', [{}])[0]
            
            return {
                'input': location,
                'valid': True,
                'formatted': {
                    'city': nearest_area.get('areaName', [{}])[0].get('value', ''),
                    'region': nearest_area.get('region', [{}])[0].get('value', ''),
                    'country': nearest_area.get('country', [{}])[0].get('value', ''),
                    'latitude': nearest_area.get('latitude', ''),
                    'longitude': nearest_area.get('longitude', ''),
                },
                'display_name': self._build_display_name(nearest_area)
            }
            
        except Exception as e:
            return {
                'input': location,
                'valid': False,
                'error': str(e)
            }
    
    def _build_display_name(self, area: Dict) -> str:
        """Build a human-readable display name from area data."""
        parts = []
        
        city = area.get('areaName', [{}])[0].get('value', '')
        region = area.get('region', [{}])[0].get('value', '')
        country = area.get('country', [{}])[0].get('value', '')
        
        if city:
            parts.append(city)
        if region and region != city:
            parts.append(region)
        if country:
            parts.append(country)
        
        return ', '.join(parts) if parts else 'Unknown Location'
    
    def get_moon_phase(self) -> Dict[str, Any]:
        """
        Get current moon phase information.
        
        Returns:
            Dictionary with moon phase data
        """
        data = self._make_request('moon')
        
        if isinstance(data, str):
            # wttr.in returns text for moon
            return {
                'moon_data': data,
                'format': 'text'
            }
        
        return {
            'moon_data': data,
            'format': 'json'
        }


def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Weather Skill for Cell 0 OS"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Current weather
    current_parser = subparsers.add_parser("current", help="Get current weather")
    current_parser.add_argument("location", help="Location (city, coords, airport code)")
    current_parser.add_argument("--units", choices=["metric", "imperial"], default="metric")
    
    # Forecast
    forecast_parser = subparsers.add_parser("forecast", help="Get weather forecast")
    forecast_parser.add_argument("location", help="Location")
    forecast_parser.add_argument("--days", type=int, default=3, choices=[1, 2, 3])
    forecast_parser.add_argument("--units", choices=["metric", "imperial"], default="metric")
    
    # Alerts
    alerts_parser = subparsers.add_parser("alerts", help="Get weather alerts")
    alerts_parser.add_argument("location", help="Location")
    
    # Air quality
    aqi_parser = subparsers.add_parser("air-quality", help="Get air quality")
    aqi_parser.add_argument("location", help="Location")
    
    # Sunrise/sunset
    sun_parser = subparsers.add_parser("sun", help="Get sunrise/sunset times")
    sun_parser.add_argument("location", help="Location")
    
    # Moon
    subparsers.add_parser("moon", help="Get moon phase")
    
    # Format location
    format_parser = subparsers.add_parser("format", help="Format/validate location")
    format_parser.add_argument("location", help="Location to format")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        skill = WeatherSkill()
        
        if args.command == "current":
            result = skill.get_current_weather(args.location, args.units)
        elif args.command == "forecast":
            result = skill.get_forecast(args.location, args.days, args.units)
        elif args.command == "alerts":
            result = skill.get_weather_alerts(args.location)
        elif args.command == "air-quality":
            result = skill.get_air_quality(args.location)
        elif args.command == "sun":
            result = skill.get_sunrise_sunset(args.location)
        elif args.command == "moon":
            result = skill.get_moon_phase()
        elif args.command == "format":
            result = skill.format_location(args.location)
        else:
            parser.print_help()
            return
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=__import__('sys').stderr)
        exit(1)


if __name__ == "__main__":
    main()
