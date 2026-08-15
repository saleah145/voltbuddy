# VoltBuddy

VoltBuddy is a smart-home energy optimization simulator that helps users understand when flexible appliances should run, shift, or pause based on electricity price periods, appliance characteristics, live regional grid demand, and live generation-mix data.

The project combines a React frontend, a FastAPI backend, PostgreSQL persistence, and live data from the U.S. Energy Information Administration (EIA). VoltBuddy intentionally uses a deterministic scoring model rather than an LLM so that every recommendation is explainable and reproducible.

## What VoltBuddy Does

Users can:

- Select household appliances to simulate.
- Choose an hour, month, and weekday.
- Compare normal hourly energy cost with VoltBuddy-optimized cost.
- See which appliances should keep running, shift, or pause.
- Review the score factors behind each optimization decision.
- View deterministic recommendations.
- Add custom appliances.
- Save groups of appliances as homes.
- Review recent simulation history.
- Track cumulative savings.
- View electricity-price and savings charts in the frontend.
- View live Southern Company regional grid-demand data.
- View a live generation-mix carbon-awareness signal.

## Core Design Principle

VoltBuddy does **not** use a large language model to make energy-control decisions.

The optimization engine uses a deterministic weighted score based on:

- Georgia Power time-of-use price period
- Appliance power draw
- Appliance priority
- Whether an appliance is interruptible
- Live regional grid-demand trend
- Live generation-mix signal

This makes each result predictable, testable, and explainable.

Critical appliances and appliances marked non-interruptible are never automatically paused.

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- HTML/CSS

### Backend

- Python 3
- FastAPI
- Pydantic
- SQLAlchemy
- Uvicorn

### Database

- PostgreSQL

### Testing

- Pytest
- FastAPI TestClient
- In-memory SQLite test database

### External Data

VoltBuddy uses the U.S. Energy Information Administration EIA-930 datasets for:

- Hourly regional electricity demand
- Hourly generation by fuel type

The current balancing authority used by VoltBuddy is Southern Company (`SOCO`).

## Project Architecture

```text
voltbuddy/
├── frontend/
│   └── React + Vite application
│
└── backend/
    ├── main.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    │
    ├── routers/
    │   ├── appliances.py
    │   ├── homes.py
    │   ├── grid.py
    │   └── simulations.py
    │
    ├── services/
    │   ├── rates.py
    │   ├── grid.py
    │   ├── optimization.py
    │   └── recommendations.py
    │
    ├── tests/
    │   ├── conftest.py
    │   ├── test_api.py
    │   ├── test_optimization.py
    │   ├── test_rates.py
    │   └── test_recommendations.py
    │
    ├── requirements.txt
    ├── pytest.ini
    ├── Dockerfile
    └── docker-compose.yml
```

## Backend Structure

### `main.py`

Creates the FastAPI application, configures CORS, initializes database tables, and registers API routers.

### `database.py`

Configures SQLAlchemy and reads the database connection from the `DATABASE_URL` environment variable.

Default local database:

```text
postgresql://localhost/voltbuddy
```

### `models.py`

Contains SQLAlchemy models for:

- Appliances
- Simulations
- Homes
- Home-appliance relationships

### `schemas.py`

Contains Pydantic request models and validation logic.

### `routers/`

Separates HTTP endpoints by feature.

### `services/`

Contains business logic independent of the API route layer.

This includes:

- Electricity-rate logic
- EIA grid-data fetching
- Optimization scoring
- Recommendation generation

## Electricity Rate Model

VoltBuddy currently models Georgia Power's Overnight Advantage time-of-use energy-charge periods.

### Super Off-Peak

Every day:

```text
11:00 PM - 7:00 AM
```

Rate used by the simulator:

```text
$0.021859 / kWh
```

### On-Peak

June through September, Monday through Friday:

```text
2:00 PM - 7:00 PM
```

Rate used by the simulator:

```text
$0.297868 / kWh
```

### Off-Peak

All remaining hours:

```text
$0.101676 / kWh
```

These values represent the energy-charge portion used by the simulation and do not attempt to reproduce a complete utility bill with taxes, fuel adjustments, service charges, or other fees.

