"""Author the project's labelled prompt data (team-written, templated, seeded).

Run:  python ml/data/build_dataset.py        (rewrites every CSV in ml/data/)

HOW THE DATA IS PRODUCED (read this before trusting any number)
---------------------------------------------------------------
The prompts are NOT collected from real users. They are written by the team as
hand-written vocabulary (who the site is for, how a section is described, names,
cities, colours) combined with hand-written sentence frames, optional filler
sentences and optional typos. Every label is derived from the *content that was
written into the prompt* by an explicit rule - never from a model:

  site_type  = the type whose noun phrase was put into the prompt
  sections   = (BASE sections of that site type  U  sections the prompt asks for
                 - sections the prompt says to leave out)  U  navbar, hero, footer
               with the exception of "only/just/nothing but ..." prompts, where the
               base set is dropped and only the requested sections remain.

Two disjoint authoring "styles" are used:
  * TRAIN style  -> prompts.csv (+ prompts_train/val/test.csv, a stratified 70/15/15 split)
  * EVAL style   -> eval_prompts.csv: different sentence frames, different noun
    phrases, different section wording, different names/cities, plus hand-labelled
    harder / ambiguous prompts and prompts with no section hints. It is never used
    for training, model selection or any threshold.
Because both styles come from the same authors, measured accuracy is optimistic
for real users' prompts. ood_probe.csv is a small hand-written list of unrelated,
nonsense, very short and non-English inputs used to measure the low-confidence check.
"""
import csv
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20251003
SECTIONS = ["navbar", "hero", "about", "features", "gallery", "pricing", "testimonials", "faq",
            "contact", "footer"]
MANDATORY = ["navbar", "hero", "footer"]
CHOOSABLE = ["about", "features", "gallery", "pricing", "testimonials", "faq", "contact"]
SITE_TYPES = ["portfolio", "restaurant", "small_business", "education", "blog", "nonprofit"]

# Sections every site of this type gets when the prompt does not say otherwise.
BASE = {
    "portfolio": ["about", "features", "gallery", "contact"],
    "restaurant": ["about", "features", "gallery", "contact"],
    "small_business": ["about", "features", "testimonials", "contact"],
    "education": ["about", "features", "faq", "contact"],
    "blog": ["about", "features", "contact"],
    "nonprofit": ["about", "features", "testimonials", "contact"],
}

