from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
    
BluffMind = ["Bluff Mind", "神仙吹牛牌"]
AgentMode = ["Agent Mode", "代理模式"]
ProgMode = ["Prog Mode", "程序模式"]
Round = ["Round", "轮次"]
TableCard = ["Table Card", "桌面牌"]
NotStartedYet = ["Not Started Yet", "尚未开始"]
Initializing = ["Initializing ...", "正在初始化 ..."]
AggLevel = ["Agg Level", "攻击等级"]
RRPosition = ["RR Position", "子弹位置"]
RRPlayed = ["RR Played", "已打枪数"]
CardsLeft = ["Cards Left", "剩余牌"]
LastPlayed = ["Last Played", "上次出牌"]
ToChallengeOrNot = ["To Challenge or Not, That's the Question", "挑战还是不挑战，这就是问题"]
KilledInRound = ["Killed In Round", "挂掉轮次:"]   

def make_screen(game=None, agent_mode=False, lang="a") -> Layout:
    if lang == "a":
        lang = 0
    else:
        lang = 1
        
    """Create the screen layout."""
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=4),
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    layout["left"].split(Layout(name="box1"), Layout(name="box4"))
    layout["right"].split(Layout(name="box2"), Layout(name="box3"))

    # Header
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="right")
    if game is not None:
        grid.add_row(
            f"[b]{BluffMind[lang]}[/b] " + (f"({AgentMode[lang]})" if agent_mode else f"({ProgMode[lang]})"),
            f"{Round[lang]}: {game.round_number}  {TableCard[lang]}: {game.table_card}"
        )
    else:
        grid.add_row(
            f"[b]{BluffMind[lang]}[/b] " + (f"({AgentMode[lang]})" if agent_mode else f"({ProgMode[lang]})"),
            f"{NotStartedYet[lang]}"
        )
    layout["header"].update(Panel(grid, style="white on blue"))
    
    if game is None:
        layout["box1"].update(Panel("", title=""))
        layout["box2"].update(Panel("", title=""))
        layout["box3"].update(Panel("", title=""))
        layout["box4"].update(Panel("", title=""))
        layout["footer"].update(Panel(f"{Initializing[lang]} ...", title=""))
        return layout

    i = 0
    for player in game.players_in_round:
        if player.in_play:
            style = "green"
        else:
            style = "blue"
        layout[f"box{i+1}"].update(Panel(
            f"{player.model}" + "\n\n"
            f"{AggLevel[lang]} : {player.aggro}" +
            "\n" +
            f"{RRPosition[lang]} : {player.rr_position}  {RRPlayed[lang]} : {player.rr_played}\n" + 
            "\n" +
            f"{CardsLeft[lang]}  : {', '.join(player.cards)}\n" + 
            f"{LastPlayed[lang]} : {', '.join(player.last_played_cards)}\n" +
            "\n" +
            f"{player.mind}\n" +
            "\n" +
            f"\"{player.taunt}\"", 
            title=f"{player.name}",
            style=style
        ))
        i += 1
    for player in game.all_players:
        if not player in game.players_in_round:
            layout[f"box{i+1}"].update(Panel(
                f"{player.model}" + "\n\n"
                "\n\n" +
                f"{KilledInRound[lang]} {player.dead_round}",
                title=f"{player.name}",
                style="red"
            ))
            i += 1

    style = "black"
    if game.screen_message_type == "challenge":
        style = "yellow"
    elif game.screen_message_type == "rr":
        style = "magenta"
    elif game.screen_message_type == "killed":
        style = "red"
    elif game.screen_message_type == "survived":
        style = "green"
    elif game.screen_message_type == "play":
        style = "blue"
        
    layout["footer"].update(Panel(game.screen_message, 
                                title=f"{ToChallengeOrNot[lang]}", 
                                style=style))
    return layout


def get_show_context(agent_mode, lang="a"):
    from rich.console import Console
    from rich.live import Live
    console = Console()
    rich_live = Live(make_screen(agent_mode=agent_mode, lang=lang), console=console, auto_refresh=False, screen=True)
    return rich_live