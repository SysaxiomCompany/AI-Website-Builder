from app.preprocess import MAX_PROMPT_CHARS, normalize_prompt
from app.slots import extract_slots


def test_normalize_collapses_whitespace_and_controls():
    assert normalize_prompt("  a \n\t b \x00 c  ") == "a b c"
    assert normalize_prompt(None) == ""
    assert normalize_prompt("ＡＢ") == "AB"          # NFKC
    assert MAX_PROMPT_CHARS == 1000


# ---- names
def test_name_quoted():
    assert extract_slots('a site for my cafe "Blue Door Cafe" with a menu')["name"] == "Blue Door Cafe"
    assert extract_slots("a site for my cafe “Blue Door” please")["name"] == "Blue Door"


def test_name_called_and_named():
    assert extract_slots("a bakery website called Sweet Crumbs with a menu")["name"] == "Sweet Crumbs"
    assert extract_slots("portfolio for a designer named Maya Lin, dark colors")["name"] == "Maya Lin"
    assert extract_slots("the name is Green Valley and we want a gallery")["name"] == "Green Valley"


def test_name_with_ampersand_and_lowercase():
    assert extract_slots("a site called Cedar & Co with services")["name"] == "Cedar & Co"
    assert extract_slots("a site called daily brew with a menu")["name"] == "Daily Brew"


def test_quoted_tagline_is_not_the_name():
    s = extract_slots('a cafe called Brew Haus with the tagline "Coffee that wakes you up"')
    assert s["name"] == "Brew Haus" and s["tagline"] == "Coffee that wakes you up"


# ---- contact details
def test_email_and_phone():
    s = extract_slots("contact me at jane.doe+site@example.co.uk or call +1 (555) 123-4567 anytime")
    assert s["email"] == "jane.doe+site@example.co.uk"
    assert s["phone"] == "+1 (555) 123-4567"


def test_phone_not_confused_with_year_or_email_digits():
    s = extract_slots("founded in 2015, email user12345678@example.com")
    assert s["phone"] == ""


def test_location_cues():
    assert extract_slots("a shop based in Austin Texas with pricing")["location"].startswith("Austin")
    assert extract_slots("we are located in denver")["location"] == "Denver"
    assert extract_slots("a bakery in Seattle")["location"] == "Seattle"


# ---- colours and tones
def test_colors_and_tones():
    s = extract_slots("an elegant, minimal site in navy and gold")
    assert s["colors"] == ["navy", "gold"]
    assert s["tones"] == ["elegant", "minimal"]


def test_prompt_without_any_slots():
    s = extract_slots("a website for my business")
    assert s == {"name": "", "tagline": "", "email": "", "phone": "", "location": "", "colors": [], "tones": []}
