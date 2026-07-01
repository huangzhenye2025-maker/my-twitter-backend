import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 这里是你的核心资产，绝对不能泄露
API_KEY = "123"
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 1. 修改前端必须传来的数据包格式，强制加上 license_key
class TweetRequest(BaseModel):
    title: str
    text: str
    lang: str = "English"
    license_key: str = ""  # 新增字段

@app.post("/generate_tweet")
async def generate_tweet(req: TweetRequest):
    # ==========================================
    # 商业核心防白嫖逻辑 (Auth Simulator)
    # 真实的场景这里会向 Lemon Squeezy 的 API 查询这张卡是否被人刷退款了、过期了没
    # ==========================================
    VALID_KEYS = ["TEST-VIP-888", "HAYE-PRO-2026"] 
    
    if req.license_key not in VALID_KEYS:
        print(f"⛔ 拦截！有人试图用无效卡密请求服务：{req.license_key}")
        # 如果卡密不对，直接拒绝服务，根本不去呼叫 DeepSeek，不花你一分钱
        return {
            "success": False, 
            "error": "无效或已过期的 License Key。请点击右上角获取正版授权！"
        }
    
    print(f"✅ 尊贵的 VIP 用户 ({req.license_key}) 来了！开始干活...")
    
    prompt = f"""
    你是一个拥有百万粉丝的 Twitter (X) 营销专家。
    网页标题：【{req.title}】
    部分内容：【{req.text}】
    请帮我把这个网页的核心内容总结成一条吸引人的推文。
    要求：
    1. 使用语言：{req.lang}
    2. 包含 2-3 个合适的 Emoji 🌟
    3. 结尾加上 2 个相关的 Hashtag #标签
    4. 语气要懂王、有煽动性。
    5. 长度不超过 280 个字符。
    6. 直接输出推文内容，不要说废话。
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个资深的海外社交媒体运营专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        tweet = response.choices[0].message.content
        return {"success": True, "tweet": tweet}
        
    except Exception as e:
        print(f"调用 API 失败: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    import os
    # 云端服务器（如 Render）会自动分配一个 PORT 环境变量，本地测试时默认使用 8000
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 商业版安全服务器准备在端口 {port} 启动...")
    uvicorn.run(app, host="0.0.0.0", port=port)
