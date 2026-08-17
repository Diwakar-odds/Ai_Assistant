import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.agents.productivity.productivity_agent import ProductivityAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Productivity Agent...")
    agent = ProductivityAgent()
    
    # 1. Test Word Generation
    print("\n--- Testing Word ---")
    word_task = Task(
        description="Create a Word document about Python",
        params={
            "title": "Python Basics",
            "content": ["Python is great.", "It is easy to learn."],
            "filename": "test_doc.docx"
        }
    )
    res_word = await agent.execute(word_task)
    print(f"Word Result: {res_word}")

    # 2. Test Excel Generation
    print("\n--- Testing Excel ---")
    excel_task = Task(
        description="Create an Excel spreadsheet for budget",
        params={
            "title": "Budget 2026",
            "data": [["Item", "Cost"], ["Laptop", 1200], ["Mouse", 25]],
            "filename": "test_sheet.xlsx"
        }
    )
    res_excel = await agent.execute(excel_task)
    print(f"Excel Result: {res_excel}")

    # 3. Test PowerPoint Generation
    print("\n--- Testing PowerPoint ---")
    ppt_task = Task(
        description="Create a PowerPoint presentation",
        params={
            "title": "AI Future",
            "subtitle": "2026 and Beyond",
            "slides": [
                {"title": "Intro", "content": "AI is evolving fast."},
                {"title": "Agents", "content": "Multi-agent systems are the future."}
            ],
            "filename": "test_pres.pptx"
        }
    )
    res_ppt = await agent.execute(ppt_task)
    print(f"PPT Result: {res_ppt}")

if __name__ == "__main__":
    asyncio.run(main())
