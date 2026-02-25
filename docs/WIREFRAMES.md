# Wireframes - Early Years Schools Pollution Monitor

## Overview

This document provides wireframes and layout specifications for all key pages in the Early Years Schools Pollution Monitor application.

---

## 1. Main Dashboard - Interactive Map View

**Page:** `/map/`  
**User:** Authenticated subscriber  
**Purpose:** Primary interface for viewing school locations and air quality data

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║  Early Years Schools Pollution Monitor        [Home] [Map] [Subscription] [Admin] ║ │
│ ║                                      [Logout] [👤 username]  ║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                          │ │
│  │                   LEAFLET MAP VIEW                       │ │
│  │                                                          │ │
│  │    📍 [Green Pin]  - Good Air Quality                   │ │
│  │    📍 [Yellow Pin] - Moderate Air Quality               │ │
│  │    📍 [Orange Pin] - Poor Air Quality                   │ │
│  │    📍 [Red Pin]    - Very Poor Air Quality              │ │
│  │                                                          │ │
│  │         [School markers distributed across map]         │ │
│  │                                                          │ │
│  │  ┌────────────────────────┐                            │ │
│  │  │ 📍 Hill Mead School    │ <-- Popup on marker click  │ │
│  │  │ Address: SW12 0HR      │                            │ │
│  │  │                        │                            │ │
│  │  │ Current Air Quality:   │                            │ │
│  │  │ NO₂:  28.4 µg/m³ ✓    │                            │ │
│  │  │ PM2.5: 12.1 µg/m³ ✓   │                            │ │
│  │  │ PM10:  18.5 µg/m³ ✓   │                            │ │
│  │  │                        │                            │ │
│  │  │ Data: Breathe London   │                            │ │
│  │  │ Updated: 14:00 today   │                            │ │
│  │  │                        │                            │ │
│  │  │ [View Details] [✕]    │                            │ │
│  │  └────────────────────────┘                            │ │
│  │                                                          │ │
│  │                       [+] [-] Zoom controls             │ │
│  │                       [⊕] Locate me                     │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Legend:                                                       │
│  🟢 Good (0-40 µg/m³)  🟡 Moderate (41-70)                   │
│  🟠 Poor (71-100)      🔴 Very Poor (>100)                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Full-screen interactive map (Leaflet.js)
- Color-coded school markers based on PM2.5 levels
- Click markers to open popup with current readings
- Zoom/pan controls visible
- Mobile-responsive: full viewport on mobile devices
- Legend shows air quality thresholds

**Responsive Behavior:**

- Desktop: Map fills viewport below navbar
- Tablet: Same layout, touch-friendly controls
- Mobile: Full screen, collapsible popup

---

## 2. Subscription Page

**Page:** `/subscriptions/`  
**User:** Unauthenticated or user without active subscription  
**Purpose:** Present subscription offering and Stripe checkout

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║  Early Years Schools Pollution Monitor        [Home] [Map] [Login] [Subscribe]   ║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│           Subscribe to Access the Air Quality Dashboard        │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                                                        │   │
│  │              💨 Early Years Schools Pollution Monitor                        │   │
│  │                                                        │   │
│  │                  £2.50 / month                         │   │
│  │                                                        │   │
│  │  ✓ Real-time air quality data from LAQN & Breathe     │   │
│  │    London sensors                                      │   │
│  │                                                        │   │
│  │  ✓ Interactive map showing 133 schools in Lambeth &   │   │
│  │    Southwark                                           │   │
│  │                                                        │   │
│  │  ✓ School-specific pollution levels (NO₂, PM2.5,      │   │
│  │    PM10)                                               │   │
│  │                                                        │   │
│  │                                                        │   │
│  │           ┌──────────────────────────┐                │   │
│  │           │   📦 Subscribe Now       │                │   │
│  │           └──────────────────────────┘                │   │
│  │                                                        │   │
│  │        🔒 Secure payment powered by Stripe             │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│                                                                │
│  If already subscribed: [Manage Subscription]                 │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Centered card layout with clear pricing
- Three key features listed
- Prominent "Subscribe Now" CTA button
- Stripe branding for trust
- Link to manage existing subscription

**Responsive Behavior:**

- Desktop: Centered card, max-width 600px
- Mobile: Full width with padding, larger buttons

---

## 3. Login Page

**Page:** `/login/`  
**User:** Unauthenticated  
**Purpose:** User authentication

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║  Early Years Schools Pollution Monitor        [Home] [Login] [Subscribe]         ║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│                          Login                                 │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                                                        │   │
│  │  Username: ________________________________            │   │
│  │                                                        │   │
│  │  Password: ________________________________            │   │
│  │                                                        │   │
│  │                                                        │   │
│  │           ┌──────────────────────────┐                │   │
│  │           │       Login              │                │   │
│  │           └──────────────────────────┘                │   │
│  │                                                        │   │
│  │  For demo: Create an account via admin panel first    │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Simple two-field form (username, password)
- Standard Django auth styling
- Demo note for assessors
- Redirects to `/map/` after successful login

