# X-Maker Pro Backend 🚀

This is the official backend server for the **X-Maker Pro** Chrome Extension. It is built with FastAPI and designed to be deployed on platforms like Render.

## 🔗 Architecture & Repositories

This product is built using a modern decoupled architecture. There are two main repositories:

1. **[my-twitter-backend](https://github.com/huangzhenye2025-maker/my-twitter-backend) (You are here)**: The engine. Handles DeepSeek AI integration, Firecrawl web scraping, and Waffo Pancake webhook payments & license verification. Hosted on Render.
2. **[x-maker-web](https://github.com/huangzhenye2025-maker/x-maker-web)**: The frontend. The official landing page built with Next.js. Handles marketing, user conversion, and policies. Hosted on Vercel.

## 🌟 Core Features

- **DeepSeek AI Integration**: Connects to the DeepSeek API to transform web content into highly engaging, viral Twitter (X) threads.
- **Firecrawl Extraction Engine**: Automatically scrapes and cleans target URLs, extracting pristine, LLM-optimized Markdown while stripping away ads and navigation bars.
- **Waffo Webhook Handler & RSA Signature Verification**: Exposures `/waffo_webhook` endpoint to handle real-time payment events. Verifies incoming Waffo Pancake signatures securely using the official **RSA-SHA256 non-symmetric encryption** (built-in test/prod public keys with configurable overrides) and guards against replay attacks (5-minute timestamp tolerance).
- **Persistent Card Database**: 
  - **Cloud MongoDB Atlas**: Persists active/refunded license keys in cloud MongoDB to survive server restarts/deploys.
  - **Local JSON File Fallback**: Automatically falls back to local `licenses.json` storage when MongoDB is not configured, facilitating zero-configuration local development.
- **Rate Limiting & Security**: Built-in anti-spam mechanisms to protect the server from abuse (maximum 3 requests per 60 seconds per license key).

## 🛠️ Tech Stack

- Python 3.12
- FastAPI & Uvicorn
- PyMongo & dnspython (MongoDB driver)
- Cryptography (for RSA-SHA256 signature verification)
- OpenAI SDK (used for DeepSeek API compatibility)

## 🔑 Environment Variables

To run this backend, configure the following environment variables (e.g., in your Render dashboard):

| Variable | Description |
|---|---|
| `DEEPSEEK_API_KEY` | Your API key from DeepSeek for AI text generation. |
| `MONGODB_URI` | Connection string for MongoDB Atlas (forces cloud MongoDB storage). |
| `WAFFO_WEBHOOK_SECRET` | Optional webhook secret for fallback validation. |
| `WAFFO_WEBHOOK_PUBLIC_KEY` | Optional public key to override default Waffo webhook validation public key. |
| `FIRECRAWL_API_KEY` | Your Firecrawl API key for advanced webpage to Markdown scraping. |
| `PYTHON_VERSION` | Set to `3.12.0` in Render. |

## 🚀 Deployment (Render)

1. Connect your GitHub repository to Render as a **Web Service**.
2. Set the Build Command to: `pip install -r requirements.txt`
3. Set the Start Command to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add the required Environment Variables in the Settings dashboard.

---
*Built for Indie Hackers, by Indie Hackers.*
