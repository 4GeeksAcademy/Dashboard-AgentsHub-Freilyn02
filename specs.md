# AgentHub Admin Dashboard - Technical Specifications

## 1. Product Description
AgentHub is a SaaS platform where businesses can rent pre-configured AI agents equipped with specific skills (e.g., web scraping, document reading, calendar management). This internal Administration Dashboard allows administrators to monitor revenue, manage users and agents, review available skills, track rentals, and debug system errors.

## 2. Tech Stack & Constraints
- **Frontend:** Semantic HTML5.
- **Styling:** Tailwind CSS via CDN (No custom CSS files, no inline `style` attributes).
- **Interactivity:** Vanilla JavaScript only (No frontend frameworks like React/Vue, no jQuery, no build tools).
- **Data:** 100% hardcoded mock data. No API or backend connections.

---

## 3. Section Specifications

### 3.1. Dashboard
1. **Metrics Grid:** A responsive 2x2 grid containing four metric cards: Total Revenue (this month), Total Loss (discounts/coupons), Active Agents, and Failing Agents. Each card includes a descriptive icon, a text label, and a prominent hardcoded value.
2. **Visual Accents:** Metric cards use distinct border or background accent colors based on their type (e.g., green for revenue, red for failing agents) and feature subtle shadow effects (`shadow-sm`).
3. **Activity Placeholder:** Below the grid, a full-width container with a dashed border (`border-dashed`) and a centered text label represents the weekly activity chart placeholder.

### 3.2. User Management
1. **Data Table:** A clean table listing at least 5 mock users with columns for Name, Email, Plan (e.g., Premium, Basic), and Status (displayed using colored badges).
2. **Action Dropdown:** Each row features a generic action button (⋮) that triggers a absolute-positioned dropdown menu with "View Details" and "Delete" options.
3. **Details Modal:** Clicking "View Details" opens a fixed overlay modal displaying the full user profile. The modal closes smoothly by clicking an explicit close button or the dark backdrop overlay.

### 3.3. Agent Management
1. **Agent List:** A structured list displaying at least 4 AI agents with columns or cards showing Agent Name, Owner, Status Badge (Active / Inactive / Failing), and a collapsible Skills section.
2. **Collapsible Skills Accordion:** Associated skills are hidden by default. Clicking an expand button reveals the skills list with a smooth CSS transition effect.
3. **Configuration Modal:** The action dropdown contains a "Configure" option that opens a modal containing the agent's system prompt inside an editable `<textarea>`.

### 3.4. Skills Catalogue
1. **Catalogue Grid:** A grid layout displaying at least 4 available skills. Each skill card shows the skill name, a brief description, and a counter badge showing how many agents currently use it.
2. **Contextual Help:** A callout banner at the top explains what a "Skill" means within the context of the AgentHub ecosystem.
3. **Actions:** Each skill includes a dropdown menu with "View Details" and "Delete" options.

### 3.5. Agent Hirings (Contracts)
1. **Contracts Table:** A table with at least 4 entries showing Client Name, Rented Agent, Contracted Skills, Contract Dates, and Total Amount Paid.
2. **Pricing Breakdown Modal:** The action dropdown includes a "View Details" option that displays a breakdown modal containing itemized prices for each contracted skill.

### 3.6. Error Log
1. **Log Feed:** A sequential list of at least 6 hardcoded execution errors, displaying a Timestamp, Agent Name, Error Type, and a short Description.
2. **Severity Badges:** Errors are visually categorized by severity using color-coded badges (e.g., Red for Critical, Yellow for Warning).
3. **Resolution Action:** Each entry has an action dropdown allowing administrators to open a modal with the full error stack trace or mark the error as resolved.

---

## 4. Component Inventory
- **Sidebar Navigation:** A persistent vertical menu displaying links to all six sections with visual indicators for the active route.
- **Metric Card:** Reusable indicator block with an icon, title, and numerical value.
- **Action Dropdown (⋮):** A toggleable contextual menu attached to list/table rows.
- **Modal Overlay:** A reusable centered popup backdrop for detail screens.
- **Status Badge:** Color-coded pill components (`bg-green-100`, `bg-red-100`, etc.) for visual states.
- **Dark Mode Toggle:** A persistent button in the top navigation bar to switch utility themes.

---

## 5. Acceptance Criteria
1. **Git History Verification:** `SPECS.md` must be committed to the repository before any HTML files are created.
2. **Single-Page or Multi-Page Structure:** The application must present all 6 sections seamlessly using semantic HTML tags (`<nav>`, `<main>`, `<section>`).
3. **Tailwind Framework Integration:** Entire styling must rely on Tailwind utility classes, including `dark:` modifiers for all core elements.
4. **Dropdown Behavior:** Clicking any (⋮) button opens its specific dropdown. Clicking outside of it must close it automatically.
5. **Modal Management:** All modals must pop up centered over a backdrop and safely close when clicking the close button or the backdrop itself.
6. **Accordion Transition:** The agent skills list must expand and collapse with an animated max-height or opacity transition.
7. **Theme Persistence:** The theme state (Light/Dark) must stay consistent across the entire browsing session.
