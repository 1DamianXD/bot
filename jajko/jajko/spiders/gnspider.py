import scrapy
import re

class GoodnightSpider(scrapy.Spider):
    name = 'goodnight'
    start_urls = ['https://goodnight.at/events']

    custom_settings = {
        'FEEDS': {
            'goodnight.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
            },
        },
    }

    def parse(self, response):
        # Extract event cards
        events = response.css('div.event-list-item')

        for e in events:
            title = e.css('h3::text').get()
            date = e.css('.event-date::text').get()
            time = e.css('.event-time::text').get()
            location = e.css('.event-location::text').get()
            url = response.urljoin(e.css('a::attr(href)').get())

            yield {
                'url': url,
                'event': title.strip() if title else '-',
                'date': date.strip() if date else '-',
                'time': time.strip() if time else '-',
                'location': location.strip() if location else '-',
                'lineup': '-',
                'content': []
            }
