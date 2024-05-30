# 使用手册（推荐使用Anaconda3进行虚拟环境管理）
## 安装环境
```
pip install pysc2/
pip install -r requirements.txt
```
## 运行
```
python scripts/test.py
```
## 参数说明
```
# GPT相关变量
api_key_ = "sk-01e7u2gwWhhrLIVpFb1b8fC1126e414bAf74D1BeFf70C9D8" # 对应的账户token, 非必要不修改
base_url_ = "https://api.bianxieai.com/v1"                       # 对应的中介API, 不修改
model_name_ = "gpt-3.5-turbo"                                    # 模型选择 (gpt-3.5-turbo, gpt-4, gpt-4o) 后面两个效果好，但是价格高，请谨慎使用

# 仿真变量
num_simulations_ = 3                                             # 仿真次数
game_time_seconds_ = 100 / 1.42                                  # 每次仿真结束的时间，时间与步长有关，同时与电脑性能有关，无法读取比赛的剩余时间， 修改时修改前面的数字100即可 
log_directory_ = "../logs"                                       # 仿真结果放的位置，命名为时间+model_name

```