# ----------------------------------------------------------------------------- vocabulary
NOUNS = {
    "train": {
        "portfolio": ["freelance photographer", "graphic designer", "web developer", "illustrator",
                      "architect", "UX designer", "video editor", "fashion designer", "motion artist",
                      "copywriter", "portfolio", "personal portfolio", "3D artist", "animator", "sculptor",
                      "art director", "product designer", "makeup artist", "wedding photographer",
                      "songwriter", "musician", "DJ", "creative director", "software engineer",
                      "journalist", "filmmaker", "ceramics artist", "potter", "cartoonist", "CV website",
                      "design studio portfolio"],
        "restaurant": ["bakery", "cafe", "pizzeria", "sushi bar", "bistro", "food truck", "coffee shop",
                       "burger joint", "ice cream parlour", "taco stand", "restaurant", "dessert bar",
                       "trattoria", "noodle house", "curry house", "bbq grill", "gastropub",
                       "sandwich shop", "donut shop", "creperie", "bagel shop", "seafood restaurant",
                       "wine bar", "pancake house", "dumpling house", "tapas bar", "salad bar",
                       "pastry shop", "chocolate shop", "smoothie bar", "fish and chip shop", "deli",
                       "cocktail bar"],
        "small_business": ["plumbing company", "hair salon", "car repair shop", "cleaning service",
                           "florist", "accounting firm", "landscaping business", "pet grooming shop",
                           "bike store", "dental clinic", "law office", "small business", "electrician",
                           "barber shop", "nail salon", "auto garage", "real estate agency",
                           "travel agency", "gym", "yoga studio", "massage clinic", "veterinary clinic",
                           "furniture store", "bookshop", "hardware store", "tailor", "dry cleaner",
                           "taxi company", "insurance agency", "window cleaning business", "tree surgeon",
                           "painting contractor", "consulting firm"],
        "education": ["online course", "coding bootcamp", "language school", "maths tutoring service",
                      "music school", "driving school", "university department", "kindergarten",
                      "science club", "tutoring academy", "school", "training institute", "college",
                      "summer camp", "homeschool group", "piano lessons", "swimming school", "reading club",
                      "nursery school", "vocational college", "test prep course", "spanish classes",
                      "maths club", "coding club", "online academy", "workshop series", "flight school",
                      "cooking school", "teacher training programme"],
        "blog": ["travel blog", "food blog", "tech blog", "fitness blog", "personal journal",
                 "parenting blog", "book review blog", "fashion blog", "finance blog", "gaming blog",
                 "blog", "writing blog", "lifestyle blog", "music blog", "sports blog", "minimalism blog",
                 "vlog", "newsletter", "podcast site", "science blog", "history blog", "politics blog",
                 "wellness blog", "career blog", "pet blog", "home decor blog", "running diary",
                 "daily diary", "opinion blog", "art blog", "student blog"],
        "nonprofit": ["animal shelter", "charity", "food bank", "environmental group", "community centre",
                      "youth foundation", "volunteer organisation", "wildlife trust",
                      "neighbourhood association", "relief fund", "non-profit", "NGO", "soup kitchen",
                      "rescue centre", "women's shelter", "tree planting group", "mutual aid network",
                      "health charity", "education charity", "cultural society", "heritage trust",
                      "church group", "alumni association", "scholarship fund", "veterans association",
                      "orphanage", "ocean cleanup group", "community garden", "foundation",
                      "cancer research charity"],
    },
    "eval": {
        "portfolio": ["tattoo artist", "game developer", "interior stylist", "sound engineer",
                      "data scientist", "jewelry maker", "landscape painter", "voice actor"],
        "restaurant": ["ramen shop", "tea house", "steakhouse", "vegan kitchen", "brewery taproom",
                       "catering service", "juice bar", "family diner"],
        "small_business": ["locksmith", "roofing contractor", "bookkeeping practice", "laundromat",
                           "handyman service", "moving company", "pest control firm", "print shop"],
        "education": ["dance academy", "exam coaching centre", "preschool", "robotics workshop",
                      "art school", "chess academy", "adult literacy programme", "tutoring centre"],
        "blog": ["gardening blog", "cycling blog", "news digest", "poetry blog", "movie review site",
                 "DIY crafts blog", "mental health blog", "photography journal"],
        "nonprofit": ["refugee support group", "library friends society", "clean water initiative",
                      "literacy charity", "homeless outreach", "park conservancy", "scouts troop",
                      "disaster relief group"],
    },
}

SITE_WORDS = {
    "train": ["website", "site", "web page", "landing page", "homepage", "web presence"],
    "eval": ["online home", "one-page site", "page on the web", "digital presence", "web space"],
}
ADJ = {
    "train": ["modern", "clean", "simple", "professional", "friendly", "elegant", "colourful",
              "minimal", "responsive", "bold", "playful", "warm", "stylish", "fresh"],
    "eval": ["sleek", "welcoming", "polished", "lightweight", "vibrant", "calm", "sharp", "cosy"],
}
NAMES = {
    "train": ["Sweet Crumbs", "Blue Harbor", "Maple Lane", "Pixel Nest", "Green Valley", "Urban Spoon",
              "Bright Minds", "Paw Palace", "Iron Oak", "Sunny Side", "Little Lantern", "Nova Studio",
              "Golden Whisk", "Quiet Pines", "Rapid Fix", "Cedar & Co", "Lotus Works", "Red Barn",
              "Stone Bridge", "Happy Tails", "Ink and Ivory", "Daily Brew", "Summit Learning",
              "Willow Creek", "Atlas Design", "Harvest Table", "Open Door", "Clear Path", "Mango Tree",
              "Silver Fox"],
    "eval": ["Copper Kettle", "Juniper Hill", "Tidewater", "Lumen Labs", "Fern & Fable", "Northwind",
             "Orchid Row", "Kindle House", "Brass Anchor", "Marigold", "Harbor Light", "Thistle Co",
             "Saffron Road", "Moonlit Pages", "Basil & Bean", "Riverbend", "Echo Valley", "Sparrow Lane",
             "Wild Meadow", "Pebble Street"],
}
CITIES = {
    "train": ["Austin", "Seattle", "Denver", "Boston", "Portland", "Chicago", "Miami", "Toronto",
              "London", "Dublin"],
    "eval": ["Leeds", "Madison", "Tucson", "Halifax", "Bristol", "Raleigh", "Perth", "Cork"],
}
COLOURS = ["blue", "green", "orange", "purple", "pink", "red", "teal", "navy", "brown", "yellow",
           "black and white", "warm orange and brown", "soft green", "deep blue", "dark grey"]
