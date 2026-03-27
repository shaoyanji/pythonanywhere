CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pages (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    body_markdown MEDIUMTEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    excerpt TEXT,
    body_markdown MEDIUMTEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    body_markdown MEDIUMTEXT,
    demo_path VARCHAR(255) NULL,
    source_path VARCHAR(255) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    featured TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nav_items (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(255) NOT NULL,
    href VARCHAR(255) NOT NULL,
    kind VARCHAR(32) NOT NULL DEFAULT 'public',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_settings (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(255) NOT NULL UNIQUE,
    value_text MEDIUMTEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    input_text MEDIUMTEXT,
    output_text MEDIUMTEXT,
    summary TEXT,
    kind VARCHAR(64) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO site_settings (`key`, value_text)
VALUES
    ('site_title', 'Shaoyan Ji Lab'),
    ('hero_title', 'Shaoyan Ji Lab'),
    ('hero_intro', 'Notes, experiments, and operational tools in a thin Flask site.'),
    ('nav_intro', 'Notes, experiments, and pages published from the database.'),
    ('meta_description', 'Shaoyan Ji Lab: notes, experiments, and operational tools.'),
    ('footer_note', 'Built with Flask, Jinja, MySQL, and a preference for thin systems.')
ON DUPLICATE KEY UPDATE value_text = VALUES(value_text);

INSERT INTO nav_items (label, href, kind, is_enabled, sort_order)
VALUES
    ('Home', '/', 'public', 1, 10),
    ('Notes', '/notes', 'public', 1, 20),
    ('Experiments', '/experiments', 'public', 1, 30),
    ('About', '/about', 'public', 1, 40)
ON DUPLICATE KEY UPDATE
    href = VALUES(href),
    kind = VALUES(kind),
    is_enabled = VALUES(is_enabled),
    sort_order = VALUES(sort_order);

INSERT INTO pages (slug, title, body_markdown, status, sort_order)
VALUES
    (
        'home',
        'Home',
        'Welcome. This site publishes notes, experiments, and a small set of public pages.',
        'published',
        10
    ),
    (
        'about',
        'About',
        'This is a compact Flask site for publishing writing, experiments, and operational context.',
        'published',
        20
    )
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    body_markdown = VALUES(body_markdown),
    status = VALUES(status),
    sort_order = VALUES(sort_order);