## Optimization Model

Each appliance receives a deterministic optimization score.

### Price Signal

```text
On-peak:        +45
Off-peak:       +10
Super off-peak: -20
```

### Appliance Power Draw

```text
>= 5.0 kW: +25
>= 1.5 kW: +15
>= 0.5 kW: +5
```

### Appliance Priority

```text
Critical: -100
Medium:    -10
Low:       +10
```

```http
DELETE /simulations
```

Clears all saved simulation history.

### Live Grid Demand

```text
Rising demand:  +10
Falling demand: -5
```

### Generation-Mix Signal

```text
Fossil-heavy:      +10
Lower-carbon mix:  -10
```

### Decision Thresholds

```text
Score >= 50:
Pause the appliance if it is interruptible and not critical.

Score >= 30:
Recommend shifting the appliance.

Score < 30:
Keep the appliance running.
```

Safety constraints override the score.

A critical or non-interruptible appliance is always kept running.

## Carbon-Awareness Signal

VoltBuddy builds a generation-mix signal from EIA-930 hourly generation-by-fuel data.

The low-carbon group currently includes:

- Nuclear
- Hydroelectric
- Wind
- Solar
- Geothermal

The fossil group currently includes:

- Coal
- Natural gas
- Oil

The signal categories are:

```text
Lower-carbon mix:
Low-carbon generation share >= 60%

Mixed generation:
Low-carbon generation share >= 35%

Fossil-heavy mix:
Low-carbon generation share < 35%
```

This is a **generation-mix indicator**, not a direct measurement of hourly CO2 intensity.

## API Endpoints

### Appliances

```http
GET /appliances
```

Returns all appliances.

```http
POST /appliances
```

Creates a custom appliance.

Example body:

```json
{
  "name": "Dish Washer",
  "kw": 1.2,
  "interruptible": true,
  "priority": "low"
}
```

```http
DELETE /appliances/{appliance_id}
```

Deletes a custom appliance. VoltBuddy's built-in demo appliances are protected from deletion. Any saved-home links using the deleted custom appliance are removed automatically.

### Homes

```http
GET /homes
```

Returns saved homes.

```http
POST /homes
```

Creates a saved home.

Example:

```json
{
  "name": "Apartment",
  "appliances": [
    "gaming_pc",
    "refrigerator"
  ]
}
```

```http
GET /homes/{home_id}
```

Returns one saved home and its appliances.

```http
DELETE /homes/{home_id}
```

Deletes a saved home.

### Simulation

```http
POST /simulate
```

Runs a VoltBuddy simulation.

Example request:

```json
{
  "hour": 16,
  "month": 8,
  "weekday": 2,
  "appliances": [
    "ev_charger",
    "gaming_pc",
    "refrigerator"
  ]
}
```

The response includes:

- Electricity rate information
- Live grid context when available
- Carbon-awareness signal when available
- Optimization summary
- Per-appliance decisions
- Score factors
- Recommendations
- Normal hourly cost
- Optimized hourly cost
- Hourly savings

### Simulation History

```http
GET /simulations
```

Returns the 20 most recent saved simulations.

```http
DELETE /simulations
```

Clears all saved simulation history.

### Live Grid

```http
GET /grid/live
```

Returns the most recent Southern Company regional electricity-demand data available from EIA.

### Carbon Signal

```http
GET /grid/carbon
```

Returns VoltBuddy's generation-mix carbon-awareness signal.

## Local Backend Setup

### 1. Enter the backend folder

```bash
cd backend
```

### 2. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Start PostgreSQL

Make sure PostgreSQL is running and that a database named `voltbuddy` exists.

The default local URL is:

```text
postgresql://localhost/voltbuddy
```

You may override it with:

```bash
export DATABASE_URL="your-database-url"
```

### 4. Configure the EIA API key

VoltBuddy can run without live EIA data, but live grid and generation-mix features require an EIA API key.

Set it in your shell:

```bash
export EIA_API_KEY="your-api-key"
```

Do not commit API keys to Git.

### 5. Start FastAPI

