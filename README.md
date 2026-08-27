# Agents, Tools, MCPs and All That
------------------------------------

## Part 1
In this post I will talk about Agents, Tools, MCPs and All That (the title being a play on the famous Vector Calculus book [Div, Grad, Curl and All that](https://www.google.com/books/edition/Div_Grad_Curl_and_All_that/sembQgAACAAJ?hl=en) that I read in undergrad) which are the newest crazes in AI and technology more broadly. I'll keep this post brief and simple. Partly because long posts are harder to write to, but also because people dont have attention anymore!

I'll go over how to buid a simple agent, use a [MCP](https://en.wikipedia.org/wiki/Model_Context_Protocol) server and observe agent behavoir; all using [LangChain](https://www.langchain.com/), [Groq](https://groq.com/), [FastMCP](https://gofastmcp.com/getting-started/welcome) and [LangSmith](https://www.langchain.com/langsmith-platform). The agent will be a simple ReAct agent. It will have tools that can help us find weather (like everyones first agent), but also help find the closest Police station and public restroom in NYC (data coming from [OpenData NYC](https://data.cityofnewyork.us/)). Very helpful things! In the back end, I'll use [MongoDB](https://www.mongodb.com/), [Redis](https://redis.io/) along with a handful of APIs to accompish these tasks.
