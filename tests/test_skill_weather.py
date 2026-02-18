#!/usr/bin/env python3
"""
Tests for Weather Skill

These tests use mocking to avoid requiring network access to wttr.in
during testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
from datetime import datetime, timedelta

# Add paths for imports - use relative paths
skills_path = os.path.join(os.path.dirname(__file__), '..', 'skills')
sys.path.insert(0, os.path.join(skills_path, 'weather'))
sys.path.insert(0, skills_path)

# Mock requests module before importing weather_skill
mock_requests = MagicMock()
mock_session = MagicMock()
mock_requests.Session.return_value = mock_session
sys.modules['requests'] = mock_requests

# Use absolute import to avoid module caching issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "weather_skill_module",
    os.path.join(skills_path, 'weather', 'weather_skill.py')
)
weather_skill_module = importlib.util.module_from_spec(spec)
sys.modules["weather_skill_module"] = weather_skill_module
spec.loader.exec_module(weather_skill_module)
WeatherSkill = weather_skill_module.WeatherSkill

spec_tools = importlib.util.spec_from_file_location(
    "weather_tools_module",
    os.path.join(skills_path, 'weather', 'tools.py')
)
weather_tools_module = importlib.util.module_from_spec(spec_tools)
sys.modules["weather_tools_module"] = weather_tools_module
spec_tools.loader.exec_module(weather_tools_module)
WeatherTools = weather_tools_module.WeatherTools


class TestWeatherSkill(unittest.TestCase):
    """Test cases for WeatherSkill class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.skill = WeatherSkill()
    
    def test_init(self):
        """Test that initialization sets up the session correctly."""
        self.assertEqual(self.skill.BASE_URL, "https://wttr.in")
        self.assertIsNotNone(self.skill.session)
    
    def test_parse_location_city(self):
        """Test parsing city name location."""
        result = self.skill._parse_location("London")
        self.assertEqual(result, "London")
    
    def test_parse_location_with_spaces(self):
        """Test parsing city name with spaces."""
        result = self.skill._parse_location("New York")
        self.assertEqual(result, "New+York")
    
    def test_parse_location_coordinates(self):
        """Test parsing coordinate location."""
        result = self.skill._parse_location("51.5074,-0.1278")
        self.assertEqual(result, "51.5074,-0.1278")
    
    def test_parse_location_airport_code(self):
        """Test parsing airport code location."""
        result = self.skill._parse_location("jfk")
        self.assertEqual(result, "JFK")
    
    def test_parse_location_domain(self):
        """Test parsing domain name location."""
        result = self.skill._parse_location("@github.com")
        self.assertEqual(result, "@github.com")
    
    def test_parse_location_special(self):
        """Test parsing special locations."""
        self.assertEqual(self.skill._parse_location("moon"), "moon")
        self.assertEqual(self.skill._parse_location(":ip"), ":ip")
        self.assertEqual(self.skill._parse_location("ip"), "ip")
    
    @patch('weather_skill.requests.Session.get')
    def test_make_request_success_json(self, mock_get):
        """Test successful JSON request."""
        mock_response = Mock()
        mock_response.json.return_value = {'current_condition': [{'temp_C': '20'}]}
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.skill._make_request("London")
        
        self.assertIsInstance(result, dict)
        self.assertIn('current_condition', result)
        mock_get.assert_called_once()
    
    @patch('weather_skill.requests.Session.get')
    def test_make_request_success_text(self, mock_get):
        """Test successful text request."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("test", "doc", 0)
        mock_response.text = "Weather data"
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.skill._make_request("London")
        
        self.assertEqual(result, "Weather data")
    
    @patch('weather_skill.requests.Session.get')
    def test_make_request_timeout(self, mock_get):
        """Test request timeout handling."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(RuntimeError) as context:
            self.skill._make_request("London")
        
        self.assertIn("timed out", str(context.exception).lower())
    
    @patch('weather_skill.requests.Session.get')
    def test_make_request_connection_error(self, mock_get):
        """Test connection error handling."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        with self.assertRaises(RuntimeError) as context:
            self.skill._make_request("London")
        
        self.assertIn("connection", str(context.exception).lower())
    
    @patch('weather_skill.requests.Session.get')
    def test_make_request_404(self, mock_get):
        """Test 404 error handling."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            self.skill._make_request("InvalidLocation12345")
        
        self.assertIn("not found", str(context.exception).lower())
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_current_weather(self, mock_request):
        """Test getting current weather."""
        mock_request.return_value = {
            'current_condition': [{
                'temp_C': '20',
                'FeelsLikeC': '18',
                'weatherDesc': [{'value': 'Sunny'}],
                'humidity': '60',
                'windspeedKmph': '15',
                'winddir16Point': 'SW',
                'pressure': '1013',
                'uvIndex': '5',
                'observation_time': '12:00 PM'
            }],
            'nearest_area': [{
                'areaName': [{'value': 'London'}],
                'region': [{'value': 'City of London'}],
                'country': [{'value': 'United Kingdom'}],
                'latitude': '51.517',
                'longitude': '-0.106'
            }]
        }
        
        result = self.skill.get_current_weather("London")
        
        self.assertEqual(result['location']['city'], 'London')
        self.assertEqual(result['location']['country'], 'United Kingdom')
        self.assertEqual(result['current']['temperature'], '20')
        self.assertEqual(result['current']['condition'], 'Sunny')
        self.assertEqual(result['units'], 'metric')
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_current_weather_imperial(self, mock_request):
        """Test getting current weather in imperial units."""
        mock_request.return_value = {
            'current_condition': [{
                'temp_F': '68',
                'FeelsLikeF': '64',
                'weatherDesc': [{'value': 'Sunny'}],
                'humidity': '60',
                'windspeedMiles': '9',
                'winddir16Point': 'SW',
            }],
            'nearest_area': [{
                'areaName': [{'value': 'London'}],
                'region': [{'value': 'City of London'}],
                'country': [{'value': 'United Kingdom'}],
            }]
        }
        
        result = self.skill.get_current_weather("London", units="imperial")
        
        self.assertEqual(result['current']['temperature'], '68')
        self.assertEqual(result['units'], 'imperial')
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_forecast(self, mock_request):
        """Test getting weather forecast."""
        mock_request.return_value = {
            'nearest_area': [{
                'areaName': [{'value': 'Paris'}],
                'country': [{'value': 'France'}],
            }],
            'weather': [
                {
                    'date': '2026-02-12',
                    'maxtempC': '15',
                    'mintempC': '8',
                    'avgtempC': '11',
                    'astronomy': [{
                        'sunrise': '07:45 AM',
                        'sunset': '06:15 PM',
                        'moon_phase': 'Waxing Gibbous',
                    }],
                    'uvIndex': '3',
                    'hourly': [
                        {'time': '0', 'tempC': '9', 'weatherDesc': [{'value': 'Clear'}]},
                        {'time': '1200', 'tempC': '14', 'weatherDesc': [{'value': 'Sunny'}]},
                    ]
                }
            ]
        }
        
        result = self.skill.get_forecast("Paris", days=1)
        
        self.assertEqual(result['location']['city'], 'Paris')
        self.assertEqual(len(result['forecast']), 1)
        self.assertEqual(result['forecast'][0]['max_temp'], '15')
        self.assertEqual(result['forecast'][0]['sunrise'], '07:45 AM')
    
    def test_get_forecast_invalid_days(self):
        """Test forecast with invalid days parameter."""
        with self.assertRaises(ValueError):
            self.skill.get_forecast("London", days=5)
        
        with self.assertRaises(ValueError):
            self.skill.get_forecast("London", days=0)
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_weather_alerts_no_alerts(self, mock_request):
        """Test getting weather alerts when none exist."""
        mock_request.return_value = {
            'current_condition': [{
                'temp_C': '20',
                'weatherCode': '113',  # Clear
                'weatherDesc': [{'value': 'Sunny'}],
                'windspeedKmph': '10',
                'visibility': '10',
            }],
            'nearest_area': [{
                'areaName': [{'value': 'Madrid'}],
                'country': [{'value': 'Spain'}],
            }]
        }
        
        result = self.skill.get_weather_alerts("Madrid")
        
        self.assertEqual(result['alert_count'], 0)
        self.assertFalse(result['has_alerts'])
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_weather_alerts_with_alerts(self, mock_request):
        """Test getting weather alerts when conditions are severe."""
        mock_request.return_value = {
            'current_condition': [{
                'temp_C': '38',
                'weatherCode': '389',  # Thunderstorm
                'weatherDesc': [{'value': 'Thunderstorm'}],
                'windspeedKmph': '70',
                'visibility': '1',
            }],
            'nearest_area': [{
                'areaName': [{'value': 'Miami'}],
                'country': [{'value': 'USA'}],
            }]
        }
        
        result = self.skill.get_weather_alerts("Miami")
        
        self.assertTrue(result['has_alerts'])
        self.assertGreater(result['alert_count'], 0)
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_air_quality_available(self, mock_request):
        """Test getting air quality when data is available."""
        mock_request.return_value = {
            'current_condition': [{
                'air_quality': {
                    'us-epa-index': '2',
                    'pm2.5': '15',
                    'pm10': '25',
                    'o3': '40',
                    'no2': '20',
                }
            }],
            'nearest_area': [{
                'areaName': [{'value': 'Berlin'}],
                'country': [{'value': 'Germany'}],
            }]
        }
        
        result = self.skill.get_air_quality("Berlin")
        
        self.assertTrue(result['available'])
        self.assertEqual(result['air_quality']['aqi'], '2')
        self.assertEqual(result['air_quality']['category'], 'Moderate')
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_air_quality_unavailable(self, mock_request):
        """Test getting air quality when data is unavailable."""
        mock_request.return_value = {
            'current_condition': [{}],
            'nearest_area': [{
                'areaName': [{'value': 'Small Town'}],
                'country': [{'value': 'Unknown'}],
            }]
        }
        
        result = self.skill.get_air_quality("Small Town")
        
        self.assertFalse(result['available'])
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_sunrise_sunset(self, mock_request):
        """Test getting sunrise/sunset times."""
        mock_request.return_value = {
            'nearest_area': [{
                'areaName': [{'value': 'Tokyo'}],
                'country': [{'value': 'Japan'}],
                'latitude': '35.6895',
                'longitude': '139.6917',
            }],
            'weather': [{
                'date': '2026-02-12',
                'astronomy': [{
                    'sunrise': '06:30 AM',
                    'sunset': '05:45 PM',
                    'moonrise': '08:00 PM',
                    'moonset': '07:15 AM',
                    'moon_phase': 'Full Moon',
                    'moon_illumination': '100',
                }]
            }]
        }
        
        result = self.skill.get_sunrise_sunset("Tokyo")
        
        self.assertEqual(result['sunrise'], '06:30 AM')
        self.assertEqual(result['sunset'], '05:45 PM')
        self.assertEqual(result['moon_phase'], 'Full Moon')
        self.assertEqual(result['day_length'], '11h 15m')
    
    def test_get_historical_weather_invalid_date(self):
        """Test historical weather with invalid date format."""
        with self.assertRaises(ValueError) as context:
            self.skill.get_historical_weather("London", "invalid-date")
        
        self.assertIn("YYYY-MM-DD", str(context.exception))
    
    def test_get_historical_weather_too_old(self):
        """Test historical weather with date too far in the past."""
        old_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        
        with self.assertRaises(ValueError) as context:
            self.skill.get_historical_weather("London", old_date)
        
        self.assertIn("last year", str(context.exception))
    
    def test_get_historical_weather_future(self):
        """Test historical weather with future date."""
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        
        with self.assertRaises(ValueError) as context:
            self.skill.get_historical_weather("London", future_date)
        
        self.assertIn("forecast", str(context.exception))
    
    @patch.object(WeatherSkill, '_make_request')
    def test_format_location_valid(self, mock_request):
        """Test formatting a valid location."""
        mock_request.return_value = {
            'nearest_area': [{
                'areaName': [{'value': 'Sydney'}],
                'region': [{'value': 'New South Wales'}],
                'country': [{'value': 'Australia'}],
                'latitude': '-33.8688',
                'longitude': '151.2093',
            }]
        }
        
        result = self.skill.format_location("Sydney")
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['formatted']['city'], 'Sydney')
        self.assertEqual(result['formatted']['country'], 'Australia')
    
    @patch.object(WeatherSkill, '_make_request')
    def test_format_location_invalid(self, mock_request):
        """Test formatting an invalid location."""
        mock_request.side_effect = RuntimeError("Location not found")
        
        result = self.skill.format_location("NotARealPlace12345")
        
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
    
    @patch.object(WeatherSkill, '_make_request')
    def test_get_moon_phase(self, mock_request):
        """Test getting moon phase."""
        mock_request.return_value = "Full Moon\nIllumination: 100%"
        
        result = self.skill.get_moon_phase()
        
        self.assertEqual(result['format'], 'text')
        self.assertIn('moon', result['moon_data'].lower())