TONES = ["elegant", "playful", "minimal", "bold", "professional", "friendly", "dark", "calm"]
FILLER = {
    "train": ["We have been around since 2015 and love what we do.",
              "It should look good on phones too.",
              "Our customers keep asking for a proper site.",
              "I am not technical at all.",
              "Keep it easy to read."],
    "eval": ["Nothing fancy, we just want people to find us.",
             "Most of our visitors will be on mobile.",
             "A friend suggested we get something online.",
             "Honestly we have no idea where to start.",
             "It needs to feel trustworthy."],
}

# How a section can be asked for. "features" depends on the site type.
PHRASES = {
    "train": {
        "about": ["an about section", "an about us page", "a short bio", "our story",
                  "a section about who we are", "an about me section", "info about us"],
        "gallery": ["a photo gallery", "a gallery", "pictures", "an image gallery", "photos",
                    "a picture grid", "a showcase of photos"],
        "pricing": ["pricing", "a pricing table", "our prices", "price plans", "packages and rates",
                    "membership plans", "fees"],
        "testimonials": ["testimonials", "customer reviews", "reviews", "client feedback",
                         "what people say about us", "a testimonials section", "student reviews",
                         "student feedback", "customer testimonials", "reviews from our clients",
                         "guest reviews", "parent reviews", "feedback from customers",
                         "ratings and reviews", "member reviews"],
        "faq": ["an FAQ", "a FAQ section", "common questions", "frequently asked questions",
                "questions and answers"],
        "contact": ["a contact form", "contact details", "a contact section", "a way to get in touch",
                    "a contact us page", "location and contact info"],
        "features": {
            "portfolio": ["my projects", "a projects section", "case studies", "a showcase of my work",
                          "selected works"],
            "restaurant": ["a menu", "a menu section", "our dishes", "a list of our specials",
                           "the food menu"],
            "small_business": ["a services list", "our services", "a section for what we offer",
                               "service offerings"],
            "education": ["course listings", "a list of courses", "our programs", "a curriculum section",
                          "the class schedule"],
            "blog": ["featured posts", "a list of recent articles", "latest posts", "a posts section",
                     "article highlights"],
            "nonprofit": ["our programs", "a list of causes", "what we do", "our initiatives",
                          "campaign highlights"],
        },
    },
    "eval": {
        "about": ["background information", "a who-are-we blurb", "the story behind the project",
                  "a bit about me", "a company profile"],
        "gallery": ["a visual showcase", "snapshots", "a grid of images", "a photo wall",
                    "visual highlights"],
        "pricing": ["what it costs", "rates", "a cost breakdown", "subscription tiers", "ticket prices"],
        "testimonials": ["quotes from happy customers", "success stories", "user feedback",
                         "endorsements", "kind words from visitors"],
        "faq": ["a help section with common queries", "Q&A", "answers to typical questions",
                "a questions page"],
        "contact": ["ways to reach us", "an enquiry form", "a message form",
                    "email and phone details", "a get-in-touch area"],
        "features": {
            "portfolio": ["recent work", "a work samples area", "client projects", "my best pieces"],
            "restaurant": ["our food and drink list", "the dishes we serve", "a menu board",
                           "daily specials"],
            "small_business": ["the jobs we do", "a list of what we handle", "our service range",
                               "our offerings"],
            "education": ["the lessons we run", "available classes", "our teaching programmes",
                          "what students learn"],
            "blog": ["newest entries", "recent stories", "a list of my writing", "top articles"],
            "nonprofit": ["the work we do", "ongoing projects", "how we help", "our causes"],
        },
    },
}
NEGATE = {
    "train": ["no {x}", "without {x}", "don't add {x}", "skip {x}"],
    "eval": ["leave out {x}", "we do not need {x}", "drop {x}", "{x} is not wanted"],
}
ONLY = {
    "train": ["only {x}", "just {x}", "a tiny site with just {x}"],
    "eval": ["nothing but {x}", "keep it to {x}", "strictly {x}"],
}

