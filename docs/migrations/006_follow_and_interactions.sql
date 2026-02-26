-- 006: 关注系统 + 互动通知

CREATE TABLE IF NOT EXISTS user_follows (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(follower_id, following_id),
    CHECK(follower_id != following_id)
);
CREATE INDEX IF NOT EXISTS idx_user_follows_follower ON user_follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_user_follows_following ON user_follows(following_id);

CREATE TABLE IF NOT EXISTS interaction_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(20) NOT NULL,
    target_type VARCHAR(20),
    target_id INTEGER,
    post_id INTEGER,
    content_preview VARCHAR(200),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_interaction_notif_user ON interaction_notifications(user_id, is_read, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_interaction_notif_dedup ON interaction_notifications(user_id, actor_id, action_type, target_type, target_id);

-- 修复历史 pair_key 脏数据
UPDATE chat_conversations
SET direct_pair_key = REPLACE(direct_pair_key, '_', ':')
WHERE c_type='direct' AND direct_pair_key LIKE '%\_%' AND direct_pair_key NOT LIKE '%:%';
