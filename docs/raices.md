# 🌳 Cacique Raíces · la enciclopedia de la familia

> So the grandchildren know where they come from: every person of the family has a page that reads like an
> encyclopedia article, written by the family itself, and a life journal that keeps growing.
> *Para que los nietos sepan de dónde vienen.*

## What's in it
| Page | What it shows |
|---|---|
| Family home | Everyone by generation (ancestors → grandchildren), the family name, motto and crest, "Today in the family" (birthdays, anniversaries, "X years ago") |
| A person's page | Photo and fact box (born, studies, work, spouse, parents, children), their saying, the story in 8 sections, gallery, **life journal** |
| Timeline | Every birth, date and journal entry of the whole family, by year |
| Generations | Who belongs to which generation, with spouse and children |
| The book | All the pages in one, ready to print or save as PDF |

**The 8 guided sections** (each comes with questions that help to write): childhood and roots · education · work ·
love and family · achievements and sacrifices · talents and favorites · faith and values · **for my grandchildren**.
Ancestors who already passed get pages too, written by the family.

## Privacy
- Everything stays in the house, on the **Vault drive** (`Vault/raices`) when it's connected.
- **Family code:** asked once per device, so visitors on the Wi-Fi can't read the pages. Not in the Invitado view.
- **Each person edits only their own page** with their own PIN. The admin can help with any page.
- Photos are resized and **lose their hidden location data (GPS)** when uploaded. Nothing is ever erased from the
  disk by the "remove" buttons for people (they're only hidden).

## Set it up
1. `cd ~/elcaciquedeck && git pull`
2. `bash ~/elcaciquedeck/raices/setup-raices.sh`
3. Open `http://<server>:8098/admin` (password: `tools/show-passwords.sh --other`):
   family name, motto, crest, **family code** → add each person (generation + PIN) → set spouse / parents / children.
4. Each person opens their page → **Editar** → PIN → answers the questions, adds photos and journal entries.

## Later
- Make the family book a **Kiwix book** so it also appears in CaciqueLibrary.
- Let the home's AI (CaciqueGuía) read the pages to answer "tell me about my great-grandfather".
- Cacique Diario can show "Today in the family" on the frames and the front page.
