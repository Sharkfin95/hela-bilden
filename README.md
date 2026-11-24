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

### Lokala källor

Källor med fältet `"region"` får en egen flik på sidan. Gävle finns redan med: Gefle Dagblad (liberal), Arbetarbladet (socialdemokratisk), SVT Gävleborg och P4 Gävleborg. Lokala nyheter visas bara under den lokala fliken. På första sidan räknas de lokala källorna bara in när de skriver om samma händelse som riksmedierna.

Vill du lägga till en ort till räcker det att ge källorna ett nytt `region`-värde, till exempel `"region": "Sandviken"`, så skapas fliken automatiskt.

GD och Arbetarbladet ligger på Bonnier News Locals gemensamma plattform. Flödesadressen för GD är bekräftad, medan Arbetarbladets följer samma mönster. Skriptet skriver ut hur många artiklar varje källa gav, så kontrollera i Actions-loggen efter första körningen att båda ger fler än 0.

`exclude_url_patterns` filtrerar bort sådant som inte är nyheter (sport, bostadsaffärer, trafikstörningar). `window_hours` styr hur långt bak i tiden sidan tittar.

## Om grupperingen

Skriptet grupperar artiklar efter hur lika deras rubriker och ingresser är (TF-IDF). Det är snabbt och kräver inga externa tjänster, men missar ibland kopplingar, särskilt för ledare och krönikor med kreativa rubriker. Höj eller sänk `threshold` i `cluster()` för att få större eller mindre grupper.

Vill du ha bättre gruppering och sammanfattningar som på Ground News kan nästa steg vara att låta en språkmodell gruppera rubrikerna och skriva en neutral sammanfattning per händelse. Fältet `summary` i news.json finns redan och visas på sidan om det är ifyllt.

## Viktigt om klassningen

Placeringen bygger på ledarsidans egen politiska beteckning och gäller inte nyhetsjournalistiken, som formellt är fristående. Stapeln visar vilka sorters källor som tar upp en händelse, inte att en enskild artikel är vinklad. Besökare kan ändra klassningen för sin egen del under fliken Källor.

Sidan visar bara rubriker med länk till originalartikeln, på samma sätt som andra nyhetsaggregatorer. Kontrollera gärna varje källas villkor för RSS-flödet om sidan ska användas offentligt eller kommersiellt.
