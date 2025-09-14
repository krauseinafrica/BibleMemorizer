-- Bible Memorizer Database Schema
-- SQLite database for comprehensive student tracking and reporting

-- Users table: handles both students and teachers/admins
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student', -- 'student', 'teacher', 'admin'
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classes/Groups table: for organizing students
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    teacher_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- Class memberships: many-to-many relationship
CREATE TABLE class_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(class_id, student_id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (student_id) REFERENCES users(id)
);

-- Bible verses table: expandable verse collection
CREATE TABLE verses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference VARCHAR(100) NOT NULL UNIQUE,
    text TEXT NOT NULL,
    translation VARCHAR(20) DEFAULT 'NIV',
    book VARCHAR(50) NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER NOT NULL,
    verse_end INTEGER,
    difficulty_level INTEGER DEFAULT 1, -- 1=easy, 2=medium, 3=hard
    word_count INTEGER,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verse sets: custom collections for classes/assignments
CREATE TABLE verse_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    teacher_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- Verse set contents: which verses are in which sets
CREATE TABLE verse_set_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_set_id INTEGER NOT NULL,
    verse_id INTEGER NOT NULL,
    order_index INTEGER DEFAULT 0,
    UNIQUE(verse_set_id, verse_id),
    FOREIGN KEY (verse_set_id) REFERENCES verse_sets(id),
    FOREIGN KEY (verse_id) REFERENCES verses(id)
);

-- Assignments: teachers assign verse sets to classes
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    class_id INTEGER NOT NULL,
    verse_set_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    due_date DATE,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (verse_set_id) REFERENCES verse_sets(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- Recitation attempts: core data matching your current Firebase structure
CREATE TABLE recitation_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    verse_id INTEGER NOT NULL,
    assignment_id INTEGER, -- nullable for practice attempts
    recitation TEXT NOT NULL,
    score INTEGER NOT NULL, -- 0-100
    attempt_number INTEGER DEFAULT 1,
    time_spent_seconds INTEGER, -- time from start to submission
    used_speech_recognition BOOLEAN DEFAULT 0,
    is_passing BOOLEAN DEFAULT 0, -- score >= 90
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (verse_id) REFERENCES verses(id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(id)
);

-- Detailed error analysis: track specific mistakes
CREATE TABLE recitation_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    error_type VARCHAR(50) NOT NULL, -- 'missing_word', 'wrong_word', 'extra_word', 'word_order'
    position INTEGER NOT NULL, -- word position in verse
    expected_word VARCHAR(100),
    actual_word VARCHAR(100),
    context_before TEXT, -- few words before error
    context_after TEXT,  -- few words after error
    FOREIGN KEY (attempt_id) REFERENCES recitation_attempts(id)
);

-- Student progress tracking: summary stats per student/verse
CREATE TABLE student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    verse_id INTEGER NOT NULL,
    total_attempts INTEGER DEFAULT 0,
    best_score INTEGER DEFAULT 0,
    latest_score INTEGER DEFAULT 0,
    is_memorized BOOLEAN DEFAULT 0, -- achieved 90%+ score
    first_memorized_at TIMESTAMP,
    last_attempt_at TIMESTAMP,
    average_score DECIMAL(5,2),
    improvement_trend VARCHAR(20), -- 'improving', 'declining', 'stable'
    UNIQUE(student_id, verse_id),
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (verse_id) REFERENCES verses(id)
);

-- Sessions: track user login sessions
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- System settings: app configuration
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_recitation_attempts_student_id ON recitation_attempts(student_id);
CREATE INDEX idx_recitation_attempts_verse_id ON recitation_attempts(verse_id);
CREATE INDEX idx_recitation_attempts_created_at ON recitation_attempts(created_at);
CREATE INDEX idx_student_progress_student_id ON student_progress(student_id);
CREATE INDEX idx_class_memberships_student_id ON class_memberships(student_id);
CREATE INDEX idx_class_memberships_class_id ON class_memberships(class_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Insert default data
INSERT INTO settings (key, value, description) VALUES
('passing_score', '90', 'Minimum score required to pass (0-100)'),
('retry_score', '80', 'Minimum score for first attempt to allow retry'),
('max_attempts', '3', 'Maximum attempts allowed per verse'),
('session_timeout', '86400', 'Session timeout in seconds (24 hours)');

-- Insert initial Bible verses (matching your current collection)
INSERT INTO verses (reference, text, book, chapter, verse_start, verse_end, word_count) VALUES
('Proverbs 3:5-6', 'Trust in the Lord with all your heart and lean not on your own understanding; in all your ways submit to him, and he will make your paths straight.', 'Proverbs', 3, 5, 6, 30),
('Philippians 4:13', 'I can do all this through him who gives me strength.', 'Philippians', 4, 13, 13, 11),
('John 3:16', 'For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.', 'John', 3, 16, 16, 28),
('Romans 8:28', 'And we know that in all things God works for the good of those who love him, who have been called according to his purpose.', 'Romans', 8, 28, 28, 26),
('Jeremiah 29:11', 'For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future.', 'Jeremiah', 29, 11, 11, 29),
('Isaiah 41:10', 'So do not fear, for I am with you; do not be dismayed, for I am your God. I will strengthen you and help you; I will uphold you with my righteous right hand.', 'Isaiah', 41, 10, 10, 34),
('Psalm 46:1', 'God is our refuge and strength, an ever-present help in trouble.', 'Psalms', 46, 1, 1, 11),
('Galatians 5:22-23', 'But the fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness, gentleness and self-control. Against such things there is no law.', 'Galatians', 5, 22, 23, 26),
('Hebrews 11:1', 'Now faith is confidence in what we hope for and assurance about what we do not see.', 'Hebrews', 11, 1, 1, 17),
('2 Timothy 3:16', 'All Scripture is God-breathed and is useful for teaching, rebuking, correcting and training in righteousness,', '2 Timothy', 3, 16, 16, 16);