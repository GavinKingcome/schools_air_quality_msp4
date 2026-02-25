# User Stories - Early Years Schools Pollution Monitor

## Project Overview

Early Years Schools Pollution Monitor provides real-time air quality monitoring for primary schools and nurseries in Lambeth and Southwark, helping parents, school staff, and administrators make informed decisions about outdoor activities and air quality management.

## Implementation Status

**Legend:**

- ✅ **IMPLEMENTED** - Feature complete and deployed
- 🔮 **PLANNED** - Future enhancement in backlog

**Current Status:**

- ✅ Implemented: 9 stories (56 points)
- 🔮 Planned: 9 stories (56 points)
- **Total:** 18 stories (112 points)

---

## Epic 1: Map Visualization & School Discovery

### US-001: View Interactive School Map ✅ IMPLEMENTED

**As a** parent or guardian  
**I want to** view an interactive map showing all schools with air quality indicators  
**So that** I can quickly see which schools have good or poor air quality

**Acceptance Criteria:**

- Map displays all schools in Lambeth and Southwark
- Schools are marked with colored pins indicating air quality levels
- Map is interactive (pan, zoom, click)
- Mobile responsive design
- Loads within 3 seconds

**Priority:** HIGH | **Story Points:** 5

---

### US-002: View School Details ✅ IMPLEMENTED

**As a** parent  
**I want to** click on a school marker to see detailed air quality information  
**So that** I can understand the pollution levels at that specific location

**Acceptance Criteria:**

- Popup shows school name, address, and current air quality readings
- Displays NO₂, NOx, PM2.5, PM10 levels with units (µg/m³)
- Shows data source (LAQN, Breathe London, or LAEI)
- Includes timestamp of last update
- Color-coded warnings if levels exceed WHO guidelines

**Priority:** HIGH | **Story Points:** 3

---

### US-003: Filter Schools by Air Quality 🔮 PLANNED

**As a** parent choosing a school  
**I want to** filter schools based on pollution levels  
**So that** I can identify schools with the best air quality

**Acceptance Criteria:**

- Filter options: "Good", "Moderate", "Poor", "Very Poor"
- Map updates in real-time when filters applied
- Shows count of schools in each category
- Clear/reset filter option available

**Priority:** MEDIUM | **Story Points:** 3

---

## Epic 2: Real-Time Data & Monitoring

### US-004: View Real-Time Sensor Data ✅ IMPLEMENTED

**As a** school administrator  
**I want to** see real-time pollution readings from nearby sensors  
**So that** I can make immediate decisions about outdoor activities

**Acceptance Criteria:**

- Data refreshes automatically every hour
- Shows readings from both LAQN and Breathe London sensors
- Displays sensor location and distance from school
- Historical trend graph (24 hours)
- Alert badge if levels exceed safe thresholds

**Priority:** HIGH | **Story Points:** 8

---

### US-005: Receive Air Quality Alerts 🔮 PLANNED

**As a** school headteacher  
**I want to** receive notifications when pollution levels are dangerous  
**So that** I can keep children indoors during high pollution episodes

**Acceptance Criteria:**

- Visual alert on dashboard when PM2.5 > 35 µg/m³ or NO₂ > 200 µg/m³
- Alert includes recommended actions
- Different severity levels (Advisory, Warning, Critical)
- Dismissible notification banner

**Priority:** MEDIUM | **Story Points:** 5

---

### US-006: Compare School Air Quality 🔮 PLANNED

**As a** parent  
**I want to** compare air quality between multiple schools  
**So that** I can make informed decisions about school selection

**Acceptance Criteria:**

- Side-by-side comparison of up to 3 schools
- Shows all pollutants (NO₂, NOx, PM2.5, PM10)
- Displays annual averages and current readings
- Export comparison as PDF

**Priority:** LOW | **Story Points:** 5

---

## Epic 3: Authentication & Access Control

### US-007: Subscribe for Access ✅ IMPLEMENTED

**As a** parent or school staff member  
**I want to** subscribe to access the full dashboard  
**So that** I can view detailed air quality data

**Acceptance Criteria:**

- Subscription page with clear pricing (£2.50/month)
- Secure Stripe payment integration
- Email confirmation after successful payment
- Immediate access to dashboard after subscription
- Free trial period (7 days)

**Priority:** HIGH | **Story Points:** 8

---

### US-008: User Login ✅ IMPLEMENTED

**As a** subscribed user  
**I want to** log in securely to access the dashboard  
**So that** my subscription is protected

**Acceptance Criteria:**

- Standard username/password login form
- Password validation and security requirements
- "Remember me" option
- Password reset functionality
- Redirect to map after successful login

**Priority:** HIGH | **Story Points:** 3

---

### US-009: Manage Subscription ✅ IMPLEMENTED

**As a** subscribed user  
**I want to** view and manage my subscription  
**So that** I can update payment details or cancel if needed

**Acceptance Criteria:**

- View current subscription status and renewal date
- Update payment method
- Cancel subscription option
- View payment history
- Download invoices

**Priority:** MEDIUM | **Story Points:** 5

---

## Epic 4: Data Management & Administration

### US-010: Admin - View All Schools ✅ IMPLEMENTED

**As a** system administrator  
**I want to** view and edit school data in the admin panel  
**So that** I can keep school information accurate and up-to-date

**Acceptance Criteria:**

- List view of all schools with filters
- Edit school details (name, address, contact info)
- Add new schools manually
- Bulk import from CSV
- View sensor assignments for each school

