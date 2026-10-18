create table if not exists public.chat_conversations (
    id uuid primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    title text not null check (char_length(title) between 1 and 120),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null
        references public.chat_conversations (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    sequence bigint generated always as identity unique,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (char_length(content) between 1 and 20000),
    created_at timestamptz not null default now()
);

create index if not exists chat_conversations_user_updated_idx
    on public.chat_conversations (user_id, updated_at desc);

create index if not exists chat_messages_conversation_sequence_idx
    on public.chat_messages (conversation_id, sequence);

alter table public.chat_conversations enable row level security;
alter table public.chat_messages enable row level security;

drop policy if exists "Users can read their chat conversations"
    on public.chat_conversations;
create policy "Users can read their chat conversations"
    on public.chat_conversations for select
    to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can create their chat conversations"
    on public.chat_conversations;
create policy "Users can create their chat conversations"
    on public.chat_conversations for insert
    to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update their chat conversations"
    on public.chat_conversations;
create policy "Users can update their chat conversations"
    on public.chat_conversations for update
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can read their chat messages"
    on public.chat_messages;
create policy "Users can read their chat messages"
    on public.chat_messages for select
    to authenticated
    using (
        (select auth.uid()) = user_id
        and exists (
            select 1
            from public.chat_conversations
            where chat_conversations.id = chat_messages.conversation_id
              and chat_conversations.user_id = (select auth.uid())
        )
    );

drop policy if exists "Users can add messages to their conversations"
    on public.chat_messages;
create policy "Users can add messages to their conversations"
    on public.chat_messages for insert
    to authenticated
    with check (
        (select auth.uid()) = user_id
        and exists (
            select 1
            from public.chat_conversations
            where chat_conversations.id = chat_messages.conversation_id
              and chat_conversations.user_id = (select auth.uid())
        )
    );

grant select, insert, update on public.chat_conversations to authenticated;
grant select, insert on public.chat_messages to authenticated;

create or replace function public.touch_chat_conversation_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    update public.chat_conversations
    set updated_at = now()
    where id = new.conversation_id;
    return new;
end;
$$;

drop trigger if exists chat_messages_touch_conversation
    on public.chat_messages;
create trigger chat_messages_touch_conversation
    after insert on public.chat_messages
    for each row
    execute function public.touch_chat_conversation_updated_at();
