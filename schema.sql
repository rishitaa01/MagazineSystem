-- ============================================================
-- Digital Magazine Management System — Database Schema
-- Database: magazine_system (SQLite3)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- TABLE: PUBLISHER
-- One publisher publishes many magazines (1:N)
-- ============================================================
CREATE TABLE IF NOT EXISTS PUBLISHER (
    publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    phone        TEXT,
    address      TEXT
);

-- ============================================================
-- TABLE: MAGAZINE
-- FK: publisher_id → PUBLISHER
-- One magazine contains many articles (1:N)
-- One magazine can have many subscribers (M:N via SUBSCRIPTION)
-- ============================================================
CREATE TABLE IF NOT EXISTS MAGAZINE (
    mag_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    language     TEXT,
    category     TEXT,
    p_date       TEXT,           -- publication date (YYYY-MM-DD)
    price        REAL DEFAULT 0,
    publisher_id INTEGER,
    FOREIGN KEY (publisher_id) REFERENCES PUBLISHER(publisher_id) ON DELETE SET NULL
);

-- ============================================================
-- TABLE: AUTHOR
-- One author writes many articles (M:N via WRITES)
-- ============================================================
CREATE TABLE IF NOT EXISTS AUTHOR (
    author_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    phone          TEXT,
    specialization TEXT
);

-- ============================================================
-- TABLE: EDITOR
-- One editor edits many articles (1:N via EDITS)
-- ============================================================
CREATE TABLE IF NOT EXISTS EDITOR (
    editor_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    experience INTEGER DEFAULT 0   -- years of experience
);

-- ============================================================
-- TABLE: ARTICLE
-- FK: mag_id → MAGAZINE (cascade delete)
-- ============================================================
CREATE TABLE IF NOT EXISTS ARTICLE (
    article_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    pages      INTEGER,
    p_date     TEXT,               -- publication date
    mag_id     INTEGER,
    FOREIGN KEY (mag_id) REFERENCES MAGAZINE(mag_id) ON DELETE CASCADE
);

-- ============================================================
-- JUNCTION TABLE: WRITES  (M:N  Author ↔ Article)
-- ============================================================
CREATE TABLE IF NOT EXISTS WRITES (
    author_id  INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    PRIMARY KEY (author_id, article_id),
    FOREIGN KEY (author_id)  REFERENCES AUTHOR(author_id)   ON DELETE CASCADE,
    FOREIGN KEY (article_id) REFERENCES ARTICLE(article_id) ON DELETE CASCADE
);

