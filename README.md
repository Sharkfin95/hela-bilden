# Hela bilden

En svensk motsvarighet till Ground News: sidan samlar rubriker från svenska nyhetskällor, grupperar artiklar som handlar om samma händelse och visar hur täckningen fördelar sig mellan källor till vänster, i mitten och till höger.

## Så hänger det ihop

```
sources.json                 Källorna: namn, RSS-flöde och politisk placering
scripts/fetch_news.py        Hämtar flödena, grupperar artiklarna, skriver site/news.json
site/index.html              Själva sidan (läser news.json)
site/news.json               Ögonblicksbild från 24 nov 2026 – skrivs över vid första körningen
.github/workflows/uppdatera.yml   Kör skriptet var 30:e minut och publicerar sidan
```

Ingen server behövs. GitHub Actions hämtar nyheterna och GitHub Pages visar sidan, gratis.

## Kom igång (cirka 10 minuter)

1. Skapa ett nytt repo på GitHub, till exempel `hela-bilden`, och ladda upp alla filer i den här mappen (behåll mappstrukturen, även `.github`).
2. Gå till **Settings → Pages** och välj **Source: GitHub Actions**.
3. Gå till fliken **Actions**, välj **Uppdatera nyheter** och klicka **Run workflow**.
4. När körningen är klar finns sidan på `https://<ditt-användarnamn>.github.io/hela-bilden/`.

Därefter uppdateras den automatiskt var 30:e minut.

> GitHub pausar schemalagda körningar i repon som inte haft någon aktivitet på 60 dagar. Gör en liten ändring eller klicka Run workflow igen om det händer.

## Testa lokalt

```bash
pip install feedparser
python scripts/fetch_news.py --sources sources.json --out site/news.json
cd site && python -m http.server 8000
# öppna http://localhost:8000
```

## Lägga till eller ändra en källa

Lägg till en rad i `sources.json`:

```json
{"id": "unt", "name": "Upsala Nya Tidning", "lean": 1, "label": "Liberal",
 "basis": "Ledarsidans egen beteckning: liberal.", "type": "Dagstidning",
 "url": "https://www.unt.se", "feed": "https://www.unt.se/rss"}
```

`lean` är placeringen: −3 långt vänster, −2 vänster, −1 lutar vänster, 0 mitten, 1 lutar höger, 2 höger, 3 långt höger. Sätt `"enabled": false` för att pausa en källa. Lägg gärna till ett kort namn för källan i `SHORT` i `site/index.html`.

### Europa och USA

Flikarna Europa och USA visar engelskspråkiga källor. De har inga deklarerade ledarbeteckningar som svenska tidningar, så placeringen bygger på AllSides Media Bias Ratings. Översättningen är: Left = −2, Lean Left = −1, Center = 0, Lean Right = 1, Right = 2.

- **Europa:** The Guardian, The Independent, BBC News, Euronews, DW, The Telegraph, Daily Mail och GB News.
- **USA:** HuffPost, The New York Times, NPR, The Washington Post, The Wall Street Journal, The Hill, The Washington Times, New York Post, Fox News och Breitbart.

Utländska artiklar grupperas aldrig ihop med svenska, eftersom källorna mäts på olika politiska skalor. Fältet `regions` i `sources.json` styr flikarnas ordning, typ (`utland` eller `lokalt`) och introtext.

Flödesadresserna är hämtade från källornas egna sidor och från RSS-katalogen Feeder. Kontrollera i Actions-loggen efter första körningen att varje källa ger fler än 0 artiklar. Ger en källa 0 artiklar, sök på "källans namn RSS" och byt adressen i `sources.json`.

### Lokala källor

Källor med fältet `"region"` får en egen flik på sidan. Gävle finns redan med: Gefle Dagblad (liberal), Arbetarbladet (socialdemokratisk), SVT Gävleborg och P4 Gävleborg. Lokala nyheter visas bara under den lokala fliken. På första sidan räknas de lokala källorna bara in när de skriver om samma händelse som riksmedierna.

