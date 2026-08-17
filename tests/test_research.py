import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.agents.research.research_agent import ResearchAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Research Agent...")
    agent = ResearchAgent()
    
    # 1. Test Wikipedia
    print("\n--- Testing Wikipedia ---")
    wiki_task = Task(description="Find wikipedia summary of Python programming language", params={"query": "Python (programming language)"})
    res_wiki = await agent.execute(wiki_task)
    if res_wiki.success:
        print(f"✅ Wiki Title: {res_wiki.data.get('title')}")
        print(f"✅ Wiki Summary: {res_wiki.data.get('summary')[:100]}...")
    else:
        print(f"❌ Wiki Failed: {res_wiki.error}")

    # 2. Test Google Search
    print("\n--- Testing Google Search ---")
    search_task = Task(description="Search for latest AI agents news", params={"query": "latest AI agents news 2025", "num_results": 2})
    res_search = await agent.execute(search_task)
    if res_search.success:
        results = res_search.data.get("results", [])
        print(f"✅ Found {len(results)} results")
        for i, r in enumerate(results):
            print(f"  {i+1}. {r.get('title')} ({r.get('url')})")
    else:
         print(f"❌ Search Failed: {res_search.error}")

    # 3. Test Scraping
    print("\n--- Testing Scraping ---")
    # Using a reliable static site or the one found in search if possible, 
    # but for stability let's use example.com or python.org
    scrape_task = Task(description="Scrape python.org", params={"url": "https://www.python.org/"})
    res_scrape = await agent.execute(scrape_task)
    if res_scrape.success:
        print(f"✅ Scraped Title: {res_scrape.data.get('title')}")
        print(f"✅ Content Snippet: {res_scrape.data.get('text_content')[:2]}")
    else:
        print(f"❌ Scraping Failed: {res_scrape.error}")

if __name__ == "__main__":
    asyncio.run(main())
