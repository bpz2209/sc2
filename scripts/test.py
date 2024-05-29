from absl import app
from pysc2.env import sc2_env
from pysc2.lib import actions, features
import json
from openai import OpenAI
import datetime
import time
import os
import matplotlib.pyplot as plt
import csv

# 定义必要的常量
_PLAYER_SELF = features.PlayerRelative.SELF
_PLAYER_ENEMY = features.PlayerRelative.ENEMY

# 定义映射关系
unit_mapping = {
    "SiegeTank": "Armor",
    "Hellion": "Mechanized Infantry",
    "Marauder": "Mortar",
    "Banshee": "Aviation",
    "SiegeTankSieged": "Artillery",
    "Reaper": "Anti-Armor",
    "Marine": "Infantry"
}

# SC2 单位类型 ID 到名称的映射（需要根据实际情况补充）
sc2_unit_type_to_name = {
    48: "Marine",
    49: "Reaper",
    53: "Hellion",
    51: "Marauder",
    55: "Banshee",
    33: "SiegeTank",
    32: "SiegeTankSieged"
}

class COA_GPT:
    def __init__(self, api_key, base_url="https://api.bianxieai.com/v1", model_name="gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.chat_log_file = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + self.model_name
        self.create_directory()

    def create_directory(self):
        if not os.path.exists(self.chat_log_file):
            os.makedirs(self.chat_log_file)

    def chat(self, context):
        start_time = time.time()  # 记录开始时间
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": context,
                }
            ]
        )
        end_time = time.time()  # 记录结束时间
        response = completion.choices[0].message.content
        elapsed_time = end_time - start_time  # 计算总的处理时间
        print(f"GPT response time: {elapsed_time:.4f} seconds")  # 保留四位小数
        print(response)
        self.log_conversation(context, response, elapsed_time)
        return response

    def log_conversation(self, question, answer, elapsed_time):
        log_path = os.path.join(self.chat_log_file, self.chat_log_file + ".txt")
        with open(log_path, "a") as file:
            file.write(f"Question:\n{question}\n")
            file.write(f"Answer:\n{answer}\n")
            file.write(f"Response time: {elapsed_time:.4f} seconds\n\n")  # 保留四位小数

    def system_prompt(self):
        example_coa_statement = """
        {
            "coa_id_0": {
                "overview": "<describes overall strategy for this COA, explain why it is feasible (the COA can accomplish the mission within the established time, space, and resource limitations), acceptable (the COA must balance cost and risk with advantage gained), suitable (the COA can accomplish the mission objective), and distinguishable (each COA must differ significantly from the others).>",
                "name": "<name that summarizes this particular COA>",
                "task_allocation": [
                    {"unit_id": 4295229441, "unit_type": "Mechanized infantry", "alliance": "Friendly", "position": {"x": 14.0, "y": 219.0}, "command": "attack_move_unit(4295229441, 35.0, 41.0)"},
                    {"unit_id": 4299948033, "unit_type": "Aviation", "alliance": "Friendly", "position": {"x": 10.0, "y": 114.0}, "command": "engage_target_unit(4295229441, 3355229433)"}
                ]
            },
            "coa_id_1": {
                "<new COA using same template as above>"
            }
        }
        """

        additional_military_info = """
        - The forms of maneuver are envelopment, flank attack, frontal attack, infiltration, penetration, and turning movement. Commanders use these forms of maneuver to orient on the enemy, not terrain.
        - The four primary offensive tasks are movement to contact, attack, exploitation, and pursuit. While it is convenient to talk of them as different tasks, in reality they flow readily from one to another.
        - There are three basic defensive tasks - area defense, mobile defense, and retrograde.
        """
        prompt = f"""
        You are a military commander assistant. Your users are military commanders and your role is to help them develop military courses of action (COA).
        The military commanders will inform you the mission objective, terrain information, and available friendly and hostile assets before you start developing the COA.
        Given this information, you will develop a number of courses of action (as specified by the commander) so they can iterate on them with you and pick their favorite one.
        For each COA to be complete, every friendly unit needs to be assigned one command from the list below. Hostile units cannot be assigned any command.
        
        1) attack_move_unit(unit_id, target_x, target_y): commands friendly unit to move to target (x, y) coordinate in the map engaging hostile units in its path.
        2) engage_target_unit(unit_id, target_unit_id, target_x, target_y): commands friendly unit to engage with hostile target unit, which is located at the target (x, y) coordinate in the map. If out of range, friendly unit will move to the target unit location before engaging.
        
        Remember, it is of vital importance that all friendly units are given commands. All generated COAs should be aggregated in a single JSON object following the template below:

        example_coa_statement:
        {example_coa_statement}

        additional_military_info:
        {additional_military_info}
        """
        return prompt

    def generate_battlefield_info(self, units_on_screen):
        """生成战场信息准备输入GPT模型"""
        # MISSION_OBJECTIVE_TIGERCLAW = "Move friendly forces from the west side of the river to the east via multiple bridges, destroy all hostile forces, and ultimately seize objective OBJ Lion East at the top right corner of the map (coordinates x: 200, y: 89)."
        MISSION_OBJECTIVE_TIGERCLAW = "Move friendly forces from the west side of the river to the east via multiple bridges, destroy all hostile forces."
        TERRAIN_TIGERCLAW = "The map is split in two major portions (west and east sides) by a river that runs from north to south. There are four bridges that can be used to cross this river. Bridge names and exit coordinates are as follows: 1) Bridge Bobcat (x: 75, y: 26), 2) Bridge Wolf (x: 76, y: 128), 3) Bridge Bear (x:81, y: 179), and 4) Bridge Lion (x: 82, y: 211)."

        raw_units_json = []
        for unit in units_on_screen:
            alliance = "Friendly" if unit.alliance == _PLAYER_SELF else "Hostile"
            unit_type = unit_mapping.get(sc2_unit_type_to_name.get(unit.unit_type, "Unknown"), "Unknown")
            position = {"x": unit.x, "y": unit.y}
            raw_units_json.append({"unit_id": unit.tag, "unit_type": unit_type, "alliance": alliance, "position": position})
        
        raw_units_str = ", ".join([str(unit) for unit in raw_units_json])
        all_info = f"""
        I need to generate a single military course of action to accomplish the following mission objective:
        {MISSION_OBJECTIVE_TIGERCLAW}
        The mission is taking place in the following map/terrain:
        {TERRAIN_TIGERCLAW}
        The available Friendly and Hostile forces with their respective identification tags, types, and position are defined in the following JSON object:
        {raw_units_str}
        """
        
        # 打印提供给GPT的战场信息
        print("GPT战场信息:")
        print(all_info)
        return all_info

