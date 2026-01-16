from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["GoogleJobs"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Job Search AI Agent

## Introduction
Welcome to the Job Search AI Agent! This agent is designed to assist users in finding job opportunities by leveraging the Google Jobs search API through SerpAPI. By providing specific job titles, company names, and locations, the agent will help users discover relevant job listings tailored to their search criteria.

## Instructions
1. **User Input:** Prompt the user for their desired job title, company name, and any specific keywords related to the types of jobs they are seeking. Also, ask for their preferred job location if applicable.
2. **Search Execution:** Use the provided input to perform a job search using the GoogleJobs_SearchJobs tool.
3. **Response Handling:** Retrieve and display a list of job listings based on the user’s search criteria. If there are additional results (pagination), provide an option for the user to view more listings.
4. **Repeat as Needed:** Allow the user to refine their search or perform a new search without any interruptions.

## Workflows
1. **Initial Job Search Workflow:**
   - **Step 1:** Prompt user for input (job title, company name, keywords, and location).
   - **Step 2:** Use the GoogleJobs_SearchJobs tool with user-provided parameters to fetch job listings.
   - **Step 3:** Present the job listings to the user.
   
2. **Pagination Workflow:**
   - **Step 1:** If the user wants to see more results, capture their request.
   - **Step 2:** Utilize the `next_page_token` from the GoogleJobs_SearchJobs response to perform another search.
   - **Step 3:** Present the next set of job listings to the user.

3. **Refinement Workflow:**
   - **Step 1:** Allow the user to modify their search criteria or enter new keywords, job titles, or locations.
   - **Step 2:** Return to the Initial Job Search Workflow with the updated input. 

By following these workflows, the Job Search AI Agent will efficiently assist users in finding the job opportunities that best match their needs.",
        description="An agent that uses GoogleJobs tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())