-- ============================================================
-- JUNCTION TABLE: EDITS  (1:N  Editor → Article)
-- ============================================================
CREATE TABLE IF NOT EXISTS EDITS (
    editor_id  INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    PRIMARY KEY (editor_id, article_id),
    FOREIGN KEY (editor_id)  REFERENCES EDITOR(editor_id)   ON DELETE CASCADE,
    FOREIGN KEY (article_id) REFERENCES ARTICLE(article_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE: SUBSCRIBER
-- ============================================================
CREATE TABLE IF NOT EXISTS SUBSCRIBER (
    subscriber_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    phone             TEXT,
    city              TEXT,
    subscription_type TEXT DEFAULT 'Monthly'  -- Monthly / Yearly / Lifetime
);

-- ============================================================
-- TABLE: SUBSCRIPTION  (M:N  Subscriber ↔ Magazine)
-- CHECK: end_date must be after start_date
-- ============================================================
CREATE TABLE IF NOT EXISTS SUBSCRIPTION (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL,
    mag_id          INTEGER NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    CHECK (end_date > start_date),
    FOREIGN KEY (subscriber_id) REFERENCES SUBSCRIBER(subscriber_id) ON DELETE CASCADE,
    FOREIGN KEY (mag_id)        REFERENCES MAGAZINE(mag_id)          ON DELETE CASCADE
);

-- ============================================================
-- TABLE: Article_Log  (for trigger logging)
-- ============================================================
CREATE TABLE IF NOT EXISTS Article_Log (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    article_name TEXT,
    action_time  TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- TRIGGER: after_article_insert
-- Logs every new article into Article_Log
-- ============================================================
CREATE TRIGGER IF NOT EXISTS after_article_insert
AFTER INSERT ON ARTICLE
BEGIN
    INSERT INTO Article_Log (article_name, action_time)
    VALUES (NEW.title, datetime('now','localtime'));
END;

-- ============================================================
-- VIEW: Article_Details
-- Joins Article + Authors (via WRITES) + Magazine + Editor (via EDITS)
-- ============================================================
CREATE VIEW IF NOT EXISTS Article_Details AS
SELECT
    a.article_id,
    a.title       AS article_title,
    a.pages,
    a.p_date      AS article_date,
    m.title       AS magazine_title,
    m.category    AS magazine_category,
    GROUP_CONCAT(DISTINCT au.name) AS author_names,
    GROUP_CONCAT(DISTINCT ed.name) AS editor_names
FROM ARTICLE a
LEFT JOIN MAGAZINE m  ON a.mag_id = m.mag_id
LEFT JOIN WRITES  w   ON a.article_id = w.article_id
LEFT JOIN AUTHOR  au  ON w.author_id  = au.author_id
LEFT JOIN EDITS   e   ON a.article_id = e.article_id
LEFT JOIN EDITOR  ed  ON e.editor_id  = ed.editor_id
GROUP BY a.article_id;

-- ============================================================
-- INDEXES: faster search operations
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_magazine_title    ON MAGAZINE(title);
CREATE INDEX IF NOT EXISTS idx_magazine_category ON MAGAZINE(category);
CREATE INDEX IF NOT EXISTS idx_author_name       ON AUTHOR(name);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Publishers
INSERT INTO PUBLISHER (name, email, phone, address) VALUES
('Penguin Random House', 'contact@penguin.com', '555-0101', '1745 Broadway, New York, NY'),
('HarperCollins', 'info@harpercollins.com', '555-0102', '195 Broadway, New York, NY'),
('Condé Nast', 'hello@condenast.com', '555-0103', '1 World Trade Center, New York, NY'),
('Hearst Media', 'press@hearst.com', '555-0104', '300 W 57th St, New York, NY'),
('Time Inc.', 'editors@timeinc.com', '555-0105', '225 Liberty St, New York, NY');

-- Magazines
INSERT INTO MAGAZINE (title, language, category, p_date, price, publisher_id) VALUES
('Tech Today',         'English', 'Technology',  '2025-01-15', 9.99,  1),
('Science Weekly',     'English', 'Science',     '2025-02-01', 7.50,  2),
('Art & Design',       'English', 'Art',         '2025-03-10', 12.00, 3),
('Health Digest',      'English', 'Health',      '2025-04-05', 6.99,  4),
('Business Insider',   'English', 'Business',    '2025-05-20', 11.50, 5),
('World Literature',   'English', 'Literature',  '2025-06-15', 8.25,  1),
('Travel Explorer',    'English', 'Travel',      '2025-07-01', 10.00, 3),
('Culinary Arts',      'French',  'Food',        '2025-08-12', 9.00,  4);

-- Authors
INSERT INTO AUTHOR (name, email, phone, specialization) VALUES
('Alice Chen',      'alice@writers.com',    '555-1001', 'Technology'),
('Bob Martinez',    'bob@writers.com',      '555-1002', 'Science'),
('Clara Hughes',    'clara@writers.com',    '555-1003', 'Art & Culture'),
('David Kim',       'david@writers.com',    '555-1004', 'Health & Wellness'),
('Eva Rossi',       'eva@writers.com',      '555-1005', 'Business'),
('Frank Okoro',     'frank@writers.com',    '555-1006', 'Travel & Food');

-- Editors
INSERT INTO EDITOR (name, email, experience) VALUES
('Grace Lin',       'grace@editors.com',    12),
('Henry Patel',     'henry@editors.com',    8),
('Isabel Novak',    'isabel@editors.com',   15),
('James Wright',    'james@editors.com',    6);

-- Articles  (12 articles across 8 magazines)
INSERT INTO ARTICLE (title, pages, p_date, mag_id) VALUES
('The Rise of Quantum Computing',   12, '2025-01-15', 1),
('AI in Everyday Life',             8,  '2025-01-15', 1),
('CRISPR and Gene Editing',         15, '2025-02-01', 2),
('Mars Exploration Update',         10, '2025-02-01', 2),
('Modern Minimalist Design',        6,  '2025-03-10', 3),
('The Art of Typography',           9,  '2025-03-10', 3),
('Nutrition Myths Debunked',        7,  '2025-04-05', 4),
('Startup Funding Strategies',      11, '2025-05-20', 5),
('Remote Work Revolution',          8,  '2025-05-20', 5),
('Shakespeare Reimagined',          14, '2025-06-15', 6),
('Hidden Gems of Southeast Asia',   10, '2025-07-01', 7),
('French Pastry Masterclass',       6,  '2025-08-12', 8);

-- WRITES  (Author ↔ Article assignments, some articles have multiple authors)
INSERT INTO WRITES (author_id, article_id) VALUES
(1, 1),   -- Alice → Quantum Computing
(1, 2),   -- Alice → AI in Everyday Life
(2, 3),   -- Bob   → CRISPR
(2, 4),   -- Bob   → Mars Exploration
(3, 5),   -- Clara → Minimalist Design
(3, 6),   -- Clara → Typography
(4, 7),   -- David → Nutrition Myths
(5, 8),   -- Eva   → Startup Funding
(5, 9),   -- Eva   → Remote Work
(3, 10),  -- Clara → Shakespeare
(6, 11),  -- Frank → Southeast Asia
(6, 12),  -- Frank → French Pastry
(1, 3),   -- Alice also co-authored CRISPR
(4, 11);  -- David also co-authored Southeast Asia

-- EDITS  (Editor → Article assignments)
INSERT INTO EDITS (editor_id, article_id) VALUES
(1, 1),   -- Grace  → Quantum Computing
(1, 2),   -- Grace  → AI
(2, 3),   -- Henry  → CRISPR
(2, 4),   -- Henry  → Mars
(3, 5),   -- Isabel → Minimalist Design
(3, 6),   -- Isabel → Typography
(4, 7),   -- James  → Nutrition
(1, 8),   -- Grace  → Startup
(1, 9),   -- Grace  → Remote Work
(3, 10),  -- Isabel → Shakespeare
(4, 11),  -- James  → Southeast Asia
(2, 12);  -- Henry  → French Pastry

-- Subscribers
INSERT INTO SUBSCRIBER (name, email, phone, city, subscription_type) VALUES
('Rahul Sharma',    'rahul@mail.com',    '555-2001', 'Mumbai',    'Yearly'),
('Priya Nair',      'priya@mail.com',    '555-2002', 'Delhi',     'Monthly'),
('John Smith',      'john@mail.com',     '555-2003', 'New York',  'Lifetime'),
('Aisha Khan',      'aisha@mail.com',    '555-2004', 'London',    'Yearly'),
('Liam O''Brien',   'liam@mail.com',     '555-2005', 'Dublin',    'Monthly'),
('Mei Wong',        'mei@mail.com',      '555-2006', 'Singapore', 'Yearly'),
('Carlos Ruiz',     'carlos@mail.com',   '555-2007', 'Madrid',    'Monthly'),
('Fatima Al-Said',  'fatima@mail.com',   '555-2008', 'Dubai',     'Lifetime');

-- Subscriptions  (some active, some expired for demo)
INSERT INTO SUBSCRIPTION (subscriber_id, mag_id, start_date, end_date) VALUES
(1, 1, '2025-01-01', '2026-01-01'),   -- Rahul  → Tech Today (active)
(1, 5, '2025-03-01', '2026-03-01'),   -- Rahul  → Business Insider (active)
(2, 2, '2025-02-01', '2025-08-01'),   -- Priya  → Science Weekly (expired)
(3, 1, '2024-06-01', '2027-06-01'),   -- John   → Tech Today (active, lifetime)
(3, 3, '2024-06-01', '2027-06-01'),   -- John   → Art & Design (active)
(4, 7, '2025-05-01', '2026-05-01'),   -- Aisha  → Travel Explorer (active)
(5, 4, '2025-04-01', '2025-10-01'),   -- Liam   → Health Digest (expired)
(6, 8, '2025-07-01', '2026-07-01'),   -- Mei    → Culinary Arts (active)
(7, 5, '2025-01-15', '2025-07-15'),   -- Carlos → Business Insider (expired)
(8, 6, '2025-06-01', '2027-06-01');   -- Fatima → World Literature (active)
