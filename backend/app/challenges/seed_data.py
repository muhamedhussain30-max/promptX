"""
Seed data — 20 challenges across all categories and difficulties.
Each challenge includes:
  - target_description (shown to players)
  - forbidden_words (shown to players)
  - required_objects / attributes / scene / relationships (hidden — for evaluation only)
"""
from app.models.challenge import Difficulty, ChallengeCategory

SEED_CHALLENGES: list[dict] = [
    # ── 1 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Construction Bear",
        "target_description": "A bear wearing a construction hat at a construction site.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["bear", "hat", "construction"],
        "required_objects": ["bear", "construction hat", "construction site"],
        "required_attributes": ["brown fur", "yellow hard hat", "orange vest"],
        "required_scene": ["construction site", "scaffolding", "machinery"],
        "required_relationships": ["bear wearing construction hat"],
    },
    # ── 2 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Piano Cat",
        "target_description": "A cat playing a keyboard instrument.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.EASY,
        "forbidden_words": ["cat", "piano", "keyboard", "playing"],
        "required_objects": ["cat", "piano", "music keys"],
        "required_attributes": ["fluffy", "paws on keys"],
        "required_scene": ["music room", "concert hall", "studio"],
        "required_relationships": ["cat seated at piano", "paws touching keys"],
    },
    # ── 3 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Mars Astronaut",
        "target_description": "An astronaut standing on a red alien planet.",
        "category": ChallengeCategory.PEOPLE,
        "difficulty": Difficulty.EASY,
        "forbidden_words": ["astronaut", "planet", "mars", "alien", "red"],
        "required_objects": ["space suit", "helmet", "rocky terrain", "alien sky"],
        "required_attributes": ["white suit", "reflective visor", "red dusty ground"],
        "required_scene": ["extraterrestrial landscape", "two moons", "red atmosphere"],
        "required_relationships": ["human figure standing on alien ground"],
    },
    # ── 4 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Drinking Elephant",
        "target_description": "An elephant drinking from a river.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.EASY,
        "forbidden_words": ["elephant", "river", "drinking", "water"],
        "required_objects": ["elephant", "river", "trunk"],
        "required_attributes": ["grey skin", "large ears", "raised trunk"],
        "required_scene": ["riverbank", "jungle", "savanna"],
        "required_relationships": ["elephant trunk lowered into water"],
    },
    # ── 5 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Mountain Castle",
        "target_description": "A medieval castle on a rocky peak.",
        "category": ChallengeCategory.ARCHITECTURE,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["castle", "medieval", "peak", "rocky", "mountain"],
        "required_objects": ["castle", "towers", "rocky cliff", "battlements"],
        "required_attributes": ["stone walls", "flags", "moat", "drawbridge"],
        "required_scene": ["rocky mountain", "dramatic sky", "stormy clouds"],
        "required_relationships": ["fortified structure perched on cliff"],
    },
    # ── 6 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Cooking Robot",
        "target_description": "A robot cooking food in a kitchen.",
        "category": ChallengeCategory.TECHNOLOGY,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["robot", "cooking", "kitchen", "food"],
        "required_objects": ["humanoid machine", "stove", "pan", "ingredients"],
        "required_attributes": ["metallic body", "glowing eyes", "apron"],
        "required_scene": ["domestic kitchen", "countertops", "utensils"],
        "required_relationships": ["mechanical figure holding cooking utensil"],
    },
    # ── 7 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Cycling Penguin",
        "target_description": "A penguin riding a bicycle.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["penguin", "bicycle", "riding", "bike"],
        "required_objects": ["penguin", "bicycle", "wheels", "handlebars"],
        "required_attributes": ["black and white bird", "two-wheeled vehicle"],
        "required_scene": ["outdoor path", "park", "icy road"],
        "required_relationships": ["bird perched on bicycle seat, feet on pedals"],
    },
    # ── 8 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Library Dragon",
        "target_description": "A dragon sleeping inside a library.",
        "category": ChallengeCategory.FANTASY,
        "difficulty": Difficulty.HARD,
        "forbidden_words": ["dragon", "library", "sleeping", "books"],
        "required_objects": ["dragon", "bookshelves", "books", "reading room"],
        "required_attributes": ["scaled creature", "wings folded", "eyes closed"],
        "required_scene": ["grand library interior", "tall shelves", "reading lamps"],
        "required_relationships": ["large reptilian beast curled asleep among shelves"],
    },
    # ── 9 ─────────────────────────────────────────────────────────────────────
    {
        "title": "Dog Driver",
        "target_description": "A dog driving a vintage car.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["dog", "car", "driving", "vintage"],
        "required_objects": ["dog", "retro automobile", "steering wheel"],
        "required_attributes": ["canine face", "paws on wheel", "old-fashioned vehicle"],
        "required_scene": ["open road", "countryside", "1950s street"],
        "required_relationships": ["canine seated in driver position of old vehicle"],
    },
    # ── 10 ────────────────────────────────────────────────────────────────────
    {
        "title": "Coffee Wizard",
        "target_description": "A wizard drinking coffee.",
        "category": ChallengeCategory.FANTASY,
        "difficulty": Difficulty.EASY,
        "forbidden_words": ["wizard", "coffee", "drinking", "magic"],
        "required_objects": ["wizard", "mug", "staff", "robes"],
        "required_attributes": ["long beard", "pointy hat", "steaming cup"],
        "required_scene": ["magical tower", "alchemy lab", "cozy study"],
        "required_relationships": ["robed sorcerer holding mug"],
    },
    # ── 11 ────────────────────────────────────────────────────────────────────
    {
        "title": "Suited Lion",
        "target_description": "A lion wearing formal clothing.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.HARD,
        "forbidden_words": ["lion", "suit", "formal", "clothing", "wearing"],
        "required_objects": ["lion", "tuxedo", "tie", "shirt"],
        "required_attributes": ["mane", "sharp teeth", "tailored jacket"],
        "required_scene": ["gala event", "office", "dinner party"],
        "required_relationships": ["feline predator dressed in business attire"],
    },
    # ── 12 ────────────────────────────────────────────────────────────────────
    {
        "title": "Artist Monkey",
        "target_description": "A monkey painting a portrait.",
        "category": ChallengeCategory.ANIMALS,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["monkey", "painting", "portrait", "canvas"],
        "required_objects": ["primate", "easel", "paintbrush", "canvas"],
        "required_attributes": ["long tail", "fur", "paint-covered hands"],
        "required_scene": ["art studio", "gallery"],
        "required_relationships": ["ape holding brush in front of canvas"],
    },
    # ── 13 ────────────────────────────────────────────────────────────────────
    {
        "title": "Desert Spaceship",
        "target_description": "A spaceship landing in a desert.",
        "category": ChallengeCategory.TECHNOLOGY,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["spaceship", "desert", "landing", "spacecraft"],
        "required_objects": ["spacecraft", "sand dunes", "landing struts", "exhaust"],
        "required_attributes": ["metallic hull", "thrusters firing", "vast sandy landscape"],
        "required_scene": ["arid desert", "clear sky", "dunes"],
        "required_relationships": ["vessel descending toward sandy terrain"],
    },
    # ── 14 ────────────────────────────────────────────────────────────────────
    {
        "title": "Reading Mermaid",
        "target_description": "A mermaid reading a book underwater.",
        "category": ChallengeCategory.FANTASY,
        "difficulty": Difficulty.HARD,
        "forbidden_words": ["mermaid", "book", "reading", "underwater"],
        "required_objects": ["mermaid", "book", "fish tail", "ocean floor"],
        "required_attributes": ["human upper body", "fish lower body", "open book"],
        "required_scene": ["ocean floor", "coral reef", "kelp forest"],
        "required_relationships": ["sea creature holding open book in submerged setting"],
    },
    # ── 15 ────────────────────────────────────────────────────────────────────
    {
        "title": "Cherry Blossom Samurai",
        "target_description": "A samurai standing beneath cherry blossoms.",
        "category": ChallengeCategory.PEOPLE,
        "difficulty": Difficulty.HARD,
        "forbidden_words": ["samurai", "cherry", "blossom", "standing"],
        "required_objects": ["samurai warrior", "katana", "cherry blossom tree", "petals"],
        "required_attributes": ["armour", "top-knot", "falling pink petals"],
        "required_scene": ["Japanese garden", "sakura trees", "spring"],
        "required_relationships": ["armoured warrior beneath flowering tree"],
    },
    # ── 16 ────────────────────────────────────────────────────────────────────
    {
        "title": "Village Turtle",
        "target_description": "A giant turtle carrying a village on its back.",
        "category": ChallengeCategory.SURREAL,
        "difficulty": Difficulty.EXPERT,
        "forbidden_words": ["turtle", "village", "carrying", "back", "giant"],
        "required_objects": ["giant tortoise", "houses", "trees", "shell platform"],
        "required_attributes": ["enormous shell", "small buildings on top", "walking through water"],
        "required_scene": ["ocean", "sky", "miniature settlement on shell"],
        "required_relationships": ["massive reptile bearing a settlement on its shell"],
    },
    # ── 17 ────────────────────────────────────────────────────────────────────
    {
        "title": "Detective Fox",
        "target_description": "A fox working as a detective.",
        "category": ChallengeCategory.FANTASY,
        "difficulty": Difficulty.MEDIUM,
        "forbidden_words": ["fox", "detective", "working", "investigation"],
        "required_objects": ["fox", "magnifying glass", "trench coat", "hat"],
        "required_attributes": ["red fur", "pointed snout", "noir outfit"],
        "required_scene": ["city street", "dark alley", "detective's office"],
        "required_relationships": ["cunning canine in detective attire examining clues"],
    },
    # ── 18 ────────────────────────────────────────────────────────────────────
    {
        "title": "Giant Pizza Chef",
        "target_description": "A chef preparing an enormous pizza.",
        "category": ChallengeCategory.FOOD,
        "difficulty": Difficulty.EASY,
        "forbidden_words": ["chef", "pizza", "enormous", "huge", "giant", "preparing"],
        "required_objects": ["chef", "oversized pizza", "toppings", "pizza peel"],
        "required_attributes": ["white apron", "tall hat", "generous toppings"],
        "required_scene": ["Italian restaurant kitchen", "brick oven"],
        "required_relationships": ["cook stretching dough for enormous circular pie"],
    },
    # ── 19 ────────────────────────────────────────────────────────────────────
    {
        "title": "Viking in Ice",
        "target_description": "A Viking sailing through icy waters.",
        "category": ChallengeCategory.PEOPLE,
        "difficulty": Difficulty.HARD,
        "forbidden_words": ["viking", "sailing", "icy", "ice", "water"],
        "required_objects": ["Viking", "longship", "icebergs", "oars"],
        "required_attributes": ["horned helmet", "fur cloak", "carved wooden vessel"],
        "required_scene": ["arctic sea", "floating ice chunks", "grey sky"],
        "required_relationships": ["Norse warrior aboard longboat navigating frozen sea"],
    },
    # ── 20 ────────────────────────────────────────────────────────────────────
    {
        "title": "Shopping Alien",
        "target_description": "An alien shopping in a supermarket.",
        "category": ChallengeCategory.SURREAL,
        "difficulty": Difficulty.EXPERT,
        "forbidden_words": ["alien", "shopping", "supermarket", "store", "grocery"],
        "required_objects": ["extraterrestrial being", "shopping cart", "supermarket shelves", "products"],
        "required_attributes": ["green skin", "large eyes", "tentacles", "normal human shoppers nearby"],
        "required_scene": ["supermarket interior", "fluorescent lighting", "product aisles"],
        "required_relationships": ["otherworldly creature casually pushing shopping cart"],
    },
]
