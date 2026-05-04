-- Add body_html columns for caching rendered markdown
-- Check and add column for pages
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pages' AND COLUMN_NAME = 'body_html');
SET @sql = IF(@exist = 0, 'ALTER TABLE pages ADD COLUMN body_html TEXT AFTER body_markdown', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add column for posts
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'posts' AND COLUMN_NAME = 'body_html');
SET @sql = IF(@exist = 0, 'ALTER TABLE posts ADD COLUMN body_html TEXT AFTER body_markdown', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add column for experiments
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'experiments' AND COLUMN_NAME = 'body_html');
SET @sql = IF(@exist = 0, 'ALTER TABLE experiments ADD COLUMN body_html TEXT AFTER body_markdown', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add indexes if they don't exist (MySQL 5.7+ supports CREATE INDEX IF NOT EXISTS)
-- For older versions, we can use similar check
SET @exist = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pages' AND INDEX_NAME = 'idx_pages_status');
SET @sql = IF(@exist = 0, 'CREATE INDEX idx_pages_status ON pages(status)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'posts' AND INDEX_NAME = 'idx_posts_status');
SET @sql = IF(@exist = 0, 'CREATE INDEX idx_posts_status ON posts(status)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'experiments' AND INDEX_NAME = 'idx_experiments_status');
SET @sql = IF(@exist = 0, 'CREATE INDEX idx_experiments_status ON experiments(status)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
