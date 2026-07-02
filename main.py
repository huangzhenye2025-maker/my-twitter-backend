import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import time

app = FastAPI()

# 记录每个 license_key 的请求时间戳
# 格式: {"key1": [timestamp1, timestamp2], "key2": [...]}
request_counts = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 这里是你的核心资产，绝对不能泄露
import os
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 1. 修改前端必须传来的数据包格式，强制加上 license_key 和个性化配置
class TweetRequest(BaseModel):
    title: str
    text: str
    lang: str = "English"
    license_key: str = ""
    tone: str = "Professional"
    custom_prompt: str = ""
    include_hashtags: bool = True

@app.post("/generate_tweet")
async def generate_tweet(req: TweetRequest):
    # ==========================================
    # 真实的商业支付与授权校验 (Lemon Squeezy API)
    # ==========================================
    if not req.license_key:
        return {"success": False, "error": "请输入 License Key！"}
        
    # --- 核心防刷机制 (Rate Limiting) 开始 ---
    now = time.time()
    if req.license_key in request_counts:
        recent_requests = [t for t in request_counts[req.license_key] if now - t < 60]
        request_counts[req.license_key] = recent_requests
        
        if len(recent_requests) >= 3:
            print(f"🚨 触发防刷保护：{req.license_key} 请求频率超限！")
            return {"success": False, "error": "您的请求太频繁啦！为保护服务器，请 1 分钟后再试。"}
    else:
        request_counts[req.license_key] = []
        
    request_counts[req.license_key].append(now)
    # --- 防刷机制结束 ---
        
    if req.license_key != "TEST-VIP-888":
        import httpx
        print(f"🔄 正在向 Lemon Squeezy 验证真实的卡密: {req.license_key} ...")
        try:
            async with httpx.AsyncClient() as http_client:
                ls_response = await http_client.post(
                    "https://api.lemonsqueezy.com/v1/licenses/validate",
                    json={"license_key": req.license_key},
                    headers={"Accept": "application/json"}
                )
            
            ls_data = ls_response.json()
            
            if not ls_data.get("valid"):
                error_msg = ls_data.get("error", "无效的 License Key")
                print(f"⛔ 拦截！此卡密被 Lemon Squeezy 官方拒绝：{error_msg}")
                return {
                    "success": False, 
                    "error": f"付款凭证无效或已退款 ({error_msg})。请支持正版！"
                }
        except Exception as e:
            print(f"连接支付验证服务器失败: {e}")
            return {"success": False, "error": "验证支付服务器时网络超时，请稍后再试。"}
            
    print(f"✅ 尊贵的付费用户 ({req.license_key}) 身份核验通过！开始呼叫 AI...")
    
    # 动态构建 Prompt 引擎
    tone_instruction = ""
    if req.tone == "Tech Bro":
        tone_instruction = "语气要像硅谷的科技大佬，喜欢用高大上的词汇，充满激情地分享见解。"
    elif req.tone == "Funny":
        tone_instruction = "语气要极其幽默、机智，最好带点自嘲或网络梗。"
    elif req.tone == "Thread":
        tone_instruction = "输出格式为一个推特长文 (Thread)，用 1/ 2/ 3/ 这样分段，层层递进地讲述核心观点。"
    else:
        tone_instruction = "语气要专业、严谨、有洞察力，适合行业专家的人设。"
        
    hashtag_instruction = "结尾加上 2-3 个相关的 Hashtag #标签。" if req.include_hashtags else "千万不要输出任何 Hashtag 标签。"
    
    custom_instruction = f"【特别注意用户的自定义指令】：{req.custom_prompt}" if req.custom_prompt.strip() else ""

    prompt = f"""
    你是一个拥有百万粉丝的 Twitter (X) 营销专家。
    网页标题：【{req.title}】
    部分内容：【{req.text}】
    请帮我把这个网页的核心内容总结成推文。
    
    具体要求如下：
    1. 使用语言：{req.lang}
    2. 人设与语气风格：{tone_instruction}
    3. 视觉元素：包含 1-3 个合适的 Emoji 🌟
    4. 标签控制：{hashtag_instruction}
    5. 长度限制：除了 Thread 风格，其余单条推文不得超过 280 个字符。
    {custom_instruction}
    
    直接输出最终的推文内容，不要有任何前言后语和解释废话。
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
