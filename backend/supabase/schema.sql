-- Task Flow 스키마 (PostgreSQL / Supabase). 근거: backend/migrations/versions/0001~0006, DATA-MODEL.md
-- 날짜는 SQLite와 같이 글자(text)로 둔다. 값 검증은 API가 한다. (D-004)

create table if not exists users (
    id bigint generated always as identity primary key,
    email text not null unique,
    password_hash text not null,
    created_at text not null
);

create table if not exists sessions (
    token_hash text primary key,
    user_id bigint not null references users(id),
    expires_at text not null
);
create index if not exists ix_sessions_user_id on sessions (user_id);

-- owner_id, subtasks.task_id 는 외래 키를 두지 않는다. (DATA-MODEL.md 4절)
create table if not exists tasks (
    id bigint generated always as identity primary key,
    title text not null,
    description text not null default '',
    status text not null default 'TODO',
    owner_id bigint,
    priority text not null default 'NORMAL',
    due_date text
);
create index if not exists ix_tasks_owner_id on tasks (owner_id);

create table if not exists subtasks (
    id bigint generated always as identity primary key,
    task_id bigint not null,
    title text not null,
    description text not null default ''
);
create index if not exists ix_subtasks_task_id on subtasks (task_id);

alter table users enable row level security;
alter table sessions enable row level security;
alter table tasks enable row level security;
alter table subtasks enable row level security;
