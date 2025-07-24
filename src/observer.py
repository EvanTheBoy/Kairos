# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import logging
from .graph.state import AgentState

logger = logging.getLogger(__name__)

def observe(state: AgentState) -> AgentState:
    """
    Observes the environment for events.
    In a real implementation, this would monitor data sources like file systems,
    IDE events, or APIs.
    
    For now, we'll simulate receiving messages from Feishu.
    """
    logger.info("Observing environment...")
    
    # Mock data: Simulate observing messages from Feishu.
    mock_events = [
        {
            "source": "feishu",
            "type": "message",
            "payload": {
                "user": "倪菲",
                "content": "各位伙伴们好，我是来自蓝驰创投的社会创新投资人菲菲。也是一只快乐狗狗超级E人～\n蓝驰创投投于2005年设立，是一家专注于早期创业公司的风险投资机构。目前，蓝驰创投在管资金规模超过150亿元人民币，是目前国内规模最大的早期基金之一，投资阶段集中于Pre-A、A轮，投资领域覆盖科技、消费和医疗健康，累计投资超200家创业企业。\n我负责的的是一支独立的投资基金，社会创新投资基金，投向那些用商业自造血手段，解决社会问题和困境群体，弱势群体的早期创业公司。群里看到了很多熟悉的面孔，还有很多已经有发心在用AI落在困境群体生活场景里的创业者们～\n社会类创业比商业类创业会更难跑通商业闭环但也具有巨大社会价值，欢迎群里的社会创新伙伴们加我微信共同讨论～希望我的经验和见解也能帮助到你们[爱心]\n期待下周杭州见啦～"
            }
        },
        {
            "source": "feishu",
            "type": "message",
            "payload": {
                "user": "巫昊林",
                "content": "温馨提醒：蓝驰Booming Hub开放麦 活动需要提前填写问卷哦，参与活动的同学将有机会一位蓝驰明星被投founder共进晚餐！\n活动信息：蓝驰Booming Hub开放麦\n你很年轻，所以无论在哪都有很多人想对你宣讲。但蓝驰创投想对你说：不！你干嘛总要听别人说？因为年轻所以创新，没有资历所以没有包袱。我们相信年轻人，所以要把舞台还给你。\n如果你不被定义、敢于跳出象限，如果你有个特别值得VC听到的idea/项目/想法……来蓝驰的Booming Hub开放麦，蓝驰管理合伙人、AI投资人、知名AI项目创始人们在现场一起听你说。全场得票最高者，可得到一项激励：直通蓝驰IC（投资委员会）或与一位蓝驰明星被投founder共进晚餐！\n点击报名蓝驰Booming Hub开放麦-Workshop报名表我们将在报名者中邀请几位上台。同时，我们将预留少数席位用作现场抢麦，让AI来公允判断。\n时间：7.24 下午 14:45-15:45\n主讲人：朱天宇（蓝驰创投管理合伙人）\n提供方：蓝驰创投\n地点：湖畔创研中心 - 工坊\n积分：2 分（需要完整参与后获得）\n🟢 本活动向公众开放，需要通行码与游客挂牌，请参考游客相关\n更多信息：蓝驰被投：https://www.lanchivc.com/projects/"
            }
        }
    ]
    
    state['raw_events'] = mock_events
    return state
