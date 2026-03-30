# Frontend Design Decisions

## Architecture Overview

**Decision**: Server-side rendered HTML templates with Flask/Jinja2 + vanilla JavaScript + CSS via CDN
**Rationale**: 
- Requirements specify "no build step required"
- Need rapid development with existing Flask backend
- Static JavaScript for SSE, chat console, and streaming
- All forms use partial page updates via AJAX (no full page reloads)
- Simple deployment without separate frontend build process

**Alternative Considered**: React/TypeScript with Vite build step
- Would require Node.js toolchain and separate deployment
- More complex but better for large-scale SPA
- Not aligned with "no build step" requirement

## Technology Stack

### Frontend
- **HTML5**: Semantic markup
- **CSS**: Tailwind CSS via CDN (no build step)
- **JavaScript**: Vanilla ES6+ with Fetch API for AJAX
- **Charts**: Chart.js via CDN for usage dashboard
- **Icons**: Font Awesome via CDN
- **Code Editor**: CodeMirror via CDN for studio configuration

### Backend Integration
- **Flask-Jinja2**: Server-side templates with base layout
- **Flask-JWT-Extended**: JWT authentication with cookie support
- **Flask-Bcrypt**: Password hashing
- **Flask-CORS**: CORS headers for API requests

## Authentication Layer

### JWT Token Management
- Store access token in HttpOnly cookie for security
- Store refresh token in HttpOnly cookie
- Implement token refresh mechanism via /api/v1/auth/refresh
- Automatic token refresh before expiration

### Password Flow
- OAuth2 password grant flow implemented via custom endpoints
- Login form POST to /api/v1/auth/login
- Registration form POST to /api/v1/auth/register
- Password reset via email with secure tokens

### Session Management
- Server-side session tracking for audit logs
- Multiple device session support
- Session revocation via UI

## UI Component Design

### Layout
- Dark sidebar navigation with active state
- Responsive grid system (Tailwind)
- Mobile-first design with hamburger menu on small screens

### Pages & Routes
1. **Home** (`/`): Landing page with platform overview
2. **Marketplace** (`/marketplace`): Grid of agent cards with search/filter
3. **Studio** (`/studio`): Split-pane agent configuration with live console
4. **Dashboard** (`/dashboard`): Usage charts, cost counter, recent runs
5. **Scheduler** (`/scheduler`): Cron-style scheduling interface
6. **Workspace** (`/workspace`): Team management, roles, audit logs
7. **Billing** (`/billing`): Stripe checkout, subscription management, invoice history

### Component Library
- **Agent Card**: Icon, description, pricing badge, "Rent" button
- **Usage Chart**: Bar chart with Chart.js
- **Split Pane**: CSS grid for studio layout
- **Data Table**: Responsive table for recent runs
- **Form Components**: Consistent validation and error states

## State Management

### Client-side State
- Minimal state stored in memory (current user, tokens)
- No complex state management needed (not SPA)
- Page-specific state via JavaScript modules

### Server-side State
- User session in database
- JWT tokens for API authentication
- Flash messages for user feedback

## Real-time Features

### Server-Sent Events (SSE)
- `/api/v1/usage/stream` for real-time dashboard updates
- `/api/v1/studio/<agent_id>/stream` for agent run streaming
- Reconnection logic with exponential backoff

### WebSocket Alternative
- Consider WebSocket for bidirectional chat (future)
- Currently using SSE for server→client push

## API Integration Pattern

### RESTful API Calls
- Fetch API with interceptors for token refresh
- Consistent error handling (401 → redirect to login)
- Loading states for all async operations

### File Structure
```
app/templates/
├── base.html              # Base template with sidebar
├── home.html
├── marketplace.html
├── studio.html
├── dashboard.html
├── scheduler.html
├── workspace.html
└── billing.html

static/
├── js/
│   ├── auth.js           # Authentication utilities
│   ├── api.js            # API client with interceptors
│   ├── sse.js            # SSE client library
│   ├── dashboard.js      # Chart initialization
│   ├── studio.js         # Code editor and console
│   └── marketplace.js    # Search and filtering
├── css/
│   └── custom.css        # Additional custom styles
└── images/               # Icons and logos
```

## Performance Considerations

### Asset Loading
- CSS and JS via CDN with SRI (Subresource Integrity)
- Lazy loading for non-critical JavaScript
- Image optimization with responsive sizes

### Caching Strategy
- Static assets with long cache headers
- API responses with appropriate cache-control
- Service Worker for offline capability (future)

## Security Considerations

### XSS Prevention
- Jinja2 auto-escaping for dynamic content
- Content Security Policy (CSP) headers
- Safe DOM manipulation with textContent (not innerHTML)

### CSRF Protection
- Double-submit cookie pattern for AJAX requests
- SameSite cookies for authentication

### Authentication Security
- HttpOnly cookies for JWT storage
- Secure flag in production
- Token expiration and rotation

## Testing Strategy

### Unit Tests
- JavaScript modules with Jest (future)
- API integration tests

### Browser Testing
- Cross-browser compatibility (Chrome, Firefox, Safari)
- Mobile responsiveness testing

## Deployment

### Integration with Existing Flask App
- Templates served from Flask routes
- Static files served via Flask static folder
- No separate build process required

### Future Migration Path
- Can evolve to React SPA by replacing templates with index.html
- API layer remains unchanged
- Progressive enhancement approach

## Decisions Log

### 2024-03-31: Server-side Rendering over SPA
**Decision**: Use Flask/Jinja2 templates instead of React SPA
**Reason**: "No build step required" requirement
**Impact**: Simpler deployment, faster initial load, easier SEO
**Trade-off**: Less interactive UI, but can enhance with JavaScript

### 2024-03-31: Tailwind CSS via CDN
**Decision**: Use Tailwind CSS via CDN instead of local build
**Reason**: Avoid CSS build step while using utility-first CSS
**Impact**: Larger initial CSS load (~2MB) but simple setup
**Alternative**: Bootstrap via CDN (smaller) but less flexible

### 2024-03-31: Vanilla JavaScript over Framework
**Decision**: Use vanilla ES6+ instead of React/Vue
**Reason**: No build step, simpler integration with server-rendered pages
**Impact**: More manual DOM manipulation but no toolchain complexity

### 2024-03-31: Chart.js for Data Visualization
**Decision**: Use Chart.js via CDN for dashboard charts
**Reason**: Simple API, good documentation, works with SSE updates
**Alternative**: D3.js (more powerful but complex)

### 2024-03-31: CodeMirror for Studio Editor
**Decision**: Use CodeMirror for agent configuration editing
**Reason**: Lightweight, supports JSON syntax highlighting
**Alternative**: Monaco Editor (VS Code) but heavier

## Open Questions

1. **OAuth2 Implementation**: Which providers to support initially?
2. **Real-time Collaboration**: Need for multiplayer editing in studio?
3. **Offline Support**: Should we implement Service Worker for basic offline?
4. **Browser Support**: Which browsers to officially support?