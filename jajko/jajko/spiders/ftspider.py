import scrapy
import re

class FreyTagSpider(scrapy.Spider):
    name = 'freytag'
    start_urls = ['https://frey-tag.at/']

    custom_settings = {
        'FEEDS': {
            'freytag.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
            },
        },
    }

    def parse(self, response):
        events = response.css('div.event')

        for e in events:
            title = e.css('h3::text').get()
            date = e.css('.date::text').get()
            time = e.css('.time::text').get()
            url = response.urljoin(e.css('a::attr(href)').get())

            yield {
                'url': url,
                'event': title.strip() if title else '-',
                'date': date.strip() if date else '-',
                'time': time.strip() if time else '-',
                'location': 'Frey Tag',
                'lineup': '-',
                'content': []
            }
