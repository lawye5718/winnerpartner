import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import threading

# ==========================================
# 核心组件：GTP 协议控制器 (用于对接 KataGo/Leela 等)
# ==========================================
class GTPController:
    def __init__(self, engine_path, model_path, config_path):
        print(f"🔄 正在启动本地围棋 AI 引擎: {engine_path}...")
        
        # 完整的 KataGo 启动命令必须包含 -model 和 -config
        cmd = [engine_path, "gtp", "-model", model_path, "-config", config_path]
            
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send_command("boardsize 19")
        self.send_command("clear_board")
        print("✅ AI 引擎启动完成并已就绪。")

    def send_command(self, cmd):
        """向引擎发送命令并阻塞读取返回结果"""
        self.process.stdin.write(cmd + "\n")
        self.process.stdin.flush()
        
        output = ""
        while True:
            line = self.process.stdout.readline()
            if line == "\n":  # GTP 协议规定输出以一个空行结束
                break
            output += line
            
        # GTP 返回成功格式为 "= 结果"，失败为 "? 错误信息"
        return output.strip().lstrip("= ")

    def sync_opponent_move(self, color, coord):
        """同步对手的招法到内部棋盘"""
        return self.send_command(f"play {color} {coord}")

    def generate_best_move(self, my_color):
        """让 AI 思考并返回最佳选点"""
        print("🤔 AI 正在疯狂算路中...")
        best_move = self.send_command(f"genmove {my_color}")
        return best_move

# 初始化 FastAPI 和 AI 引擎
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# TODO: 填入你 Mac 上实际的 KataGo 或其他引擎的路径
ENGINE_PATH = "/Users/yuanliang/projects/KataGo/cpp/katago"
MODEL_PATH = "/Users/yuanliang/projects/KataGo/default_model.bin.gz"
CONFIG_PATH = "/Users/yuanliang/superstar/superstar3.1/projects/winnerpartner/gtp_custom.cfg"

# 真正实例化引擎 (取消之前的模拟模式)
ai_engine = GTPController(ENGINE_PATH, MODEL_PATH, CONFIG_PATH) 

# 定义接收数据的格式
class MoveData(BaseModel):
    step: int
    player: str
    raw_coordinate: str

@app.post("/api/move")
async def receive_move(data: MoveData):
    print("-" * 40)
    print(f"📥 收到第 {data.step} 手 | 玩家: {data.player} | 坐标: {data.raw_coordinate}")
    
    # 转换为GTP坐标 (去除短横线)
    gtp_coord = data.raw_coordinate.replace("-", "").upper()
    
    # 我们扮演的颜色（如果当前是对手W下了，我们就应该让AI算B的招法）
    my_color = "B" if data.player == "W" else "W"
    
    ai_recommendation = ""
    
    if ai_engine:
        # 1. 告诉 AI 对手刚下在了哪
        ai_engine.sync_opponent_move(data.player, gtp_coord)
        # 2. 让 AI 生成我们的应对招法
        ai_recommendation = ai_engine.generate_best_move(my_color)
    else:
        # 【模拟模式】如果没有挂载真实AI，这里假装返回一个坐标用于测试
        import random
        cols = "ABCDEFGHJKLMNOPQRST"
        ai_recommendation = f"{random.choice(cols)}{random.randint(1, 19)}"
        print("⚠️ 引擎未挂载，返回模拟坐标")

    print(f"🎯 AI 决定下在: {ai_recommendation}")
    
    # 将 AI 的决定返回给浏览器前端
    return {
        "status": "success", 
        "opponent_move": gtp_coord,
        "ai_recommendation": ai_recommendation
    }

if __name__ == "__main__":
    print("🚀 Winner Partner 本地中枢已启动，正在监听 127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
