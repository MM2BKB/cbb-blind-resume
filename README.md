# CBB Blind Resume

Rank college basketball teams from anonymous resumes, three at a time.

The site rebuilds itself twice a day (about 7 AM and 11 PM Eastern):

- `scripts/update.py` downloads Bart Torvik's ratings and every final score from the ESPN scoreboard since Nov 2.
- `scripts/build.py` turns `template.html` and the files in `data/` into the page.
- `.github/workflows/update.yml` runs both and publishes the result with GitHub Pages.

## Files

| File | What it is |
| --- | --- |
| `template.html` | The page itself. Edit this to change how the site looks or works. |
| `data/teams.csv` | Ratings: name, conference, record, adjusted offense, adjusted defense, Barthag, tempo, WAB. |
| `data/games.csv` | Final scores: date, team, opponent, scores, game id. |
| `data/unmatched.txt` | School names from ESPN that could not be matched to a Torvik name. Add them to `ALIAS` in `scripts/update.py`. |
| `data/meta.json` | When the last update ran and whether the Torvik download worked. |

## If something goes wrong

- If the Torvik download is blocked or changes format, the site keeps its last ratings and the run still succeeds. Check `data/meta.json` (`torvik_ok`).
- To run an update by hand, open the Actions tab, choose "Update data and publish", and click Run workflow.

Ratings: barttorvik.com. Scores: ESPN. Check each site's terms before using this publicly at scale.
