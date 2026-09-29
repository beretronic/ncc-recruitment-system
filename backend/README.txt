HOW TO USE THESE FILES
=======================

This is the COMPLETE backend with the new account-management and
role-separation features. Copy every file into the matching location in
your project, overwriting what's there (complete drop-in):

  recruitment/*.py       -> backend/recruitment/
  ncc_recruitment/*.py   -> backend/ncc_recruitment/

WHAT'S NEW:

1. MODEL CHANGES (migration needed):
   - Applicant.is_active (default True) - lets Admin suspend/reactivate an
     applicant account. Login is now blocked for suspended accounts.
   - Job.updated_by / Job.updated_at - tracks who last edited a vacancy
     and when (accountability for HR's changes, per your request).

2. NEW ENDPOINTS (all Admin-only except staff/me/):
   GET  /api/staff/me/                    -> any logged-in staff member's
                                              own role (lets the frontend
                                              tell Admin and HR apart)
   GET  /api/staff/                       -> list all HR/Admin accounts
   POST /api/staff/                       -> create a new HR or Admin
                                              account (replaces having to
                                              use Django admin for this)
   PATCH /api/staff/<id>/                 -> activate/deactivate a staff
                                              account (soft delete - keeps
                                              their history intact), or
                                              change their role
                                              (cannot deactivate your own
                                              account - blocked server-side)

   GET  /api/admin/applicants/            -> list all applicant accounts
                                              with verification/active
                                              status and application counts
   PATCH /api/admin/applicants/<id>/      -> suspend/reactivate an
                                              applicant account

   GET  /api/admin/summary/               -> lightweight Admin dashboard
                                              data: vacancy counts,
                                              applicant counts, pending
                                              verifications, HR staff
                                              count. Deliberately does NOT
                                              include matching-score
                                              detail (that stays on the HR
                                              analytics dashboard).

3. Job create/edit responses now include updated_by_name and updated_at,
   so the frontend can show "last edited by X on Y" on a vacancy.

INSTALL / RUN:
  python manage.py makemigrations
  python manage.py migrate
  python manage.py runserver

The migration will ask you about a default for is_active on existing
Applicant rows if you already have some - answer with "1" for True (all
existing applicants stay active).

PERMISSION MODEL RECAP:
  - HR: create/edit vacancies, manage applications (status, interviews),
    fully autonomous - no Admin approval needed for any of this.
  - Admin: everything HR can do, PLUS: delete vacancies, manage HR/Admin
    accounts, manage applicant accounts. Admin's own dashboard is meant to
    stay lightweight (account oversight), not duplicate HR's detailed
    matching/analytics view.
