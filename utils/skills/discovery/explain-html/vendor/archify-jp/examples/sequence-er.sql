CREATE TABLE accounts (id bigint PRIMARY KEY, name text NOT NULL, active boolean NOT NULL);
CREATE TABLE tasks (id bigint PRIMARY KEY, account_id bigint NOT NULL REFERENCES accounts(id), state text NOT NULL);
SELECT a.name, t.state FROM accounts a INNER JOIN tasks t ON t.account_id = a.id WHERE a.active = true;
UPDATE tasks SET state = 'done' WHERE id = $1;
DELETE FROM tasks WHERE state = 'done';