```bash
python3 -m uvicorn main:app --reload
```

The backend will normally be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Frontend Setup

From the frontend folder:

```bash
npm install
npm run dev
```

The Vite development server normally runs at:

```text
http://localhost:5173
```

The backend CORS configuration currently allows:

```text
http://localhost:5173
http://127.0.0.1:5173
```

## Running Tests

VoltBuddy includes automated backend tests.

From the backend folder:

```bash
python3 -m pytest
```

Current verified result:

```text
30 passed
```

The suite covers:

- Electricity-rate windows
- Invalid tariff inputs
- Deterministic optimization decisions
- Critical-appliance safety behavior
- Non-interruptible appliance safety behavior
- Grid-demand score effects
- Generation-mix score effects
- Recommendation generation
- Appliance API routes
- Home API routes
- Simulation API behavior
- Simulation persistence
- Missing EIA API-key behavior
- Request validation

The tests use an in-memory SQLite database so they do not modify the local PostgreSQL development database.

## Docker

The repository includes:

```text
Dockerfile
docker-compose.yml
.dockerignore
```

The Docker configuration supports a FastAPI backend container and PostgreSQL container.

The local development machine used for this project runs macOS Monterey 12.7.4. Current Docker Desktop builds require a newer macOS version, and the available Podman virtualization path on this machine could not successfully start a Linux VM. As a result, the container configuration is included in the project but has not been locally runtime-tested on this Mac.

Normal non-containerized development works locally with Python, Uvicorn, and PostgreSQL.

## Environment Variables

### `DATABASE_URL`

Optional locally.

Default:

```text
postgresql://localhost/voltbuddy
```

Container example:

```text
postgresql://voltbuddy:voltbuddy@db:5432/voltbuddy
```

### `EIA_API_KEY`

Required only for live EIA grid and generation-mix data.

If the key is not configured, VoltBuddy returns an `available: false` response for the live grid endpoints instead of failing the application.

## Explainability

VoltBuddy is designed so users can understand why a recommendation was made.

Each appliance result can include:

- Optimization score
- Decision
- Current status
- Score factors
- Human-readable explanation
- Normal hourly cost
- Optimized hourly cost
- Estimated hourly savings
- Whether the appliance is eligible to pause

This keeps automated recommendations transparent and preserves user control.

## Current Status

Implemented features include:

- React frontend
- FastAPI backend
- PostgreSQL persistence
- Dynamic appliance retrieval
- Simulation persistence
- Simulation history
- Cumulative savings
- Electricity-price chart
- Savings chart
- Custom appliances
- Saved homes
- Georgia Power time-of-use rate model
- Live EIA grid-demand data
- Carbon-aware generation-mix signal
- Deterministic optimization engine
- Explainable recommendations
- Input validation
- Loading and error states
- Empty states
- Frontend navigation
- Insights UI
- Docker configuration
- Modular backend architecture
- Automated backend test suite
- Project documentation

## Project Goals

VoltBuddy is intended to demonstrate:

- Full-stack application development
- REST API design
- Relational database integration
- External API integration
- Deterministic decision systems
- Explainable optimization
- Validation and error handling
- Automated testing
- Modular backend architecture
- Practical energy-data modeling

## Limitations

VoltBuddy is a simulator and portfolio project.

It does not currently:

- Control real smart plugs or appliances
- Forecast future grid carbon intensity
- Reproduce a complete Georgia Power bill
- Account for every tariff, tax, rider, or utility fee
- Guarantee savings
- Automatically migrate database schemas
- Replace utility-provided billing information

Live grid data may also be delayed or temporarily unavailable depending on the EIA API.

## Future Improvements

Potential future improvements include:

- Real smart-plug integrations
- User authentication
- Per-user homes and simulation history
- Database migrations with Alembic
- Broader utility-rate support
- Forecast-based load shifting
- Historical carbon-intensity analysis
- Deployment to a public cloud environment
- Continuous integration
- Frontend automated tests
- More detailed appliance scheduling

## Author

**Saleah Mitchell**

Computer Science student building VoltBuddy as a full-stack software engineering portfolio project.
