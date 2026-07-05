# X-Maker Pro Backend 🚀

This is the official backend server for the **X-Maker Pro** Chrome Extension. It is built with FastAPI and designed to be deployed on platforms like Render.

## 🌟 Core Features

- **DeepSeek AI Integration**: Connects to the DeepSeek API to transform web content into highly engaging, viral Twitter (X) threads.
- **Firecrawl Extraction Engine**: Automatically scrapes and cleans target URLs, extracting pristine, LLM-optimized Markdown while stripping away ads and navigation bars.
- **Gumroad License Verification**: Robust payment verification via the Gumroad API, ensuring only valid, paid users can access the AI generation capabilities.
- **Rate Limiting & Security**: Built-in anti-spam mechanisms to protect the server from abuse.

## 🛠️ Tech Stack

- Python 3.12+
- FastAPI & Uvicorn
- OpenAI SDK (used for DeepSeek compatibility)
- HTTPX (for asynchronous API calls to Gumroad and Firecrawl)

## 🔑 Environment Variables

To run this backend, you must configure the following environment variables (e.g., in your Render dashboard):

| Variable | Description |
|---|---|
| `DEEPSEEK_API_KEY` | Your API key from DeepSeek for AI text generation. |
| `GUMROAD_PRODUCT_ID` | Your Gumroad Product ID for verifying user license keys. |
| `FIRECRAWL_API_KEY` | Your Firecrawl API key for advanced webpage to Markdown scraping. |
| `PYTHON_VERSION` | Set to `3.12.0` in Render. |

## 🚀 Deployment (Render)

1. Connect your GitHub repository to Render as a **Web Service**.
2. Set the Build Command to: `pip install -r requirements.txt`
3. Set the Start Command to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add the required Environment Variables.

---
*Built for Indie Hackers, by Indie Hackers.*
