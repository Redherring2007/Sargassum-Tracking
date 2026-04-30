# Autonomous Collection

Future robotic boats or drones can use Sargassum Sentinel as a tasking and telemetry platform.

Robotic devices should be able to:

- Request assigned tasks from `/api/autonomous/tasks`
- Receive GPS waypoints and polygon collection zones
- Report status to `/api/autonomous/status`
- Send live GPS, battery, speed, and heading to `/api/autonomous/telemetry`
- Mark zones as collected
- Upload images or sensor readings
- Return to dock when complete or when safety rules trigger
- Respect safe operating boundaries, exclusion zones, and weather limits

The MVP does not control vessels. It provides API placeholders and documentation for future mission management.
