# Future hosting notes (not deployed)

The current FastAPI server is intended to run locally. Supabase hosts the PostgreSQL database; it does not host this FastAPI web server. Public hosting is a separate future task.

Before deploying:

1. Choose a Python ASGI-compatible hosting provider after checking its current pricing, terms, region, networking, and persistent-environment-variable support.
2. Deploy the repository's FastAPI app with an ASGI server command such as `uvicorn web.main:app --host 0.0.0.0 --port $PORT`; do not use `--reload` in production.
3. Set `DATABASE_URL` to a server-side Supabase PostgreSQL connection URI and `SESSION_SECRET` to a newly generated, strong secret using the provider's private environment-variable settings. Never commit or expose these values.
4. Restrict database credentials to the minimum required access. Require encrypted connections to Supabase and check that the host's network can reach the chosen Supabase direct or pooled endpoint.
5. Put HTTPS in front of the app, set `COOKIE_SECURE=true`, and configure trusted proxy/forwarded-header behavior only for the actual hosting environment.
6. Run the read-only connection check and smoke-test login, role permissions, checkout, and reports after deployment. Confirm backups and operational monitoring before entering real data.

Do not run schema initialization or demo seeding implicitly in a deployment. Do not select a provider or assume a free tier without checking current terms. Do not publicly expose the development server.
