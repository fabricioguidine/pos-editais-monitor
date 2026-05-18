@echo off
REM ---------------------------------------------------------------------------
REM pos-editais-monitor - worker autostart (Windows)
REM Chamado pelo Task Scheduler no logon do usuario.
REM ---------------------------------------------------------------------------

cd /d "%~dp0.."

REM Garante que Docker subiu (PG/Redis precisam estar prontos)
REM Espera ate 90s; se nao subir, segue mesmo assim (worker vai logar erro)
set DOCKER_TRIES=0
:wait_docker
docker info >NUL 2>NUL
if %ERRORLEVEL%==0 goto docker_ok
set /a DOCKER_TRIES+=1
if %DOCKER_TRIES% GEQ 18 goto docker_ok
timeout /t 5 /nobreak >NUL
goto wait_docker
:docker_ok

REM Sobe os containers caso nao estejam (idempotente)
docker compose -f docker\docker-compose.yml up -d postgres redis smtp4dev >NUL 2>NUL

REM Aguarda PG ficar healthy (max ~60s)
set PG_TRIES=0
:wait_pg
docker exec pos-editais-monitor-postgres-1 pg_isready -U pem >NUL 2>NUL
if %ERRORLEVEL%==0 goto pg_ok
set /a PG_TRIES+=1
if %PG_TRIES% GEQ 12 goto pg_ok
timeout /t 5 /nobreak >NUL
goto wait_pg
:pg_ok

REM Env vars - ajuste aqui ou mantenha .env atualizado
REM (Estes overrides apontam para smtp4dev local. Para mailtrap, mudar host/port/user/pass.)
set PEM_SMTP_HOST=localhost
set PEM_SMTP_PORT=2525
set PEM_SMTP_USERNAME=
set PEM_SMTP_PASSWORD=
set PEM_SMTP_FROM=fabricioguidine@gmail.com
set PEM_NOTIFY_TO=fabricioguidine@gmail.com
set PEM_LLM_ENABLED=false
set PEM_LOG_FORMAT=json

REM Roda o worker (bloqueante - APScheduler em loop interno)
".venv\Scripts\pem.exe" worker >> "logs\worker.log" 2>&1
