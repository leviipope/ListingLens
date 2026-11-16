from datetime import datetime
from typing import ClassVar

import scrapy

from ..items import ProductItem


class HardverSpider(scrapy.Spider):
    name = "hardver"
    start_urls: ClassVar[list[str]] = [
        "https://hardverapro.hu/aprok/hardver/videokartya/nvidia/geforce_7xx/index.html"
    ]

    def parse(self, response):
        listings = response.css("ul.list-unstyled > li[class]")
        for listing in listings:
            data_uadid = listing.attrib.get("data-uadid")

            iced_status_str = listing.css(
                "div[class='uad-col uad-col-price'] div::attr(class)"
            ).get()
            iced_status = "iced" in (iced_status_str or "")

            price = listing.css("div[class='uad-col uad-col-price'] span::text").get()

            img_url = listing.css(
                "div[class='uad-col uad-col-image'] > a > img::attr(src)"
            ).get()
            product_url = listing.css(
                "div[class='uad-col uad-col-title'] > h1 > a::attr(href)"
            ).get()

            yield response.follow(
                product_url,
                callback=self.parse_product,
                meta={
                    "data_uadid": data_uadid,
                    "iced_status": iced_status,
                    "price": price,
                    "img_url": img_url,
                },
            )

        next_page = response.css('li.nav-arrow a[rel="next"]::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_product(self, response):
        listing_id = response.meta.get("data_uadid")
        iced_status = response.meta.get("iced_status")
        price = response.meta.get("price")
        img_url = response.meta.get("img_url")

        title = response.css("head title::text").get()

        category_text = " ".join(
            response.css("div.container > div > ol.breadcrumb")
            .xpath("string(.)")
            .get(default="")
            .split()
        )

        seller_name = response.css("td > b > a[style][href]::text").get()

        seller_profile_url = response.css("td > b > a[style][href]::attr(href)").get()
        seller_profile_url = (
            response.urljoin(seller_profile_url) if seller_profile_url else None
        )

        seller_rating = response.css("a.uad-rating-link").xpath("string(.)").get()

        location_delivery = (
            response.css("div.uad-time-location").xpath("string(.)").get(default="")
        )

        parts = location_delivery.split(
            "\n\t\t\t\t\n\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t",
            maxsplit=1,
        )

        location = " ".join(parts[0].split())
        delivery_options = " ".join(parts[1].split()) if len(parts) > 1 else None

        listed_date = (
            response.css('span[title][data-toggle="tooltip"]::text')
            .get(default="")
            .strip()
        )

        description = (
            response.css("div.uad-content div.rtif-content")
            .xpath("string(.)")
            .get(default="")
            .strip()
        )

        scraper_item = ProductItem(
            site="HardverApró",
            category=category_text,
            listing_id=listing_id,
            iced_status=iced_status,
            price=price,
            img_url=img_url,
            currency="HUF",
            title=title,
            seller_name=seller_name,
            seller_rating=seller_rating,
            seller_profile_url=seller_profile_url,
            location=location,
            delivery_options=delivery_options,
            listed_date=listed_date,
            listing_url=response.url,
            description=description,
            scrape_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        yield scraper_item
