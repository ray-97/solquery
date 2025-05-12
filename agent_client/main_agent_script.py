# main_agent_script.py (using Gemini Function Calling)

import asyncio
import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain.agents import AgentExecutor

from solquery_tool import SolQueryTool # Your custom tool

# Load environment variables (ensure GOOGLE_GEMINI_API_KEY is set in your .env)
load_dotenv()

async def run_gemini_agent_with_solquery():
    # 1. Initialize the Gemini LLM
    # Make sure your GOOGLE_GEMINI_API_KEY is set in your environment
    if not os.getenv("GOOGLE_GEMINI_API_KEY"):
        print("Error: GOOGLE_GEMINI_API_KEY not found in environment variables.")
        print("Please set it in your .env file (e.g., GOOGLE_GEMINI_API_KEY=your_key_here).")
        return

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro-latest", # Or "gemini-1.5-flash-latest" for speed/cost
        temperature=0, 
        convert_system_message_to_human=True # Often useful for Gemini
    )

    # 2. Initialize your SolQueryTool
    sol_query_tool = SolQueryTool()
    tools = [sol_query_tool]

    # 3. Bind the tools to the LLM
    # This makes the LLM aware of the tools and their schemas for function calling
    llm_with_tools = llm.bind_tools(tools)

    # 4. Create a prompt template
    # The prompt needs to allow for agent scratchpad messages where tool invocations and observations are stored
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. You have access to a powerful tool called 'solana_query_engine' that can answer questions about the Solana blockchain, including DeFi, NFTs, portfolio management, and sentiment analysis. Use this tool when appropriate."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # 5. Create the agent
    # This is a more modern way to construct an agent that uses tool calling
    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_tool_messages(x["intermediate_steps"]),
        }
        | prompt
        | llm_with_tools
        | ToolsAgentOutputParser() # Parses LLM output into AgentAction or AgentFinish
    )

    # 6. Create the AgentExecutor
    # The AgentExecutor is what actually runs the agent loop (LLM calls -> Tool calls -> LLM calls ...)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True # Good for debugging
    )

    # 7. Test with some queries
    queries = [
        "What is the current sentiment around the Tensorians NFT collection on Solana?",
        "Can you give me a portfolio overview for wallet GUMB9NqjH1hpKpsLBELLCHzDsnHAbm5esS2h5a11jN and also tell me the floor price of Mad Lads?", # an arbitrary wallet address, maybe test with something that made a transaction recently (ie. from SolScan, SolanaFM or Solana Block Explorer)
        "What are the latest DeFi activities for wallet ADDRESS_XYZ?" # Replace ADDRESS_XYZ
    ]

    # Make sure your SolQuery FastAPI application is running at http://127.0.0.1:8000/query
    print("\nEnsure your SolQuery FastAPI server is running on http://127.0.0.1:8000")
    print("----------------------------------------------------------------------\n")
    
    for query in queries:
        print(f"\n--- Running Agent with Query: '{query}' ---")
        try:
            response = await agent_executor.ainvoke({"input": query})
            print("\nAgent Final Output:")
            print(response.get("output"))
            print("--------------------------")
        except Exception as e:
            print(f"Error running agent for query '{query}': {e}")
            import traceback
            traceback.print_exc()
            print("--------------------------")

if __name__ == "__main__":
    asyncio.run(run_gemini_agent_with_solquery())