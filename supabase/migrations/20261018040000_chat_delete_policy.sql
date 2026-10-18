drop policy if exists "Users can delete their chat conversations"
    on public.chat_conversations;
create policy "Users can delete their chat conversations"
    on public.chat_conversations for delete
    to authenticated
    using ((select auth.uid()) = user_id);

grant delete on public.chat_conversations to authenticated;