FRAMES = {
    "train": [
        "Create a {adj} {site} for {npa}{name} with {secs}.",
        "I need a {adj} {site} for {npa}{name}. Include {secs}.",
        "Build me {np_a} {site}{name}, it should have {secs}.",
        "make a {site} for {npa}{name}; add {secs}",
        "{np_cap} {site}{name}: {secs}",
        "Can you generate a {adj} {site} for {npa}{name}? I want {secs}.",
        "Please design a {site} for {npa}{name} that shows {secs}.",
        "{np_cap} {site}, {adj} look, with {secs}{name}",
        "I want a {site} for {npa}{name} - {secs}.",
        "generate website {np}{name} {secs}",
    ],
    "eval": [
        "We run {np_a}{name} and want {site_a}: {secs}.",
        "Looking for a {adj} {site} to represent {np_a}{name}. It needs {secs}.",
        "{site} idea: {np}{name}, featuring {secs}",
        "My friend and I started {np_a}; set up something {adj} with {secs}{name}.",
        "Design something {adj} for {np_a}{name} - {secs} would be great.",
        "Put together {site_a} for {np_a}. Must show {secs}{name}.",
        "Hello! Could you help me with {site_a} for {np_a}{name}? Ideally {secs}.",
        "{secs}, that is what visitors of our {np} {site}{name} should see.",
    ],
}
NOHINT = {
    "train": [
        "Create a {adj} {site} for {npa}{name}.",
        "I need a {site} for {npa}{name}",
        "build a website for my {np}{name}",
        "{np_cap} {site}{name}",
        "make me a {adj} {site} for {npa}",
        "website for {npa}{name}",
    ],
    "eval": [
        "I'd like {site_a} for {np_a}{name}.",
        "Something {adj} for {np_a}{name}, nothing more specific yet.",
        "We just opened {np_a}; help us get {site}{name}.",
        "Set up a {site} for our {np}{name}.",
        "Can you do something for {np_a}{name}?",
    ],
}
NAME_FORMS = {
    "train": [" called {n}", " named {n}", ' "{n}"', " called \"{n}\"", ", its name is {n}"],
    "eval": [" - the name is {n}", ' (called "{n}")', ", {n}", " named {n}"],
}

# Hand-labelled harder / ambiguous / awkward held-out prompts (eval only). The label is the
# prompt's *primary purpose* as written by the team.
MANUAL_EVAL = [
    ("a place where I post my recipes and write about cooking", "blog", ["about", "features", "contact"]),
    ("online lessons for people who want to learn guitar with a price list", "education",
     ["about", "features", "faq", "contact", "pricing"]),
    ("we collect donations for stray cats and want volunteers to sign up", "nonprofit",
     ["about", "features", "testimonials", "contact"]),
    ("my photography work, mostly weddings, with a gallery and a contact form", "portfolio",
     ["about", "features", "gallery", "contact"]),
    ("family run pizza place with prices and photos of our oven", "restaurant",
     ["about", "features", "gallery", "contact", "pricing"]),
    ("a small web design agency offering packages, with reviews from past clients", "small_business",
     ["about", "features", "testimonials", "contact", "pricing"]),
    ("site for my sourdough bread newsletter and articles", "blog", ["about", "features", "contact"]),
    ("tutor for kids, show our class fees and frequently asked questions", "education",
     ["about", "features", "faq", "contact", "pricing"]),
    ("homepage for the local football fundraiser, just our story and how to contact us", "nonprofit",
     ["about", "contact"]),
    ("carpenter, show finished furniture pictures and what we charge", "small_business",
     ["about", "features", "testimonials", "contact", "gallery", "pricing"]),
    ("developer resume with side projects", "portfolio", ["about", "features", "gallery", "contact"]),
    ("coffee cart, only a menu and a way to find us", "restaurant", ["features", "contact"]),
    ("I want people to read my travel stories and see my photos", "blog",
     ["about", "features", "contact", "gallery"]),
    ("school science fair page with questions parents ask", "education",
     ["about", "features", "faq", "contact"]),
    ("something for my business", "small_business", ["about", "features", "testimonials", "contact"]),
    ("a site", "small_business", ["about", "features", "testimonials", "contact"]),
    ("our charity runs a marathon every year, we need a page for it", "nonprofit",
     ["about", "features", "testimonials", "contact"]),
    ("music lessons with a gallery of recitals and reviews from parents", "education",
     ["about", "features", "faq", "contact", "gallery", "testimonials"]),
    ("bistro with daily specials, customer reviews and no gallery", "restaurant",
     ["about", "features", "contact", "testimonials"]),
    ("an artist showing paintings with a price list", "portfolio",
     ["about", "features", "gallery", "contact", "pricing"]),
]

