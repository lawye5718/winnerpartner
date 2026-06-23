import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess

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
            # 【关键修复1】：设为 None 让引擎日志直接输出到控制台。
            # 既防止了未被读取导致的 PIPE 缓冲区写满死锁，又能让你在终端看到 AI 的算路胜率！
            stderr=None, 
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
            if line == "":  # 遇到 EOF，说明引擎意外退出了
                break
            # 【关键修复3】：GTP 协议以一个空行结束，使用 strip() 兼容 Mac/Win 的各种换行符
            if line.strip() == "": 
                break
            output += line
            
        # GTP 返回成功格式为 "= 结果"，失败为 "? 错误信息"
        return output.strip().lstrip("= ")

    def sync_opponent_move(self, color, coord):
        """同步网页上发生的实际招法到内部棋盘"""
        return self.send_command(f"play {color} {coord}")

    def generate_best_move(self, my_color):
        """让 AI 思考并返回最佳选点"""
        print(f"🤔 AI 正在疯狂算路中 (为 {my_color} 思考)...")
        best_move = self.send_command(f"genmove {my_color}")
        
        # 【关键修复2】：战术性悔棋 (Undo) 防不同步机制！
        # genmove 不仅会返回坐标，还会默认在内部棋盘落子。
        # 如果不 undo，等网页真实落子后油猴脚本把招法再次传回来同步时，KataGo 会报非法落子(重叠)。
        # 因此，AI 想出招法后立刻撤销，保持内部绝对干净，完全依赖网页的真实事件流来推进。
        if not best_move.startswith("?"): # 只要没有返回错误信息
            self.send_command("undo")
            
        return best_move

# 初始化 FastAPI 和 AI 引擎
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 引擎路径配置
ENGINE_PATH = "/Users/yuanliang/projects/KataGo/cpp/katago"
MODEL_PATH = "/Users/yuanliang/projects/KataGo/default_model.bin.gz"
CONFIG_PATH = "/Users/yuanliang/superstar/superstar3.1/projects/winnerpartner/gtp_custom.cfg"

# 实例化引擎
ai_engine = GTPController(ENGINE_PATH, MODEL_PATH, CONFIG_PATH) 

class MoveData(BaseModel):
    step: int
    player: str
    raw_coordinate: str

@app.post("/api/move")
async def receive_move(data: MoveData):
    print("-" * 40)
    print(f"📥 [第 {data.step} 手] 网页发生落子 | 玩家: {data.player} | 坐标: {data.raw_coordinate}")
    
    # 转换为GTP坐标 (例如: q-16 -> Q16)
    gtp_coord = data.raw_coordinate.replace("-", "").upper()
    
    # 将网页最新招法同步进 KataGo 的内部大脑
    sync_result = ai_engine.sync_opponent_move(data.player, gtp_coord)
    if sync_result.startswith("?"):
        print(f"⚠️ 引擎同步异常: {sync_result}")
    
    # 对方下了，我们要计算己方(另一种颜色)的招法
    my_color = "B" if data.player == "W" else "W"
    
    # 触发引擎计算
    ai_recommendation = ai_engine.generate_best_move(my_color)

    print(f"🎯 AI 最终决定下在: {ai_recommendation}")
    
    # 返回给油猴脚本用于高亮红点或自动执行
    return {
        "status": "success", 
        "opponent_move": gtp_coord,
        "ai_recommendation": ai_recommendation
    }

if __name__ == "__main__":
    print("🚀 Winner Partner 本地中枢已启动，正在监听 127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
