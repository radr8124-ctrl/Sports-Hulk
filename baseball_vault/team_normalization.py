import re

ALIASES = {
    "athletics":"athletics","oakland athletics":"athletics","oakland a's":"athletics","oakland as":"athletics",
    "new york mets":"new york mets","ny mets":"new york mets","mets":"new york mets",
    "new york yankees":"new york yankees","ny yankees":"new york yankees","yankees":"new york yankees",
    "los angeles angels":"los angeles angels","la angels":"los angeles angels","angels":"los angeles angels",
    "los angeles dodgers":"los angeles dodgers","la dodgers":"los angeles dodgers","dodgers":"los angeles dodgers",
    "san francisco giants":"san francisco giants","sf giants":"san francisco giants",
    "san diego padres":"san diego padres","sd padres":"san diego padres",
    "st louis cardinals":"st louis cardinals","st. louis cardinals":"st louis cardinals",
    "kansas city royals":"kansas city royals","kc royals":"kansas city royals",
    "tampa bay rays":"tampa bay rays","tb rays":"tampa bay rays",
    "toronto blue jays":"toronto blue jays","blue jays":"toronto blue jays",
    "chicago white sox":"chicago white sox","white sox":"chicago white sox",
    "chicago cubs":"chicago cubs","cubs":"chicago cubs",
    "boston red sox":"boston red sox","red sox":"boston red sox",
    "baltimore orioles":"baltimore orioles","orioles":"baltimore orioles",
    "cleveland guardians":"cleveland guardians","guardians":"cleveland guardians",
    "detroit tigers":"detroit tigers","tigers":"detroit tigers",
    "minnesota twins":"minnesota twins","twins":"minnesota twins",
    "milwaukee brewers":"milwaukee brewers","brewers":"milwaukee brewers",
    "houston astros":"houston astros","astros":"houston astros",
    "texas rangers":"texas rangers","rangers":"texas rangers",
    "seattle mariners":"seattle mariners","mariners":"seattle mariners",
    "miami marlins":"miami marlins","marlins":"miami marlins",
    "atlanta braves":"atlanta braves","braves":"atlanta braves",
    "washington nationals":"washington nationals","nationals":"washington nationals",
    "philadelphia phillies":"philadelphia phillies","phillies":"philadelphia phillies",
    "pittsburgh pirates":"pittsburgh pirates","pirates":"pittsburgh pirates",
    "cincinnati reds":"cincinnati reds","reds":"cincinnati reds",
    "colorado rockies":"colorado rockies","rockies":"colorado rockies",
    "arizona diamondbacks":"arizona diamondbacks","diamondbacks":"arizona diamondbacks","d-backs":"arizona diamondbacks",
}

def normalize_team(x):
    s=str(x or "").lower().strip()
    s=s.replace("&","and")
    s=re.sub(r"[^a-z0-9]+"," ",s)
    s=re.sub(r"\s+"," ",s).strip()
    return ALIASES.get(s,s)
