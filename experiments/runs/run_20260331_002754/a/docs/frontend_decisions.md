# Frontend Design Decisions

## Architecture
- Separate frontend application (React + Vite) served on port 3000
- Backend API (FastAPI) on port 8000
- CORS enabled for localhost:3000
- JWT authentication with access/refresh tokens stored in secure HTTP-only cookies
- API calls with axios interceptors for automatic token refresh

## Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast dev server, optimized production build)
- **Routing**: React Router v6
- **State Management**: React Context + useReducer for auth, Zustand for UI state
- **HTTP Client**: Axios with interceptors
- **CSS Framework**: Bootstrap 5 via CDN (no build step for CSS)
- **Charts**: Chart.js for usage dashboard
- **Real-time**: EventSource for SSE, WebSocket for notifications
- **Form Handling**: React Hook Form with yup validation

## Authentication Flow
1. Login: POST /api/v1/auth/login → sets access_token and refresh_token as HTTP-only cookies
2. Token refresh: Intercept 401 responses, call /api/v1/auth/refresh with refresh_token
3. Logout: POST /api/v1/auth/logout → clears cookies, redirect to login
4. Protected routes: Check auth state, redirect if not authenticated

## Project Structure
```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/            # API client, axios config, interceptors
│   ├── components/     # Reusable UI components
│   ├── contexts/       # React contexts (Auth, Theme, etc.)
│   ├── hooks/          # Custom React hooks
│   ├── layouts/        # Page layouts (with sidebar)
│   ├── pages/          # Route components
│   ├── stores/         # Zustand stores
│   ├── types/          # TypeScript interfaces
│   └── utils/          # Helper functions
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Pages & Routes
- `/` - Home/Landing page
- `/login` - Login page
- `/register` - Registration page
- `/dashboard` - User dashboard with usage charts
- `/marketplace` - Agent marketplace grid
- `/studio` - Agent studio with split pane
- `/scheduler` - Task scheduler with cron editor
- `/workspace` - Team workspace management
- `/billing` - Billing dashboard with Stripe checkout
- `/memories` - Agent memory management

## Real-time Features
- **SSE**: `/api/usage/stream` for live dashboard updates
- **WebSocket**: `/ws` for task completion notifications
- **Polling**: Fallback for browsers without WebSocket support

## Deployment
- Docker container with nginx serving built assets
- Multi-stage build for production optimization
- Environment variables for API endpoint configuration

## Security Considerations
- HTTP-only cookies for JWT storage (mitigates XSS)
- CSRF tokens for state-changing operations
- Content Security Policy configured
- Input sanitization for user-generated content
- Rate limiting on frontend API calls

## Performance
- Code splitting with React.lazy()
- Asset optimization via Vite
- Cache headers for static assets
- Lazy loading for non-critical components

## Development Workflow
- Hot module replacement in development
- TypeScript strict mode enabled
- ESLint + Prettier for code quality
- Husky pre-commit hooks