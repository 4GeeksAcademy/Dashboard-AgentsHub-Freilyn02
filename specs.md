# Freily Agent - Product And UX Specifications

## 1. Product Overview

Freily Agent is an internal administration dashboard for operating and supervising AI agents inside a SaaS-style orchestration environment. The interface is implemented as a single HTML entry point with simulated SPA navigation, hardcoded datasets, reusable modal behavior, and a native light/dark theme toggle.

The product is positioned as a control center for monitoring agent activity, managing users and contracts, reviewing skills, and inspecting operational errors.

## 2. Current Product Naming

- Product name in the interface: **Freily Agent**
- Sidebar brand label: **Freily Agent**
- Header title: **Freily Agent**

## 3. Technical Constraints

- Frontend architecture: semantic HTML5 in a single document.
- Styling system: Tailwind CSS via CDN plus a small inline `<style>` block for global theme refinements.
- Interactivity: vanilla JavaScript only.
- Data model: hardcoded mock data only.
- No build system, no component framework, and no API dependency for the UI.

## 4. Design System

### 4.1. Visual Direction

The interface follows a minimal, high-contrast visual system inspired by Uber Tech administration surfaces.

### 4.2. Core Design Rules

- Light mode uses pure white backgrounds and pure black text.
- Dark mode is controlled by the `dark` class on the root element.
- Containers use flat surfaces with thin borders instead of heavy shadows.
- Corners are restrained and mostly squared or subtly rounded.
- Tables are clean, dense, and use fine separator lines.
- Accent usage is limited and functional rather than decorative.

### 4.3. Color Behavior

#### Light Mode

- Page background: `#FFFFFF`
- Primary text: `#000000`
- Secondary text: `#545454`
- Container borders: `#E2E2E2`
- Table separators: `#EEEEEE`

#### Dark Mode

- Enabled through `document.documentElement.classList.toggle('dark', isDark)`
- All major surfaces rely on Tailwind `dark:` utilities for inversion and contrast.

## 5. Information Architecture

The dashboard exposes six primary sections:

1. Dashboard
2. User Management
3. Agent Management
4. Skills
5. Agent Contracts
6. Error Log

These sections live in the same page and are shown or hidden through SPA-style client-side navigation.

## 6. Navigation Model

### 6.1. Sidebar Navigation

- The left sidebar is persistent on desktop.
- On mobile, the sidebar opens through a hamburger trigger and is paired with a backdrop.
- Navigation links use hash targets such as `#dashboard` and `#user-management`.

### 6.2. SPA Behavior

When a sidebar item is clicked:

- The current visible section is hidden with the `hidden` class.
- The target section removes `hidden` and becomes visible.
- Only one main section is visible at a time.
- On small screens, the sidebar closes automatically after navigation.

### 6.3. Default Route

- The application initializes by showing the `dashboard` section.

## 7. Section Specifications

### 7.1. Dashboard

Purpose: provide a quick operational summary.

Current content:

- Four metric cards.
- Metrics include active agents, automation resolution, pending tickets, and user satisfaction.
- Cards use flat borders and restrained contrast rather than elevated card styling.

### 7.2. User Management

Purpose: show the active user roster and relationship to agents.

Current content:

- Responsive data table.
- Columns: User, Role, Assigned Agent, Status, Actions.
- Five hardcoded users.
- Status values are represented as flat badges using the official states:
	- Active
	- Inactive
	- Failing

### 7.3. Agent Management

Purpose: inspect agent runtime state and configure prompts.

Current content:

- Responsive table.
- Columns: expand control, Agent, Channel, State, Conversations, Actions.
- Expandable skill panels per row.
- A `Reset Hotfix Status` action.

Interactive behavior:

- Skill lists collapse and expand with animated `max-height` transitions.
- `Configure` opens a reusable modal with a prompt editor in a `<textarea>`.

### 7.4. Skills

Purpose: show the active skill inventory associated with users and agents.

Current content:

- Responsive table.
- Columns: Skill, Agent, Owner User, Version, Status, Actions.
- Skills are rendered as independent flat badges.
- Current mock skills include:
	- Document Reading
	- Calendar Management
	- Intent Classification
	- Email Triage
	- Mobile Concierge

### 7.5. Agent Contracts

Purpose: describe commercial contracts associated with agents.

Current content:

- Responsive table.
- Columns: Contract ID, Agent, Account User, Plan, Renewal, Actions.
- Current canonical agents for this section:
	- Nova
	- Atlas
	- CryptoBot
	- Arom

Interactive behavior:

- `View detail` opens a reusable modal with itemized pricing breakdowns.
- Contract detail examples include per-skill monthly fees such as `Web Browsing: $50/mo`.

### 7.6. Error Log

Purpose: expose recent runtime incidents for troubleshooting.