def initialize_env():
    """初始化SC2环境"""
    return sc2_env.SC2Env(
        map_name="TigerClaw_V1",
        players=[
            sc2_env.Agent(sc2_env.Race.terran),  # 玩家1
            sc2_env.Bot(sc2_env.Race.zerg, sc2_env.Difficulty.medium)  # 玩家2：计算机
        ],
        agent_interface_format=features.AgentInterfaceFormat(
            feature_dimensions=features.Dimensions(screen=84, minimap=64),
            use_raw_units=True
        ),
        step_mul=1,  # 将步长增加到1，以降低游戏速度
        game_steps_per_episode=0,
        visualize=True,
    )

def get_unit_weapon_info(unit):
    """获取单位的武器信息"""
    if hasattr(unit, 'weapons') and unit.weapons:
        weapon = unit.weapons[0]
        return weapon.range, weapon.damage
    return 0, 0

def print_units(timestep):
    """打印当前存在的单位信息"""
    units_on_screen = [unit for unit in timestep.observation.raw_units]
    print("战场信息:")
    for unit in units_on_screen:
        alliance = "友军" if unit.alliance == _PLAYER_SELF else "敌军"
        sc2_unit_name = sc2_unit_type_to_name.get(unit.unit_type, "Unknown")
        tc_unit_name = unit_mapping.get(sc2_unit_name, "Unknown")
        attack_range, attack_damage = get_unit_weapon_info(unit)
        print(f"联盟: {alliance}, 单位ID: {unit.tag}, 单位类型: {unit.unit_type}, TigerClaw 类型: {tc_unit_name}, 位置: ({unit.x}, {unit.y}), "
              f"攻击范围: {attack_range}, 攻击力: {attack_damage}, 血量: {unit.health} "
              f"护盾: {unit.shield if hasattr(unit, 'shield') else 'N/A'}, 能量: {unit.energy if hasattr(unit, 'energy') else 'N/A'}")
    return units_on_screen

