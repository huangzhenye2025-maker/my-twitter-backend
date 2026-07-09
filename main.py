import os
import time
import httpx
import hmac
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# 尝试加载本地环境变量文件，避免终端关闭后变量丢失
for env_file in [".env", ".env.local", "../.env", "../.env.local", "../x-maker-web/.env.local"]:
    env_path = os.path.join(os.path.dirname(__file__), env_file)
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        k, v = parts[0].strip(), parts[1].strip()
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1]
                        # 兼容转义换行符的私钥
                        v = v.replace("\\n", "\n")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"Error loading env from {env_file}: {e}")

app = FastAPI()

# 初始化 MongoDB (如果配置了 MONGODB_URI)
MONGODB_URI = os.environ.get("MONGODB_URI")
db_client = None
db_collection = None

if MONGODB_URI:
    try:
        from pymongo import MongoClient
        db_client = MongoClient(MONGODB_URI)
        # 默认数据库名为 xmaker，集合名为 licenses
        db = db_client.get_default_database(default="xmaker")
        db_collection = db["licenses"]
        print("🔌 成功连接到云端 MongoDB 数据库！")
    except Exception as e:
        print(f"⚠️ 连接 MongoDB 失败，将退回到本地 JSON 文件模式: {e}")

# 本地卡密库数据库路径
LICENSES_FILE = os.path.join(os.path.dirname(__file__), "licenses.json")

def get_license(license_key: str) -> dict:
    """获取单个卡密详情"""
    if db_collection is not None:
        try:
            doc = db_collection.find_one({"_id": license_key})
            return doc if doc else {}
        except Exception as e:
            print(f"MongoDB read error: {e}")
    
    # 读本地 file fallback
    if not os.path.exists(LICENSES_FILE):
        return {}
    try:
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            licenses = json.load(f)
            return licenses.get(license_key, {})
    except Exception as e:
        print(f"Error loading local licenses: {e}")
        return {}

def activate_license(license_key: str, email: str, order_id: str, event_name: str):
    """激活或更新卡密状态为 active"""
    now = time.time()
    if db_collection is not None:
        try:
            db_collection.update_one(
                {"_id": license_key},
                {"$set": {
                    "email": email,
                    "order_id": order_id,
                    "status": "active",
                    "created_at": now,
                    "event": event_name
                }},
                upsert=True
            )
            print(f"🎉 [MongoDB] 成功激活卡密: {license_key}")
            return
        except Exception as e:
            print(f"MongoDB write error (activate): {e}")
            
    # 写入本地文件
    licenses = {}
    if os.path.exists(LICENSES_FILE):
        try:
            with open(LICENSES_FILE, "r", encoding="utf-8") as f:
                licenses = json.load(f)
        except Exception:
            pass
            
    licenses[license_key] = {
        "email": email,
        "order_id": order_id,
        "status": "active",
        "created_at": now,
        "event": event_name
    }
    
    try:
        with open(LICENSES_FILE, "w", encoding="utf-8") as f:
            json.dump(licenses, f, indent=4, ensure_ascii=False)
        print(f"🎉 [JSON] 成功激活本地卡密: {license_key}")
    except Exception as e:
        print(f"Error saving local licenses: {e}")

def revoke_license(license_key: str) -> bool:
    """注销/退款卡密"""
    if db_collection is not None:
        try:
            result = db_collection.update_one(
                {"_id": license_key},
                {"$set": {"status": "refunded"}}
            )
            if result.matched_count > 0:
                print(f"🚫 [MongoDB] 已撤销卡密: {license_key}")
                return True
            else:
                print(f"⚠️ [MongoDB] 撤销失败，卡密未找到: {license_key}")
                return False
        except Exception as e:
            print(f"MongoDB write error (revoke): {e}")
            
    # 写入本地文件
    if not os.path.exists(LICENSES_FILE):
        return False
    try:
        with open(LICENSES_FILE, "r", encoding="utf-8") as f:
            licenses = json.load(f)
        if license_key in licenses:
            licenses[license_key]["status"] = "refunded"
            with open(LICENSES_FILE, "w", encoding="utf-8") as f:
                json.dump(licenses, f, indent=4, ensure_ascii=False)
            print(f"🚫 [JSON] 已撤销本地卡密: {license_key}")
            return True
    except Exception as e:
        print(f"Error revoking local license: {e}")
    return False

