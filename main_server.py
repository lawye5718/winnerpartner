import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import threading
import sys
import re

class GTPController:
    def __init__(self, engine_path, model_path, config_path):
        print(f"🔄 正在启动本地围棋 AI 引擎: {engine_path}...")
        self.lock = threading.Lock()
        
        cmd = [engine_path, "gtp", "-model", model_path, "-config", config_path]
        
        # 将 stderr 重定向为 PIPE，以便我们通过代码读取胜率
        self.process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1
        )
        
        self.current_winrate = 50.0  # 初始胜率
        
        # 启动后台守护线程，实时读取 KataGo 的思考日志并提取胜率
        self.stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self.stderr_thread.start()
        
        self.send_command("boardsize 19")
        self.send_command("clear_board")
        self.send_command("time_settings 0 5 1") # 思考时间：每步5秒
        print("✅ AI 引擎启动完成并已就绪。")

    def _read_stderr(self):
        """后台线程：实时解析引擎输出，提取胜率"""
        for line in iter(self.process.stderr.readline, ''):
            if line == "": break
            
            # 将引擎的思考日志同步打印到终端，保持控制台的可读性
            sys.stdout.write(line)
            sys.stdout.flush()
            
            # 使用正则抓取胜率 (例如: "winrate 0.4503")
            match = re.search(r"winrate\s+([0-9.]+)", line)
            if match:
                self.current_winrate = float(match.group(1)) * 100

    def send_command(self, cmd):
        with self.lock:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush()
            output = ""
            while True:
                line = self.process.stdout.readline()
                if line == "" or line.strip() == "": 
                    break
                output += line
            return output.strip().lstrip("= ")

    def sync_move(self, color, coord):
        """无条件同步网页实际发生的招法"""
        return self.send_command(f"play {color} {coord}")

    def generate_best_move(self, my_color):
        best_move = self.send_command(f"genmove {my_color}")
        if not best_move.startswith("?"): 
            self.send_command("undo") # 战术悔棋，保持内部状态等待网页事实
        return best_move

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# TODO: 确认你的路径
ENGINE_PATH = "/Users/yuanliang/projects/KataGo/cpp/katago"
MODEL_PATH = "/Users/yuanliang/projects/KataGo/default_model.bin.gz"
CONFIG_PATH = "/Users/yuanliang/superstar/superstar3.1/projects/winnerpartner/gtp_custom.cfg"

ai_engine = GTPController(ENGINE_PATH, MODEL_PATH, CONFIG_PATH) 

class MoveData(BaseModel):
    step: int
    player: str
    raw_coordinate: str
    my_color: str

@app.post("/api/move")
def receive_move(data: MoveData):
    print("=" * 50)
    gtp_coord = data.raw_coordinate.replace("-", "").upper()
    
    # 1. 事实同步：不论是你的变招还是对手的招，立刻刻入 KataGo 大脑
    print(f"📥 [第 {data.step} 手] DOM事实落子 | 玩家: {data.player} | 坐标: {gtp_coord}")
    ai_engine.sync_move(data.player, gtp_coord)
    
    ai_recommendation = ""
    
    # 2. 判断是否需要算路
    if data.player != data.my_color:
        print(f"🤔 轮到己方 [{data.my_color}]，正在呼叫 KataGo 计算对策...")
        ai_recommendation = ai_engine.generate_best_move(data.my_color)
        print(f"🎯 AI 决定下在: {ai_recommendation}，当前胜率: {ai_engine.current_winrate:.1f}%")
    else:
        print(f"👤 己方(你)已完成实战落子 ({gtp_coord})，大脑状态已同步。")

    return {
        "status": "success", 
        "ai_recommendation": ai_recommendation,
        "winrate": ai_engine.current_winrate  # 将胜率传给前端画图
    }

if __name__ == "__main__":
    print("🚀 Winner Partner 本地中枢已启动，正在监听 0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
