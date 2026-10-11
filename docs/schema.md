# Schéma de la base — cannabis-data-fusion

8 tables relationnelles. Clés primaires UUID, clés étrangères vers `cultivars.cultivar_id`.
Conventions : `verified` = pedigree confirmé par ≥2 sources ; chaque ligne porte sa source (`source`, `source_url`) pour le badge par source.

```sql
-- 1. BREEDERS
CREATE TABLE breeders (
    breeder_id   UUID PRIMARY KEY,
    breeder_name TEXT NOT NULL,
    country      TEXT,
    year_founded INTEGER,
    website      TEXT
);

-- 2. CULTIVARS
CREATE TABLE cultivars (
    cultivar_id   UUID PRIMARY KEY,
    cultivar_name TEXT NOT NULL,
    breeder_id    UUID REFERENCES breeders(breeder_id),
    year_released INTEGER,
    cultivar_type TEXT,          -- indica / sativa / hybrid / auto / cbd-rich / clone-only / landrace
    verified      BOOLEAN DEFAULT FALSE
);

-- 3. PEDIGREE (vérité génétique — SeedFinder + breeders officiels)
CREATE TABLE pedigree (
    pedigree_id UUID PRIMARY KEY,
    cultivar_id UUID REFERENCES cultivars(cultivar_id),
    mother_id   UUID REFERENCES cultivars(cultivar_id),
    father_id   UUID REFERENCES cultivars(cultivar_id),
    backcross   TEXT,            -- ex. "Bx2"
    generation  TEXT,            -- ex. "F1", "S1"
    source      TEXT NOT NULL,   -- seedfinder | breeder_officiel | kannapedia
    source_url  TEXT
);

-- 4. LAB_RESULTS (SQDC + déclaratif seedbanks — pas de base COA publique par cultivar)
CREATE TABLE lab_results (
    coa_id         UUID PRIMARY KEY,
    cultivar_id    UUID REFERENCES cultivars(cultivar_id),
    lab_name       TEXT,         -- ex. "SQDC", "Leafly-déclaratif"
    test_date      DATE,
    thca           DECIMAL(5,2),
    thc_total      DECIMAL(5,2),
    cbd            DECIMAL(5,2),
    cbga           DECIMAL(5,2),
    cbda           DECIMAL(5,2),
    moisture       DECIMAL(5,2),
    water_activity DECIMAL(4,3),
    source         TEXT NOT NULL,
    source_url     TEXT
);

-- 5. TERPENES (rattachés à un résultat labo)
CREATE TABLE terpenes (
    terpene_id    UUID PRIMARY KEY,
    coa_id        UUID REFERENCES lab_results(coa_id),
    myrcene       DECIMAL(5,3),
    limonene      DECIMAL(5,3),
    caryophyllene DECIMAL(5,3),
    linalool      DECIMAL(5,3),
    ocimene       DECIMAL(5,3),
    humulene      DECIMAL(5,3),
    pinene        DECIMAL(5,3),
    total_terpenes DECIMAL(5,3)
);

-- 6. CULTIVATION_DATA (GrowDiaries + grow info Leafly + fiches breeders)
CREATE TABLE cultivation_data (
    cultivation_id UUID PRIMARY KEY,
    cultivar_id    UUID REFERENCES cultivars(cultivar_id),
    flowering_days INTEGER,
    stretch_factor DECIMAL(3,2),  -- ex. 1.5 = +50 % en stretch
    height_cm      INTEGER,
    yield_g_m2     INTEGER,
    mold_resistance INTEGER CHECK (mold_resistance BETWEEN 1 AND 10),
    pm_resistance   INTEGER CHECK (pm_resistance BETWEEN 1 AND 10),
    vigor_score     INTEGER CHECK (vigor_score BETWEEN 1 AND 10),
    difficulty      TEXT,          -- facile / moyen / difficile
    source          TEXT NOT NULL,
    source_url      TEXT
);

-- 7. HASH_DATA (marché extraction 2026)
CREATE TABLE hash_data (
    hash_id           UUID PRIMARY KEY,
    cultivar_id       UUID REFERENCES cultivars(cultivar_id),
    fresh_frozen_yield DECIMAL(5,2),
    wash_percentage    DECIMAL(5,2),
    rosin_return       DECIMAL(5,2),
    melt_score         INTEGER CHECK (melt_score BETWEEN 1 AND 10),
    source             TEXT NOT NULL,
    source_url         TEXT
);

-- 8. MARKET_DATA (Leafly + signaux marché)
CREATE TABLE market_data (
    market_id           UUID PRIMARY KEY,
    cultivar_id         UUID REFERENCES cultivars(cultivar_id),
    retail_popularity    INTEGER,  -- notes / avis Leafly
    wholesale_popularity INTEGER,
    extraction_popularity INTEGER,
    social_mentions      INTEGER,
    search_volume        INTEGER,
    commercial_score     DECIMAL(5,2),  -- voir docs/commercial-score.md
    source               TEXT NOT NULL
);
```

## Notes

- **Badge par source** : chaque fiche compilée (`data/compiled/`) liste ses sources — ex. `SeedFinder + Leafly + GrowDiaries`.
- **Champs dérivés** (scores 1–10 : `vigor_score`, `mold_resistance`, `bag_appeal`…) : calculés par heuristique documentée dans `docs/commercial-score.md`, jamais inventés — si la donnée brute manque, le champ reste NULL.
- **THC/terpènes labo** : la SQDC (tests obligatoires, étiquetage) est la source de référence ; Leafly/seedbanks en déclaratif ; aucune base COA publique par cultivar n’existe (audit 2026-10-11).
