import scrapy
import re


class MySpider(scrapy.Spider):
    name = 'daswerk'
    start_urls = ['https://www.daswerk.org/programm']

    custom_settings = {
        "FEEDS": {
            "daswerk.json": {"format": "json", "overwrite": True, "encoding": "utf8"},
        }
    }

    def parse(self, response):
        # Extract all event links
        links = response.css('a.preview-item--link::attr(href)').getall()
        self.logger.info(f"Found {len(links)} event links")

        for link in links:
            yield response.follow(link, callback=self.parse_event)

    def parse_event(self, response):
        # Extract event title, date, and description content
        title = response.css('p.main--header-title::text').get()
        date = response.css('li::text').get()
        content = [t.strip() for t in response.css('div.col-lg-10 *::text').getall() if t.strip()]

        # Join all text into one string for regex search
        text = " ".join(content)

        # Regex for time formats like "23:00 Uhr", "11PM-6AM", "START: 23 UHR // 11 PM"
        time_match = re.search(
            r'(\d{1,2}[:.]\d{2}\s*Uhr|\d{1,2}\s*(?:AM|PM)(?:\s*-\s*\d{1,2}\s*(?:AM|PM))?)',
            text,
            re.IGNORECASE
        )
        time = time_match.group(0) if time_match else "-"

        # Output to daswerk.json
        yield {
            'url': response.url,
            'event': title,
            'date': date,
            'time': time,
            'content': content,
            'location': 'Das Werk',
            'lineup': '-'
        }
