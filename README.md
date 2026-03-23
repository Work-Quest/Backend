Superuser 
- Username : admin
- Password : 12345678

## Demo world (default **4 users**, **2 projects**)

Seeds a **small squad** you can also scale up: default **4** accounts, **2** projects (first **Done**,
rest **Working**), **~8 tasks** each. **All** demo users join **every** project (manual “full party”
layout). **Working** projects skew toward **open** tasks so you can still use the app (move to done,
battle, real `TaskLog`s). **Done** projects get **ProjectEndSummary** for finished-project APIs.

```bash
python manage.py seed_mock_user --reset
```

- Log in as **`wqdemo_01`** / **`demo1234`** (also `wqdemo_02` … `wqdemo_04` by default).
- **Reset** removes every `<prefix>_*` user and all projects they owned or joined; or run `clear_mock_data`.
- **Achievements** (UI) are string IDs **`01`–`06`** from `achievement_service.py` / `achievementConstants.ts` (not the Django `Achievement` table). **04** cannot unlock if every member stays **Alive**.
- **Bosses**: `boss_image` **`b01`–`b03`** (Dracula / Golem / Gnoll) synced with `battleConfig.ts`.
- **Avatars**: `selected_character_id` **1–9** → sprites **`c01`–`c09`** (`avatar.ts`).

Options:

- `--username-prefix myteam` → `myteam_01`, …
- `--players 8` `--projects 3` `--tasks-per-project 12`
- `--password secret` `--seed 99` (reproducible randomness)