OOD_PROBES = [
    ("asdf qwerty", "gibberish"), ("zxcv bnm", "gibberish"), ("kjhgf lkjh poiuy", "gibberish"),
    ("!!!???", "gibberish"), ("12345 67890", "gibberish"), ("lorem ipsum dolor sit amet", "gibberish"),
    ("qwertyuiop asdfghjkl", "gibberish"), ("aaaa bbbb cccc", "gibberish"),
    ("what is the capital of France", "unrelated"), ("how do I reset my router password", "unrelated"),
    ("write me a poem about autumn", "unrelated"), ("who won the world cup in 2018", "unrelated"),
    ("translate hello into Spanish", "unrelated"), ("book a flight to London tomorrow", "unrelated"),
    ("explain how photosynthesis works", "unrelated"), ("what time is it in Tokyo", "unrelated"),
    ("solve x squared plus two x equals eight", "unrelated"), ("my laptop is making a strange noise", "unrelated"),
    ("hi", "too short"), ("site", "too short"), ("a", "too short"), ("make", "too short"), ("ok", "too short"),
    ("crea un sitio web para mi panaderia con menu y galeria", "non-English"),
    ("ich brauche eine webseite fuer mein restaurant", "non-English"),
    ("creer un site pour mon cafe avec une carte", "non-English"),
    ("我想要一个网站", "non-English"),
    ("मुझे एक वेबसाइट चाहिए", "non-English"),
    ("quiero una pagina para mi escuela de musica", "non-English"),
    ("SELECT * FROM users;", "code"), ("def main(): pass", "code"),
]


# ----------------------------------------------------------------------------- generator
def a_an(phrase):
    return ("an " if phrase[0].lower() in "aeiou" else "a ") + phrase


def cap(s):
    return s[0].upper() + s[1:]


def join_list(rng, items):
    if len(items) == 1:
        return items[0]
    style = rng.choice(["and", "and", "oxford", "plus", "comma"])
    if style == "plus":
        return " plus ".join(items) if len(items) == 2 else ", ".join(items[:-1]) + " plus " + items[-1]
    if style == "comma":
        return ", ".join(items)
    if style == "oxford" and len(items) > 2:
        return ", ".join(items[:-1]) + ", and " + items[-1]
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 2 else " and ".join(items)


def typo(rng, text, p_word=0.12):
    out = []
    for w in text.split(" "):
        core = re.sub(r"[^A-Za-z]", "", w)
        if len(core) >= 5 and rng.random() < p_word:
            i = rng.randrange(1, len(w) - 2)
            kind = rng.choice(["swap", "drop", "dup"])
            if kind == "swap":
                w = w[:i] + w[i + 1] + w[i] + w[i + 2:]
            elif kind == "drop":
                w = w[:i] + w[i + 1:]
            else:
                w = w[:i] + w[i] + w[i:]
        out.append(w)
    return " ".join(out)


def make_prompt(rng, style, site_type):
    """Returns (text, sections) for one generated prompt. Labels follow the rules in the module doc."""
    np_ = rng.choice(NOUNS[style][site_type])
    ph = PHRASES[style]
    base = list(BASE[site_type])
    mode = rng.choices(["nohint", "mention", "only", "negate"], weights=[18, 58, 12, 12])[0]
    mentioned, negated, only = [], [], False
    if mode == "mention":
        mentioned = rng.sample(CHOOSABLE, rng.choice([1, 2, 2, 3, 3, 4]))
    elif mode == "only":
        only = True
        mentioned = rng.sample(CHOOSABLE, rng.choice([2, 2, 3]))
    elif mode == "negate":
        negated = rng.sample(base, 1)
        pool = [s for s in CHOOSABLE if s not in negated]
        mentioned = rng.sample(pool, rng.choice([1, 2]))

    def phrase(sec):
        if sec == "features":
            return rng.choice(ph["features"][site_type])
        return rng.choice(ph[sec])

    adj = rng.choice(ADJ[style])
    site = rng.choice(SITE_WORDS[style])
    name = ""
    if rng.random() < 0.45:
        name = rng.choice(NAME_FORMS[style]).format(n=rng.choice(NAMES[style]))
    npa = a_an(np_) if rng.random() < 0.75 else np_
    fmt = dict(adj=adj, site=site, site_a=a_an(site), np=np_, npa=npa, np_a=a_an(np_), np_cap=cap(np_), name=name)
    if mode == "nohint":
        text = rng.choice(NOHINT[style]).format(**fmt)
        sections = set(base)
    else:
        items = [phrase(s) for s in mentioned]
        rng.shuffle(items)
        secs = join_list(rng, items)
        if only:
            secs = rng.choice(ONLY[style]).format(x=secs)
        if negated:
            neg = rng.choice(NEGATE[style]).format(x=re.sub(r"^(a|an|the|our|my)\s+", "", phrase(negated[0])))
            secs = secs + (", " if rng.random() < 0.5 else " but ") + neg
        text = rng.choice(FRAMES[style]).format(secs=secs, **fmt)
        sections = set(mentioned) if only else (set(base) | set(mentioned))
        sections -= set(negated)
    # optional extras: colours, tone, city, filler sentence
    extra = []
    r = rng.random()
    if r < 0.18:
        extra.append(f"Use {rng.choice(COLOURS)} colours.")
    elif r < 0.30:
        extra.append(f"I'd like it to feel {rng.choice(TONES)}.")
    if rng.random() < 0.15:
        extra.append(f"We are based in {rng.choice(CITIES[style])}.")
    if rng.random() < 0.20:
        extra.append(rng.choice(FILLER[style]))
    if extra:
        if not text.rstrip().endswith((".", "?", "!")):
            text = text.rstrip() + "."
        text = text.rstrip() + " " + " ".join(extra)
        if rng.random() < 0.25:                       # filler first instead of last
            text = " ".join(extra) + " " + text.replace(" ".join(extra), "").strip()
    if not text.rstrip().endswith((".", "?", "!")) and rng.random() < 0.4:
        text = text.rstrip() + "."
    if rng.random() < 0.15:
        text = text.lower()
    if rng.random() < 0.18:
        text = typo(rng, text)
    sections |= set(MANDATORY)
    return re.sub(r"\s+", " ", text).strip(), [s for s in SECTIONS if s in sections]