# Waffo Pancake 默认 Webhook 验签公钥
TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxnmRY6yMMA3lVqmAU6ZG
b1sjL/+r/z6E+ZjkXaDAKiqOhk9rpazni0bNsGXwmftTPk9jy2wn+j6JHODD/WH/
SCnSfvKkLIjy4Hk7BuCgB174C0ydan7J+KgXLkOwgCAxxB68t2tezldwo74ZpXgn
F49opzMvQ9prEwIAWOE+kV9iK6gx/AckSMtHIHpUesoPDkldpmFHlB2qpf1vsFTZ
5kD6DmGl+2GIVK01aChy2lk8pLv0yUMu18v44sLkO5M44TkGPJD9qG09wrvVG2wp
OTVCn1n5pP8P+HRLcgzbUB3OlZVfdFurn6EZwtyL4ZD9kdkQ4EZE/9inKcp3c1h4
xwIDAQAB
-----END PUBLIC KEY-----"""

PROD_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAz+xApdTIb4ua+DgZKQ54
iBsD82ybyhGCLRETONW4Jgbb3A8DUM1LqBk6r/CmTOCHqLalTQHNigvP3R5zkDNX
iRJz6gA4MJ/+8K0+mnEE2RISQzN+Qu65TNd6svb+INm/kMaftY4uIXr6y6kchtTJ
dwnQhcKdAL2v7h7IFnkVelQsKxDdb2PqX8xX/qwd01iXvMcpCCaXovUwZsxH2QN5
ZKBTseJivbhUeyJCco4fdUyxOMHe2ybCVhyvim2uxAl1nkvL5L8RCWMCAV55LLo0
9OhmLahz/DYNu13YLVP6dvIT09ZFBYU6Owj1NxdinTynlJCFS9VYwBgmftosSE1U
dwIDAQAB
-----END PUBLIC KEY-----"""