def attack_move_unit(env, timestep, unit_id, target_x, target_y):
    """命令单位移动到指定坐标并攻击途中的敌人"""
    try:
        action = actions.RAW_FUNCTIONS.Attack_pt("now", unit_id, (target_x, target_y))
        print(f"Executing attack-move command for unit {unit_id} to position ({target_x, target_y})")
        try:
            env.step([action])
        except Exception as e:
            print(f"Error when executing attack-move command: {e}")
    except ValueError as e:
        print("Attack_pt action is not available.")

def engage_target_unit(env, timestep, unit_id, target_unit_id):
    """命令单位攻击指定ID的目标单位，并且不攻击其他目标"""
    try:
        action = actions.RAW_FUNCTIONS.Attack_unit("now", unit_id, target_unit_id)
        print(f"Executing engage command for unit {unit_id} to attack target unit with ID {target_unit_id}")
        try:
            env.step([action])
        except Exception as e:
            print(f"Error when executing engage command: {e}")
    except ValueError as e:
        print("Attack_unit action is not available.")

def parse_command(command):
    """解析命令"""
    parsed_commands = []
    units_with_commands = set()
    for coa_id, coa in command.items():
        print(f"解析 {coa_id}: {coa['name']}")
        for task in coa['task_allocation']:
            try:
                unit_id = task['unit_id']
                command_str = task['command']
                units_with_commands.add(unit_id)
                print(command_str)
                if command_str:
                    try:
                        command_name, args = command_str.split('(', 1)
                        args = args.rstrip(')').split(', ')
                        if command_name == "attack_move_unit":
                            parsed_commands.append((attack_move_unit, unit_id, float(args[1]), float(args[2])))
                        elif command_name == "engage_target_unit":
                            parsed_commands.append((engage_target_unit, unit_id, int(args[1])))
                    except ValueError:
                        print(f"Failed to parse command: {command_str}")
                else:
                    print(f"No command for unit_id: {unit_id}")
            except:
                print(f"Failed to parse task: {task}")
    return parsed_commands, units_with_commands

