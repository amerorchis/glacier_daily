from datetime import date
import requests
from astral import LocationInfo, sun
from bs4 import BeautifulSoup
import json
import threading
from datetime import datetime
import concurrent.futures
from time import sleep

class WeatherThread(threading.Thread):
    sites = {'West Glacier': 'MSO/116,208', 'Logan Pass':'TFX/29,211', 'St. Mary': 'TFX/38,212', 'Two Medicine': 'TFX/39,200', 'Many Glacier': 'TFX/31,216', 'Polebridge': 'MSO/108,222'}

    def __init__(self, site):
        threading.Thread.__init__(self)
        self.site = site
        self.message = ""

    def run(self):
        self.message = self.weather_cond(self.site)
    
    def sanitize_cond(self, cond):
        cond = cond.split(' then ')[0].lower().replace('thunderstorms', 't-storms').replace('and','&').replace('likely','').replace('chance','').replace('  ',' ')
        cond = cond[1:] if cond[0] == ' ' else cond
        cond = cond[:-1] if cond[-1] == ' ' else cond
        return cond
    
    def weather_cond(self, place):
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(f'https://api.weather.gov/gridpoints/{self.sites[place]}/forecast', headers=headers)

        retries = 0
        while r.status_code != 200 and retries < 10:
            print(f'Weather error for {place}: status code {r.status_code}')
            r = requests.get(f'https://api.weather.gov/gridpoints/{self.sites[place]}/forecast', headers=headers)
            retries += 1
            sleep(1)

        forecast = json.loads(r.content)
        today, tonight = forecast['properties']['periods'][0], forecast['properties']['periods'][1]

        # if place == "West Glacier":
        #    print(forecast)

        high = today['temperature']
        low = tonight['temperature']
        cond = self.sanitize_cond(today['shortForecast'])

        return place, high, low, cond

    def old_weather_cond(self, place) -> str:
        """Scrape weather data from web using weather.com. Not in use anymore with weather.gov api taking over."""

        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(f'https://weather.com/weather/today/l/{self.sites[place]}', headers=headers)
        soup = BeautifulSoup(r.content, 'html5lib')
        cond = soup.find('div', {'class': 'CurrentConditions--phraseValue--mZC_p'}).get_text(separator=" ").strip()
        h_l = soup.find_all('span', {'data-testid': 'TemperatureValue'})
        return(place, h_l[1].text[:-1], h_l[2].text[:-1], cond.lower())
        # return(f"<li>{place}: {cond.lower()}.\nHigh: {h_l[1].text[:-1]}F, Low: {h_l[2].text[:-1]}F</li>\n")

class WeatherContent:
    sites = {'West Glacier': '48.49,-113.98', 'Logan Pass':'48.69,-113.71', 'St. Mary': '48.74,-113.43', 'Two Medicine': '48.49,-113.36', 'Many Glacier': '48.80,-113.66', 'Polebridge': '18cad3f29e1c4d63a9ff31c6f57950bafde82e3f29ca33c6e5bbf80a36c32e26'}

    def __init__(self):
        self.futures()
        self.message1 += "<br><br>Forecasts Around the Park:"
    
    def futures(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
            length_fut = executor.submit(self.day_length)
            aqi_fut = executor.submit(self.aqi)
            weather_fut = executor.submit(self.thread_weather)
            alerts_fut = executor.submit(weather_alerts)

            self.message1 = length_fut.result()
            self.message2 = aqi_fut.result()
            alerts = alerts_fut.result()
            done = weather_fut.done()
            
            if alerts:
                self.message2 += alerts

    def day_length(self) -> str:
        # Create West Glacier LI object
        wg = LocationInfo(name='west glacier', region='MT', timezone='US/Mountain', latitude=48.4950, longitude=-113.9811)

        # Create West Glacier sun object
        s = sun.sun(wg.observer, date=date.today(), tzinfo=wg.timezone)

        # Calculate day length and convert to readable format and string.
        today_length = s['sunset'] - s['sunrise']
        
        # Format the sunrise and sunset times.
        hour = s['sunset'].hour - 12
        minute = s['sunset'].minute
        sunset = f"{hour}:{minute:02d}"
        hour = s['sunrise'].hour
        minute = s['sunrise'].minute
        sunrise = f"{hour}:{minute:02d}"
        
        hours = today_length.seconds // 3600
        minutes = (today_length.seconds - (hours * 3600)) // 60
        return f"Today, sunrise is at {sunrise}am and sunset is at {sunset}pm. There will be {hours} hours and {minutes} minutes of daylight.\n"

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

    def thread_weather(self):
        threads = []
        self.results = []

        # Create a thread for each site and start them
        for site in self.sites:
            thread = WeatherThread(site)
            thread.start()
            threads.append(thread)

        # Wait for all threads to finish
        for thread in threads:
            thread.join()
            self.results.append(thread.message)
        
        return True

def weather_data():
    return WeatherContent()


if __name__ == "__main__":
    from weather_alerts import weather_alerts
    from weather_aqi import get_air_quality
    print(weather_data().results)
    
else:
    from weather.weather_alerts import weather_alerts
    from weather.weather_aqi import get_air_quality