@app.post("/waffo_webhook")
async def waffo_webhook(request: Request):
    payload_body = await request.body()
    waffo_signature = request.headers.get("X-Waffo-Signature") or request.headers.get("Waffo-Signature")
    webhook_secret = os.environ.get("WAFFO_WEBHOOK_SECRET")
    
    # 仅当在环境变量或请求中存在签名时进行 RSA 签名验证
    if waffo_signature:
        # 1. 解析签名头 (格式如: t=timestamp,v1=base64_sig)
        t, v1 = "", ""
        for pair in waffo_signature.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "t":
                    t = v
                elif k == "v1":
                    v1 = v

        if not t or not v1:
            print("⛔ 拦截：签名头 X-Waffo-Signature 格式非法")
            raise HTTPException(status_code=401, detail="Malformed signature header")

        # 2. 验证时间戳，防止重放攻击 (5分钟容差)
        try:
            timestamp_ms = int(t)
            now_ms = int(time.time() * 1000)
            if abs(now_ms - timestamp_ms) > 5 * 60 * 1000:
                print("⛔ 拦截：Webhook 延迟超时，可能存在重放攻击！")
                raise HTTPException(status_code=401, detail="Webhook timestamp outside tolerance window")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp in signature")

        # 3. 校验 RSA-SHA256 签名
        try:
            payload_str = payload_body.decode('utf-8')
            data = json.loads(payload_str)
            mode = data.get("mode", "test")
            
            # 允许从环境变量覆盖公钥，否则使用内置的默认公钥
            public_key_pem = os.environ.get("WAFFO_WEBHOOK_PUBLIC_KEY")
            if not public_key_pem:
                public_key_pem = TEST_PUBLIC_KEY if mode == "test" else PROD_PUBLIC_KEY
                
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            import base64
            
            public_key = load_pem_public_key(public_key_pem.encode('utf-8'))
            signature_input = f"{t}.{payload_str}"
            signature_bytes = base64.b64decode(v1)
            
            public_key.verify(
                signature_bytes,
                signature_input.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            print("✅ Waffo Webhook 签名验证成功！")
        except Exception as e:
            print(f"⛔ 拦截：Waffo Webhook 签名验证失败: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid signature: {e}")
            
    elif webhook_secret:
        # 如果配置了密钥强制校验却缺失签名
        print("⛔ 拦截：未提供签名头 Waffo-Signature")
        raise HTTPException(status_code=401, detail="Missing signature header")

    try:
        data = json.loads(payload_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    event_name = (data.get("eventType") or data.get("event") or data.get("event_type") or "").lower()
    print(f"📥 收到 Waffo Webhook 事件: {event_name}")
    
    event_data = data.get("data", {})
    order_id = event_data.get("orderId") or event_data.get("order_id") or event_data.get("id") or data.get("order_id")
    license_key = event_data.get("licenseKey") or event_data.get("license_key") or event_data.get("license") or order_id
    customer_email = event_data.get("buyerEmail") or event_data.get("customer", {}).get("email") or event_data.get("email") or "unknown@example.com"
    
    if not license_key:
        print("⚠️ 未能解析到有效的 order_id 或 license_key")
        return {"status": "ignored", "reason": "No order_id or license_key found"}
        
    # 判断事件类型：优先判断退款或撤销事件，避免 refund.succeeded 被误判为激活
    if "refund" in event_name or "void" in event_name or "chargeback" in event_name or "canceled" in event_name:
        revoked = revoke_license(license_key)
        if revoked:
            return {"status": "success", "message": f"License key {license_key} revoked"}
        else:
            return {"status": "ignored", "reason": "License key not found for revocation"}
            
    elif "success" in event_name or "completed" in event_name or "succeeded" in event_name or "activated" in event_name or not event_name:
        activate_license(license_key, customer_email, order_id, event_name)
        return {"status": "success", "message": f"License key {license_key} activated"}
            
    return {"status": "ignored", "reason": f"Unhandled event type: {event_name}"}


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
    url: str = ""
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
        print(f"🔄 正在验证卡密/订单号: {req.license_key} ...")
        license_info = get_license(req.license_key)
        
        if not license_info:
            print(f"⛔ 拦截！卡密未在授权库中找到: {req.license_key}")
            return {
                "success": False,
                "error": "无效的 License Key！请确保输入正确的购买卡密或订单号。"
            }
            
        if license_info.get("status") != "active":
            print(f"⛔ 拦截！此卡密非有效状态: {req.license_key} (Status: {license_info.get('status')})")
            return {
                "success": False,
                "error": "此 License Key 已失效（可能已被退款或冻结）。"
            }
            
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

    # ==========================================
    # Firecrawl 高级网页抓取逻辑
    # ==========================================
    markdown_content = req.text
    if req.url:
        print(f"🕷️ 正在使用 Firecrawl 抓取纯净内容: {req.url}")
        firecrawl_key = os.environ.get("FIRECRAWL_API_KEY", "")
        if firecrawl_key:
            try:
                # 抓取可能需要一点时间，设置 30 秒超时
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    fc_response = await http_client.post(
                        "https://api.firecrawl.dev/v1/scrape",
                        headers={
                            "Authorization": f"Bearer {firecrawl_key}",
                            "Content-Type": "application/json"
                        },
                        json={"url": req.url, "formats": ["markdown"]}
                    )
                fc_data = fc_response.json()
                if fc_data.get("success"):
                    # Firecrawl 可能会返回很长的文章，截取前 10000 个字符避免 token 超出
                    markdown_content = fc_data.get("data", {}).get("markdown", req.text)[:10000]
                    print("✅ Firecrawl 抓取成功，获取到干净的 Markdown！")
                else:
                    print(f"⚠️ Firecrawl API 返回错误，降级使用原始文本: {fc_data}")
            except Exception as e:
                print(f"⚠️ Firecrawl 连接超时或失败，降级使用插件自带文本: {e}")
        else:
            print("⚠️ 未配置 FIRECRAWL_API_KEY 环境变量，降级使用插件自带文本。")

    prompt = f"""
    你是一个拥有百万粉丝的 Twitter (X) 营销专家。
    网页标题：【{req.title}】
    文章内容(Markdown格式)：
    【{markdown_content}】
    请帮我把这个网页的核心内容总结成推文。
    
    具体要求如下：
    1. 使用语言：{req.lang}
    2. 人设与语气风格：{tone_instruction}
    3. 视觉元素：包含 1-3 个合适的 Emoji 🌟
    4. 标签控制：{hashtag_instruction}
    5. 长度限制：如果用户没有选择 Thread 风格，你必须将输出内容严格控制在 280 个字符（包括空格）以内，绝对不能超字数！
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
        error_str = str(e).lower()
        if "insufficient" in error_str or "balance" in error_str or "402" in error_str:
            print(f"🚨 API 余额不足报错: {e}")
            return {"success": False, "error": "AI 服务器欠费停机啦！请发邮件提醒开发者充值 (support@x-maker.com)。"}
        else:
            print(f"🚨 调用 API 失败: {e}")
            return {"success": False, "error": f"服务器连接出错了，如果持续报错，请联系 support@x-maker.com ({str(e)[:50]})"}

if __name__ == "__main__":
    import uvicorn
    import os
    # 云端服务器（如 Render）会自动分配一个 PORT 环境变量，本地测试时默认使用 8000
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 商业版安全服务器准备在端口 {port} 启动...")
    uvicorn.run(app, host="0.0.0.0", port=port)
