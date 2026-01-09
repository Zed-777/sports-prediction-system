from PIL import Image, ImageStat

paths = [
    "reports/leagues/premier-league/matches/tottenham-hotspur-football-club_vs_liverpool-football-club_2025-12-20/prediction_card.png",
    "reports/leagues/premier-league/matches/aston-villa-football-club_vs_manchester-united-football-club_2025-12-21/prediction_card.png",
]
for p in paths:
    try:
        im = Image.open(p).convert("RGB")
        stat = ImageStat.Stat(im)
        mean = stat.mean
        var = stat.var
        extrema = im.getextrema()
        w, h = im.size
        nonwhite = sum(1 for px in im.getdata() if px != (255, 255, 255))
        print(p)
        print(f" size={w}x{h}")
        print(f" mean={mean}, var={var}, nonwhite_pixels={nonwhite}")
    except Exception as e:
        print(p, "ERROR", e)
