import concurrent.futures

try:
    from weather_alerts import weather_alerts
    from night_sky import aurora_forecast
    from weather_aqi import get_air_quality
    from new_forecast import get_forecast
    from season import get_season
except ModuleNotFoundError:
    from weather.weather_alerts import weather_alerts
    from weather.night_sky import aurora_forecast
    from weather.weather_aqi import get_air_quality
    from weather.new_forecast import get_forecast
    from weather.season import get_season

    
class WeatherContent:

    def __init__(self):
        self.futures()
        self.message1 += "<br><br>Forecasts Around the Park:"
    
    def futures(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
            aqi_fut = executor.submit(self.aqi)
            weather_fut = executor.submit(get_forecast)
            alerts_fut = executor.submit(weather_alerts)
            aurora_fut = executor.submit(aurora_forecast)
            season_fut = executor.submit(get_season)

            self.results, self.message1 = weather_fut.result()
            self.message2 = aqi_fut.result()
            self.season = season_fut.result()
            alerts = alerts_fut.result()
            aurora = aurora_fut.result()

            if aurora:
                self.message2 += aurora
            if alerts:
                self.message2 += alerts

    def aqi(self) -> str:
        aqi_num = get_air_quality(59936)
        if aqi_num:
            if aqi_num <= 50:
                quality = 'good.'
            elif 50 < aqi_num <= 100:
                quality = 'moderate.'
            elif 100 < aqi_num <= 150:
                quality = 'unhealthy for sensitive groups. Children, older adults, active people, and people with heart or lung disease (such as asthma) should reduce prolonged or heavy exertion outdoors.'
            elif 150 < aqi_num <= 200:
                quality = 'unhealthy. Children, older adults, active people, and people with heart or lung disease (such as asthma) should avoid prolonged or heavy exertion outdoors. Everyone else should reduce prolonged or heavy exertion outdoors.'
            elif 200 < aqi_num <= 300:
                quality = 'very unhealthy. Children, older adults, active people, and people with heart or lung disease (such as asthma) should avoid all outdoor exertion. Everyone else should avoid prolonged or heavy exertion outdoors.'
            elif 300 < aqi_num <= 500:
                quality = 'hazardous. Everyone should avoid all physical activity outdoors.'
            return f'<p style="margin:0 0 12px; font-size:12px; line-height:18px; color:#333333;">The current AQI in West Glacier is {aqi_num}. This air quality is considered {quality}</p>'
        else:
            return ''


def weather_data():
    return WeatherContent()


if __name__ == "__main__":
    print(weather_data().message2)