**Responsive Behavior:**

- Desktop: Centered form, max-width 400px
- Mobile: Full width with padding

---

## 4. Admin Panel - Schools List

**Page:** `/admin/schools/school/`  
**User:** Staff user or superuser  
**Purpose:** Manage school data

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║ Django administration          [View site] [Change password]║ │
│ ║                                              [Log out] GK    ║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Home › Schools › Schools                                      │
│                                                                │
│  ┌─ FILTER ──────────────┐  Select school to change          │
│  │                       │                                    │
│  │ By data source        │  [🔍 Search] ________________      │
│  │  ○ All                │                                    │
│  │  ○ DIRECT (8)         │  ┌────────────────────────────┐   │
│  │  ○ ADJUSTED (32)      │  │ + Add school               │   │
│  │  ○ LAEI (93)          │  └────────────────────────────┘   │
│  │                       │                                    │
│  │ By borough            │  ┌──────────────────────────────┐ │
│  │  ○ Lambeth (85)       │  │ School Name     | Borough | DS│ │
│  │  ○ Southwark (48)     │  ├──────────────────────────────┤ │
│  │                       │  │ Hill Mead       | Lambeth | D │ │
│  │ By school type        │  │ Rosendale       | Lambeth | A │ │
│  │  ○ Primary (115)      │  │ St Helen's      | Lambeth | L │ │
│  │  ○ Nursery (18)       │  │ Judith Kerr     | Lambeth | D │ │
│  │                       │  │ ...                           │ │
│  └───────────────────────┘  └──────────────────────────────┘ │
│                                                                │
│  Showing 1-25 of 133 schools              [1] [2] [3] ... [6] │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Standard Django admin interface
- Filter sidebar (data source, borough, school type)
- Search functionality
- List display shows key fields
- Pagination for large datasets
- Add new school button

---

## 5. Admin Panel - Sensor Management

**Page:** `/admin/air_quality/sensor/`  
**User:** Staff user or superuser  
**Purpose:** Monitor and manage air quality sensors

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║ Django administration          [View site] [Change password]║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Home › Air Quality › Sensors                                  │
│                                                                │
│  ┌─ FILTER ──────────────┐  Select sensor to change          │
│  │                       │                                    │
│  │ By network            │  [🔍 Search] ________________      │
│  │  ○ All                │                                    │
│  │  ○ LAQN (16)          │  ┌────────────────────────────┐   │
│  │  ○ BREATHE (26)       │  │ + Add sensor               │   │
│  │                       │  └────────────────────────────┘   │
│  │ By site type          │                                    │
│  │  ○ Urban bg (15)      │  ┌──────────────────────────────┐ │
│  │  ○ Roadside (12)      │  │ Site Code | Name    | Network│ │
│  │  ○ Kerbside (9)       │  ├──────────────────────────────┤ │
│  │                       │  │ LB1      | Lambeth | LAQN  │✓│ │
│  │ By status             │  │ BRE1234  | Clapham | BREATHE│✓│ │
│  │  ○ Active (38)        │  │ SK6      | Peckham | LAQN  │✓│ │
│  │  ○ Inactive (4)       │  │ ...                           │ │
│  │                       │  └──────────────────────────────┘ │
│  └───────────────────────┘                                    │
│                                                                │
│  Showing 1-25 of 42 sensors               [1] [2]             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Filter by network (LAQN/Breathe London)
- Filter by site type and active status
- Green checkmark for active sensors
- Search by site code or name

---

## 6. Subscription Management Page

**Page:** `/subscriptions/manage/`  
**User:** Authenticated subscriber  
**Purpose:** View current subscription status