**Priority:** HIGH | **Story Points:** 5

---

### US-011: Admin - Manage Sensors ✅ IMPLEMENTED

**As a** system administrator  
**I want to** manage sensor data and assignments  
**So that** schools receive accurate pollution readings

**Acceptance Criteria:**

- List all LAQN and Breathe London sensors
- Mark sensors as active/inactive
- View sensor status and last reading timestamp
- Manually trigger sensor data refresh
- View which schools are assigned to each sensor

**Priority:** MEDIUM | **Story Points:** 5

---

### US-012: Admin - View Data Quality Metrics 🔮 PLANNED

**As a** system administrator  
**I want to** monitor data quality and API health  
**So that** I can ensure the platform provides reliable information

**Acceptance Criteria:**

- Dashboard showing API status (LAQN, Breathe London)
- Data completeness percentage per sensor
- Failed API call logs
- Sensor data gaps visualization
- Email alerts for API failures

**Priority:** MEDIUM | **Story Points:** 8

---

## Epic 5: Mobile & Accessibility

### US-013: Mobile-Responsive Map ✅ IMPLEMENTED

**As a** parent on mobile  
**I want to** view the school map on my phone  
**So that** I can check air quality while on the go

**Acceptance Criteria:**

- Map displays correctly on mobile devices (iOS, Android)
- Touch gestures work (pinch zoom, pan)
- Popup information readable on small screens
- Fast loading on 4G connection
- Works in both portrait and landscape

**Priority:** HIGH | **Story Points:** 5

---

### US-014: Accessible Interface 🔮 PLANNED

**As a** visually impaired user  
**I want to** use the platform with screen readers  
**So that** I can access air quality information independently

**Acceptance Criteria:**

- All images have alt text
- Proper ARIA labels on interactive elements
- Keyboard navigation support
- High contrast mode option
- WCAG 2.1 AA compliance

**Priority:** MEDIUM | **Story Points:** 5

---

## Epic 6: Data Sources & Integration

### US-015: Hybrid Data Approach ✅ IMPLEMENTED

**As a** data analyst  
**I want to** understand how the system combines LAEI, LAQN, and Breathe London data  
**So that** I can trust the accuracy of the readings

**Acceptance Criteria:**

- Documentation explains data methodology
- Each school shows its data source clearly
- Direct sensor readings preferred over modelled data
- LAEI baseline adjusted by LAQN when no direct sensor available
- Data source badge visible on map and school details

**Priority:** HIGH | **Story Points:** 13

---

### US-016: Automated Data Updates ✅ IMPLEMENTED

**As a** system administrator  
**I want to** air quality data to update automatically  
**So that** users always see current information without manual intervention

**Acceptance Criteria:**

- Cron job fetches sensor readings every hour
- Failed fetches retry up to 3 times
- TimescaleDB stores historical readings efficiently
- Stale data flagged if > 3 hours old
- Admin notification if data hasn't updated in 6 hours

**Priority:** HIGH | **Story Points:** 8

---

## Epic 7: Reporting & Analytics

### US-017: Export School Report 🔮 PLANNED

**As a** school administrator  
**I want to** export air quality reports for my school  
**So that** I can share data with governors and parents

**Acceptance Criteria:**

- PDF export with school logo and branding
- Last 30 days of pollution data
- Graphs showing trends
- Comparison to WHO guidelines
- Downloadable within 5 seconds

**Priority:** LOW | **Story Points:** 8

---

### US-018: View Historical Trends 🔮 PLANNED

**As a** parent  
**I want to** see how air quality has changed over time  
**So that** I can understand if conditions are improving or worsening

**Acceptance Criteria:**

- Line graph showing last 90 days
- Toggle between different pollutants
- Compare to previous year (if data available)
- Annotations for high pollution events
- Mobile-friendly chart

**Priority:** LOW | **Story Points:** 8

---

## Summary

**Total Stories:** 18  
**Total Story Points:** 112  
**High Priority:** 9 stories (61 points)  
**Medium Priority:** 6 stories (38 points)  
**Low Priority:** 3 stories (21 points)

---

## Definition of Done

A user story is considered "Done" when:

- ✅ All acceptance criteria met
- ✅ Code reviewed and merged
- ✅ Unit tests written and passing (>80% coverage)
- ✅ Manual testing completed on Chrome, Firefox, Safari
- ✅ Mobile responsive testing passed
- ✅ Documentation updated
- ✅ Deployed to staging environment
- ✅ Product Owner approval received

---

## Backlog Prioritization

### Sprint 1 (MVP - Weeks 1-2)

- US-001: View Interactive School Map
- US-002: View School Details
- US-010: Admin - View All Schools
- US-015: Hybrid Data Approach

### Sprint 2 (Real-Time Data - Weeks 3-4)

- US-004: View Real-Time Sensor Data
- US-016: Automated Data Updates
- US-011: Admin - Manage Sensors

### Sprint 3 (Subscription & Auth - Weeks 5-6)

- US-007: Subscribe for Access
- US-008: User Login
- US-009: Manage Subscription

### Sprint 4 (Polish & Extend - Weeks 7-8)

- US-003: Filter Schools by Air Quality
- US-005: Receive Air Quality Alerts
- US-013: Mobile-Responsive Map
- US-014: Accessible Interface

### Future Backlog

- US-006: Compare School Air Quality
- US-012: Admin - View Data Quality Metrics
- US-017: Export School Report
- US-018: View Historical Trends