class TestWeatherTools(unittest.TestCase):
    """Test cases for WeatherTools class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tools = WeatherTools()
    
    def test_format_weather_summary(self):
        """Test formatting weather summary."""
        weather_data = {
            'location': {
                'city': 'London',
                'country': 'United Kingdom',
            },
            'current': {
                'temperature': '18',
                'feels_like': '16',
                'condition': 'Partly cloudy',
                'humidity': '65',
                'wind_speed': '12',
                'wind_direction': 'SW',
                'pressure': '1015',
                'uv_index': '4',
            },
            'units': 'metric'
        }
        
        result = self.tools.format_weather_summary(weather_data)
        
        self.assertIn('London', result)
        self.assertIn('Partly cloudy', result)
        self.assertIn('18°C', result)
    
    @patch.object(WeatherSkill, 'get_current_weather')
    def test_get_weather_now(self, mock_get):
        """Test getting current weather summary."""
        mock_get.return_value = {
            'location': {'city': 'Paris', 'country': 'France'},
            'current': {
                'temperature': '22',
                'feels_like': '21',
                'condition': 'Sunny',
                'humidity': '50',
                'wind_speed': '8',
                'wind_direction': 'NE',
            },
            'units': 'metric'
        }
        
        result = self.tools.get_weather_now("Paris")
        
        self.assertIn('Paris', result)
        self.assertIn('Sunny', result)
        self.assertIn('22°C', result)
    
    @patch.object(WeatherSkill, 'get_current_weather')
    def test_get_weather_now_error(self, mock_get):
        """Test error handling in get_weather_now."""
        mock_get.side_effect = RuntimeError("Network error")
        
        result = self.tools.get_weather_now("Invalid")
        
        self.assertIn('❌ Error', result)
    
    @patch.object(WeatherSkill, 'get_forecast')
    def test_get_forecast_summary(self, mock_get):
        """Test getting forecast summary."""
        mock_get.return_value = {
            'location': {'city': 'Berlin', 'country': 'Germany'},
            'forecast': [
                {
                    'date': '2026-02-12',
                    'max_temp': '10',
                    'min_temp': '2',
                    'sunrise': '07:15 AM',
                    'sunset': '05:30 PM',
                    'hourly': [{'condition': 'Cloudy'}]
                }
            ]
        }
        
        result = self.tools.get_forecast_summary("Berlin", days=1)
        
        self.assertIn('Berlin', result)
        self.assertIn('2026-02-12', result)
        self.assertIn('Cloudy', result)
    
    @patch.object(WeatherSkill, 'get_weather_alerts')
    def test_get_alerts_summary_no_alerts(self, mock_get):
        """Test alerts summary when no alerts."""
        mock_get.return_value = {
            'location': {'city': 'Rome', 'country': 'Italy'},
            'alerts': [],
            'has_alerts': False
        }
        
        result = self.tools.get_alerts_summary("Rome")
        
        self.assertIn('No weather alerts', result)
    
    @patch.object(WeatherSkill, 'get_weather_alerts')
    def test_get_alerts_summary_with_alerts(self, mock_get):
        """Test alerts summary when alerts exist."""
        mock_get.return_value = {
            'location': {'city': 'Miami', 'country': 'USA'},
            'alerts': [
                {'type': 'wind', 'severity': 'warning', 'description': 'High winds expected'}
            ],
            'has_alerts': True
        }
        
        result = self.tools.get_alerts_summary("Miami")
        
        self.assertIn('Weather Alerts', result)
        self.assertIn('High winds', result)
    
    @patch.object(WeatherSkill, 'get_air_quality')
    def test_get_air_quality_summary_available(self, mock_get):
        """Test air quality summary when data available."""
        mock_get.return_value = {
            'location': {'city': 'Beijing', 'country': 'China'},
            'available': True,
            'air_quality': {
                'aqi': '4',
                'category': 'Unhealthy',
                'description': 'Everyone may experience health effects',
                'color': 'red',
                'pm25': '35',
                'pm10': '60',
            }
        }
        
        result = self.tools.get_air_quality_summary("Beijing")
        
        self.assertIn('Beijing', result)
        self.assertIn('Unhealthy', result)
        self.assertIn('PM2.5', result)
    
    @patch.object(WeatherSkill, 'get_air_quality')
    def test_get_air_quality_summary_unavailable(self, mock_get):
        """Test air quality summary when data unavailable."""
        mock_get.return_value = {
            'location': {'city': 'Small Town', 'country': 'Unknown'},
            'available': False
        }
        
        result = self.tools.get_air_quality_summary("Small Town")
        
        self.assertIn('not available', result)
    
    @patch.object(WeatherSkill, 'get_sunrise_sunset')
    def test_get_sun_times(self, mock_get):
        """Test getting sun times summary."""
        mock_get.return_value = {
            'location': {'city': 'Cairo', 'country': 'Egypt'},
            'date': '2026-02-12',
            'sunrise': '06:45 AM',
            'sunset': '06:15 PM',
            'day_length': '11h 30m',
            'moonrise': '07:30 PM',
            'moonset': '06:30 AM',
            'moon_phase': 'Waxing Crescent',
            'moon_illumination': '25'
        }
        
        result = self.tools.get_sun_times("Cairo")
        
        self.assertIn('Cairo', result)
        self.assertIn('06:45 AM', result)
        self.assertIn('11h 30m', result)
    
    def test_get_weather_emoji(self):
        """Test weather emoji mapping."""
        self.assertEqual(self.tools._get_weather_emoji('Sunny'), '☀️')
        self.assertEqual(self.tools._get_weather_emoji('Partly cloudy'), '⛅')
        self.assertEqual(self.tools._get_weather_emoji('Cloudy'), '☁️')
        self.assertEqual(self.tools._get_weather_emoji('Light rain'), '🌧️')
        self.assertEqual(self.tools._get_weather_emoji('Heavy rain'), '⛈️')  # Heavy triggers severe
        self.assertEqual(self.tools._get_weather_emoji('Snow'), '❄️')
        self.assertEqual(self.tools._get_weather_emoji('Thunderstorm'), '⛈️')
        self.assertEqual(self.tools._get_weather_emoji('Fog'), '🌫️')
        self.assertEqual(self.tools._get_weather_emoji('Windy'), '💨')
    
    @patch.object(WeatherSkill, 'get_current_weather')
    @patch.object(WeatherSkill, 'get_forecast')
    @patch.object(WeatherSkill, 'get_weather_alerts')
    @patch.object(WeatherSkill, 'get_air_quality')
    def test_check_weather_for_trip(
        self, mock_aqi, mock_alerts, mock_forecast, mock_current
    ):
        """Test trip weather check."""
        mock_current.return_value = {
            'location': {'city': 'Barcelona', 'country': 'Spain'},
            'current': {
                'temperature': '25',
                'condition': 'Sunny',
                'humidity': '60',
            },
            'units': 'metric'
        }
        mock_forecast.return_value = {
            'location': {'city': 'Barcelona', 'country': 'Spain'},
            'forecast': [
                {
                    'date': '2026-02-12',
                    'max_temp': '26',
                    'min_temp': '18',
                    'hourly': [{'condition': 'Sunny'}]
                }
            ]
        }
        mock_alerts.return_value = {'has_alerts': False, 'alerts': []}
        mock_aqi.return_value = {'available': False}
        
        result = self.tools.check_weather_for_trip("Barcelona")
        
        self.assertIn('Barcelona', result)
        self.assertIn('Sunny', result)
        self.assertIn('FORECAST', result)
    
    @patch.object(WeatherSkill, 'get_current_weather')
    def test_compare_locations(self, mock_get):
        """Test comparing locations."""
        mock_get.side_effect = [
            {
                'location': {'city': 'London'},
                'current': {'temperature': '15', 'condition': 'Rainy'}
            },
            {
                'location': {'city': 'Paris'},
                'current': {'temperature': '18', 'condition': 'Cloudy'}
            }
        ]
        
        result = self.tools.compare_locations(['London', 'Paris'])
        
        self.assertIn('London', result)
        self.assertIn('Paris', result)
    
    @patch.object(WeatherSkill, 'get_forecast')
    def test_should_pack_umbrella_yes(self, mock_get):
        """Test umbrella check when rain expected."""
        mock_get.return_value = {
            'location': {'city': 'Seattle'},
            'forecast': [{
                'date': '2026-02-12',
                'hourly': [{'chance_of_rain': '80'}]
            }]
        }
        
        result = self.tools.should_pack_umbrella("Seattle")
        
        self.assertIn('umbrella', result.lower())
        self.assertIn('80%', result)
    
    @patch.object(WeatherSkill, 'get_forecast')
    def test_should_pack_umbrella_no(self, mock_get):
        """Test umbrella check when no rain expected."""
        mock_get.return_value = {
            'location': {'city': 'Dubai'},
            'forecast': [{
                'date': '2026-02-12',
                'hourly': [{'chance_of_rain': '5'}]
            }]
        }
        
        result = self.tools.should_pack_umbrella("Dubai")
        
        self.assertIn('No umbrella', result)
    
    @patch.object(WeatherSkill, 'get_current_weather')
    @patch.object(WeatherSkill, 'get_weather_alerts')
    def test_is_good_for_outdoor_activity_good(self, mock_alerts, mock_current):
        """Test outdoor activity check when weather is good."""
        mock_current.return_value = {
            'location': {'city': 'San Diego'},
            'current': {
                'temperature': '22',
                'condition': 'Sunny',
                'wind_speed': '10',
                'uv_index': '6'
            },
            'units': 'metric'
        }
        mock_alerts.return_value = {'has_alerts': False}
        
        result = self.tools.is_good_for_outdoor_activity("San Diego", "beach")
        
        self.assertIn('Perfect', result)
    
    @patch.object(WeatherSkill, 'get_current_weather')
    @patch.object(WeatherSkill, 'get_weather_alerts')
    def test_is_good_for_outdoor_activity_bad(self, mock_alerts, mock_current):
        """Test outdoor activity check when weather is bad."""
        mock_current.return_value = {
            'location': {'city': 'London'},
            'current': {
                'temperature': '5',
                'condition': 'Heavy rain',
                'wind_speed': '25',
            },
            'units': 'metric'
        }
        mock_alerts.return_value = {'has_alerts': False}
        
        result = self.tools.is_good_for_outdoor_activity("London", "hiking")
        
        self.assertIn('Not ideal', result)


class TestModuleLevelFunctions(unittest.TestCase):
    """Test module-level convenience functions."""
    
    @patch('tools.WeatherTools.get_weather_now')
    def test_current(self, mock_fn):
        """Test current() convenience function."""
        mock_fn.return_value = "Weather data"
        
        from tools import current
        result = current("London")
        
        self.assertEqual(result, "Weather data")
        mock_fn.assert_called_once_with("London", "metric")
    
    @patch('tools.WeatherTools.get_forecast_summary')
    def test_forecast(self, mock_fn):
        """Test forecast() convenience function."""
        mock_fn.return_value = "Forecast data"
        
        from tools import forecast
        result = forecast("Paris", days=2)
        
        self.assertEqual(result, "Forecast data")
        mock_fn.assert_called_once_with("Paris", 2, "metric")
    
    @patch('tools.WeatherTools.get_alerts_summary')
    def test_alerts(self, mock_fn):
        """Test alerts() convenience function."""
        mock_fn.return_value = "Alerts data"
        
        from tools import alerts
        result = alerts("Tokyo")
        
        self.assertEqual(result, "Alerts data")
    
    @patch('tools.WeatherTools.get_air_quality_summary')
    def test_air_quality(self, mock_fn):
        """Test air_quality() convenience function."""
        mock_fn.return_value = "AQI data"
        
        from tools import air_quality
        result = air_quality("Beijing")
        
        self.assertEqual(result, "AQI data")
    
    @patch('tools.WeatherTools.get_sun_times')
    def test_sun_times(self, mock_fn):
        """Test sun_times() convenience function."""
        mock_fn.return_value = "Sun times"
        
        from tools import sun_times
        result = sun_times("Cairo")
        
        self.assertEqual(result, "Sun times")
    
    @patch('tools.WeatherTools.get_moon_info')
    def test_moon(self, mock_fn):
        """Test moon() convenience function."""
        mock_fn.return_value = "Moon phase"
        
        from tools import moon
        result = moon()
        
        self.assertEqual(result, "Moon phase")
    
    @patch('tools.WeatherTools.check_weather_for_trip')
    def test_trip_weather(self, mock_fn):
        """Test trip_weather() convenience function."""
        mock_fn.return_value = "Trip weather"
        
        from tools import trip_weather
        result = trip_weather("Barcelona", days=5)
        
        self.assertEqual(result, "Trip weather")
    
    @patch('tools.WeatherTools.compare_locations')
    def test_compare(self, mock_fn):
        """Test compare() convenience function."""
        mock_fn.return_value = "Comparison"
        
        from tools import compare
        result = compare("London", "Paris", "Tokyo")
        
        self.assertEqual(result, "Comparison")
    
    @patch('tools.WeatherTools.should_pack_umbrella')
    def test_umbrella(self, mock_fn):
        """Test umbrella() convenience function."""
        mock_fn.return_value = "Umbrella advice"
        
        from tools import umbrella
        result = umbrella("Seattle", days=3)
        
        self.assertEqual(result, "Umbrella advice")
    
    @patch('tools.WeatherTools.is_good_for_outdoor_activity')
    def test_good_for(self, mock_fn):
        """Test good_for() convenience function."""
        mock_fn.return_value = "Activity advice"
        
        from tools import good_for
        result = good_for("hiking", "Mountains")
        
        self.assertEqual(result, "Activity advice")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
