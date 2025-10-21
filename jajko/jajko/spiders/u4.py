import scrapy
import json

class U4Spider(scrapy.Spider):
    name = 'u4'
    start_urls = ['https://www.u4.at/events-veranstaltungen/']

    custom_settings = {
        'FEEDS': {
            'u4_events.json': {
                'format': 'json',
                'overwrite': True,
                'encoding': 'utf8',
            },
        },
    }

    # Words to ignore in the content
    FILTER_KEYWORDS = {
        "RESERVIEREN", "EVENTS", "MENÜ UMSCHALTEN", "FALCO", "APP", "MERCH", "LOST & FOUND",
        "KONTAKT", "MAIN MENU", "LET'S TALK", "SHORTCUTS", "BOOK A TABLE", "CONTACT",
        "B2B", "DATENSCHUTZ", "IMPRESSUM", "GET THE U4 APP", "INSTAGRAM", "FACEBOOK",
        "X", "|", "COPYRIGHT"
    }

    def parse(self, response):
        events = response.css('div.eventon_list_event')
        self.logger.info(f"Found {len(events)} U4 event cards")

        for event in events:
            url = event.css('a::attr(href)').get()

            day = event.css('em.date::text').get(default='-').strip()
            month = event.css('em.month::text').get(default='-').strip()
            time = event.css('em.time::text').get(default='').strip() or "-"

            formatted_date = f"{day}. {month} 2025" if day != '-' and month != '-' else "-"

            yield response.follow(
                url,
                callback=self.parse_event,
                cb_kwargs={
                    'formatted_date': formatted_date,
                    'formatted_time': time,
                }
            )

    def parse_event(self, response, formatted_date, formatted_time):
        # Extract and clean content
        raw_content = [t.strip() for t in response.css('div *::text').getall() if t.strip()]
        filtered_content = [
            t for t in raw_content
            if t.upper() not in self.FILTER_KEYWORDS and not t.startswith('|')
        ]

        # Extract proper title from JSON-LD
        json_text = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if json_text:
            try:
                json_data = json.loads(json_text)
                title = json_data.get("name", "-")
            except Exception:
                title = "-"
        else:
            title = response.css('h1::text').get(default='-').strip()

        yield {
            'url': response.url,
            'event': title,
            'date': formatted_date,
            'time': formatted_time,
            'content': filtered_content,
            'location': 'U4 Club Wien',
            'lineup': '-'
        }

