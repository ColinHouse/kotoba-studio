# Third-party notices

Kotoba Studio itself is licensed under the **GNU Affero General Public License v3.0 or later**
(see `LICENSE`). The data and libraries it uses carry their own terms, listed here.

## Dictionary data

**JMdict / JMnedict / KANJIDIC** — © Electronic Dictionary Research and Development Group
(EDRDG), licensed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

- Project page: <https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project>
- Licence: <https://www.edrdg.org/edrdg/licence.html>

Kotoba Studio downloads JMdict at runtime from
[scriptin/jmdict-simplified](https://github.com/scriptin/jmdict-simplified) (the JSON
conversion, Apache-2.0 for the conversion code, CC BY-SA 4.0 for the data itself).
The repository additionally ships a **derived subset** of JMdict used only as a test
fixture, at `backend/kotoba/data/jmdict_fixture.json`; that file is a derivative work and
is therefore also CC BY-SA 4.0.

The acknowledgement EDRDG asks for is shown to users in the app's Settings → 词典 section
and repeated in the README.

## Pitch accent data

**Kanjium** — © Uros O., licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). This is downloaded at runtime
from <https://github.com/mifunetoshiro/kanjium> only when the user installs pitch data in
Settings → 词典. No pitch data is bundled with the repository, and the acknowledgement is shown
next to the install control.

## Japanese morphological analysis

- **fugashi** (MIT) — Cython wrapper around **MeCab** (BSD 3-clause).
- **unidic-lite** (MIT packaging) bundles **UniDic**, which is distributed under a choice of
  the GPL, LGPL or BSD licence by the National Institute for Japanese Language and Linguistics.
  Kotoba Studio uses it under the BSD option.

## Spaced repetition

- **py-fsrs** (MIT), implementing the FSRS-6 algorithm by the
  [Open Spaced Repetition](https://github.com/open-spaced-repetition) project.

## Other runtime dependencies

All remaining Python and JavaScript dependencies are distributed under permissive licences
(MIT, BSD or Apache-2.0), which are compatible with the AGPL. Notable ones: FastAPI,
SQLAlchemy, Alembic, Pydantic, Uvicorn, Pillow, mss, httpx, keyring, segno, genanki,
RapidOCR (Apache-2.0), Vue, Vite, Pinia, Vue Router, Tailwind CSS and Workbox.

Optional platform OCR engines (Apple Vision, Windows.Media.Ocr) are provided by the
operating system and are not redistributed here.

## Content not covered above

`backend/kotoba/data/jp_contractions.json` and `backend/kotoba/data/homograph_traps_zh.json`
are original to this project and are covered by the project licence.
