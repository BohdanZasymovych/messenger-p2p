
-- Create the role (user) if it doesn't exist
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'messenger_user_1') THEN
        CREATE ROLE messenger_user_1 WITH LOGIN PASSWORD 'some_password_1';
    END IF;
END
$$;

-- Create the database if it doesn't exist
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'messenger_user_db_1') THEN
        CREATE DATABASE messenger_user_db_1 OWNER messenger_user_1;
    END IF;
END
$$;

-- Connect to the database and create the messages table
\c messenger_user_db_1

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);