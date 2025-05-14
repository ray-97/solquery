import asyncio
import os
from dotenv import load_dotenv
from solquery_tool import SolQueryTool

# Langchain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # <<< ENSURE THIS LINE IS PRESENT
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents import AgentExecutor

# Load environment variables (ensure GOOGLE_GEMINI_API_KEY is set in your .env)
load_dotenv()

async def run_gemini_agent_with_solquery():
    gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

    if not gemini_api_key:
        print("Error: GOOGLE_GEMINI_API_KEY not found in environment variables.")
        return

    print(f"DEBUG: Using Gemini API Key (first 5 chars): {gemini_api_key[:5]} for Langchain agent.")

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", 
            google_api_key=gemini_api_key, # Explicitly pass the key
            temperature=0,
            # convert_system_message_to_human=True # This is being deprecated, 
                                                 # try removing it or ensure your Langchain version handles it.
                                                 # For newer models/versions of langchain-google-genai,
                                                 # system messages are often handled natively without this flag.
        )

        # ... rest of your agent setup (tools, prompt, agent, executor) ...
        # (sol_query_tool = SolQueryTool(), tools = [sol_query_tool], etc.)

        # ... (your existing code for llm_with_tools, prompt, agent, agent_executor)

        # Example from your previous setup to ensure consistency:
        sol_query_tool = SolQueryTool()
        tools = [sol_query_tool]
        llm_with_tools = llm.bind_tools(tools) # This is a good modern approach

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful assistant. You have access to a powerful tool called 'solana_query_engine' that can answer questions about the Solana blockchain, including DeFi, NFTs, portfolio management, and sentiment analysis. Use this tool when appropriate."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_tool_messages(x["intermediate_steps"]),
            }
            | prompt
            | llm_with_tools
            | ToolsAgentOutputParser()
        )
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True, 
            handle_parsing_errors=True
        )
        # ... rest of your query execution loop ...
        queries = [
            "What is the current sentiment around the Tensorians NFT collection on Solana?",
            "Can you give me a portfolio overview for wallet HWdeCUjBvPP1HJ5oCJt7aNsvMWpWoDgiejUWvfFX6T7R and also tell me the floor price of FARTCOIN?", 
            "What are the latest DeFi activities for wallet 4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6?"
        ]
        for query in queries:
            print(f"\n--- Running Agent with Query: '{query}' ---")
            response = await agent_executor.ainvoke({"input": query})
            print("\nAgent Final Output:")
            print(response.get("output"))
            print("--------------------------")


    except Exception as e:
        print(f"An error occurred during agent setup or execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # (Ensure SolQuery FastAPI is running)
    asyncio.run(run_gemini_agent_with_solquery())
