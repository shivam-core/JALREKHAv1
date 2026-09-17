# JALREKHAv1

When routes change, plans should too.

JALREKHA is a disaster-planning simulator built for coordinators conducting scenario exercises. It helps planners explore how assumed flood conditions and road closures affect access to limited shelter capacity.

## Features
- Dynamic Water Levels: Instantly visualize affected areas and routes.
- Constraint Allocation: Allocates populations based on nearest available shelter capacity, prioritizing maximum people sheltered, then minimizing total travel time.
- Custom Road Closures & Overrides: Test interventions by "closing" specific roads or manually opening extra shelter capacity.

## AI Disclaimer
AI tools (Antigravity, GitHub Copilot) assisted with ideation, planning, code generation, debugging and documentation. The team reviewed and tested the submitted implementation.

## Project Structure
- `/public`: Frontend UI
- `/app.py`: FastAPI server
- `/engine`: Routing and allocation logic
- `/scripts`: Data preparation scripts
- `/data`: Geographic and scenario data

## Tech Stack
- Frontend: Vanilla HTML/JS + MapLibre GL JS
- Backend: FastAPI, NetworkX
- Data Preparation: Rasterio, PySheds, OSMnx, Shapely
- Deployment: Vercel (Hobby tier)
