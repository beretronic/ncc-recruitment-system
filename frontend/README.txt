HOW TO USE THESE FILES
=======================

This is the COMPLETE frontend with separate Admin and HR dashboards, staff
account management, applicant account management, and a redesigned
CV-review-first flow for HR. Delete your entire frontend/src folder and
vite.config.ts, then copy everything in this zip into frontend/.

USE THIS TOGETHER WITH backend_rbac_complete.zip - this frontend calls
endpoints (/api/staff/..., /api/admin/...) that only exist in that backend
package.

WHAT'S NEW:

1. TWO SEPARATE DASHBOARDS
   - /hr/dashboard  -> HR Dashboard: vacancies (create/edit, no delete),
     analytics (status funnel, time-to-hire, top-candidates leaderboard),
     and applicant review.
   - /admin/dashboard -> Admin Dashboard: lightweight vacancy/applicant
     counts (no matching-score detail), HR/Admin account management
     (create new staff, suspend/reactivate), applicant account management
     (suspend/reactivate).
   - After login, you're automatically routed to the correct one based on
     your ACTUAL role (fetched from /api/staff/me/), not just "staff" in
     general. If an HR account somehow ends up at /admin/dashboard (or vice
     versa), they get redirected to their correct dashboard automatically.

2. CV-REVIEW-FIRST FLOW FOR HR
   Previously, each applicant row had a status dropdown you could change
   without ever opening their CV. Now: clicking an applicant row opens a
   review modal showing their CV inline FIRST, with status-change buttons,
   interview scheduling, and their audit history all inside that same
   modal - so a decision is made only after actually looking at the CV.
   Bulk status update (via checkboxes) is still available separately for
   batch operations that don't need individual review.

3. STAFF ACCOUNT MANAGEMENT (Admin only)
   Admin can create new HR (or Admin) accounts directly from the frontend
   - no more needing Django admin for this. Admin can also suspend/
   reactivate any HR/Admin account (soft delete - preserves their history,
   e.g. jobs they posted are untouched). An Admin cannot deactivate their
   own account (blocked, both frontend and backend).

4. APPLICANT ACCOUNT MANAGEMENT (Admin only)
   Admin can view all applicant accounts (verified status, active status,
   how many applications they've submitted) and suspend/reactivate one if
   needed.

RUN:
  npm run dev

FULL TEST WALKTHROUGH:

1. Log in as your existing Admin superuser. You should land on
   /admin/dashboard (not /hr/dashboard).
2. Confirm the summary cards show vacancy/applicant counts - no match
   scores anywhere on this page.
3. Click "HR / Admin Accounts" tab -> "+ Add account" -> create a new HR
   account (pick role "HR").
4. Click "Applicant Accounts" tab - you should see your test applicants,
   with a Suspend/Reactivate toggle.
5. Log out, log in as the NEW HR account you just created. You should land
   on /hr/dashboard - and NOT be able to navigate to /admin/dashboard (it
   will bounce you back to /hr/dashboard if you try).
6. On the HR Dashboard, expand a vacancy with applicants, click an
   applicant row - the CV should load inline in the modal, with action
   buttons and status history below it.
7. Change their status from inside the modal - confirm it updates, and
   the audit history updates live in the same modal.
8. Go back to Admin, try suspending that HR account you created - then
   try logging in as them again - login should now fail (Django blocks
   inactive users automatically).
9. Try having HR attempt to reach /admin/dashboard by typing the URL
   directly - confirm they're redirected, not shown an error page.

This completes the role-separation redesign - Admin and HR now have
genuinely different, purpose-built dashboards instead of sharing one page
with a permission check bolted on.
