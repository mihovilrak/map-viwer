# Map Viewer Frontend

React + Vite + TypeScript frontend application for viewing geospatial vector and raster layers. Displays a list of available layers and renders them on an interactive MapLibre GL map with support for both vector tiles (PostGIS via Tegola) and raster tiles (COGs via rio-tiler).

## Overview

The frontend provides:
- **Layer Browser**: Sidebar listing all available layers from the backend
- **Interactive Map**: MapLibre GL map with OpenStreetMap base layer
- **Vector Layer Support**: Displays PostGIS vector layers as vector tiles
- **Raster Layer Support**: Displays COG raster layers as raster tiles
- **Layer Navigation**: Click to zoom to layer extent and add to map
- **Responsive UI**: Clean sidebar + map layout

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx              # Main application component
│   ├── App.test.tsx         # Unit tests
│   ├── App.interactions.test.tsx  # Interaction tests
│   ├── main.tsx             # Application entrypoint
│   ├── styles.css           # Global styles
│   └── vite-env.d.ts        # Vite type definitions
├── e2e/                     # End-to-end tests (Playwright)
├── coverage/                # Test coverage reports
├── package.json             # Dependencies and scripts
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite build configuration
├── vitest.config.ts         # Vitest test configuration
├── eslint.config.cjs        # ESLint configuration
├── playwright.config.ts     # Playwright E2E configuration
└── tsdoc.config.json        # TSDoc documentation configuration
```

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running (see `../backend/README.md`)
- Tegola service running (for vector tiles)

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
# Create .env file (optional)
# VITE_API_BASE_URL=http://localhost:8000
```

If `VITE_API_BASE_URL` is not set, the app defaults to the current origin or `http://localhost:8000`.

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`.

## Development

### Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Fix ESLint errors automatically |
| `npm run test` | Run unit tests (Vitest) |
| `npm run test:coverage` | Run tests with coverage report (60% threshold) |
| `npm run typecheck` | Type check with TypeScript compiler |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check code formatting |
| `npm run docs:ts` | Generate TSDoc documentation |
| `npm run e2e` | Run end-to-end tests (Playwright) |

### Code Quality

The project uses:
- **ESLint**: Linting with Google TypeScript style guide
- **Prettier**: Code formatting
- **TypeScript**: Strict type checking
- **TSDoc**: Documentation generation

Run code quality checks:
```bash
# Lint
npm run lint

# Fix linting issues
npm run lint:fix

# Type check
npm run typecheck

# Format code
npm run format

# Check formatting
npm run format:check
```

### Testing

#### Unit Tests (Vitest)

Run unit tests:
```bash
npm test
```

Run with coverage (60% threshold):
```bash
npm run test:coverage
```

Coverage thresholds:
- Statements: 60%
- Branches: 60%
- Functions: 60%
- Lines: 60%

#### End-to-End Tests (Playwright)

Run E2E tests:
```bash
npm run e2e
```

**Note**: E2E tests require the application to be running. Set `E2E_BASE_URL` environment variable if the app is not at `http://localhost:5173`.

### Code Style

- Follow [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- Use TSDoc for documentation (`/** */` comments)
- TypeScript strict mode enabled
- Use functional components with React hooks
- Prefer named exports over default exports

### Documentation

Generate TypeScript documentation:
```bash
npm run docs:ts
```

Documentation will be generated in the `docs/` directory.

## Architecture

### Component Structure

- **App.tsx**: Main application component
  - Manages layer list state
  - Handles map initialization
  - Implements layer focus/navigation logic
  - Adds vector/raster layers to map dynamically

### Map Integration

- **MapLibre GL**: Open-source map rendering library
- **Base Layer**: OpenStreetMap tiles
- **Vector Tiles**: Served via `/tiles/vector/{layer}/{z}/{x}/{y}.pbf`
- **Raster Tiles**: Served via `/tiles/raster/{layer_id}/{z}/{x}/{y}.png`

### API Integration

The frontend communicates with the backend API:
- `GET /api/layers` - Fetch all available layers
- Vector tiles: `/tiles/vector/{layer_name}/{z}/{x}/{y}.pbf`
- Raster tiles: `/tiles/raster/{layer_id}/{z}/{x}/{y}.png`

API base URL is configurable via `VITE_API_BASE_URL` environment variable.

## Dependencies

### Runtime Dependencies
- `react` / `react-dom`: React framework
- `maplibre-gl`: Map rendering library
- `axios`: HTTP client for API requests

### Development Dependencies
- `vite`: Build tool and dev server
- `typescript`: Type checking
- `@vitejs/plugin-react`: React support for Vite
- `vitest`: Unit testing framework
- `@testing-library/react`: React testing utilities
- `@playwright/test`: End-to-end testing
- `eslint` / `@typescript-eslint/*`: Linting
- `prettier`: Code formatting
- `@microsoft/tsdoc`: Documentation generation

See `package.json` for complete list.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | Current origin or `http://localhost:8000` |

**Note**: Vite requires the `VITE_` prefix for environment variables to be exposed to the client.

## Building for Production

Build the production bundle:
```bash
npm run build
```

The output will be in the `dist/` directory, ready to be served by any static file server.

Preview the production build:
```bash
npm run preview
```

## Docker

The frontend can be containerized. See the main project `docker-compose.yml` for the full setup, or build manually:

```bash
# Build
docker build -t map-viewer-frontend .

# Run
docker run -p 5173:80 map-viewer-frontend
```

## Troubleshooting

### API Connection Issues
- Verify backend is running at the configured `VITE_API_BASE_URL`
- Check browser console for CORS errors
- Ensure backend `ALLOW_ORIGINS` includes the frontend URL

### Map Not Rendering
- Check browser console for MapLibre errors
- Verify MapLibre CSS is imported (should be in `main.tsx`)
- Ensure map container has explicit width/height

### Vector Tiles Not Loading
- Verify Tegola service is running
- Check backend is proxying requests correctly
- Verify layer exists in PostGIS database

### Raster Tiles Not Loading
- Verify COG files exist and are accessible
- Check backend rio-tiler service is working
- Verify layer metadata includes correct `provider: "cog"`

### Type Errors
- Run `npm run typecheck` to see all TypeScript errors
- Ensure all dependencies are installed: `npm install`
- Check `tsconfig.json` configuration

