# Control Panel Frontend

This frontend is source-managed under `src/` and runtime-served from `dist/`.

## Build pipeline

- Build command: `scripts/frontend/build_control_panel_frontend.sh`
- Current build strategy: deterministic copy (`src -> dist`) without external toolchain.
- Docker contract: `services/control-panel/Dockerfile` copies `frontend/dist` into image.

## Structure

- `src/app/`: app shell runtime bootstrap.
- `src/modules/`: domain module ownership area.
- `src/components/`: shared UI helpers and primitives.
- `src/services/`: API/auth transport helpers.
- `src/state/`: persisted UI/session state keys.
- `src/styles/`: theme/tokens and global styles.
