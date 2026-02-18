#!/usr/bin/env python3
"""
Tools for Weather Skill - Agent Integration
High-level tools for AI agents to interact with weather data

Provides semantic, agent-friendly methods for weather operations
with natural language support.
"""

from typing import Optional, List, Dict, Any, Union
try:
    from .weather_skill import WeatherSkill
except ImportError:
    from weather_skill import WeatherSkill


class WeatherTools:
    """
    High-level tools for AI agents to access weather information.
    
    This class provides semantic, agent-friendly methods for common
    weather operations with natural language support.
    """
    
    def __init__(self):
        self.skill = WeatherSkill()
    
    # ========================================================================
    # Discovery Tools
    # ========================================================================
    
    def format_weather_summary(self, weather_data: Dict[str, Any]) -> str:
        """
        Format weather data into a human-readable summary.
        
        Args:
            weather_data: Weather data dictionary
            
        Returns:
            Formatted string
        """
        location = weather_data.get('location', {})
        current = weather_data.get('current', {})
        units = weather_data.get('units', 'metric')
        
        temp_unit = '°C' if units == 'metric' else '°F'
        speed_unit = 'km/h' if units == 'metric' else 'mph'
        
        city = location.get('city', 'Unknown')
        country = location.get('country', '')
        location_str = f"{city}, {country}" if country else city
        
        temp = current.get('temperature', 'N/A')
        feels_like = current.get('feels_like', 'N/A')
        condition = current.get('condition', 'Unknown')
        humidity = current.get('humidity', 'N/A')
        wind = current.get('wind_speed', 'N/A')
        wind_dir = current.get('wind_direction', '')
        
        result = [
            f"🌤️  Weather in {location_str}",
            "",
            f"   {condition}",
            f"   Temperature: {temp}{temp_unit} (feels like {feels_like}{temp_unit})",
            f"   Humidity: {humidity}%",
            f"   Wind: {wind} {speed_unit} {wind_dir}",
        ]
        
        # Add optional fields if present
        if current.get('pressure'):
            result.append(f"   Pressure: {current['pressure']} mb")
        if current.get('uv_index'):
            uv = current['uv_index']
            uv_emoji = '🔴' if int(uv) > 5 else '🟡' if int(uv) > 2 else '🟢'
            result.append(f"   UV Index: {uv_emoji} {uv}")
        if current.get('visibility'):
            result.append(f"   Visibility: {current['visibility']} km")
        
        return "\n".join(result)
    
    def get_weather_now(self, location: str, units: str = "metric") -> str:
        """
        Get current weather in a human-readable format.
        
        Args:
            location: Location (city, coordinates, airport code, etc.)
            units: 'metric' or 'imperial'
            
        Returns:
            Formatted weather string
        """
        try:
            data = self.skill.get_current_weather(location, units)
            return self.format_weather_summary(data)
        except Exception as e:
            return f"❌ Error getting weather: {e}"
    
    def get_forecast_summary(self, location: str, days: int = 3, units: str = "metric") -> str:
        """
        Get a summary weather forecast.
        
        Args:
            location: Location
            days: Number of days (1-3)
            units: 'metric' or 'imperial'
            
        Returns:
            Formatted forecast string
        """
        try:
            data = self.skill.get_forecast(location, days, units)
            location_info = data.get('location', {})
            forecast = data.get('forecast', [])
            
            city = location_info.get('city', 'Unknown')
            country = location_info.get('country', '')
            location_str = f"{city}, {country}" if country else city
            
            temp_unit = '°C' if units == 'metric' else '°F'
            
            result = [
                f"📅 Weather Forecast for {location_str}",
                "",
            ]
            
            for day in forecast:
                date = day.get('date', 'Unknown')
                max_temp = day.get('max_temp', 'N/A')
                min_temp = day.get('min_temp', 'N/A')
                condition = day.get('hourly', [{}])[0].get('condition', 'Unknown')
                
                # Get emoji for weather
                emoji = self._get_weather_emoji(condition)
                
                result.append(f"{emoji} {date}: {min_temp}{temp_unit} - {max_temp}{temp_unit}, {condition}")
                result.append(f"   ☀️  Sunrise: {day.get('sunrise', 'N/A')}  🌅 Sunset: {day.get('sunset', 'N/A')}")
                result.append("")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error getting forecast: {e}"
    
    def get_alerts_summary(self, location: str) -> str:
        """
        Get weather alerts in a human-readable format.
        
        Args:
            location: Location
            
        Returns:
            Formatted alerts string
        """
        try:
            data = self.skill.get_weather_alerts(location)
            location_info = data.get('location', {})
            alerts = data.get('alerts', [])
            
            city = location_info.get('city', 'Unknown')
            country = location_info.get('country', '')
            location_str = f"{city}, {country}" if country else city
            
            if not alerts:
                return f"✅ No weather alerts for {location_str}"
            
            result = [
                f"⚠️  Weather Alerts for {location_str}",
                "",
            ]
            
            for alert in alerts:
                severity = alert.get('severity', 'warning')
                alert_type = alert.get('type', 'general')
                description = alert.get('description', '')
                
                emoji = '🔴' if severity == 'severe' else '🟡' if severity == 'warning' else '🟢'
                
                result.append(f"{emoji} {alert_type.upper()}: {description}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error getting alerts: {e}"
    
    def get_air_quality_summary(self, location: str) -> str:
        """
        Get air quality information in a human-readable format.
        
        Args:
            location: Location
            
        Returns:
            Formatted air quality string
        """
        try:
            data = self.skill.get_air_quality(location)
            location_info = data.get('location', {})
            aqi_data = data.get('air_quality', {})
            
            city = location_info.get('city', 'Unknown')
            country = location_info.get('country', '')
            location_str = f"{city}, {country}" if country else city
            
            if not data.get('available', False):
                return f"📊 Air quality data not available for {location_str}"
            
            aqi = aqi_data.get('aqi', 'N/A')
            category = aqi_data.get('category', 'Unknown')
            description = aqi_data.get('description', '')
            color = aqi_data.get('color', 'gray')
            
            # Emoji based on color
            color_emoji = {
                'green': '🟢',
                'yellow': '🟡',
                'orange': '🟠',
                'red': '🔴',
                'purple': '🟣',
                'maroon': '🟤',
            }.get(color, '⚪')
            
            result = [
                f"🌫️  Air Quality for {location_str}",
                "",
                f"{color_emoji} AQI: {aqi} - {category}",
                f"   {description}",
                "",
                "Pollutant Levels:",
            ]
            
            # Add pollutant details
            if aqi_data.get('pm25') != 'N/A':
                result.append(f"   PM2.5: {aqi_data['pm25']} µg/m³")
            if aqi_data.get('pm10') != 'N/A':
                result.append(f"   PM10: {aqi_data['pm10']} µg/m³")
            if aqi_data.get('o3') != 'N/A':
                result.append(f"   Ozone (O₃): {aqi_data['o3']} µg/m³")
            if aqi_data.get('no2') != 'N/A':
                result.append(f"   NO₂: {aqi_data['no2']} µg/m³")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error getting air quality: {e}"
    
    def get_sun_times(self, location: str) -> str:
        """
        Get sunrise and sunset times in a human-readable format.
        
        Args:
            location: Location
            
        Returns:
            Formatted sun times string
        """
        try:
            data = self.skill.get_sunrise_sunset(location)
            location_info = data.get('location', {})
            
            city = location_info.get('city', 'Unknown')
            country = location_info.get('country', '')
            location_str = f"{city}, {country}" if country else city
            
            result = [
                f"☀️  Sun Times for {location_str}",
                f"   Date: {data.get('date', 'Today')}",
                "",
                f"   🌅 Sunrise: {data.get('sunrise', 'N/A')}",
                f"   🌇 Sunset: {data.get('sunset', 'N/A')}",
                f"   ⏱️  Day Length: {data.get('day_length', 'N/A')}",
                "",
                f"   🌙 Moonrise: {data.get('moonrise', 'N/A')}",
                f"   🌕 Moonset: {data.get('moonset', 'N/A')}",
                f"   Phase: {data.get('moon_phase', 'N/A')}",
            ]
            
            if data.get('moon_illumination') != 'N/A':
                result.append(f"   Illumination: {data['moon_illumination']}%")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error getting sun times: {e}"
    
    def get_moon_info(self) -> str:
        """
        Get moon phase information.
        
        Returns:
            Formatted moon information
        """
        try:
            data = self.skill.get_moon_phase()
            
            if data.get('format') == 'text':
                return f"🌙 Moon Phase:\n\n{data.get('moon_data', 'No data available')}"
            
            return f"🌙 Moon Phase:\n\n{data.get('moon_data', {})}"
            
        except Exception as e:
            return f"❌ Error getting moon info: {e}"
    
    def _get_weather_emoji(self, condition: str) -> str:
        """Get emoji for weather condition."""
        condition_lower = condition.lower()
        
        if 'sun' in condition_lower or 'clear' in condition_lower:
            return '☀️'
        elif 'cloud' in condition_lower:
            if 'partly' in condition_lower:
                return '⛅'
            return '☁️'
        elif 'rain' in condition_lower:
            if 'heavy' in condition_lower:
                return '⛈️'
            return '🌧️'
        elif 'snow' in condition_lower:
            return '❄️'
        elif 'thunder' in condition_lower or 'storm' in condition_lower:
            return '⛈️'
        elif 'fog' in condition_lower or 'mist' in condition_lower:
            return '🌫️'
        elif 'wind' in condition_lower:
            return '💨'
        else:
            return '🌤️'
    
    # ========================================================================
    # Action Tools
    # ========================================================================
    
    def check_weather_for_trip(
        self, 
        location: str, 
        days: int = 3, 
        units: str = "metric"
    ) -> str:
        """
        Get a comprehensive weather check for trip planning.
        
        Args:
            location: Destination
            days: How many days to check
            units: 'metric' or 'imperial'
            
        Returns:
            Formatted trip weather report
        """
        try:
            # Get current weather
            current = self.skill.get_current_weather(location, units)
            
            # Get forecast
            forecast = self.skill.get_forecast(location, days, units)
            
            # Get alerts
            alerts = self.skill.get_weather_alerts(location)
            
            # Get air quality
            aqi = self.skill.get_air_quality(location)
            
            location_info = current.get('location', {})
            city = location_info.get('city', 'Unknown')
            country = location_info.get('country', '')
            location_str = f"{city}, {country}" if country else city
            
            result = [
                f"✈️  Weather Report for {location_str}",
                "=" * 50,
                "",
            ]
            
            # Current conditions
            result.append(self.format_weather_summary(current))
            result.append("")
            
            # Alerts
            if alerts.get('has_alerts'):
                result.append("⚠️  WEATHER ALERTS:")
                for alert in alerts.get('alerts', []):
                    result.append(f"   • {alert.get('description', '')}")
                result.append("")
            
            # Air quality
            if aqi.get('available'):
                aqi_data = aqi.get('air_quality', {})
                category = aqi_data.get('category', '')
                if category not in ['Good', 'Moderate']:
                    result.append(f"🌫️  Air Quality: {category}")
                    result.append("")
            
            # Forecast
            result.append("📅 FORECAST:")
            for day in forecast.get('forecast', []):
                date = day.get('date', '')
                temp_unit = '°C' if units == 'metric' else '°F'
                max_temp = day.get('max_temp', 'N/A')
                min_temp = day.get('min_temp', 'N/A')
                condition = day.get('hourly', [{}])[0].get('condition', '')
                emoji = self._get_weather_emoji(condition)
                
                result.append(f"   {emoji} {date}: {min_temp}{temp_unit} - {max_temp}{temp_unit}, {condition}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error checking trip weather: {e}"
    
    def compare_locations(
        self, 
        locations: List[str], 
        units: str = "metric"
    ) -> str:
        """
        Compare current weather across multiple locations.
        
        Args:
            locations: List of locations to compare
            units: 'metric' or 'imperial'
            
        Returns:
            Formatted comparison string
        """
        if not locations:
            return "No locations provided"
        
        results = []
        temp_unit = '°C' if units == 'metric' else '°F'
        
        result = [
            f"🌍 Weather Comparison",
            "",
        ]
        
        for location in locations:
            try:
                data = self.skill.get_current_weather(location, units)
                location_info = data.get('location', {})
                current = data.get('current', {})
                
                city = location_info.get('city', location)
                temp = current.get('temperature', 'N/A')
                condition = current.get('condition', 'Unknown')
                emoji = self._get_weather_emoji(condition)
                
                result.append(f"{emoji} {city}: {temp}{temp_unit}, {condition}")
                
            except Exception as e:
                result.append(f"❌ {location}: Error - {e}")
        
        return "\n".join(result)
    
    def should_pack_umbrella(self, location: str, days: int = 1) -> str:
        """
        Check if you should pack an umbrella for a location.
        
        Args:
            location: Location to check
            days: Number of days to check
            
        Returns:
            Recommendation string
        """
        try:
            forecast = self.skill.get_forecast(location, days)
            location_info = forecast.get('location', {})
            city = location_info.get('city', location)
            
            rain_probability = 0
            rain_days = []
            
            for day in forecast.get('forecast', []):
                date = day.get('date', '')
                hourly = day.get('hourly', [])
                
                for hour in hourly:
                    chance = hour.get('chance_of_rain', '0')
                    try:
                        chance_int = int(chance)
                        if chance_int > rain_probability:
                            rain_probability = chance_int
                        if chance_int > 50 and date not in rain_days:
                            rain_days.append(date)
                    except:
                        pass
            
            if rain_probability > 70:
                return f"☔ Definitely pack an umbrella for {city}! Rain expected ({rain_probability}% chance)."
            elif rain_probability > 40:
                days_str = f" on {', '.join(rain_days)}" if rain_days else ""
                return f"🌂 Consider bringing an umbrella to {city}{days_str} ({rain_probability}% chance of rain)."
            else:
                return f"☀️ No umbrella needed for {city}. Low chance of rain ({rain_probability}%)."
                
        except Exception as e:
            return f"❌ Error checking weather: {e}"
    
    def is_good_for_outdoor_activity(
        self, 
        location: str, 
        activity: str = "general"
    ) -> str:
        """
        Check if weather is good for outdoor activities.
        
        Args:
            location: Location to check
            activity: Type of activity (hiking, beach, picnic, etc.)
            
        Returns:
            Recommendation string
        """
        try:
            current = self.skill.get_current_weather(location)
            alerts = self.skill.get_weather_alerts(location)
            
            location_info = current.get('location', {})
            current_data = current.get('current', {})
            city = location_info.get('city', location)
            
            temp = current_data.get('temperature', 0)
            condition = current_data.get('condition', '').lower()
            wind = current_data.get('wind_speed', 0)
            uv = current_data.get('uv_index', 0)
            
            issues = []
            
            # Check for alerts
            if alerts.get('has_alerts'):
                issues.append("⚠️ weather alerts in effect")
            
            # Check temperature
            try:
                temp_int = int(temp)
                units = current.get('units', 'metric')
                
                if activity.lower() == 'beach':
                    if temp_int < 20 and units == 'metric':
                        issues.append(f"❄️ too cold ({temp}°)")
                elif activity.lower() == 'hiking':
                    if temp_int > 35 and units == 'metric':
                        issues.append(f"🥵 too hot ({temp}°)")
                    elif temp_int < -10 and units == 'metric':
                        issues.append(f"❄️ too cold ({temp}°)")
                else:
                    if temp_int < 0 and units == 'metric':
                        issues.append(f"❄️ freezing ({temp}°)")
                    elif temp_int > 38 and units == 'metric':
                        issues.append(f"🥵 extreme heat ({temp}°)")
            except:
                pass
            
            # Check conditions
            bad_conditions = ['rain', 'storm', 'thunder', 'snow', 'blizzard', 'fog']
            if any(bc in condition for bc in bad_conditions):
                issues.append(f"🌧️ {condition}")
            
            # Check wind
            try:
                wind_int = int(wind)
                if wind_int > 50:
                    issues.append(f"💨 very windy ({wind} km/h)")
            except:
                pass
            
            # Generate response
            if not issues:
                return f"✅ Perfect weather for {activity} in {city}! {condition}, {temp}°"
            else:
                issues_str = " | ".join(issues)
                return f"⚠️ Not ideal for {activity} in {city}: {issues_str}"
                
        except Exception as e:
            return f"❌ Error checking weather: {e}"


# Convenience functions for direct import
_tools_instance = None

def _get_tools() -> WeatherTools:
    """Get or create singleton tools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = WeatherTools()
    return _tools_instance


# Expose common operations as module-level functions
def current(location: str, units: str = "metric") -> str:
    """Get current weather."""
    return _get_tools().get_weather_now(location, units)

def forecast(location: str, days: int = 3, units: str = "metric") -> str:
    """Get weather forecast."""
    return _get_tools().get_forecast_summary(location, days, units)

def alerts(location: str) -> str:
    """Get weather alerts."""
    return _get_tools().get_alerts_summary(location)

def air_quality(location: str) -> str:
    """Get air quality."""
    return _get_tools().get_air_quality_summary(location)

def sun_times(location: str) -> str:
    """Get sunrise/sunset times."""
    return _get_tools().get_sun_times(location)

def moon() -> str:
    """Get moon phase."""
    return _get_tools().get_moon_info()

def trip_weather(location: str, days: int = 3, units: str = "metric") -> str:
    """Get comprehensive trip weather."""
    return _get_tools().check_weather_for_trip(location, days, units)

def compare(*locations: str, units: str = "metric") -> str:
    """Compare weather across locations."""
    return _get_tools().compare_locations(list(locations), units)

def umbrella(location: str, days: int = 1) -> str:
    """Check if umbrella is needed."""
    return _get_tools().should_pack_umbrella(location, days)

def good_for(activity: str, location: str) -> str:
    """Check if weather is good for an activity."""
    return _get_tools().is_good_for_outdoor_activity(location, activity)
