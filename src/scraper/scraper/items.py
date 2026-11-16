# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass


@dataclass
class ProductItem:
    # Listing identity
    site: str
    listing_id: str
    listing_url: str

    # Product information
    title: str
    category: str | None = None
    description: str | None = None
    img_url: str | None = None

    # Pricing
    price: str | None = None
    currency: str | None = None

    # Seller information
    seller_name: str | None = None
    seller_rating: str | None = None
    seller_profile_url: str | None = None
    location: str | None = None

    # Delivery
    delivery_options: str | None = None

    # Listing metadata
    iced_status: bool = False
    listed_date: str | None = None
    scrape_date: str | None = None
