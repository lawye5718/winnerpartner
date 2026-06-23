import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import threading

# ==========================================
# 核心组件：GTP 协议控制器 (用于对接 KataGo)
# ==========================================
class GTPController:
    def __init__(self, engine_path, model_path, config_path):
        print(f"🔄 正在启动本地围棋 AI 引擎: {engine_path}...")
        
        # 【关键修复1】：加入线程锁，防止高频并发请求导致输入输出流崩溃
        self.lock = threading.Lock()
        
        cmd = [engine_path, "gtp", "-model", model_path, "-config", config_path]
            
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # 允许引擎日志直接打印到终端
            text=True,
            bufsize=1
        )
        
        # 初始化棋盘
        self.send_command("boardsize 19")
        self.send_command("clear_board")
        
        # 【关键修复2】：强制设置思考时间 (0秒主时间，每步5秒，1次读秒)
        # 防止 KataGo 无限期算路导致“半天没反应”
        self.send_command("time_settings 0 5 1")
        
        print("✅ AI 引擎启动完成并已就绪。")

    def send_command(self, cmd):
        """向引擎发送命令并阻塞读取返回结果（带线程锁）"""
        with self.lock:
            # 发送指令前打印日志，方便定位问题
            print(f"\n[GTP 发送] ➡️ {cmd}")
            
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush()
            
            output = ""
            while True:
                line = self.process.stdout.readline()
                if line == "":  # EOF
                    break
                if line.strip() == "": # 遇到空行说明这条GTP指令返回完毕
                    break
                output += line
                
            res = output.strip()
            print(f"[GTP 接收] ⬅️ {res}")
            return res.lstrip("= ")

    def sync_opponent_move(self, color, coord):
        """同步网页上发生的实际招法到内部棋盘"""
        return self.send_command(f"play {color} {coord}")

    def generate_best_move(self, my_color):
        """让 AI 思考并返回最佳选点"""
        best_move = self.send_command(f"genmove {my_color}")
        
        # 战术性悔棋 (Undo)，防状态不同步机制
        if not best_move.startswith("?"): 
            self.send_command("undo")
            
        return best_move

# 初始化 FastAPI
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

# 【关键修复3】：移除 async 关键字！
# 这样 FastAPI 会将其放入后台线程池执行，彻底解决阻塞 ASGI 事件循环导致的死锁假死！
@app.post("/api/move")
def receive_move(data: MoveData):
    print("=" * 50)
    print(f"📥 [第 {data.step} 手] 网页发生落子 | 玩家: {data.player} | 坐标: {data.raw_coordinate}")
    
    gtp_coord = data.raw_coordinate.replace("-", "").upper()
    
    # 1. 同步对手最新招法
    sync_result = ai_engine.sync_opponent_move(data.player, gtp_coord)
    if sync_result.startswith("?"):
        print(f"⚠️ 引擎同步异常: {sync_result}")
    
    # 2. 我们扮演对手的相反颜色
    my_color = "B" if data.player == "W" else "W"
    print(f"🤔 正在呼叫 KataGo 为 [{my_color}] 计算反击招法...")
    
    # 3. 触发引擎计算
    ai_recommendation = ai_engine.generate_best_move(my_color)

    print(f"🎯 AI 最终决定下在: {ai_recommendation}")
    
    return {
        "status": "success", 
        "opponent_move": gtp_coord,
        "ai_recommendation": ai_recommendation
    }

if __name__ == "__main__":
    print("🚀 Winner Partner 本地中枢已启动，正在监听 127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
