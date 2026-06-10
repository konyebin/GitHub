# Autonomous-Ai-drone-scripts

<ClientOnly>
  <DemoPanel slug="autonomous-ai-drone-scripts" />
</ClientOnly>

## What it is

**Autonomous multirotor research** — end-to-end AI navigation, obstacle avoidance, and a **person-following** stack (camera + LiDAR + object detection) tested on real flights. Runs on **NVIDIA Jetson Nano** on the aircraft.

## When to use it

- Jetson Nano drone software setup
- Person-following / point-to-point autonomy experiments
- ArduPilot SITL simulation workflows

## Stack and entry points

| Item | Path |
|------|------|
| Overview | `Autonomous-Ai-drone-scripts/README.md` |
| Build guide | `Autonomous-Ai-drone-scripts/BUILD.md` |
| Manuals | `Autonomous-Ai-drone-scripts/manuals/` |

## Prerequisites

| Need | Detail |
|------|--------|
| Hardware | Jetson Nano, Pixhawk-class stack per BUILD.md |
| OS / deps | Jetson inference, ArduPilot, project-specific installs in BUILD.md |

## How to run

Follow **`BUILD.md`** for Jetson setup, jetson-inference clone, and ArduPilot SITL. Training/tooling for the full E2E pilot model is proprietary to MRR; person-following components are documented in the README.

## Canonical docs

- `~/Documents/GitHub/Autonomous-Ai-drone-scripts/README.md`
- `~/Documents/GitHub/Autonomous-Ai-drone-scripts/BUILD.md`
