-- Add body_html columns for caching rendered markdown
-- Each statement is separate to avoid multi-statement issues

ALTER TABLE pages ADD COLUMN body_html TEXT AFTER body_markdown;
ALTER TABLE posts ADD COLUMN body_html TEXT AFTER body_markdown;
ALTER TABLE experiments ADD COLUMN body_html TEXT AFTER body_markdown;

-- Add indexes for faster lookups
CREATE INDEX idx_pages_status ON pages(status);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_experiments_status ON experiments(status);