def run_game(unused_argv):
    # COA-GPT
    coa_gpt = COA_GPT(api_key="sk-01e7u2gwWhhrLIVpFb1b8fC1126e414bAf74D1BeFf70C9D8", base_url="https://api.bianxieai.com/v1", model_name="gpt-3.5-turbo")

    # 仿真次数
    num_simulations = 1
    for sim in range(num_simulations):
        scores = []
        plt.ion()  # 开启交互模式
        fig, ax = plt.subplots()
        line, = ax.plot(scores)
        ax.set_xlabel('Step')
        ax.set_ylabel('Score')
        ax.set_title(f'Score Over Time - Simulation {sim + 1}')

        print(f"Starting simulation {sim + 1} of {num_simulations}")
        command_json = """
        {
        "coa_id_0": {
            "overview": "The objective of this COA is to conduct a frontal attack on the enemy forces. This COA is feasible as the friendly units have sufficient firepower and can engage the hostiles effectively. It is acceptable as the cost and risk are balanced with the advantage gained. It is suitable as it directly aligns with the mission objective. It is distinguishable as it differs significantly from the other COAs.",
            "name": "Frontal Attack",
            "task_allocation": [
                {"unit_id": 4295229441, "unit_type": "Mechanized infantry", "alliance": "Friendly", "position": {"x": 14.0, "y": 219.0}, "command": "attack_move_unit(4295229441, 80.0, 219.0)"},
                {"unit_id": 4299948033, "unit_type": "Aviation", "alliance": "Friendly", "position": {"x": 10.0, "y": 114.0}, "command": "engage_target_unit(4295229441, 3355229433, 80.0, 219.0)"}
            ]
        },
        "coa_id_1": {
            "overview": "The objective of this COA is to conduct a flank attack on the enemy forces. This COA is feasible as the friendly units can maneuver to the enemy's weak flank. It is acceptable as the cost and risk are balanced with the advantage gained. It is suitable as it directly aligns with the mission objective. It is distinguishable as it differs significantly from the other COAs.",
            "name": "Flank Attack",
            "task_allocation": [
                {"unit_id": 4295229441, "unit_type": "Mechanized infantry", "alliance": "Friendly", "position": {"x": 14.0, "y": 219.0}, "command": "attack_move_unit(4295229441, 60.0, 170.0)"},
                {"unit_id": 4299948033, "unit_type": "Aviation", "alliance": "Friendly", "position": {"x": 10.0, "y": 114.0}, "command": "engage_target_unit(4295229441, 3355229433, 60.0, 170.0)"}
            ]
        },
        "coa_id_2": {
            "overview": "The objective of this COA is to conduct a infiltration maneuver to surprise the enemy forces from behind. This COA is feasible as the terrain allows for covert movements of friendly units. It is acceptable as the cost and risk are balanced with the advantage gained. It is suitable as it directly aligns with the mission objective. It is distinguishable as it differs significantly from the other COAs.",
            "name": "Infiltration Maneuver",
            "task_allocation": [
                {"unit_id": 4295229441, "unit_type": "Mechanized infantry", "alliance": "Friendly", "position": {"x": 14.0, "y": 219.0}, "command": "attack_move_unit(4295229441, 150.0, 10.0)"},
                {"unit_id": 4299948033, "unit_type": "Aviation", "alliance": "Friendly", "position": {"x": 10.0, "y": 114.0}, "command": "engage_target_unit(4295229441, 3355229433, 150.0, 10.0)"}
            ]
        }
    }
        """
        command = json.loads(command_json)
        parsed_commands, units_with_commands = parse_command(command)

        with initialize_env() as env:
            timesteps = env.reset()
            timestep = timesteps[0]
            units_on_screen = print_units(timestep)
            info = coa_gpt.generate_battlefield_info(units_on_screen)
            system_prompt = coa_gpt.system_prompt()
            response = coa_gpt.chat(system_prompt + info)
            print("在info下的回复：")
            print(response)

            # 获取所有友军单位的ID
            all_friendly_unit_ids = {unit.tag for unit in units_on_screen if unit.alliance == _PLAYER_SELF}
            while True:
                timestep = timesteps[0]
                units_on_screen = print_units(timestep)

                if not units_on_screen:
                    break  # 没有友方单位，结束循环

                # 执行解析后的命令
                # 寻找response中的命令({}部分)
                response_json_start = response.find("{")
                response_json_end = response.rfind("}") + 1
                if response_json_start != -1 and response_json_end != -1:
                    response_json = response[response_json_start:response_json_end]
                    try:
                        parsed_commands, units_with_commands = parse_command(json.loads(response_json))
                        for command_func, *args in parsed_commands:
                            print(f"Executing GPT command: {command_func.__name__} with args: {args}")
                            command_func(env, timestep, *args)
                            timesteps = env.step([actions.RAW_FUNCTIONS.no_op()])
                    except json.JSONDecodeError:
                        print("Failed to parse JSON from GPT response.")
                
                # 打印未接收到命令的单位
                units_without_commands = all_friendly_unit_ids - units_with_commands
                if units_without_commands:
                    print("Units without commands:")
                    for unit_id in units_without_commands:
                        print(f"Unit ID: {unit_id}")

                # 打印命令已完成的单位
                print("Commands executed for units:")
                for unit_id in units_with_commands:
                    print(f"Unit ID: {unit_id}")

                # 记录分数
                score = timestep.observation['score_cumulative'][0]
                scores.append(score)
                print(f"Current Score: {score}")

                # 实时更新图表
                line.set_ydata(scores)
                line.set_xdata(range(len(scores)))
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)

                # 实时保存分数到CSV文件
                csv_path = os.path.join(coa_gpt.chat_log_file, f"simulation_{sim + 1}_scores.csv")
                with open(csv_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Step", "Score"])
                    for i, score in enumerate(scores):
                        writer.writerow([i, score])

                # 检查游戏是否结束
                game_end = timestep.last()
                print(f"Game End: {game_end}")
                if game_end:
                    break

        # 最后保存图表
        plt_path = os.path.join(coa_gpt.chat_log_file, f"simulation_{sim + 1}_scores.png")
        plt.savefig(plt_path)
        plt.close(fig)

    plt.ioff()

if __name__ == "__main__":
    app.run(run_game)