Current content:

- Responsive table rendered from a JavaScript array (`errorLogEntries`).
- Columns: Timestamp, Agent, User, Level, Message, Actions.
- Current mock agents in this section:
	- Nova
	- Atlas
	- CryptoBot
	- Arom

Interactive behavior:

- Table rows are rendered dynamically from state.
- If the array becomes empty, the UI displays `No hay errores recientes`.
- `View detail` opens a modal with a simulated stack trace in a readonly `<textarea>`.

## 8. Shared Components Inventory

### 8.1. Sidebar

- Persistent desktop navigation.
- Mobile overlay mode with hamburger trigger.

### 8.2. Header

- Dynamic formatted date label.
- Main title: Freily Agent.
- Compact theme toggle button.

### 8.3. Metric Card

- Reusable summary container.
- Flat border treatment.
- Large numeric emphasis.

### 8.4. Data Table

- Shared visual grammar across all administrative sections.
- Overflow-safe horizontal scrolling on narrow screens.
- Thin separators and compact spacing.

### 8.5. Status Badge

Official project states:

- Active: green flat badge.
- Inactive: gray flat badge.
- Failing: red flat badge.

### 8.6. Skill Badge

- Independent text capsule for a single skill label.
- Used in the Skills table as clean non-merged tokens.

### 8.7. Row Action Menu

- Triggered by the `⋮` button.
- Floating menu positioned near the invoking control.
- Auto-closes on outside click, resize, or scroll.

### 8.8. Reusable Modal

- Centered overlay container.
- Shared close controls:
	- explicit close button
	- close icon
	- backdrop click

### 8.9. Theme Toggle

- Compact icon button in the header.
- Persists theme choice in `localStorage`.
- Uses the root `dark` class only.

## 9. Interactive Behaviors

### 9.1. Theme Toggle

- Clicking the header theme control toggles dark mode by adding or removing `dark` on `document.documentElement`.
- Theme preference is persisted as `light` or `dark` in `localStorage`.
- If no preference exists, the UI falls back to `prefers-color-scheme`.

### 9.2. SPA Section Switching

- Sidebar navigation behaves like an in-page SPA.
- Only the selected main section is visible at one time.

### 9.3. Agent Skill Accordions

- Expand and collapse inline beneath agent rows.
- Use transition classes for animated reveal.

### 9.4. Dynamic Error Log Rendering

- Error Log is not hardcoded directly in the DOM.
- It is rendered from an in-memory array and refreshed through `renderErrorLog()`.

### 9.5. Hotfix Reset

Clicking `Reset Hotfix Status`:

- Resets selected agent and skill statuses to healthy states.
- Clears the `errorLogEntries` array.
- Re-renders Error Log to show an empty-state message.

### 9.6. Contextual Modal Content

#### Agent Management

- `Configure` opens a textarea with a simulated editable system prompt.

#### Agent Contracts

- `View detail` opens itemized price breakdown content.

#### Error Log

- `View detail` opens a simulated stack trace in a readonly textarea.

## 10. Data Consistency Rules

- Product name must remain **Freily Agent** in visible branding.
- The theme system must remain root-class driven through `dark`.
- Status taxonomy must remain restricted to Active, Inactive, and Failing where standardized badges are used.
- Contracts and error logs should keep the agreed mock agent set when consistency is required:
	- Nova
	- Atlas
	- CryptoBot
	- Arom

## 11. Acceptance Criteria

### 11.1. Branding

- The visible application branding must read **Freily Agent** in the sidebar and main header.

### 11.2. Visual System

- Light mode must use a flat Uber-style white/black palette.
- Dark mode must be controlled only through the root `dark` class.
- Core surfaces must use thin borders and avoid heavy shadows.

### 11.3. Navigation

- Clicking a sidebar link must hide the current section and show the selected one.
- On mobile, the sidebar must close after a navigation click.

### 11.4. Row Action Menus

- Only one floating action menu may be open at a time.
- Clicking outside the menu must close it.

### 11.5. Modals

- The modal system must support reusable contextual content by section.
- Modals must close from backdrop click and explicit close controls.

### 11.6. Agent Management Behavior

- Skills must expand and collapse inline.
- `Configure` must open an editable textarea prompt.

### 11.7. Contracts Behavior

- `View detail` must display itemized contract pricing.

### 11.8. Error Log Behavior

- Error Log rows must come from the JavaScript data array.
- `View detail` must display a simulated stack trace.
- Resetting hotfix status must clear the error history state and render the empty-state message.

### 11.9. Theme Persistence

- Theme preference must survive reloads through `localStorage`.

## 12. Out Of Scope

- Real backend persistence.
- Authentication.
- API-driven routing.
- Real-time metrics or live operational monitoring.
- Server-sourced modal content.