def generate(rng, style, n_per_type):
    seen, rows = set(), []
    for t in SITE_TYPES:
        count = 0
        while count < n_per_type:
            text, secs = make_prompt(rng, style, t)
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append((text, t, "|".join(secs)))
            count += 1
    return rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def stratified_split(rng, rows, fr=(0.70, 0.15, 0.15)):
    by_type = {}
    for r in rows:
        by_type.setdefault(r[1], []).append(r)
    parts = ([], [], [])
    for t in SITE_TYPES:
        items = by_type[t][:]
        rng.shuffle(items)
        a = int(round(len(items) * fr[0]))
        b = a + int(round(len(items) * fr[1]))
        parts[0].extend(items[:a])
        parts[1].extend(items[a:b])
        parts[2].extend(items[b:])
    for p in parts:
        rng.shuffle(p)
    return parts


def main():
    rng = random.Random(SEED)
    train_rows = generate(rng, "train", 200)                     # 1200 prompts
    rng.shuffle(train_rows)
    eval_rows = generate(random.Random(SEED + 1), "eval", 17)    # 102 generated
    eval_text = {r[0].lower() for r in eval_rows}
    for text, t, secs in MANUAL_EVAL:
        sec = sorted(set(secs) | set(MANDATORY), key=SECTIONS.index)
        assert text.lower() not in eval_text
        eval_rows.append((text, t, "|".join(sec)))
    random.Random(SEED + 2).shuffle(eval_rows)

    # leakage guards: no shared text, no shared noun phrase
    assert not ({r[0].lower() for r in train_rows} & {r[0].lower() for r in eval_rows})
    tn = {n for v in NOUNS["train"].values() for n in v}
    en = {n for v in NOUNS["eval"].values() for n in v}
    assert not (tn & en)
    assert len(train_rows) >= 500 and len(eval_rows) >= 80

    hdr = ["text", "site_type", "sections"]
    write_csv(os.path.join(HERE, "prompts.csv"), hdr, train_rows)
    tr, va, te = stratified_split(random.Random(SEED + 3), train_rows)
    write_csv(os.path.join(HERE, "prompts_train.csv"), hdr, tr)
    write_csv(os.path.join(HERE, "prompts_val.csv"), hdr, va)
    write_csv(os.path.join(HERE, "prompts_test.csv"), hdr, te)
    write_csv(os.path.join(HERE, "eval_prompts.csv"), hdr, eval_rows)
    write_csv(os.path.join(HERE, "ood_probe.csv"), ["text", "kind"], OOD_PROBES)
    print(f"prompts.csv {len(train_rows)} | train {len(tr)} val {len(va)} test {len(te)} | "
          f"eval_prompts.csv {len(eval_rows)} | ood_probe.csv {len(OOD_PROBES)}")


if __name__ == "__main__":
    main()
