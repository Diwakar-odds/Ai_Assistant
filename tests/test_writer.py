import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.agents.writer.writer_agent import WriterAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Writer Agent (Mock Mode)...")
    agent = WriterAgent()
    
    # 1. Test Article Writing
    print("\n--- Testing Article Writing ---")
    article_task = Task(description="Write an article about AI Agents", params={"topic": "Future of AI Agents", "filename": "test_article.md"})
    res_article = await agent.execute(article_task)
    if res_article.success:
        print(f"✅ Content Generated ({len(res_article.data.get('content'))} chars)")
        print(f"Preview: {res_article.data.get('content')[:100]}...")
    else:
         print(f"❌ Article Failed: {res_article.error}")

    # 2. Test Email Draft
    print("\n--- Testing Email Draft ---")
    email_task = Task(description="Draft an email about project updates", params={"topic": "Project Alpha", "type": "email"})
    res_email = await agent.execute(email_task)
    if res_email.success:
        print(f"✅ Email Generated")
        print(f"Preview: {res_email.data.get('content')[:100]}...")
    else:
        print(f"❌ Email Failed: {res_email.error}")

if __name__ == "__main__":
    asyncio.run(main())