Vill du lägga till en ort till räcker det att ge källorna ett nytt `region`-värde, till exempel `"region": "Sandviken"`, så skapas fliken automatiskt.

GD och Arbetarbladet ligger på Bonnier News Locals gemensamma plattform. Flödesadressen för GD är bekräftad, medan Arbetarbladets följer samma mönster. Skriptet skriver ut hur många artiklar varje källa gav, så kontrollera i Actions-loggen efter första körningen att båda ger fler än 0.

`exclude_url_patterns` filtrerar bort sådant som inte är nyheter (sport, bostadsaffärer, trafikstörningar). `window_hours` styr hur långt bak i tiden sidan tittar.

## Om grupperingen

Skriptet grupperar artiklar efter hur lika deras rubriker och ingresser är (TF-IDF). Två spärrar minskar felaktiga ihopslagningar:

- **Siffror räknas.** Har två rubriker siffror som inte stämmer överens, till exempel olika priser, kvadratmeter eller antal, sänks likheten kraftigt. Därför hamnar inte två olika husförsäljningar ihop bara för att rubrikerna följer samma mall.
- **Lokalt hålls lokalt.** En artikel från en lokal källa slås bara ihop med riksmedier eller med en annan ort om rubrikerna är mycket lika, till exempel när samma TT-text ligger i flera tidningar.

Inställningarna finns överst i `scripts/fetch_news.py`: `THRESHOLD`, `CROSS_THRESHOLD` och `NUMBER_PENALTY`. Höj värdena för färre men säkrare grupper, sänk dem för fler.

Grupperingen är fortfarande ungefärlig och missar ibland kopplingar, särskilt för ledare och krönikor med kreativa rubriker. Vill du ha bättre gruppering och sammanfattningar som på Ground News kan nästa steg vara att låta en språkmodell gruppera rubrikerna och skriva en neutral sammanfattning per händelse. Fältet `summary` i news.json visas på sidan om det är ifyllt.

### Filtrera bort automatiska artiklar

Lokaltidningar publicerar många automatiskt skrivna notiser om husförsäljningar. Vill du slippa dem, lägg till ett mönster i `exclude_title_patterns` i `sources.json`:

```json
"exclude_title_patterns": ["(villa|radhus|kedjehus|parhus|bostadsrätt|lägenhet|fritidshus|hus)\\b.*\\b(såld|sålt|gick för)"]
```

## Bilder

Varje händelse visar en bild med källangivelse, och bilden länkar till artikeln den kommer från. Skriptet tar bilden ur RSS-flödet när den finns där (Ekot, ETC och GP har bilder i sina flöden). För händelser som saknar bild hämtar det artikelns delningsbild, alltså den bild som visas när någon delar länken. SVT:s flöde saknar till exempel bilder, så där behövs delningsbilden.

- `og_image_lookups` i `sources.json` styr hur många artikelsidor som högst kontrolleras per körning. Händelser med flest källor kommer först. Sätt värdet till `0` för att bara använda bilder ur flödena.
- Bilderna visas direkt från källornas egna servrar och sparas inte någonstans. Om en bild inte går att ladda döljs den.
- Actions-loggen visar hur många artiklar med bild varje källa gav.

## Viktigt om klassningen

Placeringen bygger på ledarsidans egen politiska beteckning och gäller inte nyhetsjournalistiken, som formellt är fristående. Stapeln visar vilka sorters källor som tar upp en händelse, inte att en enskild artikel är vinklad. Besökare kan ändra klassningen för sin egen del under fliken Källor.

Sidan visar rubriker och bilder med länk till originalartikeln, på samma sätt som andra nyhetsaggregatorer. Kontrollera gärna varje källas villkor för RSS-flödet om sidan ska användas offentligt eller kommersiellt.
