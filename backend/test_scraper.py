"""Quick test for the scraper engine."""
import asyncio
from app.services.scraper.engine import ScraperEngine


async def test_scraper():
    print("Starting scraper test...")

    async with ScraperEngine() as scraper:
        # Test scraping a simple page
        url = "https://www.eventbrite.com/d/switzerland--zurich/events/"
        print(f"Scraping: {url}")

        result = await scraper.scrape_page(url)

        if result.success:
            print(f"SUCCESS!")
            print(f"Title: {result.title}")
            print(f"Content length: {len(result.content or '')} chars")
            print(f"Metadata keys: {list(result.metadata.keys())}")

            # Try to extract event data
            event_data = await scraper.extract_event_data(result)
            if event_data:
                print(f"Event data found: {event_data}")
            else:
                print("No structured event data found")
        else:
            print(f"FAILED: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_scraper())