```
┌────────────────────────────────────────────────────────────────┐
│ ╔════════════════════════════════════════════════════════════╗ │
│ ║  Early Years Schools Pollution Monitor        [Home] [Map] [Subscription] [Admin] ║ │
│ ║                                      [Logout] [👤 username]  ║ │
│ ╚════════════════════════════════════════════════════════════╝ │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│                   Manage Your Subscription                     │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                                                        │   │
│  │  Status: 🟢 Active                                     │   │
│  │                                                        │   │
│  │  Current Period:                                       │   │
│  │  January 15, 2026 - February 15, 2026                  │   │
│  │                                                        │   │
│  │  Days Remaining: 17 days                               │   │
│  │                                                        │   │
│  │  Amount: £2.50/month                                   │   │
│  │                                                        │   │
│  │  ─────────────────────────────────────────             │   │
│  │                                                        │   │
│  │  To cancel your subscription, contact Stripe           │   │
│  │  support or manage via your Stripe customer portal.    │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│              [← Back to Dashboard]                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Key Features:**

- Clear status indicator (Active/Canceled)
- Billing period dates
- Days remaining countdown
- Simple cancel instructions

---

## 7. Mobile View - Map (Portrait)

**Device:** iPhone/Android (375px width)  
**Orientation:** Portrait

```
┌─────────────────┐
│Early Years Sch. │ ← Header (truncated)
│Pollution Monitor│
│Map Schools Login│ ← Nav links wrap
├─────────────────┤
│                 │
│   📍📍          │
│       📍        │
│  📍             │
│          📍     │
│    📍  📍       │
│                 │
│  [+] [-]        │ ← Zoom controls
│   [⊕]           │ ← Locate me
│                 │
│                 │
│ ┌─────────────┐ │
│ │Hill Mead Sch│ │ ← Compact popup
│ │NO₂: 28 µg/m³│ │
│ │PM2.5: 12 ✓  │ │
│ │[Details] [✕]│ │
│ └─────────────┘ │
│                 │
│                 │
│ 🟢🟡🟠🔴 Legend │ ← Compact legend
└─────────────────┘
```

**Key Features:**

- Standard horizontal navigation (wraps on small screens)
- No hamburger menu - simple link layout
- Full-screen map for maximum visibility
- Touch-friendly markers and controls
- Compact popup with essential info
- Bottom legend remains visible

---

## 8. Stripe Checkout (External)

**Flow:** User clicks "Subscribe Now" → Redirects to Stripe Checkout

```
┌────────────────────────────────────────────────────────────────┐
│                         stripe                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Pay Early Years Schools Pollution Monitor                                           │
│                                                                │
│  Email: ___________________________________                    │
│                                                                │
│  Card information                                              │
│  ┌────────────────────────────────────────┐                   │
│  │ 1234 5678 9012 3456                    │                   │
│  └────────────────────────────────────────┘                   │
│  ┌─────────────┬──────────────────────────┐                   │
│  │ MM / YY     │  CVC                     │                   │
│  └─────────────┴──────────────────────────┘                   │
│                                                                │
│  Cardholder name                                               │
│  _______________________________________________               │
│                                                                │
│  Country: United Kingdom ▼                                     │
│                                                                │
│  [ ] Save card for future purchases                            │
│                                                                │
│         ┌──────────────────────────┐                          │
│         │   Subscribe - £2.50      │                          │
│         └──────────────────────────┘                          │
│                                                                │
│  Powered by stripe                                             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Note:** This is Stripe's hosted checkout page, not part of your application UI.

---

## Design System

### Color Palette

**Air Quality Indicators:**

- 🟢 Good: `#28a745` (Green)
- 🟡 Moderate: `#ffc107` (Yellow)
- 🟠 Poor: `#fd7e14` (Orange)
- 🔴 Very Poor: `#dc3545` (Red)

**Brand Colors:**

- Primary: `#007bff` (Bootstrap blue)
- Success: `#28a745`
- Danger: `#dc3545`
- Warning: `#ffc107`

**Neutrals:**

- Text: `#212529` (Dark gray)
- Background: `#f8f9fa` (Light gray)
- White: `#ffffff`

### Typography

- **Headings:** System font stack (Helvetica, Arial, sans-serif)
- **Body:** 16px base font size
- **Mobile:** 14px minimum for readability

### Spacing

- Container padding: 1rem (mobile), 2rem (desktop)
- Card padding: 1.5rem
- Button padding: 0.75rem 1.5rem

### Breakpoints

- Mobile: < 576px
- Tablet: 576px - 768px
- Desktop: > 768px

---

## Interaction Patterns

### Map Interactions

1. **Click marker** → Show popup with school details
2. **Click popup [View Details]** → Navigate to detailed school page (if implemented)
3. **Click popup [✕]** → Close popup
4. **Zoom buttons** → Zoom in/out on map
5. **Locate me** → Center map on user's location

### Form Submissions

1. **Subscribe button** → POST to `/subscriptions/checkout/` → Redirect to Stripe
2. **Login form** → POST to `/login/` → Redirect to `/map/`
3. **Admin forms** → Standard Django admin behavior

### Loading States

- Map loading: "Loading schools..." message with spinner
- Data fetching: Subtle loading indicator on navbar
- Form submission: Button shows "Processing..." state

---

## Accessibility Considerations

- **Keyboard Navigation:** All interactive elements accessible via Tab key
- **Screen Readers:** ARIA labels on map controls and buttons
- **Color Contrast:** All text meets WCAG AA standards (4.5:1 ratio)
- **Focus Indicators:** Visible outline on focused elements
- **Alt Text:** All informational images have descriptive alt text

---

## Notes for Assessors

These wireframes represent the **implemented** features of Early Years Schools Pollution Monitor. The design follows Bootstrap conventions for rapid development while maintaining clean, professional aesthetics. Mobile responsiveness is achieved through Bootstrap's grid system and custom CSS media queries.

**Tools Used:**

- Frontend: Bootstrap 5, Leaflet.js for mapping
- Backend: Django templates with minimal JavaScript
- Payment: Stripe Checkout (hosted page)

---

## Future Enhancements (Not Wireframed)

- Filter controls on map page
- School comparison side-by-side view
- Historical trends graphs
- Alert notification system
- Data quality dashboard for admins
- PDF export functionality
