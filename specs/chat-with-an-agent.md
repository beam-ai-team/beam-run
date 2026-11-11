# Chat with an agent

## Status (11 November 2026)

Built, checked on staging, and verified in a fresh Codex task, then moved onto the latest main
as version 0.7.1-prism.5 and opened for review.

## Outcome

Someone in Claude Code, Codex or Cursor can say "chat with the Invoice Matcher" and then keep
talking to that agent like a conversation: send a message, see the reply, answer its
questions, ask for changes, and ask something new, without thinking about runs.

Beam has no chat feature to call, so every message is a normal run. The coding assistant hides
that and keeps the thread together.

## How a conversation maps onto runs

| The person does | Beam Run does |
| --- | --- |
| Opens the chat ("chat with X") | Finds the agent, uses the published version (or the draft if asked), says what the agent can do outside Beam |
| Sends the first message | Starts a run with the message as it is, waits for it, shows the agent's reply in plain words |
| The agent asks a question mid-run | Shows the question; the person's reply goes back as the answer |
| The agent wants approval to act (send, post, update) | Shows exactly what it will do and waits for yes or no |
| Asks for a change ("shorter") or something new | Starts a new run whose input opens with "Earlier in this conversation:", one line per earlier message and reply, then "My new message:" |
| Says "stop" | Stops the run that is still going, after confirming |

## What was built

1. **A new playbook, "Chat with an agent"**, listed in the Beam skill beside the others.
2. **A "wait for a run" command.** It checks the run every three seconds and returns once it
   finishes, fails or pauses for the person (gives up after five minutes by default).
3. **A fix to answering an agent's question.** Beam only accepts an answer that repeats the
   agent's exact question. Beam Run was sending the field's short name instead, so every answer
   failed, in chat and in the existing "clear what's waiting on me" playbook. It now sends the
   question itself.
4. **Tests.** Command-line checks for the wait command and the answer fix, and two assistant
   scenarios: a first message where the agent asks a question, and "make that shorter".
5. **A test agent definition** for repeating the staging check. A disposable draft agent built
   from it, "Beam Run Chat Validation", is in the Beam AI staging workspace.

## What staging showed

- **Beam's live run feed sends nothing.** It connects and then stays silent while the run
  changes, with either sign-in method. So Beam Run checks the run on a timer instead.
- **Re-running a step with feedback ignores the feedback.** Beam stores the request ("make it two
  sentences") but the agent's answer doesn't change. So change requests are new runs carrying the
  conversation, not re-runs. This also avoids repeating a step that already sent an email.
- **Some agents throw the conversation away.** An agent's first step picks out "the message" from
  the input. A loosely described step keeps only the newest line, so follow-ups lose their
  context. An agent whose step is described as "the whole input, word for word" handled all
  three messages correctly. The playbook checks this once per chat and, if the agent drops the
  context, tells the person and offers to change that step.
- **A question can come back on every run.** An agent that asks a fixed question (who is this
  for?) asks it again on each new message. The playbook offers the earlier answer and waits for a
  yes rather than reusing it silently.

## Safety stops that stay

- An agent that can act outside Beam: ask before every message's run, not once per chat.
- Approvals, rejections and stopping a run always wait for a clear yes.
- An answer is sent as the person typed it; anything filled in or reused is shown first.

## Risks

- Every message is a full run, with the time and credits that takes.
- The conversation recap is the agent's only memory. Long chats make long inputs.
- Five of the existing installation checks fail on the developer's machine. They fail the same
  way without this work, so they are not caused by it.
